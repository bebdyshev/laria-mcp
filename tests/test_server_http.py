import anyio
import httpx
import pytest
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.shared.memory import create_connected_server_and_client_session

from laria_mcp.discovery import ToolSpec
from laria_mcp.server import LariaServer


def add(a: int, b: int) -> int:
    return a + b


def sub(a: int, b: int) -> int:
    return a - b


ADD = ToolSpec("add", add, "Add.")
SUB = ToolSpec("sub", sub, "Subtract.")


@pytest.mark.anyio
async def test_advertises_and_sends_list_changed():
    server = LariaServer("t")
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
    server = LariaServer("t", token="s3cret")
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
    first = LariaServer("a")
    first.start_http(port=free_port)
    try:
        with pytest.raises(OSError):
            LariaServer("b").start_http(port=free_port)
    finally:
        first.stop_http()


def test_cannot_start_twice(free_port):
    server = LariaServer("t")
    server.start_http(port=free_port)
    try:
        with pytest.raises(RuntimeError):
            server.start_http(port=free_port)
    finally:
        server.stop_http()
