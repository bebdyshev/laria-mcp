"""Execute a notebook file headlessly and return its namespace."""

from __future__ import annotations

import contextlib # used for contextlib.redirect_stdout, which captures print outputs
import io
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TextIO

import nbformat # to read Jupyter notebooks
from IPython.core.interactiveshell import InteractiveShell  # Provides an enhanced "exec()"-like function specialized for Jupyter notebooks
from traitlets.config import Config # a dictionary-like object that is indexed with dotted attributes instead. Used to make configurations for IPython/Jupyter


class HeadlessShell(InteractiveShell): # Inherit/Subclass InteractiveShell attributes and methods, however overrides the method "enable_gui" and disables interactive GUI to remain headless
    """IPython shell without GUI integration, so `%matplotlib inline` works outside Jupyter."""

    def enable_gui(self, gui: str | None = None) -> None:  # noqa: D102
        return None


class NotebookLoadError(Exception): # Inherit/Subclass Exception for custom exception
    """A code cell raised while the notebook was being loaded."""

    def __init__(self, cell_number: int, error: BaseException):
        self.cell_number = cell_number
        self.error = error
        super().__init__(f"Cell {cell_number} failed: {type(error).__name__}: {error}") # Calls Exception.__init__


@dataclass
class LoadedNotebook:
    path: Path
    namespace: dict[str, Any]   # Stores the Python context, specifically variable names and their values
    sources: list[str]
    notebook: nbformat.NotebookNode


def _new_shell() -> HeadlessShell:
    config = Config()
    config.HistoryManager.enabled = False   # ensures history management features are disabled (e.g., creating a database file for history logs)
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
            if cell.cell_type != "code" or not cell.source.strip(): # if not code or cell is empty
                continue
            result = shell.run_cell(cell.source, store_history=False, silent=True)
            if not result.success:
                error = result.error_in_exec or result.error_before_exec    # runtime_error or syntax_error
                raise NotebookLoadError(index + 1, error)                   # cell number starts from index 1
            sources.append(shell.transform_cell(cell.source))               # transform cell code with IPython syntax to use Python syntax and store it into a list
    return LoadedNotebook(path=path, namespace=shell.user_ns, sources=sources, notebook=notebook)
