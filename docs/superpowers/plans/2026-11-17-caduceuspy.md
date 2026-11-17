# caduceuspy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship `caduceuspy`, a PyPI package that serves a Jupyter notebook's functions as MCP tools (CLI and live-kernel modes), with hot reload, a call-log widget, approval mode, object handles, whole-notebook-as-a-tool, and Hermes config generation.

**Architecture:** A notebook is executed (headless IPython shell for files, or the live kernel), functions are discovered with `ast`, and each one is wrapped and registered on an MCP `FastMCP` server (official `mcp` SDK 1.x). The wrapper handles approval, handle resolution, stdout capture, error formatting and result conversion. Live mode runs the server over streamable HTTP on a background thread and shows calls in an ipywidgets panel.

**Tech Stack:** Python ≥3.10, `mcp` 1.x (`FastMCP`), `nbformat`, `nbclient`, `IPython`, `ipywidgets`, `PyYAML`, `uvicorn` (via `mcp`), `pytest` + `anyio` pytest plugin, hatchling, GitHub Actions, Jupyter Book 1.x.

Spec: `docs/superpowers/specs/2026-11-17-caduceuspy-design.md`

## Global Constraints

- Distribution name `caduceuspy`; import package `caduceuspy`; CLI command `caduceus`; magic `%caduceus`. Never use the import name `caduceus` (taken by an unrelated PyPI package).
- `requires-python = ">=3.10"`.
- Runtime dependencies exactly: `mcp>=1.20,<2`, `nbformat>=5.9`, `nbclient>=0.10`, `ipython>=8.12`, `ipywidgets>=8`, `pyyaml>=6`. `mcp>=1.20` is required for `FastMCP.remove_tool`; `<2` because mcp 2.x renamed `FastMCP` and the course JupyterHub / Hermes use 1.x.
- `pandas`, `numpy`, `matplotlib` are optional: detect via `sys.modules`, never import them at module top level in `src/`.
- The package contains no LLM client and makes no LLM/API calls.
- HTTP server binds `127.0.0.1` only. Default port `8765`. Endpoint path `/mcp`.
- Text results are capped at 4000 characters; DataFrame tables show at most 50 rows (preview 10 rows when larger).
- Approval timeout default 60 s. Whole-notebook per-cell timeout default 600 s.
- Repo: `https://github.com/bebdyshev/cs1302a-project` (public). Docs: `https://bebdyshev.github.io/cs1302a-project/`.
- Every commit message ends with the team's normal attribution (no special trailer required). Each owner commits their own tasks from their own GitHub account (teamwork rubric).

## File Structure

```
pyproject.toml                         # Task 1
README.md                              # Task 1 (stub), Task 15 (full)
LICENSE                                # Task 1
.gitignore                             # Task 1
.github/workflows/ci.yml               # Task 1
.github/workflows/release.yml          # Task 9
.github/workflows/docs.yml             # Task 15
src/caduceuspy/__init__.py             # Task 1 (tool decorator, version), Task 13 (extension hook)
src/caduceuspy/__main__.py             # Task 8
src/caduceuspy/loader.py               # Task 2
src/caduceuspy/discovery.py            # Task 3
src/caduceuspy/handles.py              # Task 4
src/caduceuspy/results.py              # Task 5
src/caduceuspy/server.py               # Task 6, Task 7
src/caduceuspy/cli.py                  # Task 8, Task 11, Task 12
src/caduceuspy/widget.py               # Task 10
src/caduceuspy/hermes.py               # Task 11
src/caduceuspy/notebook_tool.py        # Task 12
src/caduceuspy/magic.py                # Task 13, Task 14
src/caduceuspy/hotreload.py            # Task 14
tests/conftest.py                      # Task 1 (make_notebook fixture, anyio backend, free_port)
tests/test_*.py                        # one per module
examples/make_examples.py              # Task 15
examples/sales_demo.ipynb              # Task 15 (generated)
docs/                                  # Task 15 (Jupyter Book)
docs/demo-script.md                    # Task 16
```

## Owners and order

| Task | Owner | Day |
|---|---|---|
| 1 Scaffold | Kerey | 1 |
| 2 Loader | Member 6 | 1 |
| 3 Discovery | Member 6 | 1 |
| 4 Handles | Bibek | 1 |
| 5 Results | Bibek | 1–2 |
| 6 Server core | Bibek | 1–2 |
| 7 Server notifications + HTTP | Bibek | 2 |
| 8 CLI `serve` | Daniil | 1 |
| 9 Release v0.1.0 | Kerey | 1 |
| 10 Widget | Vladan | 2–3 |
| 11 Hermes config | Daniil | 2 |
| 12 Notebook tool | Daniil | 3–4 |
| 13 Magic (live mode) | Matthias | 2–3 |
| 14 Hot reload | Matthias | 3 |
| 15 Docs + examples | Kerey | 3–4 |
| 16 JupyterHub/Hermes verification + demo | Daniil + all | 4–5 |

Tasks 2, 4 and 10 can start in parallel right after Task 1. Task 6 needs 3, 4, 5. Task 8 needs 2, 3, 6.

## Dev setup (everyone, once)

```bash
git clone https://github.com/bebdyshev/cs1302a-project.git
cd cs1302a-project
uv venv -p 3.12 && source .venv/bin/activate
uv pip install -e ".[dev]"
pytest -q
```

---

### Task 1: Project scaffold (Kerey)

**Files:**
- Create: `pyproject.toml`, `README.md`, `LICENSE`, `.gitignore`, `.github/workflows/ci.yml`, `src/caduceuspy/__init__.py`, `tests/conftest.py`, `tests/test_package.py`

**Interfaces:**
- Produces: `caduceuspy.__version__: str`; `caduceuspy.TOOL_MARKER = "__caduceus_tool__"`; `caduceuspy.tool(fn) -> fn` (sets `fn.__caduceus_tool__ = True`).
- Produces test fixtures: `make_notebook(cells) -> Path` where each cell is a `str` (code) or `(str, list[str])` (code, tags); `free_port() -> int`; `anyio_backend` = `"asyncio"`; session-scoped `ip` (shared IPython test shell).

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[build-system]
requires = ["hatchling>=1.25"]
build-backend = "hatchling.build"

[project]
name = "caduceuspy"
dynamic = ["version"]
description = "Serve a Jupyter notebook's functions as MCP tools for AI agents such as Hermes and Claude."
readme = "README.md"
requires-python = ">=3.10"
license = "MIT"
license-files = ["LICENSE"]
authors = [{ name = "group27 (cs1302a)" }]
keywords = ["jupyter", "notebook", "mcp", "model-context-protocol", "agents", "hermes", "llm-tools"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Framework :: Jupyter",
    "Intended Audience :: Developers",
    "Intended Audience :: Science/Research",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]
dependencies = [
    "mcp>=1.20,<2",
    "nbformat>=5.9",
    "nbclient>=0.10",
    "ipython>=8.12",
    "ipywidgets>=8",
    "pyyaml>=6",
]

[project.optional-dependencies]
dev = ["pytest>=8", "ipykernel>=6", "pandas>=2", "numpy>=1.24", "matplotlib>=3.7", "httpx>=0.27"]

[project.urls]
Homepage = "https://github.com/bebdyshev/cs1302a-project"
Documentation = "https://bebdyshev.github.io/cs1302a-project/"
Issues = "https://github.com/bebdyshev/cs1302a-project/issues"

[project.scripts]
caduceus = "caduceuspy.cli:main"

[tool.hatch.version]
path = "src/caduceuspy/__init__.py"

