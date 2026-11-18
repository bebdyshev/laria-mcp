"""laria_mcp: serve a Jupyter notebook's functions as MCP tools for AI agents."""

from __future__ import annotations

from typing import Any, Callable, TypeVar

__version__ = "0.1.0"

TOOL_MARKER = "__laria_tool__"

F = TypeVar("F", bound=Callable[..., Any])


def tool(fn: F) -> F:
    """Mark a notebook function as an MCP tool.

    If any function in a notebook is marked, only marked functions are exposed.
    """
    setattr(fn, TOOL_MARKER, True)
    return fn


__all__ = ["TOOL_MARKER", "__version__", "tool"]
