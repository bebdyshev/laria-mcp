"""Notebook panel that shows agent tool calls and asks for approval."""

from __future__ import annotations

import html
import threading
from typing import Optional

import ipywidgets as widgets

from laria_mcp.server import CallEvent

_ICONS = {"ok": "✅", "error": "❌", "denied": "🚫", "pending": "⏳"}


def _call_text(event: CallEvent) -> str:
    args = ", ".join(f"{key}={value!r}" for key, value in event.args.items())
    return f"{event.tool}({args})"


class CallLog:
    def __init__(self, max_rows: int = 50) -> None:
        self.max_rows = max_rows
        self.header = widgets.HTML()
        self.rows = widgets.VBox([])
        self.widget = widgets.VBox([self.header, self.rows])
        self._lock = threading.Lock()
        self.set_status("not serving")

    def set_status(self, text: str) -> None:
        self.header.value = f"<b>☤ laria</b> — {html.escape(text)}"

    def _append(self, child: widgets.Widget) -> None:
        with self._lock:
            self.rows.children = (self.rows.children + (child,))[-self.max_rows :]

    @staticmethod
    def format_event(event: CallEvent) -> str:
        icon = _ICONS.get(event.status, "•")
        detail = (event.error or event.preview)[:300]
        return (
            f"<code>{icon} {html.escape(_call_text(event))}</code> "
            f"<span style='color:gray'>{event.duration_ms:.0f} ms</span>"
            f"<pre style='margin:0 0 4px 1.5em;white-space:pre-wrap'>{html.escape(detail)}</pre>"
        )

    def record(self, event: CallEvent) -> None:
        self._append(widgets.HTML(self.format_event(event)))

    def request_approval(self, event: CallEvent, timeout: float = 60.0) -> Optional[bool]:
        done = threading.Event()
        decision: dict[str, bool] = {}
        label = widgets.HTML(f"🤖 Agent wants to call <code>{html.escape(_call_text(event))}</code>")
        approve = widgets.Button(description="Approve", button_style="success")
        deny = widgets.Button(description="Deny", button_style="danger")

        def choose(value: bool):
            def handler(_button: widgets.Button) -> None:
                if not done.is_set():
                    decision["value"] = value
                    done.set()

            return handler

        approve.on_click(choose(True))
        deny.on_click(choose(False))
        self._append(widgets.HBox([label, approve, deny]))
        finished = done.wait(timeout)
        approve.disabled = True
        deny.disabled = True
        result = decision.get("value") if finished else None
        label.value += {True: " — approved", False: " — denied", None: " — timed out"}[result]
        return result
