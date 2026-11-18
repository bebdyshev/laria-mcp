import laria_mcp
from laria_mcp.discovery import ToolSpec, discover


def run(sources):
    ns = {"__name__": "__main__"}
    for src in sources:
        exec(src, ns)
    return discover(sources, ns)


def test_public_functions_are_exposed_in_order():
    specs = run(["def b():\n    'B doc.'\n", "def a():\n    pass\n", "def _hidden():\n    pass\n"])
    assert [s.name for s in specs] == ["b", "a"]
    assert specs[0].description == "B doc."
    assert specs[1].description == "Notebook function a."
    assert isinstance(specs[0], ToolSpec)


def test_comment_marker_limits_exposure():
    specs = run(["def a():\n    pass\n\n# @tool\ndef b():\n    pass\n"])
    assert [s.name for s in specs] == ["b"]


def test_decorator_marker_limits_exposure():
    src = "import laria_mcp\n\n@laria_mcp.tool\ndef b():\n    pass\n\ndef a():\n    pass\n"
    assert [s.name for s in run([src])] == ["b"]


def test_attribute_marker_counts():
    ns = {"__name__": "__main__"}
    exec("def a():\n    pass\ndef b():\n    pass\n", ns)
    laria_mcp.tool(ns["b"])
    assert [s.name for s in discover(["def a():\n    pass\ndef b():\n    pass\n"], ns)] == ["b"]


def test_imported_and_async_functions_are_skipped():
    specs = run(["from os.path import join\nasync def fetch():\n    pass\ndef keep():\n    pass\n"])
    assert [s.name for s in specs] == ["keep"]


def test_redefinition_uses_current_object_and_unparsable_source_is_ignored():
    sources = ["def f():\n    return 1\n", "def f():\n    return 2\n"]
    ns = {"__name__": "__main__"}
    for src in sources:
        exec(src, ns)
    specs = discover(sources + ["this is not python"], ns)
    assert len(specs) == 1 and specs[0].fn() == 2


def test_names_missing_from_namespace_are_skipped():
    assert discover(["def ghost():\n    pass\n"], {}) == []
