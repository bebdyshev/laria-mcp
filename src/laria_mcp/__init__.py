"""laria_mcp: serve a Jupyter notebook's functions as MCP tools for AI agents."""

from __future__ import annotations

from typing import Any, Callable, TypeVar

__version__ = "0.1.1"

TOOL_MARKER = "__laria_tool__"

F = TypeVar("F", bound=Callable[..., Any])


def tool(fn: F) -> F:
    """Mark a notebook function as an MCP tool.

    If any function in a notebook is marked, only marked functions are exposed.
    """
    setattr(fn, TOOL_MARKER, True)
    return fn


def load_ipython_extension(ipython: Any) -> None:
    """Enable `%laria` via `%load_ext laria_mcp`."""
    from laria_mcp.magic import load_ipython_extension as _load

    _load(ipython)


def unload_ipython_extension(ipython: Any) -> None:
    from laria_mcp.magic import unload_ipython_extension as _unload

    _unload(ipython)


__all__ = ["TOOL_MARKER", "__version__", "tool"]
