import inspect

import pytest
from mcp import types

from laria_mcp.notebook_tool import (
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
