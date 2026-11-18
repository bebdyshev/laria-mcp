"""Convert Python return values into MCP content."""

from __future__ import annotations

import base64
import io
import json
import sys
from typing import Any, Union

from mcp import types

from laria_mcp.handles import HandleStore

MAX_TEXT = 4000
MAX_TABLE_ROWS = 50
PREVIEW_ROWS = 10
MAX_ARRAY_ITEMS = 100

Content = Union[types.TextContent, types.ImageContent]


def _text(text: str) -> types.TextContent:
    return types.TextContent(type="text", text=text)


def cap_text(text: str, limit: int = MAX_TEXT) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n... [truncated {len(text) - limit} chars]"


def _instance_of(value: Any, module: str, class_name: str) -> bool:
    loaded = sys.modules.get(module)
    cls = getattr(loaded, class_name, None) if loaded is not None else None
    return isinstance(cls, type) and isinstance(value, cls)


def markdown_table(df: Any) -> str:
    columns = [str(df.index.name or "")] + [str(c) for c in df.columns]

    def row(cells: list[str]) -> str:
        return "| " + " | ".join(c.replace("|", "\\|") for c in cells) + " |"

    lines = [row(columns), "|" + "---|" * len(columns)]
    for index, values in zip(df.index, df.itertuples(index=False)):
        lines.append(row([str(index)] + [str(v) for v in values]))
    return "\n".join(lines)


def _as_handle(value: Any, store: HandleStore, preview: str) -> list[Content]:
    handle = store.put(value)
    return [_text(f"Stored as handle {handle} (pass this string to other tools to use the object).\n{cap_text(preview)}")]


def _dataframe(df: Any, store: HandleStore) -> list[Content]:
    handle = store.put(df)
    rows, cols = df.shape
    if rows <= MAX_TABLE_ROWS:
        body = markdown_table(df)
    else:
        body = f"DataFrame with {rows} rows x {cols} columns. First {PREVIEW_ROWS} rows:\n" + markdown_table(
            df.head(PREVIEW_ROWS)
        )
    return [_text(f"{cap_text(body)}\n\nHandle: {handle}")]


def _figure(fig: Any) -> types.ImageContent:
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", bbox_inches="tight")
    data = base64.b64encode(buffer.getvalue()).decode("ascii")
    return types.ImageContent(type="image", data=data, mimeType="image/png")


def to_content(value: Any, store: HandleStore) -> list[Content]:
    """Turn a tool's return value into MCP content blocks."""
    if value is None:
        return [_text("(no return value)")]
    if isinstance(value, str):
        return [_text(cap_text(value))]
    if isinstance(value, (bool, int, float)):
        return [_text(json.dumps(value))]
    if isinstance(value, list) and value and all(
        isinstance(item, (types.TextContent, types.ImageContent)) for item in value
    ):
        return value
    if _instance_of(value, "pandas", "Series"):
        value = value.to_frame()
    if _instance_of(value, "pandas", "DataFrame"):
        return _dataframe(value, store)
    if _instance_of(value, "matplotlib.figure", "Figure"):
        return [_figure(value)]
    if _instance_of(value, "matplotlib.axes", "Axes"):
        return [_figure(value.figure)]
    if _instance_of(value, "numpy", "ndarray"):
        if value.size <= MAX_ARRAY_ITEMS:
            return [_text(json.dumps(value.tolist()))]
        return _as_handle(value, store, f"array shape={value.shape} dtype={value.dtype}\n{value!r}")
    if isinstance(value, (dict, list, tuple)):
        try:
            return [_text(cap_text(json.dumps(value, indent=2)))]
        except (TypeError, ValueError):
            pass
    return _as_handle(value, store, repr(value))
