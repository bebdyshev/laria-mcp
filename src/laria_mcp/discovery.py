"""Find the notebook functions that should become MCP tools."""

from __future__ import annotations  # Does not function like a normal import. Tells Python that this script will reference classes before they were defined (and other features). Useful for older versions of Python.

import ast  # Abstract Syntax Tree, parses/analyzes python source code
import inspect  # analyzes live Python objects
from dataclasses import dataclass   # Helps create dunder methods like __init__ for you
from typing import Any, Callable, Iterable, Mapping     # Used for autocomplete features, and also improves readability of code

from laria_mcp import TOOL_MARKER


@dataclass(frozen=True) # frozen=True makes this "immutable after creation".
class ToolSpec:     # an object with the following attributes, create this object with ToolSpec(...)
    name: str
    fn: Callable[..., Any]
    description: str

# "lines" is the literal lines of source code.
def _is_marked(node: ast.FunctionDef, lines: list[str]) -> bool:    # returns bool for whether a defined function (ast.FunctionDef) is marked with a tool marker.
    for decorator in node.decorator_list:       # go through the decorators (top to bottom), excludes comments
        target = decorator.func if isinstance(decorator, ast.Call) else decorator   # ast.Call if callable/function, else uncertain ast object
        if isinstance(target, ast.Name) and target.id == "tool":    # if it is a variable (ast.Name) named "tool" (name str is stored in ast.Name.id)
            return True
        if isinstance(target, ast.Attribute) and target.attr == "tool":     # if the ending attribute is named "tool" (ending attribute name str is stored in ast.Attribute.attr)
            return True
    # If none of the decorators are markers, the code below runs to check for the comment marker "#@tool" instead:
    first_line = node.decorator_list[0].lineno if node.decorator_list else node.lineno # gets the first line number of the function definition including the decorators, the top decorator's line number if there are any decorators, otherwise the line number of def is used. Previously: min([d.lineno for d in node.decorator_list] + [node.lineno])
    if first_line >= 2:     # The first line is Line 1, which the marker can be on, so it is impossible for the function definition to have the comment marker if it's on Line 1. So we check >= 2. 
        # Python list indexes starts from zero (the variable "lines" is a list), however line numbers start from 1 (the variable "first_line"). So "first_line" is located at the index first_line-1 in "lines". The previous line's index in "lines" is therefore (first_line-1)-1. The comment marker must be directly before the function definition.
        previous = lines[first_line - 2].replace(" ", "")       # Ignore spaces
        if previous == "#@tool":        # if the previous line is the comment marker "#@tool"
            return True
    return False    # no marker matched


def _defined_functions(sources: Iterable[str]) -> tuple[list[str], set[str]]:
    names: list[str] = []
    nameset: set[str] = set()
    marked: set[str] = set()
    for source in sources:
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        lines = source.splitlines()
        for node in tree.body:  # for all ast objects/nodes in the top level (so excludes functions defined in functions etc.)
            if isinstance(node, ast.FunctionDef):
                if node.name not in nameset:
                    names.append(node.name)
                    nameset.add(node.name)
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
        selected = [name for name in names if not name.startswith("_")]     # if nothing is marked, ignore "private functions" (they start with "_")
    specs: list[ToolSpec] = []
    for name in selected:
        fn = namespace.get(name)
        if not inspect.isfunction(fn) or fn.__module__ != "__main__":   # if not user-defined function or if the function is imported
            continue
        if inspect.iscoroutinefunction(fn):     # ignore threading/coroutine functions
            continue
        description = inspect.getdoc(fn) or f"Notebook function {name}."
        specs.append(ToolSpec(name=name, fn=fn, description=description))
    return specs
