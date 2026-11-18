"""MCP server that exposes notebook functions as tools."""

from __future__ import annotations

import asyncio
import contextlib
import inspect
import io
import json
import threading
import time
import traceback
from dataclasses import dataclass
from typing import Any, Callable, Optional

import uvicorn
from mcp import types
from mcp.server.lowlevel.server import NotificationOptions
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from pydantic import TypeAdapter

from laria_mcp.discovery import ToolSpec
from laria_mcp.handles import HandleStore, UnknownHandleError
from laria_mcp.results import cap_text, to_content


@dataclass
class CallEvent:
    tool: str
    args: dict[str, Any]
    status: str = "pending"
    duration_ms: float = 0.0
    preview: str = ""
    error: str = ""


Approver = Callable[[CallEvent], Optional[bool]]
CallListener = Callable[[CallEvent], None]


def _schema_ok(annotation: Any) -> bool:
    try:
        TypeAdapter(annotation).json_schema()
        return True
    except Exception:
        return False


def _json_ok(value: Any) -> bool:
    try:
        json.dumps(value)
        return True
    except (TypeError, ValueError):
        return False


def json_safe_signature(fn: Callable[..., Any]) -> inspect.Signature:
    """Signature the MCP SDK can turn into JSON schema; unknown types become `str` (handles)."""
    try:
        signature = inspect.signature(fn, eval_str=True)
    except Exception:
        signature = inspect.signature(fn)
    params = []
    for param in signature.parameters.values():
        if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
            continue
        annotation = param.annotation
        if annotation is not param.empty and not _schema_ok(annotation):
            annotation = str
        default = param.default
        if default is not param.empty and not _json_ok(default):
            default = None
        params.append(
            param.replace(kind=param.POSITIONAL_OR_KEYWORD, annotation=annotation, default=default)
        )
    return inspect.Signature(params)


def format_exception(exc: BaseException) -> str:
    frames = traceback.extract_tb(exc.__traceback__)[-5:]
    trace = "".join(traceback.format_list(frames))
    return f"{type(exc).__name__}: {exc}\nTraceback (most recent call last, trimmed):\n{trace}"