[tool.hatch.build.targets.wheel]
packages = ["src/caduceuspy"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: Create `LICENSE` (MIT), `.gitignore`, `README.md` stub**

`LICENSE`: standard MIT text with `Copyright (c) 2026 group27 (cs1302a)`.

`.gitignore`:

```
__pycache__/
*.egg-info/
.venv/
dist/
build/
.pytest_cache/
docs/_build/
.ipynb_checkpoints/
```

`README.md`:

```markdown
# caduceuspy

Turn a Jupyter notebook into an MCP server, so AI agents (Hermes, Claude, ...) can call its functions as tools.

    pip install caduceuspy
    caduceus serve analysis.ipynb

Full documentation: https://bebdyshev.github.io/cs1302a-project/
```

- [ ] **Step 3: Write the failing test `tests/test_package.py`**

```python
import caduceuspy


def test_version_is_set():
    assert caduceuspy.__version__ == "0.1.0"


def test_tool_decorator_marks_and_returns_same_function():
    def f(x: int) -> int:
        return x

    marked = caduceuspy.tool(f)
    assert marked is f
    assert getattr(f, caduceuspy.TOOL_MARKER) is True
```

- [ ] **Step 4: Create `tests/conftest.py`**

```python
from __future__ import annotations

import socket
from pathlib import Path
from typing import Callable, Sequence, Union

import nbformat
import pytest
from nbformat.v4 import new_code_cell, new_notebook

Cell = Union[str, tuple[str, list[str]]]


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def make_notebook(tmp_path: Path) -> Callable[..., Path]:
    """Write a notebook from code strings or (code, tags) tuples; return its path."""

    def _make(cells: Sequence[Cell], name: str = "nb.ipynb") -> Path:
        nb = new_notebook()
        nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
        for cell in cells:
            if isinstance(cell, tuple):
                source, tags = cell
                nb.cells.append(new_code_cell(source, metadata={"tags": tags}))
            else:
                nb.cells.append(new_code_cell(cell))
        path = tmp_path / name
        nbformat.write(nb, path)
        return path

    return _make


@pytest.fixture
def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def ip():
    """One IPython shell shared by all tests (start_ipython returns None after the first call)."""
    import IPython
    from IPython.testing.globalipapp import start_ipython

    return start_ipython() or IPython.get_ipython()
```

- [ ] **Step 5: Run the test to verify it fails**

Run: `pytest tests/test_package.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'caduceuspy'` (or install error because `src/caduceuspy` does not exist).

- [ ] **Step 6: Create `src/caduceuspy/__init__.py`**

```python
"""caduceuspy: serve a Jupyter notebook's functions as MCP tools for AI agents."""

from __future__ import annotations

from typing import Any, Callable, TypeVar

__version__ = "0.1.0"

TOOL_MARKER = "__caduceus_tool__"

F = TypeVar("F", bound=Callable[..., Any])


def tool(fn: F) -> F:
    """Mark a notebook function as an MCP tool.

    If any function in a notebook is marked, only marked functions are exposed.
    """
    setattr(fn, TOOL_MARKER, True)
    return fn


__all__ = ["TOOL_MARKER", "__version__", "tool"]
```

- [ ] **Step 7: Install and run tests**

Run: `uv pip install -e ".[dev]" && pytest tests/test_package.py -v`
Expected: 2 passed.

- [ ] **Step 8: Create `.github/workflows/ci.yml`**

```yaml
name: CI
on:
  push:
    branches: [main]
  pull_request:
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - run: pip install -e ".[dev]"
      - run: pytest -q
```

- [ ] **Step 9: Commit and push**

```bash
git add pyproject.toml README.md LICENSE .gitignore .github/workflows/ci.yml src/caduceuspy/__init__.py tests/conftest.py tests/test_package.py
git commit -m "chore: scaffold caduceuspy package with tool decorator and CI"
git push origin main
```

---

### Task 2: Notebook loader (Member 6)

**Files:**
- Create: `src/caduceuspy/loader.py`
- Test: `tests/test_loader.py`

**Interfaces:**
- Consumes: `make_notebook` fixture (Task 1).
- Produces:
  - `class NotebookLoadError(Exception)` with attributes `cell_number: int` (1-based, counting all cells) and `error: BaseException`; `str()` is `"Cell {n} failed: {Type}: {message}"`.
  - `@dataclass LoadedNotebook(path: Path, namespace: dict[str, Any], sources: list[str], notebook: nbformat.NotebookNode)`. `sources` = IPython-transformed (pure Python) code of each executed code cell.
  - `load_notebook(path: str | Path, *, stdout: TextIO | None = None) -> LoadedNotebook`. Prints from cells go to `stdout` (default: discarded). Does **not** change the working directory (the CLI does that).

- [ ] **Step 1: Write the failing tests `tests/test_loader.py`**

```python
import io

import pytest

from caduceuspy.loader import NotebookLoadError, load_notebook


def test_executes_cells_into_namespace(make_notebook):
    path = make_notebook(["x = 2", "def double(a: int) -> int:\n    return a * x"])
    loaded = load_notebook(path)
    assert loaded.namespace["double"](5) == 10
    assert loaded.namespace["double"].__module__ == "__main__"
    assert loaded.path == path


def test_sources_are_transformed_python(make_notebook):
    path = make_notebook(["%time y = 1", "z = 3"])
    loaded = load_notebook(path)
    assert loaded.sources[0].startswith("get_ipython().run_line_magic(")
    assert loaded.sources[1].strip() == "z = 3"


def test_matplotlib_inline_magic_does_not_crash(make_notebook):
    path = make_notebook(["%matplotlib inline\nok = True"])
    assert load_notebook(path).namespace["ok"] is True


def test_prints_go_to_given_stream(make_notebook):
    path = make_notebook(["print('hello')"])
    buf = io.StringIO()
    load_notebook(path, stdout=buf)
    assert "hello" in buf.getvalue()


def test_failing_cell_reports_cell_number(make_notebook):
    path = make_notebook(["a = 1", "1 / 0"])
    with pytest.raises(NotebookLoadError) as info:
        load_notebook(path)
    assert info.value.cell_number == 2
    assert isinstance(info.value.error, ZeroDivisionError)
    assert str(info.value).startswith("Cell 2 failed: ZeroDivisionError")


def test_each_load_gets_a_fresh_namespace(make_notebook):
    first = load_notebook(make_notebook(["secret = 1"], name="a.ipynb"))
    second = load_notebook(make_notebook(["other = 2"], name="b.ipynb"))
    assert "secret" in first.namespace
    assert "secret" not in second.namespace
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_loader.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'caduceuspy.loader'`.

- [ ] **Step 3: Implement `src/caduceuspy/loader.py`**

```python
"""Execute a notebook file headlessly and return its namespace."""

from __future__ import annotations

import contextlib
import io
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TextIO

import nbformat
from IPython.core.interactiveshell import InteractiveShell
from traitlets.config import Config


class HeadlessShell(InteractiveShell):
    """IPython shell without GUI integration, so `%matplotlib inline` works outside Jupyter."""

    def enable_gui(self, gui: str | None = None) -> None:  # noqa: D102
        return None


class NotebookLoadError(Exception):
    """A code cell raised while the notebook was being loaded."""

    def __init__(self, cell_number: int, error: BaseException):
        self.cell_number = cell_number
        self.error = error
        super().__init__(f"Cell {cell_number} failed: {type(error).__name__}: {error}")


@dataclass
class LoadedNotebook:
    path: Path
    namespace: dict[str, Any]
    sources: list[str]
    notebook: nbformat.NotebookNode


def _new_shell() -> HeadlessShell:
    config = Config()
    config.HistoryManager.enabled = False
    return HeadlessShell(config=config)


def load_notebook(path: str | Path, *, stdout: TextIO | None = None) -> LoadedNotebook:
    """Run every code cell of `path` in order in a fresh headless IPython shell."""
    path = Path(path)
    notebook = nbformat.read(path, as_version=4)
    shell = _new_shell()
    sources: list[str] = []
    target = stdout if stdout is not None else io.StringIO()
    with contextlib.redirect_stdout(target):
        for index, cell in enumerate(notebook.cells):
            if cell.cell_type != "code" or not cell.source.strip():
                continue
            result = shell.run_cell(cell.source, store_history=False, silent=True)
            if not result.success:
                error = result.error_in_exec or result.error_before_exec
                raise NotebookLoadError(index + 1, error)
            sources.append(shell.transform_cell(cell.source))
    return LoadedNotebook(path=path, namespace=shell.user_ns, sources=sources, notebook=notebook)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_loader.py -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add src/caduceuspy/loader.py tests/test_loader.py
git commit -m "feat(loader): execute notebooks headlessly and report failing cell"
```

---

### Task 3: Tool discovery (Member 6)

**Files:**
- Create: `src/caduceuspy/discovery.py`
- Test: `tests/test_discovery.py`

**Interfaces:**
- Consumes: `caduceuspy.TOOL_MARKER` (Task 1).
- Produces:
  - `@dataclass(frozen=True) ToolSpec(name: str, fn: Callable[..., Any], description: str)`.
  - `discover(sources: Iterable[str], namespace: Mapping[str, Any]) -> list[ToolSpec]` in first-definition order.
  - Rules: candidates are top-level sync `def`s found in `sources`; exposed objects must be plain functions in `namespace` with `__module__ == "__main__"`. If any candidate is marked (decorator named `tool` or `x.tool`, a `# @tool` comment on the line directly above the `def`/first decorator, or the `TOOL_MARKER` attribute), only marked ones are exposed; otherwise all names not starting with `_`. Description = `inspect.getdoc(fn)` or `"Notebook function {name}."`.

- [ ] **Step 1: Write the failing tests `tests/test_discovery.py`**

```python
import caduceuspy
from caduceuspy.discovery import ToolSpec, discover


def run(sources):
    ns = {"__name__": "__main__"}
    for src in sources:
        exec(src, ns)
    return discover(sources, ns)


def test_public_functions_are_exposed_in_order():
    specs = run(["def b():\n    'B doc.'\n", "def a():\n    pass\n", "def _hidden():\n    pass\n"])
    assert [s.name for s in specs] == ["b", "a"]
    assert specs[0].description == "B doc."
    assert specs[1].description == "Notebook function a."
    assert isinstance(specs[0], ToolSpec)


def test_comment_marker_limits_exposure():
    specs = run(["def a():\n    pass\n\n# @tool\ndef b():\n    pass\n"])
    assert [s.name for s in specs] == ["b"]


def test_decorator_marker_limits_exposure():
    src = "import caduceuspy\n\n@caduceuspy.tool\ndef b():\n    pass\n\ndef a():\n    pass\n"
    assert [s.name for s in run([src])] == ["b"]


def test_attribute_marker_counts():
    ns = {"__name__": "__main__"}
    exec("def a():\n    pass\ndef b():\n    pass\n", ns)
    caduceuspy.tool(ns["b"])
    assert [s.name for s in discover(["def a():\n    pass\ndef b():\n    pass\n"], ns)] == ["b"]


def test_imported_and_async_functions_are_skipped():
    specs = run(["from os.path import join\nasync def fetch():\n    pass\ndef keep():\n    pass\n"])
    assert [s.name for s in specs] == ["keep"]


def test_redefinition_uses_current_object_and_unparsable_source_is_ignored():
    sources = ["def f():\n    return 1\n", "def f():\n    return 2\n"]
    ns = {"__name__": "__main__"}
    for src in sources:
        exec(src, ns)
    specs = discover(sources + ["this is not python"], ns)
    assert len(specs) == 1 and specs[0].fn() == 2


def test_names_missing_from_namespace_are_skipped():
    assert discover(["def ghost():\n    pass\n"], {}) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_discovery.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'caduceuspy.discovery'`.

- [ ] **Step 3: Implement `src/caduceuspy/discovery.py`**

```python
"""Find the notebook functions that should become MCP tools."""

from __future__ import annotations

import ast
import inspect
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping

from caduceuspy import TOOL_MARKER


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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_discovery.py -v`
Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add src/caduceuspy/discovery.py tests/test_discovery.py
git commit -m "feat(discovery): find notebook functions and @tool markers"
```

---

### Task 4: Object handles (Bibek)

**Files:**
- Create: `src/caduceuspy/handles.py`
- Test: `tests/test_handles.py`

**Interfaces:**
- Produces:
  - `HANDLE_RE` matching `^(df|series|arr|obj)#[0-9a-f]{4}$`.
  - `class UnknownHandleError(KeyError)` with `.handle: str`; `str()` → `"Unknown handle 'df#xxxx'"`.
  - `class HandleStore` with `put(obj) -> str`, `get(handle) -> Any`, `__contains__`, `__len__`, `resolve(value) -> Any`, `resolve_args(kwargs: Mapping[str, Any]) -> dict[str, Any]`. Prefix: `DataFrame`→`df`, `Series`→`series`, `ndarray`→`arr`, else `obj`.

- [ ] **Step 1: Write the failing tests `tests/test_handles.py`**

```python
import pandas as pd
import pytest

from caduceuspy.handles import HANDLE_RE, HandleStore, UnknownHandleError


def test_put_returns_typed_handle_and_get_returns_object():
    store = HandleStore()
    df = pd.DataFrame({"a": [1]})
    handle = store.put(df)
    assert handle.startswith("df#") and HANDLE_RE.match(handle)
    assert store.get(handle) is df
    assert handle in store and len(store) == 1


def test_other_objects_use_obj_prefix():
    assert HandleStore().put(object()).startswith("obj#")


def test_handles_are_unique():
    store = HandleStore()
    handles = {store.put(object()) for _ in range(200)}
    assert len(handles) == 200


def test_resolve_args_replaces_known_handles_only():
    store = HandleStore()
    obj = object()
    handle = store.put(obj)
    resolved = store.resolve_args({"data": handle, "n": 3, "label": "hello#world"})
    assert resolved == {"data": obj, "n": 3, "label": "hello#world"}


def test_unknown_handle_raises():
    with pytest.raises(UnknownHandleError) as info:
        HandleStore().resolve("df#abcd")
    assert str(info.value) == "Unknown handle 'df#abcd'"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_handles.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'caduceuspy.handles'`.

- [ ] **Step 3: Implement `src/caduceuspy/handles.py`**

```python
"""Keep large or non-serializable results server-side and refer to them by handle."""

from __future__ import annotations

import re
import secrets
from typing import Any, Mapping

HANDLE_RE = re.compile(r"^(df|series|arr|obj)#[0-9a-f]{4}$")

_PREFIXES = {"DataFrame": "df", "Series": "series", "ndarray": "arr"}


class UnknownHandleError(KeyError):
    def __init__(self, handle: str):
        super().__init__(handle)
        self.handle = handle

    def __str__(self) -> str:
        return f"Unknown handle '{self.handle}'"


class HandleStore:
    def __init__(self) -> None:
        self._objects: dict[str, Any] = {}

    def put(self, obj: Any) -> str:
        prefix = _PREFIXES.get(type(obj).__name__, "obj")
        while True:
            handle = f"{prefix}#{secrets.token_hex(2)}"
            if handle not in self._objects:
                break
        self._objects[handle] = obj
        return handle

    def get(self, handle: str) -> Any:
        try:
            return self._objects[handle]
        except KeyError:
            raise UnknownHandleError(handle) from None

    def __contains__(self, handle: object) -> bool:
        return handle in self._objects

    def __len__(self) -> int:
        return len(self._objects)

    def resolve(self, value: Any) -> Any:
        if isinstance(value, str) and HANDLE_RE.match(value):
            return self.get(value)
        return value

    def resolve_args(self, kwargs: Mapping[str, Any]) -> dict[str, Any]:
        return {key: self.resolve(value) for key, value in kwargs.items()}
```

Note: `secrets.token_hex(2)` gives 65,536 ids per prefix; the uniqueness loop covers collisions.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_handles.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add src/caduceuspy/handles.py tests/test_handles.py
git commit -m "feat(handles): store large objects and resolve handle arguments"
```

---

### Task 5: Result conversion (Bibek)

**Files:**
- Create: `src/caduceuspy/results.py`
- Test: `tests/test_results.py`

**Interfaces:**
- Consumes: `HandleStore` (Task 4).
- Produces:
  - Constants `MAX_TEXT = 4000`, `MAX_TABLE_ROWS = 50`, `PREVIEW_ROWS = 10`, `MAX_ARRAY_ITEMS = 100`.
  - `Content = types.TextContent | types.ImageContent`.
  - `cap_text(text: str, limit: int = MAX_TEXT) -> str`.
  - `markdown_table(df) -> str`.
  - `to_content(value: Any, store: HandleStore) -> list[Content]`. Rules: `None` → `"(no return value)"`; `str` → capped text; `bool/int/float` → JSON; list whose items are all `TextContent`/`ImageContent` → returned unchanged; pandas `Series` → treated as one-column DataFrame; DataFrame → stored as handle, text = markdown table (≤50 rows) or shape line + first 10 rows, plus `Handle: df#xxxx`; matplotlib `Figure`/`Axes` → PNG `ImageContent`; numpy array ≤100 items → JSON list, else handle + repr; `dict/list/tuple` → JSON if serializable; anything else → handle + capped `repr()`.

- [ ] **Step 1: Write the failing tests `tests/test_results.py`**

```python
import base64

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from mcp import types

from caduceuspy.handles import HandleStore
from caduceuspy.results import MAX_TEXT, cap_text, markdown_table, to_content


def text_of(content):
    assert all(isinstance(c, types.TextContent) for c in content)
    return "\n".join(c.text for c in content)


def test_scalars_and_none():
    store = HandleStore()
    assert text_of(to_content(None, store)) == "(no return value)"
    assert text_of(to_content(3, store)) == "3"
    assert text_of(to_content(True, store)) == "true"
    assert text_of(to_content("hi", store)) == "hi"


def test_long_text_is_capped():
    out = text_of(to_content("x" * (MAX_TEXT + 10), HandleStore()))
    assert out.startswith("x" * MAX_TEXT) and "truncated 10 chars" in out
    assert cap_text("short") == "short"


def test_json_collections():
    assert '"a": 1' in text_of(to_content({"a": 1}, HandleStore()))


def test_small_dataframe_is_table_plus_handle():
    store = HandleStore()
    df = pd.DataFrame({"name": ["a", "b"], "value": [1, 2]})
    out = text_of(to_content(df, store))
    assert "| name | value |" in out
    assert "Handle: df#" in out
    assert len(store) == 1


def test_large_dataframe_is_preview_plus_handle():
    store = HandleStore()
    df = pd.DataFrame({"v": range(500)})
    out = text_of(to_content(df, store))
    assert "500 rows x 1 columns" in out
    assert out.count("\n| ") <= 12
    assert "Handle: df#" in out


def test_figure_becomes_png_image():
    fig, ax = plt.subplots()
    ax.plot([1, 2, 3])
    content = to_content(fig, HandleStore())
    assert isinstance(content[0], types.ImageContent)
    assert content[0].mimeType == "image/png"
    assert base64.b64decode(content[0].data)[:4] == b"\x89PNG"
    plt.close(fig)


def test_arrays_small_json_large_handle():
    store = HandleStore()
    assert text_of(to_content(np.arange(3), store)) == "[0, 1, 2]"
    out = text_of(to_content(np.zeros(1000), store))
    assert "arr#" in out and "shape=(1000,)" in out


def test_unserializable_object_becomes_handle():
    class Model:
        def __repr__(self):
            return "Model()"

    store = HandleStore()
    out = text_of(to_content(Model(), store))
    assert "obj#" in out and "Model()" in out


def test_content_list_passes_through():
    items = [types.TextContent(type="text", text="already content")]
    assert to_content(items, HandleStore()) == items


def test_markdown_table_escapes_pipes():
    table = markdown_table(pd.DataFrame({"a": ["x|y"]}))
    assert "x\\|y" in table
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_results.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'caduceuspy.results'`.

- [ ] **Step 3: Implement `src/caduceuspy/results.py`**

```python
"""Convert Python return values into MCP content."""

from __future__ import annotations

import base64
import io
import json
import sys
from typing import Any, Union

from mcp import types

from caduceuspy.handles import HandleStore

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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_results.py -v`
Expected: 10 passed.

- [ ] **Step 5: Commit**

```bash
git add src/caduceuspy/results.py tests/test_results.py
git commit -m "feat(results): convert DataFrames, figures, arrays and objects to MCP content"
```

---

### Task 6: Server core — tool registration and calls (Bibek)

**Files:**
- Create: `src/caduceuspy/server.py`
- Test: `tests/test_server.py`

**Interfaces:**
- Consumes: `ToolSpec` (Task 3), `HandleStore`, `UnknownHandleError` (Task 4), `to_content`, `cap_text` (Task 5).
- Produces:
  - `@dataclass CallEvent(tool: str, args: dict[str, Any], status: str = "pending", duration_ms: float = 0.0, preview: str = "", error: str = "")`; `status` ∈ `pending|ok|error|denied`.
  - `Approver = Callable[[CallEvent], bool | None]` (True approve, False deny, None timeout). `CallListener = Callable[[CallEvent], None]`.
  - `json_safe_signature(fn) -> inspect.Signature` (non-JSON-schema annotations become `str`; `*args/**kwargs` dropped; return annotation removed).
  - `format_exception(exc: BaseException) -> str`.
  - `class CaduceusServer(name: str = "caduceus", *, store: HandleStore | None = None, approver: Approver | None = None, listener: CallListener | None = None, token: str | None = None)` with attributes `.name`, `.store`, `.mcp` (the `FastMCP`), property `.tool_names -> list[str]`, and methods `set_tools(specs: list[ToolSpec]) -> bool` (True if the advertised tool list changed; always rebinds function bodies) and `run_stdio() -> None`.

- [ ] **Step 1: Write the failing tests `tests/test_server.py`**

```python
import pandas as pd
import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from caduceuspy.discovery import ToolSpec
from caduceuspy.server import CaduceusServer, CallEvent, json_safe_signature

pytestmark = pytest.mark.anyio


def spec(fn, doc="doc"):
    return ToolSpec(name=fn.__name__, fn=fn, description=doc)


def add(a: int, b: int = 1) -> int:
    return a + b


def boom(x: int) -> int:
    raise ValueError("bad x")


def make_df(n: int) -> pd.DataFrame:
    return pd.DataFrame({"v": range(n)})


def count_rows(df: pd.DataFrame) -> int:
    return len(df)


def noisy() -> str:
    print("side effect")
    return "done"


async def test_lists_tools_with_schema():
    server = CaduceusServer("t")
    server.set_tools([spec(add, "Add numbers.")])
    async with create_connected_server_and_client_session(server.mcp) as client:
        tools = (await client.list_tools()).tools
    assert [t.name for t in tools] == ["add"]
    assert tools[0].description == "Add numbers."
    assert tools[0].inputSchema["properties"]["a"]["type"] == "integer"
    assert tools[0].inputSchema["required"] == ["a"]


async def test_call_returns_converted_content_and_emits_event():
    events: list[CallEvent] = []
    server = CaduceusServer("t", listener=events.append)
    server.set_tools([spec(add)])
    async with create_connected_server_and_client_session(server.mcp) as client:
        result = await client.call_tool("add", {"a": 2, "b": 3})
    assert not result.isError
    assert result.content[0].text == "5"
    assert events[-1].status == "ok" and events[-1].tool == "add"
    assert events[-1].args == {"a": 2, "b": 3}


async def test_exceptions_become_error_results():
    events: list[CallEvent] = []
    server = CaduceusServer("t", listener=events.append)
    server.set_tools([spec(boom)])
    async with create_connected_server_and_client_session(server.mcp) as client:
        result = await client.call_tool("boom", {"x": 1})
    assert result.isError
    assert "ValueError: bad x" in result.content[0].text
    assert events[-1].status == "error"


async def test_handles_chain_between_tools():
    server = CaduceusServer("t")
    server.set_tools([spec(make_df), spec(count_rows)])
    async with create_connected_server_and_client_session(server.mcp) as client:
        first = await client.call_tool("make_df", {"n": 7})
        handle = first.content[0].text.rsplit("Handle: ", 1)[1].strip()
        second = await client.call_tool("count_rows", {"df": handle})
        missing = await client.call_tool("count_rows", {"df": "df#0000"})
    assert second.content[0].text == "7"
    assert missing.isError and "Unknown handle 'df#0000'" in missing.content[0].text


async def test_stdout_is_captured_into_result():
    server = CaduceusServer("t")
    server.set_tools([spec(noisy)])
    async with create_connected_server_and_client_session(server.mcp) as client:
        result = await client.call_tool("noisy", {})
    assert result.content[0].text == "done"
    assert "side effect" in result.content[1].text


@pytest.mark.parametrize("decision,message", [(False, "Call denied by user"), (None, "Approval timed out")])
async def test_approver_can_block_calls(decision, message):
    events: list[CallEvent] = []
    server = CaduceusServer("t", approver=lambda event: decision, listener=events.append)
    server.set_tools([spec(add)])
    async with create_connected_server_and_client_session(server.mcp) as client:
        result = await client.call_tool("add", {"a": 1})
    assert result.isError and message in result.content[0].text
    assert events[-1].status == "denied"


def test_set_tools_reports_changes_and_rebinds_bodies():
    server = CaduceusServer("t")
    assert server.set_tools([ToolSpec("add", add, "doc")]) is True
    assert server.set_tools([ToolSpec("add", add, "doc")]) is False

    def same_signature(a: int, b: int = 1) -> int:
        return a - b

    assert server.set_tools([ToolSpec("add", same_signature, "doc")]) is False
    assert server._fns["add"](5, 1) == 4

    def new_signature(a: int, b: int = 1, c: int = 0) -> int:
        return a + b + c

    assert server.set_tools([ToolSpec("add", new_signature, "doc")]) is True
    assert server.set_tools([]) is True
    assert server.tool_names == []


def test_json_safe_signature_replaces_unknown_types():
    sig = json_safe_signature(count_rows)
    assert sig.parameters["df"].annotation is str
    assert sig.return_annotation is sig.empty
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_server.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'caduceuspy.server'`.

- [ ] **Step 3: Implement `src/caduceuspy/server.py`**

```python
"""MCP server that exposes notebook functions as tools."""

from __future__ import annotations

import contextlib
import inspect
import io
import json
import threading
import time
import traceback
from dataclasses import dataclass
from typing import Any, Callable, Optional

from mcp import types
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from pydantic import TypeAdapter

from caduceuspy.discovery import ToolSpec
from caduceuspy.handles import HandleStore, UnknownHandleError
from caduceuspy.results import cap_text, to_content


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


class CaduceusServer:
    def __init__(
        self,
        name: str = "caduceus",
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

    def run_stdio(self) -> None:
        """Serve over stdin/stdout until the client disconnects (blocking)."""
        self.mcp.run("stdio")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_server.py -v`
Expected: 9 passed (the parametrized approver test counts twice).

- [ ] **Step 5: Commit**

```bash
git add src/caduceuspy/server.py tests/test_server.py
git commit -m "feat(server): register notebook functions as MCP tools with approval, handles and errors"
```

---

### Task 7: Server — tools-changed notifications, HTTP thread, token auth (Bibek)

**Files:**
- Modify: `src/caduceuspy/server.py`
- Test: `tests/test_server_http.py`

**Interfaces:**
- Consumes: `CaduceusServer` (Task 6).
- Produces on `CaduceusServer`:
  - Capability `tools.listChanged = true` advertised at initialization.
  - `notify_tools_changed() -> None` — thread-safe; sends `notifications/tools/list_changed` to every session that has listed tools.
  - `start_http(host: str = "127.0.0.1", port: int = 8765) -> str` — starts uvicorn on a daemon thread, returns `http://{host}:{port}/mcp`; raises `OSError` if it cannot bind; raises `RuntimeError` if already running. One `start_http` per instance.
  - `join_http() -> None` (blocks until stopped), `stop_http() -> None`, property `http_url -> str | None`.
  - When `token` is set, HTTP requests without `Authorization: Bearer <token>` get 401.

- [ ] **Step 1: Write the failing tests `tests/test_server_http.py`**

```python
import anyio
import httpx
import pytest
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.shared.memory import create_connected_server_and_client_session

from caduceuspy.discovery import ToolSpec
from caduceuspy.server import CaduceusServer


def add(a: int, b: int) -> int:
    return a + b


def sub(a: int, b: int) -> int:
    return a - b


ADD = ToolSpec("add", add, "Add.")
SUB = ToolSpec("sub", sub, "Subtract.")


@pytest.mark.anyio
async def test_advertises_and_sends_list_changed():
    server = CaduceusServer("t")
    server.set_tools([ADD])
    received: list[str] = []

    async def on_message(message):
        received.append(type(getattr(message, "root", message)).__name__)

    async with create_connected_server_and_client_session(server.mcp, message_handler=on_message) as client:
        init = await client.list_tools()
        assert [t.name for t in init.tools] == ["add"]
        assert server.set_tools([ADD, SUB]) is True
        server.notify_tools_changed()
        await anyio.sleep(0.2)
        assert "ToolListChangedNotification" in received
        assert {t.name for t in (await client.list_tools()).tools} == {"add", "sub"}


async def _call_over_http(url: str, token: str | None) -> str:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    async with streamablehttp_client(url, headers=headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("add", {"a": 2, "b": 3})
            return result.content[0].text


def test_http_round_trip_with_token(free_port):
    server = CaduceusServer("t", token="s3cret")
    server.set_tools([ADD])
    url = server.start_http(port=free_port)
    try:
        assert url == f"http://127.0.0.1:{free_port}/mcp"
        assert server.http_url == url
        assert anyio.run(_call_over_http, url, "s3cret") == "5"
        assert httpx.post(url, json={}).status_code == 401
    finally:
        server.stop_http()
    assert server.http_url is None


def test_http_port_in_use_raises(free_port):
    first = CaduceusServer("a")
    first.start_http(port=free_port)
    try:
        with pytest.raises(OSError):
            CaduceusServer("b").start_http(port=free_port)
    finally:
        first.stop_http()


def test_cannot_start_twice(free_port):
    server = CaduceusServer("t")
    server.start_http(port=free_port)
    try:
        with pytest.raises(RuntimeError):
            server.start_http(port=free_port)
    finally:
        server.stop_http()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_server_http.py -v`
Expected: FAIL — `AttributeError: 'CaduceusServer' object has no attribute 'notify_tools_changed'` / `start_http`.

- [ ] **Step 3: Extend `src/caduceuspy/server.py`**

Add imports at the top (merge with existing ones):

```python
import asyncio

import uvicorn
from mcp.server.lowlevel.server import NotificationOptions
```

In `CaduceusServer.__init__`, after `self._fingerprints = {}` add:

```python
        self._sessions: list[tuple[Any, asyncio.AbstractEventLoop]] = []
        self._http: uvicorn.Server | None = None
        self._thread: threading.Thread | None = None
        self.http_url: str | None = None
        self._advertise_list_changed()
        self._track_sessions()
```

Add these methods to `CaduceusServer`:

```python
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

        thread = threading.Thread(target=run, name="caduceus-http", daemon=True)
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_server.py tests/test_server_http.py -v`
Expected: all pass (13 total).

- [ ] **Step 5: Commit**

```bash
git add src/caduceuspy/server.py tests/test_server_http.py
git commit -m "feat(server): HTTP transport on a thread, token auth, tools-changed notifications"
```

---

### Task 8: CLI `caduceus serve` (Daniil)

**Files:**
- Create: `src/caduceuspy/cli.py`, `src/caduceuspy/__main__.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `load_notebook`, `NotebookLoadError` (Task 2); `discover` (Task 3); `CaduceusServer` (Tasks 6–7).
- Produces:
  - `build_parser() -> argparse.ArgumentParser`; `main(argv: list[str] | None = None) -> int`.
  - `serve_name(path: Path) -> str`: notebook stem, lowercased, non-alphanumerics → `_`.
  - `caduceus serve NOTEBOOK [--http] [--port 8765] [--token T] [--name N]`. Prints status to **stderr only** (stdout is the MCP channel). Exit 1 with `caduceus: Cell N failed: ...` on load error.
  - `python -m caduceuspy` runs `main()`.

- [ ] **Step 1: Write the failing tests `tests/test_cli.py`**

```python
import sys

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from caduceuspy.cli import main, serve_name


def test_serve_name_is_sanitized(tmp_path):
    assert serve_name(tmp_path / "Sales Report-2026.ipynb") == "sales_report_2026"


def test_load_error_exits_1(make_notebook, capsys, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)  # cmd_serve changes directory; restore it after the test
    path = make_notebook(["1 / 0"])
    assert main(["serve", str(path)]) == 1
    assert "caduceus: Cell 1 failed: ZeroDivisionError" in capsys.readouterr().err


@pytest.mark.anyio
async def test_stdio_end_to_end(make_notebook):
    path = make_notebook([
        "print('cell output must not corrupt stdout')",
        "def greet(name: str) -> str:\n    'Say hello.'\n    return f'hello {name}'",
    ])
    params = StdioServerParameters(command=sys.executable, args=["-m", "caduceuspy", "serve", str(path)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = (await session.list_tools()).tools
            result = await session.call_tool("greet", {"name": "Hermes"})
    assert [t.name for t in tools] == ["greet"]
    assert result.content[0].text == "hello Hermes"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_cli.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'caduceuspy.cli'`.

- [ ] **Step 3: Implement `src/caduceuspy/cli.py`**

```python
"""Command-line interface: `caduceus serve` and `caduceus hermes-config`."""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

from caduceuspy.discovery import discover
from caduceuspy.loader import NotebookLoadError, load_notebook
from caduceuspy.server import CaduceusServer


def _log(message: str) -> None:
    print(f"caduceus: {message}", file=sys.stderr, flush=True)


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
    server = CaduceusServer(args.name or serve_name(path), token=args.token)
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="caduceus", description="Serve a Jupyter notebook as MCP tools.")
    commands = parser.add_subparsers(dest="command", required=True)

    serve = commands.add_parser("serve", help="Serve a notebook's functions as MCP tools.")
    serve.add_argument("notebook", help="Path to the .ipynb file")
    serve.add_argument("--http", action="store_true", help="Serve over HTTP instead of stdio")
    serve.add_argument("--port", type=int, default=8765)
    serve.add_argument("--token", default=None, help="Require 'Authorization: Bearer <token>' (HTTP only)")
    serve.add_argument("--name", default=None, help="Server name shown to agents")
    serve.set_defaults(func=cmd_serve)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)
```

`src/caduceuspy/__main__.py`:

```python
import sys

from caduceuspy.cli import main

sys.exit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_cli.py -v`
Expected: 3 passed.

- [ ] **Step 5: Manual smoke test**

Run: `caduceus serve --help`
Expected: usage text listing `--http`, `--port`, `--token`, `--name`.

- [ ] **Step 6: Commit**

```bash
git add src/caduceuspy/cli.py src/caduceuspy/__main__.py tests/test_cli.py
git commit -m "feat(cli): caduceus serve over stdio or HTTP"
```

---

### Task 9: First release v0.1.0 to PyPI (Kerey)

**Files:**
- Create: `.github/workflows/release.yml`

**Interfaces:**
- Consumes: everything from Tasks 1–8 on `main` with CI green.
- Produces: `caduceuspy 0.1.0` on PyPI with Homepage = repo URL; automated releases on tags `v*`.

- [ ] **Step 1: Make the repo public and confirm CI is green**

GitHub → `bebdyshev/cs1302a-project` → Settings → General → Danger Zone → Change visibility → Public. Then check the Actions tab: latest CI run on `main` is green.

- [ ] **Step 2: Build and check locally**

```bash
rm -rf dist && uv build
uvx twine check dist/*
```

Expected: `caduceuspy-0.1.0-py3-none-any.whl` and `caduceuspy-0.1.0.tar.gz`; twine reports `PASSED` for both.

- [ ] **Step 3: Verify the wheel installs cleanly in a fresh env**

```bash
uv venv -p 3.10 /tmp/cad-check && /tmp/cad-check/bin/python -m ensurepip -q
/tmp/cad-check/bin/python -m pip install dist/caduceuspy-0.1.0-py3-none-any.whl
/tmp/cad-check/bin/caduceus serve --help
```

Expected: install succeeds without resolver conflicts; help text prints.

- [ ] **Step 4: Publish 0.1.0 manually (claims the name today)**

Create a PyPI account (enable 2FA), create an API token scoped to "Entire account" (first upload only), then:

```bash
uv publish --token pypi-XXXXXXXX
```

Expected: `https://pypi.org/project/caduceuspy/0.1.0/` exists; sidebar shows Homepage → GitHub repo. Then on PyPI → project → Settings → add co-maintainers (each team member's PyPI username), and delete the account-wide token.

- [ ] **Step 5: Configure trusted publishing for later releases**

PyPI → caduceuspy → Settings → Publishing → Add GitHub publisher: owner `bebdyshev`, repo `cs1302a-project`, workflow `release.yml`, environment `pypi`. In GitHub → Settings → Environments → New environment `pypi`.

- [ ] **Step 6: Create `.github/workflows/release.yml`**

```yaml
name: Release
on:
  push:
    tags: ["v*"]
jobs:
  publish:
    runs-on: ubuntu-latest
    environment: pypi
    permissions:
      id-token: write
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install build && python -m build
      - uses: pypa/gh-action-pypi-publish@release/v1
```

Release procedure for every later version: bump `__version__` in `src/caduceuspy/__init__.py` and the version test in `tests/test_package.py`, commit, then `git tag v0.X.0 && git push origin v0.X.0`.

- [ ] **Step 7: Commit**

```bash
git add .github/workflows/release.yml
git commit -m "ci: publish to PyPI on version tags via trusted publishing"
git push origin main
```

---

### Task 10: Call-log and approval widget (Vladan)

**Files:**
- Create: `src/caduceuspy/widget.py`
- Test: `tests/test_widget.py`

**Interfaces:**
- Consumes: `CallEvent` (Task 6).
- Produces `class CallLog(max_rows: int = 50)`:
  - `.widget` (`ipywidgets.VBox`) — display this once.
  - `set_status(text: str) -> None` — header becomes `☤ caduceus — {text}`.
  - `record(event: CallEvent) -> None` — appends a row (keeps last `max_rows`).
  - `format_event(event: CallEvent) -> str` (static) — HTML for a row.
  - `request_approval(event: CallEvent, timeout: float = 60.0) -> bool | None` — appends a row with Approve/Deny buttons and blocks the calling (server) thread until a click (True/False) or timeout (None). Must be safe to call from a non-main thread.

- [ ] **Step 1: Write the failing tests `tests/test_widget.py`**

```python
import threading
import time

from caduceuspy.server import CallEvent
from caduceuspy.widget import CallLog


def event(**kw):
    base = dict(tool="top_customers", args={"n": 3}, status="ok", duration_ms=12.3, preview="| a |")
    base.update(kw)
    return CallEvent(**base)


def test_status_header():
    log = CallLog()
    log.set_status("serving 3 tools")
    assert "serving 3 tools" in log.header.value


def test_record_appends_escaped_rows_and_trims():
    log = CallLog(max_rows=2)
    for i in range(3):
        log.record(event(args={"n": i}))
    assert len(log.rows.children) == 2
    html = CallLog.format_event(event(preview="<script>"))
    assert "top_customers(n=3)" in html and "&lt;script&gt;" in html and "12 ms" in html


def test_error_rows_show_error_text():
    assert "ValueError" in CallLog.format_event(event(status="error", error="ValueError: bad"))


def click_later(log, index, delay=0.1):
    def run():
        time.sleep(delay)
        box = log.rows.children[-1]
        box.children[index].click()

    threading.Thread(target=run).start()


def test_approve_and_deny_buttons():
    log = CallLog()
    click_later(log, 1)
    assert log.request_approval(event(), timeout=5) is True
    click_later(log, 2)
    assert log.request_approval(event(), timeout=5) is False
    approve, deny = log.rows.children[-1].children[1:]
    assert approve.disabled and deny.disabled


def test_approval_times_out():
    log = CallLog()
    assert log.request_approval(event(), timeout=0.1) is None
    assert "timed out" in log.rows.children[-1].children[0].value
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_widget.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'caduceuspy.widget'`.

- [ ] **Step 3: Implement `src/caduceuspy/widget.py`**

```python
"""Notebook panel that shows agent tool calls and asks for approval."""

from __future__ import annotations

import html
import threading
from typing import Optional

import ipywidgets as widgets

from caduceuspy.server import CallEvent

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
        self.header.value = f"<b>☤ caduceus</b> — {html.escape(text)}"

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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_widget.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add src/caduceuspy/widget.py tests/test_widget.py
git commit -m "feat(widget): call-log panel with approve/deny buttons"
```

---

### Task 11: Hermes config generation (Daniil)

**Files:**
- Create: `src/caduceuspy/hermes.py`
- Modify: `src/caduceuspy/cli.py` (add `hermes-config` command)
- Test: `tests/test_hermes.py`

**Interfaces:**
- Consumes: `serve_name` (Task 8).
- Produces:
  - `DEFAULT_CONFIG = Path("~/.hermes/config.yaml")`.
  - `stdio_entry(notebook: Path, *, timeout: int | None = None) -> dict` → `{"command": sys.executable, "args": ["-m", "caduceuspy", "serve", "<abs path>"], ["timeout": t]}`.
  - `http_entry(url: str, *, token: str | None = None, timeout: int | None = None) -> dict` → `{"url": url, ["headers": {"Authorization": "Bearer <token>"}], ["timeout": t]}`.
  - `to_yaml(name: str, entry: dict) -> str` → YAML for `{"mcp_servers": {name: entry}}`.
  - `write_config(name: str, entry: dict, path: Path = DEFAULT_CONFIG) -> Path` — merges into existing YAML (backup to `config.yaml.bak` first), creates parent dir if needed.
  - CLI: `caduceus hermes-config NOTEBOOK [--live] [--port 8765] [--token T] [--name N] [--timeout S] [--config PATH] [--print]`.

- [ ] **Step 1: Write the failing tests `tests/test_hermes.py`**

```python
import sys

import yaml

from caduceuspy.cli import main
from caduceuspy.hermes import http_entry, stdio_entry, to_yaml, write_config


def test_stdio_entry_uses_current_python_and_absolute_path(tmp_path):
    nb = tmp_path / "a.ipynb"
    entry = stdio_entry(nb, timeout=700)
    assert entry == {"command": sys.executable, "args": ["-m", "caduceuspy", "serve", str(nb.resolve())], "timeout": 700}


def test_http_entry_with_token():
    entry = http_entry("http://127.0.0.1:8765/mcp", token="t")
    assert entry == {"url": "http://127.0.0.1:8765/mcp", "headers": {"Authorization": "Bearer t"}}


def test_to_yaml_round_trips():
    text = to_yaml("sales", {"url": "u"})
    assert yaml.safe_load(text) == {"mcp_servers": {"sales": {"url": "u"}}}


def test_write_config_merges_and_backs_up(tmp_path):
    config = tmp_path / "config.yaml"
    config.write_text("model: hermes-4\nmcp_servers:\n  github:\n    command: npx\n")
    write_config("sales", {"url": "u"}, config)
    data = yaml.safe_load(config.read_text())
    assert data["model"] == "hermes-4"
    assert set(data["mcp_servers"]) == {"github", "sales"}
    assert (tmp_path / "config.yaml.bak").exists()


def test_write_config_creates_missing_file(tmp_path):
    config = tmp_path / "new" / "config.yaml"
    write_config("x", {"url": "u"}, config)
    assert yaml.safe_load(config.read_text()) == {"mcp_servers": {"x": {"url": "u"}}}


def test_cli_print_live(tmp_path, capsys):
    nb = tmp_path / "Sales Demo.ipynb"
    nb.write_text("{}")
    assert main(["hermes-config", str(nb), "--live", "--port", "9000", "--print"]) == 0
    data = yaml.safe_load(capsys.readouterr().out)
    assert data == {"mcp_servers": {"sales_demo": {"url": "http://127.0.0.1:9000/mcp"}}}


def test_cli_writes_config(tmp_path, capsys):
    nb = tmp_path / "a.ipynb"
    nb.write_text("{}")
    config = tmp_path / "config.yaml"
    assert main(["hermes-config", str(nb), "--config", str(config)]) == 0
    assert yaml.safe_load(config.read_text())["mcp_servers"]["a"]["args"][-1] == str(nb.resolve())
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_hermes.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'caduceuspy.hermes'`.

- [ ] **Step 3: Implement `src/caduceuspy/hermes.py`**

```python
"""Generate Hermes Agent `mcp_servers` config entries."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG = Path("~/.hermes/config.yaml")


def stdio_entry(notebook: Path, *, timeout: int | None = None) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "command": sys.executable,
        "args": ["-m", "caduceuspy", "serve", str(Path(notebook).resolve())],
    }
    if timeout:
        entry["timeout"] = timeout
    return entry


def http_entry(url: str, *, token: str | None = None, timeout: int | None = None) -> dict[str, Any]:
    entry: dict[str, Any] = {"url": url}
    if token:
        entry["headers"] = {"Authorization": f"Bearer {token}"}
    if timeout:
        entry["timeout"] = timeout
    return entry


def to_yaml(name: str, entry: dict[str, Any]) -> str:
    return yaml.safe_dump({"mcp_servers": {name: entry}}, sort_keys=False)


def write_config(name: str, entry: dict[str, Any], path: Path = DEFAULT_CONFIG) -> Path:
    path = Path(path).expanduser()
    data: dict[str, Any] = {}
    if path.exists():
        shutil.copy2(path, path.with_name(path.name + ".bak"))
        data = yaml.safe_load(path.read_text()) or {}
    servers = data.get("mcp_servers") or {}
    servers[name] = entry
    data["mcp_servers"] = servers
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False))
    return path
```

- [ ] **Step 4: Add the `hermes-config` command to `src/caduceuspy/cli.py`**

Add import: `from caduceuspy import hermes`.

Add function:

```python
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
```

In `build_parser()`, before `return parser`:

```python
    config = commands.add_parser("hermes-config", help="Add this notebook to Hermes Agent's MCP config.")
    config.add_argument("notebook", help="Path to the .ipynb file")
    config.add_argument("--live", action="store_true", help="Point Hermes at a live %%caduceus serve session")
    config.add_argument("--port", type=int, default=8765)
    config.add_argument("--token", default=None)
    config.add_argument("--name", default=None)
    config.add_argument("--timeout", type=int, default=None, help="Per-call timeout in seconds for Hermes")
    config.add_argument("--config", default=str(hermes.DEFAULT_CONFIG), help="Hermes config file")
    config.add_argument("--print", action="store_true", help="Print YAML instead of writing the file")
    config.set_defaults(func=cmd_hermes_config)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_hermes.py tests/test_cli.py -v`
Expected: all pass (10 total).

- [ ] **Step 6: Commit**

```bash
git add src/caduceuspy/hermes.py src/caduceuspy/cli.py tests/test_hermes.py
git commit -m "feat(hermes): generate and merge Hermes mcp_servers config"
```

---

### Task 12: Whole notebook as a tool (Daniil)

**Files:**
- Create: `src/caduceuspy/notebook_tool.py`
- Modify: `src/caduceuspy/cli.py` (`serve` adds the notebook tool; new `--notebook-timeout`, `--no-notebook-tool`)
- Test: `tests/test_notebook_tool.py`

**Interfaces:**
- Consumes: `ToolSpec` (Task 3), `cap_text` (Task 5).
- Produces:
  - `class NotebookRunError(Exception)`.
  - `@dataclass(frozen=True) Parameter(name: str, default: Any, annotation: Any)`.
  - `find_parameters_cell(nb) -> int | None` (first code cell tagged `parameters`).
  - `parse_parameters(source: str) -> list[Parameter]` (simple `name = <literal>` and `name: T = <literal>`; non-literals skipped; `None` default → annotation `Any`).
  - `notebook_tool_name(path: Path) -> str` → `"run_" + sanitized stem`.
  - `run_notebook(path: Path, values: dict[str, Any], *, timeout: int = 600) -> list[Content]` — executes a copy with an injected cell after the parameters cell, returns text of all outputs after the injected cell (`stream`, `execute_result`/`display_data` `text/plain`, capped 8000 chars) and up to 5 PNG images. Raises `NotebookRunError` on cell error or timeout.
  - `build_notebook_tool(path: Path, *, timeout: int = 600) -> ToolSpec | None` (None if no parameters cell).

- [ ] **Step 1: Write the failing tests `tests/test_notebook_tool.py`**

```python
import inspect

import pytest
from mcp import types

from caduceuspy.notebook_tool import (
    NotebookRunError,
    build_notebook_tool,
    notebook_tool_name,
    parse_parameters,
    run_notebook,
)

REPORT = [
    ("region = 'EU'\nyear: int = 2025\nlimit = None\nnot_literal = len('x')", ["parameters"]),
    "print(f'report for {region} {year}')",
    "{'region': region, 'year': year}",
]


def test_parse_parameters():
    params = parse_parameters(REPORT[0][0])
    assert [(p.name, p.default) for p in params] == [("region", "EU"), ("year", 2025), ("limit", None)]
    assert params[0].annotation is str and params[1].annotation is int


def test_tool_name(tmp_path):
    assert notebook_tool_name(tmp_path / "Sales Report.ipynb") == "run_sales_report"


def test_build_returns_none_without_parameters_cell(make_notebook):
    assert build_notebook_tool(make_notebook(["x = 1"])) is None


def test_build_tool_signature(make_notebook):
    spec = build_notebook_tool(make_notebook(REPORT, name="report.ipynb"))
    assert spec.name == "run_report"
    sig = inspect.signature(spec.fn)
    assert list(sig.parameters) == ["region", "year", "limit"]
    assert sig.parameters["year"].default == 2025
    assert "region" in spec.description


def test_run_injects_values_and_collects_outputs(make_notebook):
    spec = build_notebook_tool(make_notebook(REPORT, name="report.ipynb"), timeout=60)
    content = spec.fn(region="US")
    text = "\n".join(c.text for c in content if isinstance(c, types.TextContent))
    assert "report for US 2025" in text
    assert "'region': 'US'" in text


def test_failing_notebook_raises(make_notebook):
    path = make_notebook([("x = 1", ["parameters"]), "1 / 0"])
    with pytest.raises(NotebookRunError, match="ZeroDivisionError"):
        run_notebook(path, {"x": 2}, timeout=60)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_notebook_tool.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'caduceuspy.notebook_tool'`.

- [ ] **Step 3: Implement `src/caduceuspy/notebook_tool.py`**

```python
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

from caduceuspy.discovery import ToolSpec
from caduceuspy.results import cap_text

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
    injected = "# Parameters injected by caduceus\n" + "\n".join(f"{k} = {v!r}" for k, v in values.items())
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
```

- [ ] **Step 4: Wire into `caduceus serve` in `src/caduceuspy/cli.py`**

Add import: `from caduceuspy.notebook_tool import build_notebook_tool`.

In `cmd_serve`, replace `specs = discover(loaded.sources, loaded.namespace)` with:

```python
    specs = discover(loaded.sources, loaded.namespace)
    if not args.no_notebook_tool:
        notebook_spec = build_notebook_tool(path, timeout=args.notebook_timeout)
        if notebook_spec is not None:
            specs.append(notebook_spec)
```

In `build_parser()`, add to the `serve` subparser:

```python
    serve.add_argument("--notebook-timeout", type=int, default=600, help="Per-cell timeout for run_<notebook>")
    serve.add_argument("--no-notebook-tool", action="store_true", help="Do not expose run_<notebook>")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_notebook_tool.py tests/test_cli.py -v`
Expected: all pass (9 total). The run tests start a real kernel (a few seconds each).

- [ ] **Step 6: Commit**

```bash
git add src/caduceuspy/notebook_tool.py src/caduceuspy/cli.py tests/test_notebook_tool.py
git commit -m "feat(notebook-tool): expose whole notebook with parameters cell as run_<name>"
```

---

### Task 13: Live kernel magic `%caduceus` (Matthias)

**Files:**
- Create: `src/caduceuspy/magic.py`
- Modify: `src/caduceuspy/__init__.py` (add `load_ipython_extension`, `unload_ipython_extension`)
- Test: `tests/test_magic.py`

**Interfaces:**
- Consumes: `discover` (Task 3), `CaduceusServer` (Tasks 6–7), `CallLog` (Task 10), `hermes.http_entry/to_yaml` (Task 11), `build_notebook_tool` (Task 12), `serve_name` (Task 8).
- Produces:
  - `class LiveSession(shell, *, name: str, port: int, token: str | None, approve: bool, approval_timeout: float, notebook: Path | None, notebook_timeout: int)` with `.server`, `.log`, `.url`, `specs() -> list[ToolSpec]`, `start() -> str`, `stop() -> None`.
  - `class CaduceusMagics(Magics)` with line magic `caduceus`: `serve [--port 8765] [--token T] [--approve] [--approval-timeout 60] [--notebook PATH] [--notebook-timeout 600] [--name N]`, `stop`, `status`. Attribute `.session: LiveSession | None`.
  - `detect_notebook(user_ns) -> Path | None` (from `__session__` or `__vsc_ipynb_file__` if it is an existing `.ipynb`).
  - `load_ipython_extension(ipython)`, `unload_ipython_extension(ipython)`.

- [ ] **Step 1: Write the failing tests `tests/test_magic.py`**

```python
import anyio
import pytest
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from caduceuspy.magic import CaduceusMagics, detect_notebook


@pytest.fixture
def shell(ip):
    ip.run_line_magic("load_ext", "caduceuspy")
    yield ip
    magics = ip.magics_manager.registry["CaduceusMagics"]
    if magics.session is not None:
        ip.run_line_magic("caduceus", "stop")


async def list_tool_names(url):
    async with streamablehttp_client(url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            return sorted(t.name for t in (await session.list_tools()).tools)


def test_serve_exposes_live_functions_and_prints_hermes_yaml(shell, free_port, capsys):
    shell.run_cell("def live_tool(x: int) -> int:\n    return x + 1", store_history=True)
    shell.run_line_magic("caduceus", f"serve --port {free_port} --name demo")
    magics = shell.magics_manager.registry["CaduceusMagics"]
    url = magics.session.url
    assert url == f"http://127.0.0.1:{free_port}/mcp"
    assert "live_tool" in anyio.run(list_tool_names, url)
    out = capsys.readouterr().out
    assert "mcp_servers:" in out and f"url: {url}" in out


def test_status_and_stop(shell, free_port, capsys):
    shell.run_line_magic("caduceus", f"serve --port {free_port}")
    shell.run_line_magic("caduceus", "status")
    assert "serving" in capsys.readouterr().out
    shell.run_line_magic("caduceus", "stop")
    assert shell.magics_manager.registry["CaduceusMagics"].session is None


def test_second_serve_is_refused(shell, free_port, capsys):
    shell.run_line_magic("caduceus", f"serve --port {free_port}")
    shell.run_line_magic("caduceus", f"serve --port {free_port}")
    assert "Already serving" in capsys.readouterr().out


def test_bad_arguments_do_not_raise(shell, capsys):
    shell.run_line_magic("caduceus", "frobnicate")
    assert "usage" in capsys.readouterr().err.lower()


def test_detect_notebook(tmp_path):
    nb = tmp_path / "x.ipynb"
    nb.write_text("{}")
    assert detect_notebook({"__session__": str(nb)}) == nb
    assert detect_notebook({"__session__": str(tmp_path / "missing.ipynb")}) is None
    assert detect_notebook({}) is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_magic.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'caduceuspy.magic'`.

- [ ] **Step 3: Implement `src/caduceuspy/magic.py`**

```python
"""`%caduceus` line magic: serve the live kernel's functions over MCP."""

from __future__ import annotations

import argparse
import shlex
from pathlib import Path
from typing import Any, Mapping, Optional

from IPython.core.magic import Magics, line_magic, magics_class
from IPython.display import display

from caduceuspy import hermes
from caduceuspy.cli import serve_name
from caduceuspy.discovery import ToolSpec, discover
from caduceuspy.notebook_tool import build_notebook_tool
from caduceuspy.server import CaduceusServer
from caduceuspy.widget import CallLog


def detect_notebook(user_ns: Mapping[str, Any]) -> Optional[Path]:
    for key in ("__session__", "__vsc_ipynb_file__"):
        value = user_ns.get(key)
        if isinstance(value, str) and value.endswith(".ipynb"):
            for candidate in (Path(value), Path.cwd() / Path(value).name):
                if candidate.exists():
                    return candidate.resolve()
    return None


class LiveSession:
    def __init__(
        self,
        shell: Any,
        *,
        name: str,
        port: int,
        token: Optional[str],
        approve: bool,
        approval_timeout: float,
        notebook: Optional[Path],
        notebook_timeout: int,
    ) -> None:
        self.shell = shell
        self.port = port
        self.log = CallLog()
        approver = (lambda event: self.log.request_approval(event, timeout=approval_timeout)) if approve else None
        self.server = CaduceusServer(name, approver=approver, listener=self.log.record, token=token)
        self.notebook_spec = build_notebook_tool(notebook, timeout=notebook_timeout) if notebook else None
        self.url: Optional[str] = None

    def specs(self) -> list[ToolSpec]:
        specs = discover(self.shell.user_ns.get("In", []), self.shell.user_ns)
        if self.notebook_spec is not None:
            specs.append(self.notebook_spec)
        return specs

    def start(self) -> str:
        self.server.set_tools(self.specs())
        self.url = self.server.start_http(port=self.port)
        self.log.set_status(f"serving {len(self.server.tool_names)} tools at {self.url}")
        return self.url

    def stop(self) -> None:
        self.server.stop_http()
        self.log.set_status("stopped")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="%caduceus", add_help=True)
    commands = parser.add_subparsers(dest="command", required=True)
    serve = commands.add_parser("serve")
    serve.add_argument("--port", type=int, default=8765)
    serve.add_argument("--token", default=None)
    serve.add_argument("--approve", action="store_true")
    serve.add_argument("--approval-timeout", type=float, default=60.0)
    serve.add_argument("--notebook", default=None)
    serve.add_argument("--notebook-timeout", type=int, default=600)
    serve.add_argument("--name", default=None)
    commands.add_parser("stop")
    commands.add_parser("status")
    return parser


@magics_class
class CaduceusMagics(Magics):
    session: Optional[LiveSession] = None

    @line_magic
    def caduceus(self, line: str) -> None:
        """%caduceus serve|stop|status — serve this kernel's functions as MCP tools."""
        try:
            args = _parser().parse_args(shlex.split(line))
        except SystemExit:
            return None
        getattr(self, f"_{args.command}")(args)
        return None

    def _serve(self, args: argparse.Namespace) -> None:
        if self.session is not None:
            print(f"Already serving at {self.session.url}. Run %caduceus stop first.")
            return
        notebook = Path(args.notebook).resolve() if args.notebook else detect_notebook(self.shell.user_ns)
        name = args.name or (serve_name(notebook) if notebook else "notebook")
        session = LiveSession(
            self.shell,
            name=name,
            port=args.port,
            token=args.token,
            approve=args.approve,
            approval_timeout=args.approval_timeout,
            notebook=notebook,
            notebook_timeout=args.notebook_timeout,
        )
        display(session.log.widget)
        try:
            url = session.start()
        except OSError as exc:
            session.log.set_status("failed to start")
            print(f"{exc}. Try %caduceus serve --port <other port>.")
            return
        self.session = session
        timeout = args.notebook_timeout + 30 if session.notebook_spec else None
        entry = hermes.http_entry(url, token=args.token, timeout=timeout)
        print(f"Serving {len(session.server.tool_names)} tools: {', '.join(session.server.tool_names)}")
        print("Add this to ~/.hermes/config.yaml, then run /reload-mcp in Hermes:\n")
        print(hermes.to_yaml(name, entry))

    def _stop(self, args: argparse.Namespace) -> None:
        if self.session is None:
            print("Not serving.")
            return
        self.session.stop()
        self.session = None
        print("Stopped.")

    def _status(self, args: argparse.Namespace) -> None:
        if self.session is None:
            print("Not serving.")
            return
        tools = ", ".join(self.session.server.tool_names)
        print(f"serving at {self.session.url}: {tools}")


def load_ipython_extension(ipython: Any) -> None:
    ipython.register_magics(CaduceusMagics)


def unload_ipython_extension(ipython: Any) -> None:
    magics = ipython.magics_manager.registry.get("CaduceusMagics")
    if magics is not None and magics.session is not None:
        magics.session.stop()
        magics.session = None
```

- [ ] **Step 4: Add the extension hooks to `src/caduceuspy/__init__.py`**

Append before `__all__`:

```python
def load_ipython_extension(ipython: Any) -> None:
    """Enable `%caduceus` via `%load_ext caduceuspy`."""
    from caduceuspy.magic import load_ipython_extension as _load

    _load(ipython)


def unload_ipython_extension(ipython: Any) -> None:
    from caduceuspy.magic import unload_ipython_extension as _unload

    _unload(ipython)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_magic.py -v`
Expected: 5 passed.

- [ ] **Step 6: Manual check in JupyterLab**

Run `jupyter lab`, new notebook:

```python
%load_ext caduceuspy
def hello(name: str) -> str:
    "Greet someone."
    return f"hi {name}"
%caduceus serve
```

Expected: a panel headed `☤ caduceus — serving 1 tools at http://127.0.0.1:8765/mcp` and a printed Hermes YAML block. Then `npx @modelcontextprotocol/inspector`, connect to `http://127.0.0.1:8765/mcp` (Streamable HTTP), call `hello` → the call appears in the panel.

- [ ] **Step 7: Commit**

```bash
git add src/caduceuspy/magic.py src/caduceuspy/__init__.py tests/test_magic.py
git commit -m "feat(magic): %caduceus serve/stop/status for live kernel serving"
```

---

### Task 14: Hot reload (Matthias)

**Files:**
- Create: `src/caduceuspy/hotreload.py`
- Modify: `src/caduceuspy/magic.py` (`LiveSession.start/stop` use `HotReloader`)
- Test: `tests/test_hotreload.py`

**Interfaces:**
- Consumes: `CaduceusServer.set_tools`, `.notify_tools_changed`, `.tool_names` (Tasks 6–7); `LiveSession` (Task 13).
- Produces: `class HotReloader(shell, server, rediscover: Callable[[], list[ToolSpec]], on_change: Callable[[list[str]], None] | None = None)` with `start()`, `stop()`, `refresh() -> bool`. Registered on IPython `post_run_cell`; skips failed cells; on change calls `server.notify_tools_changed()` and `on_change(server.tool_names)`.

- [ ] **Step 1: Write the failing tests `tests/test_hotreload.py`**

```python
from caduceuspy.discovery import discover
from caduceuspy.hotreload import HotReloader
from caduceuspy.server import CaduceusServer


class SpyServer(CaduceusServer):
    def __init__(self):
        super().__init__("spy")
        self.notified = 0

    def notify_tools_changed(self):
        self.notified += 1


def make(shell):
    server = SpyServer()
    changes = []
    reloader = HotReloader(
        shell,
        server,
        lambda: discover(shell.user_ns.get("In", []), shell.user_ns),
        on_change=changes.append,
    )
    return server, reloader, changes


def test_new_function_triggers_notification(ip):
    shell = ip
    server, reloader, changes = make(shell)
    reloader.start()
    try:
        shell.run_cell("def hr_alpha(x: int) -> int:\n    return x", store_history=True)
        assert "hr_alpha" in server.tool_names
        assert server.notified == 1 and "hr_alpha" in changes[-1]
        shell.run_cell("unrelated = 1", store_history=True)
        assert server.notified == 1
        shell.run_cell("def hr_alpha(x: int, y: int = 0) -> int:\n    return x + y", store_history=True)
        assert server.notified == 2
    finally:
        reloader.stop()


def test_failed_cells_are_ignored_and_stop_unregisters(ip):
    shell = ip
    server, reloader, _ = make(shell)
    reloader.start()
    shell.run_cell("def hr_beta():\n    pass\n1 / 0", store_history=True)
    assert "hr_beta" not in server.tool_names
    reloader.stop()
    shell.run_cell("def hr_gamma():\n    pass", store_history=True)
    assert "hr_gamma" not in server.tool_names
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_hotreload.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'caduceuspy.hotreload'`.

- [ ] **Step 3: Implement `src/caduceuspy/hotreload.py`**

```python
"""Re-discover tools after every executed cell and notify connected agents."""

from __future__ import annotations

from typing import Any, Callable, Optional

from caduceuspy.discovery import ToolSpec
from caduceuspy.server import CaduceusServer


class HotReloader:
    def __init__(
        self,
        shell: Any,
        server: CaduceusServer,
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
            print(f"caduceus: hot reload failed: {type(exc).__name__}: {exc}")
```

- [ ] **Step 4: Wire into `LiveSession` in `src/caduceuspy/magic.py`**

Add import: `from caduceuspy.hotreload import HotReloader`.

In `LiveSession.__init__`, after `self.url = None` add:

```python
        self.reloader = HotReloader(shell, self.server, self.specs, on_change=self._on_tools_changed)
```

Add method:

```python
    def _on_tools_changed(self, names: list[str]) -> None:
        self.log.set_status(f"serving {len(names)} tools at {self.url} (updated: {', '.join(names)})")
```

In `LiveSession.start`, before `return self.url` add `self.reloader.start()`. In `LiveSession.stop`, first line add `self.reloader.stop()`.

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/test_hotreload.py tests/test_magic.py -v`
Expected: 7 passed.

- [ ] **Step 6: Commit**

```bash
git add src/caduceuspy/hotreload.py src/caduceuspy/magic.py tests/test_hotreload.py
git commit -m "feat(hotreload): update tools after each cell and notify agents"
```

- [ ] **Step 7: Release v0.2.0 (Kerey)**

Bump `__version__ = "0.2.0"` and the version assertion in `tests/test_package.py`, run `pytest -q`, commit `chore: release 0.2.0`, then `git tag v0.2.0 && git push origin main v0.2.0`. Expected: Release workflow green; `pip install caduceuspy==0.2.0` works.

---

### Task 15: Docs site, README, example notebook (Kerey)

**Files:**
- Create: `docs/_config.yml`, `docs/_toc.yml`, `docs/intro.md`, `docs/quickstart.md`, `docs/live-mode.md`, `docs/features.md`, `docs/hermes.md`, `docs/jupyterhub.md`, `docs/comparison.md`, `.github/workflows/docs.yml`, `examples/make_examples.py`, `examples/sales_demo.ipynb` (generated)
- Modify: `README.md`

**Interfaces:**
- Consumes: CLI and magic behaviour from Tasks 8–14 (document exactly those flags).
- Produces: `https://bebdyshev.github.io/cs1302a-project/`; `examples/sales_demo.ipynb` used by the demo (Task 16).

- [ ] **Step 1: Create `examples/make_examples.py`**

```python
"""Generate examples/sales_demo.ipynb (run: python examples/make_examples.py)."""

from pathlib import Path

import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

cells = [
    new_markdown_cell("# Sales demo\nServe this notebook to an AI agent with `%caduceus serve`."),
    new_code_cell("%load_ext caduceuspy\nimport numpy as np\nimport pandas as pd\nimport matplotlib.pyplot as plt"),
    new_code_cell("region = 'EU'\nyear = 2026", metadata={"tags": ["parameters"]}),
    new_code_cell(
        "rng = np.random.default_rng(7)\n"
        "orders = pd.DataFrame({\n"
        "    'customer': rng.choice(['Acme', 'Globex', 'Initech', 'Umbrella', 'Hooli', 'Stark'], 2000),\n"
        "    'region': rng.choice(['EU', 'US', 'APAC'], 2000),\n"
        "    'month': rng.integers(1, 13, 2000),\n"
        "    'amount': rng.gamma(2.0, 150.0, 2000).round(2),\n"
        "})"
    ),
    new_code_cell(
        "def top_customers(n: int = 5, region: str = 'EU') -> pd.DataFrame:\n"
        "    \"\"\"Return the n customers with the highest total revenue in a region (EU, US or APAC).\"\"\"\n"
        "    sub = orders[orders.region == region]\n"
        "    return sub.groupby('customer', as_index=False).amount.sum().nlargest(n, 'amount')\n"
        "\n"
        "def orders_for(region: str = 'EU', min_amount: float = 0.0) -> pd.DataFrame:\n"
        "    \"\"\"Return all orders in a region with amount >= min_amount (returns a handle for large results).\"\"\"\n"
        "    return orders[(orders.region == region) & (orders.amount >= min_amount)]\n"
        "\n"
        "def summarize(df: pd.DataFrame) -> dict:\n"
        "    \"\"\"Summarize an orders DataFrame (pass a df# handle): count, total and mean amount.\"\"\"\n"
        "    return {'orders': int(len(df)), 'total': float(df.amount.sum()), 'mean': float(df.amount.mean())}\n"
        "\n"
        "def revenue_chart(region: str = 'EU'):\n"
        "    \"\"\"Plot monthly revenue for a region and return the chart.\"\"\"\n"
        "    monthly = orders[orders.region == region].groupby('month').amount.sum()\n"
        "    fig, ax = plt.subplots(figsize=(6, 3))\n"
        "    monthly.plot(kind='bar', ax=ax, title=f'{region} revenue by month')\n"
        "    plt.close(fig)\n"
        "    return fig"
    ),
    new_code_cell(
        "report = orders[orders.region == region]\n"
        "print(f'{region} {year}: {len(report)} orders, total {report.amount.sum():,.2f}')\n"
        "top_customers(3, region)"
    ),
    new_code_cell("# %caduceus serve --approve"),
]

nb = new_notebook(cells=cells)
nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
out = Path(__file__).with_name("sales_demo.ipynb")
nbformat.write(nb, out)
print(f"wrote {out}")
```

- [ ] **Step 2: Generate and smoke-test the example**

```bash
python examples/make_examples.py
caduceus hermes-config examples/sales_demo.ipynb --print
python - <<'EOF'
import anyio, sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
async def main():
    p = StdioServerParameters(command=sys.executable, args=["-m", "caduceuspy", "serve", "examples/sales_demo.ipynb"])
    async with stdio_client(p) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            print(sorted(t.name for t in (await s.list_tools()).tools))
            print((await s.call_tool("top_customers", {"n": 2})).content[0].text)
anyio.run(main)
EOF
```

Expected: tools `['orders_for', 'revenue_chart', 'run_sales_demo', 'summarize', 'top_customers']` and a 2-row markdown table ending with `Handle: df#....`.

- [ ] **Step 3: Create Jupyter Book config**

`docs/_config.yml`:

```yaml
title: caduceuspy
author: group27 (cs1302a)
logo: ""
execute:
  execute_notebooks: "off"
repository:
  url: https://github.com/bebdyshev/cs1302a-project
  path_to_book: docs
  branch: main
html:
  use_repository_button: true
  use_issues_button: true
```

`docs/_toc.yml`:

```yaml
format: jb-book
root: intro
chapters:
  - file: quickstart
  - file: live-mode
  - file: features
  - file: hermes
  - file: jupyterhub
  - file: comparison
```

- [ ] **Step 4: Write the doc pages**

`docs/intro.md` must contain, in this order: a one-sentence pitch ("Turn any Jupyter notebook into an MCP server so AI agents can call its functions as tools."); **Motivation** (agents can already *drive* notebooks, but a notebook's analysis can't be *served* to an agent as a typed API without rewriting it as a package or server); **Innovation** (bullet list: Jupyter-native, live kernel state, hot reload, object handles, approval, whole-notebook tool, no LLM inside); **The name** (the caduceus is the staff of Hermes, the messenger; Hermes Agent is our reference client); a 6-line example using `sales_demo.ipynb`.

`docs/quickstart.md`: `pip install caduceuspy`; CLI mode (`caduceus serve notebook.ipynb`, `--http --port --token --name --notebook-timeout --no-notebook-tool`); tool discovery rules copied from the spec section 4 (public functions, `@caduceuspy.tool` / `# @tool` opt-in, async functions ignored, type hints → schema, docstring → description).

`docs/live-mode.md`: `%load_ext caduceuspy`, `%caduceus serve [--port] [--token] [--approve] [--approval-timeout] [--notebook] [--notebook-timeout] [--name]`, `%caduceus status`, `%caduceus stop`; the call-log panel; hot reload (edit + rerun a cell; agents get `tools/list_changed`; if your client ignores it, run `/reload-mcp` in Hermes); note that tool calls run one at a time.

`docs/features.md`: one section each for result conversion table (copy the rules from Task 5 interfaces), object handles (example: `orders_for` → `df#a3f9` → `summarize(df="df#a3f9")`), approval mode, whole-notebook tool (`parameters` tag, how to tag a cell in JupyterLab: Property Inspector → Cell tags), stdout capture.

`docs/hermes.md`: config for stdio (`caduceus hermes-config notebook.ipynb`) and live (`--live --port`), the generated YAML for both, `/reload-mcp`, `timeout` note (Hermes default 120 s; set it higher for `run_<notebook>`).

`docs/jupyterhub.md`: install with `pip install --user caduceuspy` (or in the course env), run `%caduceus serve --token <random>` in a notebook, open a pod terminal, `caduceus hermes-config <nb> --live --token <same>` then start Hermes; the server only listens on `127.0.0.1`, and the token protects it from other users on shared nodes.

`docs/comparison.md`: the table from spec section 2, plus "when to use what".

- [ ] **Step 5: Build docs locally**

```bash
uv pip install "jupyter-book>=1,<2"
jupyter-book build docs/
```

Expected: `docs/_build/html/index.html` exists; build prints no errors (warnings OK).

- [ ] **Step 6: Create `.github/workflows/docs.yml`**

```yaml
name: Docs
on:
  push:
    branches: [main]
permissions:
  contents: read
  pages: write
  id-token: write
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install "jupyter-book>=1,<2"
      - run: jupyter-book build docs/
      - uses: actions/upload-pages-artifact@v3
        with:
          path: docs/_build/html
  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
    steps:
      - uses: actions/deploy-pages@v4
```

GitHub → Settings → Pages → Source: "GitHub Actions".

- [ ] **Step 7: Expand `README.md`**

Sections: pitch + badges (PyPI version `https://img.shields.io/pypi/v/caduceuspy`), 30-second quickstart (CLI and live mode), feature list, link to docs, "How it differs" (3 lines from comparison), team (names of the six members), license.

- [ ] **Step 8: Commit, push, verify**

```bash
git add docs examples README.md .github/workflows/docs.yml
git commit -m "docs: Jupyter Book site, README and sales demo notebook"
git push origin main
```

Expected: Docs workflow green; `https://bebdyshev.github.io/cs1302a-project/` loads.

---

### Task 16: JupyterHub + Hermes verification, final release, demo (Daniil + all)

**Files:**
- Create: `docs/demo-script.md`
- Modify: `docs/jupyterhub.md`, `docs/hermes.md` (record verified findings)

**Interfaces:**
- Consumes: `caduceuspy` on PyPI, `examples/sales_demo.ipynb`.
- Produces: verified compatibility notes; final release `v1.0.0`; rehearsed 60-second demo.

- [ ] **Step 1: Install on the course JupyterHub (do this on Day 1 with 0.1.0 too)**

In a JupyterHub terminal:

```bash
python --version
pip install --user caduceuspy
pip check
caduceus --help
hermes --version
python -c "import mcp, importlib.metadata as m; print(m.version('mcp'))"
```

Expected: Python ≥3.10, no resolver errors, `pip check` → "No broken requirements found." Record the Python, Hermes and mcp versions in `docs/jupyterhub.md`. If `pip check` reports a conflict, open an issue with the output and fix the version range in `pyproject.toml` the same day.

- [ ] **Step 2: Verify live mode with Hermes in the pod**

1. Upload `examples/sales_demo.ipynb`, run all cells, then run `%caduceus serve --token demo123`.
2. In a pod terminal: `caduceus hermes-config sales_demo.ipynb --live --token demo123`, then start `hermes`.
3. Ask: "Who are the top 3 customers in the US?" Expected: Hermes calls `top_customers`; the row appears in the notebook panel.
4. Ask: "Get EU orders over 500 and summarize them." Expected: `orders_for` returns a `df#` handle and Hermes passes it to `summarize`.

- [ ] **Step 3: Verify hot reload behaviour in Hermes**

Add a new cell `def best_month(region: str = "EU") -> int: ...`, run it, then ask Hermes to use it **without** `/reload-mcp`. Record in `docs/hermes.md` whether Hermes picked it up automatically. If not, document "run `/reload-mcp` after adding tools" and put that step in the demo script.

- [ ] **Step 4: Verify approval and the whole-notebook tool**

`%caduceus stop`, then `%caduceus serve --token demo123 --approve`. Ask Hermes for a chart; click **Deny** → Hermes reports the denial. Ask again; click **Approve** → chart returned. Ask "Re-run the sales report for APAC" → `run_sales_demo(region="APAC")` returns the printed summary. Record timings.

- [ ] **Step 5: Write `docs/demo-script.md`**

A 60-second script with six 10-second beats, one per member, each with the exact thing to type or click:

| Beat | Speaker | Action |
|---|---|---|
| 1 | Kerey | Problem + pitch: "Agents can drive notebooks; caduceuspy lets a notebook *serve* agents." `pip install caduceuspy` already done. |
| 2 | Member 6 | Show `sales_demo.ipynb` functions; run `%caduceus serve --approve`. Panel appears. |
| 3 | Bibek | In Hermes: "Top 3 US customers?" Approve → table + handle in the panel. |
| 4 | Matthias | Add `best_month` cell, run it; Hermes uses it (or `/reload-mcp`). |
| 5 | Vladan | Hermes asks to plot; click **Deny**, then re-ask and Approve → chart. |
| 6 | Daniil | "Re-run the report for APAC" → `run_sales_demo`; close with PyPI + docs links. |

- [ ] **Step 6: Final release**

Bump `__version__ = "1.0.0"` and the version test, commit `chore: release 1.0.0`, `git tag v1.0.0 && git push origin main v1.0.0`. On JupyterHub: `pip install --user -U caduceuspy` and repeat Step 2 quickly.

- [ ] **Step 7: Rehearse twice and submit**

Time the demo (≤ 60 s). Submit on the course page: PyPI link `https://pypi.org/project/caduceuspy/`, repo link, docs link.

- [ ] **Step 8: Commit**

```bash
git add docs/demo-script.md docs/jupyterhub.md docs/hermes.md
git commit -m "docs: JupyterHub/Hermes verification notes and demo script"
git push origin main
```
