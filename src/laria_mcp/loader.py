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
