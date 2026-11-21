"""`%laria` line magic: serve the live kernel's functions over MCP."""

from __future__ import annotations

import argparse
import shlex
from pathlib import Path
from typing import Any, Mapping, Optional

from IPython.core.magic import Magics, line_magic, magics_class
from IPython.display import display

from laria_mcp import hermes
from laria_mcp.cli import serve_name
from laria_mcp.hotreload import HotReloader
from laria_mcp.discovery import ToolSpec, discover
from laria_mcp.notebook_tool import build_notebook_tool
from laria_mcp.server import LariaServer
from laria_mcp.widget import CallLog


def detect_notebook(user_ns: Mapping[str, Any]) -> Optional[Path]:
    for key in ("__session__", "__vsc_ipynb_file__"):
        value = user_ns.get(key)
        if isinstance(value, str) and value.endswith(".ipynb"):
            for candidate in (Path(value), Path.cwd() / Path(value).name):
                if candidate.exists():
                    return candidate.resolve()
    return None


class LiveSession:
    def __init__(
        self,
        shell: Any,
        *,
        name: str,
        port: int,
        token: Optional[str],
        approve: bool,
        approval_timeout: float,
        notebook: Optional[Path],
        notebook_timeout: int,
    ) -> None:
        self.shell = shell
        self.port = port
        self.log = CallLog()
        approver = (lambda event: self.log.request_approval(event, timeout=approval_timeout)) if approve else None
        self.server = LariaServer(name, approver=approver, listener=self.log.record, token=token)
        self.notebook_spec = build_notebook_tool(notebook, timeout=notebook_timeout) if notebook else None
        self.url: Optional[str] = None
        self.reloader = HotReloader(shell, self.server, self.specs, on_change=self._on_tools_changed)

    def _on_tools_changed(self, names: list[str]) -> None:
        tools=", ".join(names) or "(none)"
        self.log.set_status(f"serving {len(names)} tools at {self.url} (updated: {tools})")

    def specs(self) -> list[ToolSpec]:
        specs = discover(self.shell.user_ns.get("In", []), self.shell.user_ns)
        if self.notebook_spec is not None:
            specs.append(self.notebook_spec)
        return specs

    def start(self) -> str:
        self.server.set_tools(self.specs())
        self.url = self.server.start_http(port=self.port)
        self.log.set_status(f"serving {len(self.server.tool_names)} tools at {self.url}")
        self.reloader.start()
        return self.url

    def stop(self) -> None:
        self.reloader.stop()
        self.server.stop_http()
        self.log.set_status("stopped")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="%laria", add_help=True)
    commands = parser.add_subparsers(dest="command", required=True)
    serve = commands.add_parser("serve")
    serve.add_argument("--port", type=int, default=8765)
    serve.add_argument("--token", default=None)
    serve.add_argument("--approve", action="store_true")
    serve.add_argument("--approval-timeout", type=float, default=60.0)
    serve.add_argument("--notebook", default=None)
    serve.add_argument("--notebook-timeout", type=int, default=600)
    serve.add_argument("--name", default=None)
    commands.add_parser("stop")
    commands.add_parser("status")
    return parser


@magics_class
class LariaMagics(Magics):
    session: Optional[LiveSession] = None

    @line_magic
    def laria(self, line: str) -> None:
        """%laria serve|stop|status — serve this kernel's functions as MCP tools."""
        try:
            args = _parser().parse_args(shlex.split(line))
        except SystemExit:
            return None
        getattr(self, f"_{args.command}")(args)
        return None

    def _serve(self, args: argparse.Namespace) -> None:
        if self.session is not None:
            print(f"Already serving at {self.session.url}. Run %laria stop first.")
            return
        notebook = Path(args.notebook).resolve() if args.notebook else detect_notebook(self.shell.user_ns)
        name = args.name or (serve_name(notebook) if notebook else "notebook")
        session = LiveSession(
            self.shell,
            name=name,
            port=args.port,
            token=args.token,
            approve=args.approve,
            approval_timeout=args.approval_timeout,
            notebook=notebook,
            notebook_timeout=args.notebook_timeout,
        )
        display(session.log.widget)
        try:
            url = session.start()
        except OSError as exc:
            session.log.set_status("failed to start")
            print(f"{exc}. Try %laria serve --port <other port>.")
            return
        self.session = session
        timeout = args.notebook_timeout + 30 if session.notebook_spec else None
        entry = hermes.http_entry(url, token=args.token, timeout=timeout)
        tools=', '.join(session.server.tool_names) or "(none)"
        print(f"Serving {len(session.server.tool_names)} tools: {tools}")
        print("Add this to ~/.hermes/config.yaml, then run /reload-mcp in Hermes:\n")
        print(hermes.to_yaml(name, entry))

    def _stop(self, args: argparse.Namespace) -> None:
        if self.session is None:
            print("Not serving.")
            return
        self.session.stop()
        self.session = None
        print("Stopped.")

    def _status(self, args: argparse.Namespace) -> None:
        if self.session is None:
            print("Not serving.")
            return
        tools = ", ".join(self.session.server.tool_names) or "(none)"
        print(f"serving at {self.session.url}: {tools}")


def load_ipython_extension(ipython: Any) -> None:
    ipython.register_magics(LariaMagics)


def unload_ipython_extension(ipython: Any) -> None:
    magics = ipython.magics_manager.registry.get("LariaMagics")
    if magics is not None and magics.session is not None:
        magics.session.stop()
        magics.session = None
