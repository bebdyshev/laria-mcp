"""Expose a whole notebook (papermill-style `parameters` cell) as one MCP tool."""

from __future__ import annotations

import ast
import inspect
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import nbformat
from mcp import types
from nbclient import NotebookClient
from nbclient.exceptions import CellExecutionError, CellTimeoutError

from laria_mcp.discovery import ToolSpec
from laria_mcp.results import cap_text

MAX_OUTPUT_TEXT = 8000
MAX_IMAGES = 5


class NotebookRunError(Exception):
    pass


@dataclass(frozen=True)
class Parameter:
    name: str
    default: Any
    annotation: Any


def find_parameters_cell(nb: nbformat.NotebookNode) -> Optional[int]:
    for index, cell in enumerate(nb.cells):
        if cell.cell_type == "code" and "parameters" in cell.get("metadata", {}).get("tags", []):
            return index
    return None


def parse_parameters(source: str) -> list[Parameter]:
    params: list[Parameter] = []
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name, value_node = node.targets[0].id, node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.value is not None:
            name, value_node = node.target.id, node.value
        else:
            continue
        try:
            value = ast.literal_eval(value_node)
        except ValueError:
            continue
        params.append(Parameter(name, value, Any if value is None else type(value)))
    return params


def notebook_tool_name(path: Path) -> str:
    stem = re.sub(r"[^a-z0-9]+", "_", Path(path).stem.lower()).strip("_") or "notebook"
    return f"run_{stem}"


def _collect(cells: list[nbformat.NotebookNode]) -> list[Any]:
    texts: list[str] = []
    images: list[types.ImageContent] = []
    for cell in cells:
        for output in cell.get("outputs", []):
            kind = output.get("output_type")
            if kind == "stream":
                texts.append(output.get("text", ""))
            elif kind in ("execute_result", "display_data"):
                data = output.get("data", {})
                if "image/png" in data and len(images) < MAX_IMAGES:
                    images.append(types.ImageContent(type="image", data=data["image/png"], mimeType="image/png"))
                elif "text/plain" in data:
                    texts.append(data["text/plain"] + "\n")
    text = cap_text("".join(texts).strip() or "(notebook produced no text output)", MAX_OUTPUT_TEXT)
    return [types.TextContent(type="text", text=text), *images]


def run_notebook(path: Path, values: dict[str, Any], *, timeout: int = 600) -> list[Any]:
    path = Path(path)
    nb = nbformat.read(path, as_version=4)
    index = find_parameters_cell(nb)
    if index is None:
        raise NotebookRunError(f"{path.name} has no cell tagged 'parameters'")
    injected = "# Parameters injected by laria\n" + "\n".join(f"{k} = {v!r}" for k, v in values.items())
    nb.cells.insert(index + 1, nbformat.v4.new_code_cell(injected, metadata={"tags": ["injected-parameters"]}))
    kernel = nb.metadata.get("kernelspec", {}).get("name", "python3")
    client = NotebookClient(nb, timeout=timeout, kernel_name=kernel, resources={"metadata": {"path": str(path.parent)}})
    try:
        client.execute()
    except CellTimeoutError as exc:
        raise NotebookRunError(f"A cell exceeded the {timeout}s timeout: {exc}") from None
    except CellExecutionError as exc:
        raise NotebookRunError(f"{exc.ename}: {exc.evalue}") from None
    return _collect(nb.cells[index + 2 :])


def build_notebook_tool(path: Path, *, timeout: int = 600) -> Optional[ToolSpec]:
    path = Path(path).resolve()
    nb = nbformat.read(path, as_version=4)
    index = find_parameters_cell(nb)
    if index is None:
        return None
    params = parse_parameters(nb.cells[index].source)
    name = notebook_tool_name(path)

    def run(**values: Any) -> list[Any]:
        merged = {p.name: values.get(p.name, p.default) for p in params}
        return run_notebook(path, merged, timeout=timeout)

    run.__name__ = name
    run.__signature__ = inspect.Signature(  # type: ignore[attr-defined]
        [inspect.Parameter(p.name, inspect.Parameter.POSITIONAL_OR_KEYWORD, default=p.default, annotation=p.annotation)
         for p in params]
    )
    listed = ", ".join(f"{p.name} (default {p.default!r})" for p in params) or "none"
    description = (
        f"Re-run the whole notebook {path.name} with new parameter values and return its outputs "
        f"(printed text, results and charts). Parameters: {listed}."
    )
    return ToolSpec(name=name, fn=run, description=description)
