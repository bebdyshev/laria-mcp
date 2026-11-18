import pandas as pd
import pytest
from mcp.shared.memory import create_connected_server_and_client_session

from laria_mcp.discovery import ToolSpec
from laria_mcp.server import LariaServer, CallEvent, json_safe_signature

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
    server = LariaServer("t")
    server.set_tools([spec(add, "Add numbers.")])
    async with create_connected_server_and_client_session(server.mcp) as client:
        tools = (await client.list_tools()).tools
    assert [t.name for t in tools] == ["add"]
    assert tools[0].description == "Add numbers."
    assert tools[0].inputSchema["properties"]["a"]["type"] == "integer"
    assert tools[0].inputSchema["required"] == ["a"]


async def test_call_returns_converted_content_and_emits_event():
    events: list[CallEvent] = []
    server = LariaServer("t", listener=events.append)
    server.set_tools([spec(add)])
    async with create_connected_server_and_client_session(server.mcp) as client:
        result = await client.call_tool("add", {"a": 2, "b": 3})
    assert not result.isError
    assert result.content[0].text == "5"
    assert events[-1].status == "ok" and events[-1].tool == "add"
    assert events[-1].args == {"a": 2, "b": 3}


async def test_exceptions_become_error_results():
    events: list[CallEvent] = []
    server = LariaServer("t", listener=events.append)
    server.set_tools([spec(boom)])
    async with create_connected_server_and_client_session(server.mcp) as client:
        result = await client.call_tool("boom", {"x": 1})
    assert result.isError
    assert "ValueError: bad x" in result.content[0].text
    assert events[-1].status == "error"


async def test_handles_chain_between_tools():
    server = LariaServer("t")
    server.set_tools([spec(make_df), spec(count_rows)])
    async with create_connected_server_and_client_session(server.mcp) as client:
        first = await client.call_tool("make_df", {"n": 7})
        handle = first.content[0].text.rsplit("Handle: ", 1)[1].strip()
        second = await client.call_tool("count_rows", {"df": handle})
        missing = await client.call_tool("count_rows", {"df": "df#0000"})
    assert second.content[0].text == "7"
    assert missing.isError and "Unknown handle 'df#0000'" in missing.content[0].text


async def test_stdout_is_captured_into_result():
    server = LariaServer("t")
    server.set_tools([spec(noisy)])
    async with create_connected_server_and_client_session(server.mcp) as client:
        result = await client.call_tool("noisy", {})
    assert result.content[0].text == "done"
    assert "side effect" in result.content[1].text


@pytest.mark.parametrize("decision,message", [(False, "Call denied by user"), (None, "Approval timed out")])
async def test_approver_can_block_calls(decision, message):
    events: list[CallEvent] = []
    server = LariaServer("t", approver=lambda event: decision, listener=events.append)
    server.set_tools([spec(add)])
    async with create_connected_server_and_client_session(server.mcp) as client:
        result = await client.call_tool("add", {"a": 1})
    assert result.isError and message in result.content[0].text
    assert events[-1].status == "denied"


def test_set_tools_reports_changes_and_rebinds_bodies():
    server = LariaServer("t")
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
