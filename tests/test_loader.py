import io

import pytest

from laria_mcp.loader import NotebookLoadError, load_notebook


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
