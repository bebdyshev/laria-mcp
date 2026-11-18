import laria_mcp


def test_version_is_set():
    assert laria_mcp.__version__ == "0.1.0"


def test_tool_decorator_marks_and_returns_same_function():
    def f(x: int) -> int:
        return x

    marked = laria_mcp.tool(f)
    assert marked is f
    assert getattr(f, laria_mcp.TOOL_MARKER) is True
