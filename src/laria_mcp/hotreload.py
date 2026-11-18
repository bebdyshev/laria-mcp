"""Re-discover tools after every executed cell and notify connected agents."""

from __future__ import annotations

from typing import Any, Callable, Optional

from laria_mcp.discovery import ToolSpec
from laria_mcp.server import LariaServer


class HotReloader:
    def __init__(
        self,
        shell: Any,
        server: LariaServer,
        rediscover: Callable[[], list[ToolSpec]],
        on_change: Optional[Callable[[list[str]], None]] = None,
    ) -> None:
        self.shell = shell
        self.server = server
        self.rediscover = rediscover
        self.on_change = on_change

    def start(self) -> None:
        self.shell.events.register("post_run_cell", self._on_post_run_cell)

    def stop(self) -> None:
        try:
            self.shell.events.unregister("post_run_cell", self._on_post_run_cell)
        except ValueError:
            pass

    def refresh(self) -> bool:
        changed = self.server.set_tools(self.rediscover())
        if changed:
            self.server.notify_tools_changed()
            if self.on_change is not None:
                self.on_change(self.server.tool_names)
        return changed

    def _on_post_run_cell(self, result: Any) -> None:
        if not result.success:
            return
        try:
            self.refresh()
        except Exception as exc:  # never break the user's notebook
            print(f"laria: hot reload failed: {type(exc).__name__}: {exc}")
