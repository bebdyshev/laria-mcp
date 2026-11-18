"""Find the notebook functions that should become MCP tools."""

from __future__ import annotations

import ast
import inspect
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping

from laria_mcp import TOOL_MARKER


@dataclass(frozen=True)
class ToolSpec:
    name: str
    fn: Callable[..., Any]
    description: str


def _is_marked(node: ast.FunctionDef, lines: list[str]) -> bool:
    for decorator in node.decorator_list:
        target = decorator.func if isinstance(decorator, ast.Call) else decorator
        if isinstance(target, ast.Name) and target.id == "tool":
            return True
        if isinstance(target, ast.Attribute) and target.attr == "tool":
            return True
    first_line = min([d.lineno for d in node.decorator_list] + [node.lineno])
    if first_line >= 2:
        previous = lines[first_line - 2].replace(" ", "")
        if previous == "#@tool":
            return True
    return False


def _defined_functions(sources: Iterable[str]) -> tuple[list[str], set[str]]:
    names: list[str] = []
    marked: set[str] = set()
    for source in sources:
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        lines = source.splitlines()
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                if node.name not in names:
                    names.append(node.name)
                if _is_marked(node, lines):
                    marked.add(node.name)
    return names, marked


def discover(sources: Iterable[str], namespace: Mapping[str, Any]) -> list[ToolSpec]:
    """Return tool specs for functions defined in `sources` and present in `namespace`."""
    names, marked = _defined_functions(sources)
    marked |= {name for name in names if getattr(namespace.get(name), TOOL_MARKER, False)}
    if marked:
        selected = [name for name in names if name in marked]
    else:
        selected = [name for name in names if not name.startswith("_")]
    specs: list[ToolSpec] = []
    for name in selected:
        fn = namespace.get(name)
        if not inspect.isfunction(fn) or fn.__module__ != "__main__":
            continue
        if inspect.iscoroutinefunction(fn):
            continue
        description = inspect.getdoc(fn) or f"Notebook function {name}."
        specs.append(ToolSpec(name=name, fn=fn, description=description))
    return specs
