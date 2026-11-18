import sys

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from laria_mcp.cli import main, serve_name


def test_serve_name_is_sanitized(tmp_path):
    assert serve_name(tmp_path / "Sales Report-2026.ipynb") == "sales_report_2026"


def test_load_error_exits_1(make_notebook, capsys, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)  # cmd_serve changes directory; restore it after the test
    path = make_notebook(["1 / 0"])
    assert main(["serve", str(path)]) == 1
    assert "laria: Cell 1 failed: ZeroDivisionError" in capsys.readouterr().err


@pytest.mark.anyio
async def test_stdio_end_to_end(make_notebook):
    path = make_notebook([
        "print('cell output must not corrupt stdout')",
        "def greet(name: str) -> str:\n    'Say hello.'\n    return f'hello {name}'",
    ])
    params = StdioServerParameters(command=sys.executable, args=["-m", "laria_mcp", "serve", str(path)])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = (await session.list_tools()).tools
            result = await session.call_tool("greet", {"name": "Hermes"})
    assert [t.name for t in tools] == ["greet"]
    assert result.content[0].text == "hello Hermes"
