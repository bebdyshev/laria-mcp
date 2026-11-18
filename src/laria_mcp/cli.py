"""Command-line interface: `laria serve` and `laria hermes-config`."""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

from laria_mcp import hermes
from laria_mcp.discovery import discover
from laria_mcp.notebook_tool import build_notebook_tool
from laria_mcp.loader import NotebookLoadError, load_notebook
from laria_mcp.server import LariaServer


def _log(message: str) -> None:
    print(f"laria: {message}", file=sys.stderr, flush=True)


def serve_name(path: Path) -> str:
    return re.sub(r"[^a-z0-9]+", "_", path.stem.lower()).strip("_") or "notebook"


def cmd_serve(args: argparse.Namespace) -> int:
    os.environ.setdefault("MPLBACKEND", "Agg")
    path = Path(args.notebook).resolve()
    if not path.exists():
        _log(f"notebook not found: {path}")
        return 1
    os.chdir(path.parent)
    try:
        loaded = load_notebook(path, stdout=sys.stderr)
    except NotebookLoadError as exc:
        _log(str(exc))
        return 1
    specs = discover(loaded.sources, loaded.namespace)
    if not args.no_notebook_tool:
        notebook_spec = build_notebook_tool(path, timeout=args.notebook_timeout)
        if notebook_spec is not None:
            specs.append(notebook_spec)
    server = LariaServer(args.name or serve_name(path), token=args.token)
    server.set_tools(specs)
    _log(f"serving {len(specs)} tools: {', '.join(s.name for s in specs) or '(none)'}")
    if args.http:
        try:
            url = server.start_http(port=args.port)
        except OSError as exc:
            _log(str(exc))
            return 1
        _log(f"listening on {url} (Ctrl+C to stop)")
        try:
            server.join_http()
        except KeyboardInterrupt:
            server.stop_http()
    else:
        server.run_stdio()
    return 0


def cmd_hermes_config(args: argparse.Namespace) -> int:
    path = Path(args.notebook).resolve()
    name = args.name or serve_name(path)
    if args.live:
        entry = hermes.http_entry(f"http://127.0.0.1:{args.port}/mcp", token=args.token, timeout=args.timeout)
    else:
        entry = hermes.stdio_entry(path, timeout=args.timeout)
    if args.print:
        print(hermes.to_yaml(name, entry), end="")
        return 0
    written = hermes.write_config(name, entry, Path(args.config))
    _log(f"added '{name}' to {written}. In Hermes run /reload-mcp (or restart Hermes).")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="laria", description="Serve a Jupyter notebook as MCP tools.")
    commands = parser.add_subparsers(dest="command", required=True)

    serve = commands.add_parser("serve", help="Serve a notebook's functions as MCP tools.")
    serve.add_argument("notebook", help="Path to the .ipynb file")
    serve.add_argument("--http", action="store_true", help="Serve over HTTP instead of stdio")
    serve.add_argument("--port", type=int, default=8765)
    serve.add_argument("--token", default=None, help="Require 'Authorization: Bearer <token>' (HTTP only)")
    serve.add_argument("--name", default=None, help="Server name shown to agents")
    serve.add_argument("--notebook-timeout", type=int, default=600, help="Per-cell timeout for run_<notebook>")
    serve.add_argument("--no-notebook-tool", action="store_true", help="Do not expose run_<notebook>")
    serve.set_defaults(func=cmd_serve)
    config = commands.add_parser("hermes-config", help="Add this notebook to Hermes Agent's MCP config.")
    config.add_argument("notebook", help="Path to the .ipynb file")
    config.add_argument("--live", action="store_true", help="Point Hermes at a live %%laria serve session")
    config.add_argument("--port", type=int, default=8765)
    config.add_argument("--token", default=None)
    config.add_argument("--name", default=None)
    config.add_argument("--timeout", type=int, default=None, help="Per-call timeout in seconds for Hermes")
    config.add_argument("--config", default=str(hermes.DEFAULT_CONFIG), help="Hermes config file")
    config.add_argument("--print", action="store_true", help="Print YAML instead of writing the file")
    config.set_defaults(func=cmd_hermes_config)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)