class LariaServer:
    def __init__(
        self,
        name: str = "laria",
        *,
        store: HandleStore | None = None,
        approver: Approver | None = None,
        listener: CallListener | None = None,
        token: str | None = None,
    ) -> None:
        self.name = name
        self.store = store or HandleStore()
        self.approver = approver
        self.listener = listener
        self.token = token
        self.mcp = FastMCP(name)
        self._lock = threading.Lock()
        self._fns: dict[str, Callable[..., Any]] = {}
        self._fingerprints: dict[str, tuple[str, str]] = {}
        self._sessions: list[tuple[Any, asyncio.AbstractEventLoop]] = []
        self._http: uvicorn.Server | None = None
        self._thread: threading.Thread | None = None
        self.http_url: str | None = None
        self._advertise_list_changed()
        self._track_sessions()

    @property
    def tool_names(self) -> list[str]:
        return list(self._fns)

    def set_tools(self, specs: list[ToolSpec]) -> bool:
        """Sync registered tools with `specs`. Returns True if the advertised list changed."""
        wanted = {spec.name: spec for spec in specs}
        changed = False
        for name in list(self._fns):
            if name not in wanted:
                self.mcp.remove_tool(name)
                del self._fns[name]
                del self._fingerprints[name]
                changed = True
        for name, spec in wanted.items():
            signature = json_safe_signature(spec.fn)
            fingerprint = (str(signature), spec.description)
            self._fns[name] = spec.fn
            if self._fingerprints.get(name) == fingerprint:
                continue
            if name in self._fingerprints:
                self.mcp.remove_tool(name)
            self.mcp.add_tool(self._make_tool(name, signature), name=name, description=spec.description)
            self._fingerprints[name] = fingerprint
            changed = True
        return changed

    def _make_tool(self, name: str, signature: inspect.Signature) -> Callable[..., Any]:
        def call(**kwargs: Any) -> Any:
            return self._invoke(name, kwargs)

        call.__name__ = name
        call.__signature__ = signature  # type: ignore[attr-defined]
        return call

    def _emit(self, event: CallEvent) -> None:
        if self.listener is None:
            return
        try:
            self.listener(event)
        except Exception:
            pass

    def _fail(self, event: CallEvent, status: str, message: str, started: float) -> ToolError:
        event.status = status
        event.error = message
        event.duration_ms = (time.perf_counter() - started) * 1000
        self._emit(event)
        return ToolError(message)

    def _invoke(self, name: str, kwargs: dict[str, Any]) -> list[Any]:
        event = CallEvent(tool=name, args=dict(kwargs))
        started = time.perf_counter()
        if self.approver is not None:
            decision = self.approver(event)
            if decision is not True:
                message = "Call denied by user" if decision is False else "Approval timed out"
                raise self._fail(event, "denied", message, started)
        captured = io.StringIO()
        try:
            with self._lock, contextlib.redirect_stdout(captured):
                value = self._fns[name](**self.store.resolve_args(kwargs))
                content = to_content(value, self.store)
        except UnknownHandleError as exc:
            raise self._fail(event, "error", str(exc), started) from None
        except Exception as exc:
            raise self._fail(event, "error", format_exception(exc), started) from None
        printed = captured.getvalue()
        if printed:
            content = list(content) + [types.TextContent(type="text", text="stdout:\n" + cap_text(printed))]
        event.status = "ok"
        event.duration_ms = (time.perf_counter() - started) * 1000
        first = content[0]
        event.preview = first.text[:300] if isinstance(first, types.TextContent) else "[image]"
        self._emit(event)
        return content

    def _advertise_list_changed(self) -> None:
        lowlevel = self.mcp._mcp_server
        original = lowlevel.create_initialization_options

        def options(notification_options=None, experimental_capabilities=None):
            return original(NotificationOptions(tools_changed=True), experimental_capabilities)

        lowlevel.create_initialization_options = options

    def _track_sessions(self) -> None:
        original = self.mcp.list_tools

        async def list_tools():
            self._remember_session()
            return await original()

        self.mcp._mcp_server.list_tools()(list_tools)

    def _remember_session(self) -> None:
        try:
            session = self.mcp.get_context().session
        except Exception:
            return
        if all(known is not session for known, _ in self._sessions):
            self._sessions.append((session, asyncio.get_running_loop()))

    def notify_tools_changed(self) -> None:
        """Tell connected clients to re-fetch the tool list. Safe to call from any thread."""
        try:
            running = asyncio.get_running_loop()
        except RuntimeError:
            running = None
        for session, loop in list(self._sessions):
            if loop.is_closed():
                self._sessions.remove((session, loop))
                continue
            coroutine = session.send_tool_list_changed()
            if loop is running:
                loop.create_task(coroutine)
            else:
                asyncio.run_coroutine_threadsafe(coroutine, loop)

    def _http_app(self) -> Any:
        app = self.mcp.streamable_http_app()
        if not self.token:
            return app
        expected = f"Bearer {self.token}".encode()

        async def require_token(scope, receive, send):
            if scope["type"] == "http" and dict(scope["headers"]).get(b"authorization") != expected:
                await send({"type": "http.response.start", "status": 401,
                            "headers": [(b"content-type", b"text/plain")]})
                await send({"type": "http.response.body", "body": b"unauthorized"})
                return
            await app(scope, receive, send)

        return require_token

    def start_http(self, host: str = "127.0.0.1", port: int = 8765) -> str:
        """Serve streamable HTTP on a background thread; return the endpoint URL."""
        if self._http is not None:
            raise RuntimeError(f"HTTP server already running at {self.http_url}")
        config = uvicorn.Config(self._http_app(), host=host, port=port, log_level="warning")
        server = uvicorn.Server(config)

        def run() -> None:
            try:
                asyncio.run(server.serve())
            except BaseException:  # uvicorn calls sys.exit(1) when it cannot bind
                pass

        thread = threading.Thread(target=run, name="laria-http", daemon=True)
        thread.start()
        deadline = time.monotonic() + 10
        while not server.started:
            if not thread.is_alive():
                raise OSError(f"Could not start server on {host}:{port} (is the port in use?)")
            if time.monotonic() > deadline:
                server.should_exit = True
                raise OSError(f"Timed out starting server on {host}:{port}")
            time.sleep(0.05)
        self._http, self._thread = server, thread
        self.http_url = f"http://{host}:{port}/mcp"
        return self.http_url

    def join_http(self) -> None:
        if self._thread is not None:
            self._thread.join()

    def stop_http(self) -> None:
        if self._http is None:
            return
        self._http.should_exit = True
        if self._thread is not None:
            self._thread.join(timeout=5)
        self._http = None
        self._thread = None
        self._sessions.clear()
        self.http_url = None

    def run_stdio(self) -> None:
        """Serve over stdin/stdout until the client disconnects (blocking)."""
        self.mcp.run("stdio")
