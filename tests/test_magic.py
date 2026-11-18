import anyio
import pytest
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from laria_mcp.magic import LariaMagics, detect_notebook


@pytest.fixture
def shell(ip):
    ip.run_line_magic("load_ext", "laria_mcp")
    yield ip
    magics = ip.magics_manager.registry["LariaMagics"]
    if magics.session is not None:
        ip.run_line_magic("laria", "stop")


async def list_tool_names(url):
    async with streamablehttp_client(url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            return sorted(t.name for t in (await session.list_tools()).tools)


def test_serve_exposes_live_functions_and_prints_hermes_yaml(shell, free_port, capsys):
    shell.run_cell("def live_tool(x: int) -> int:\n    return x + 1", store_history=True)
    shell.run_line_magic("laria", f"serve --port {free_port} --name demo")
    magics = shell.magics_manager.registry["LariaMagics"]
    url = magics.session.url
    assert url == f"http://127.0.0.1:{free_port}/mcp"
    assert "live_tool" in anyio.run(list_tool_names, url)
    out = capsys.readouterr().out
    assert "mcp_servers:" in out and f"url: {url}" in out


def test_status_and_stop(shell, free_port, capsys):
    shell.run_line_magic("laria", f"serve --port {free_port}")
    shell.run_line_magic("laria", "status")
    assert "serving" in capsys.readouterr().out
    shell.run_line_magic("laria", "stop")
    assert shell.magics_manager.registry["LariaMagics"].session is None


def test_second_serve_is_refused(shell, free_port, capsys):
    shell.run_line_magic("laria", f"serve --port {free_port}")
    shell.run_line_magic("laria", f"serve --port {free_port}")
    assert "Already serving" in capsys.readouterr().out


def test_bad_arguments_do_not_raise(shell, capsys):
    shell.run_line_magic("laria", "frobnicate")
    assert "usage" in capsys.readouterr().err.lower()


def test_detect_notebook(tmp_path):
    nb = tmp_path / "x.ipynb"
    nb.write_text("{}")
    assert detect_notebook({"__session__": str(nb)}) == nb
    assert detect_notebook({"__session__": str(tmp_path / "missing.ipynb")}) is None
    assert detect_notebook({}) is None
