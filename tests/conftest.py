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
