import base64

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from mcp import types

from laria_mcp.handles import HandleStore
from laria_mcp.results import MAX_TEXT, cap_text, markdown_table, to_content


def text_of(content):
    assert all(isinstance(c, types.TextContent) for c in content)
    return "\n".join(c.text for c in content)


def test_scalars_and_none():
    store = HandleStore()
    assert text_of(to_content(None, store)) == "(no return value)"
    assert text_of(to_content(3, store)) == "3"
    assert text_of(to_content(True, store)) == "true"
    assert text_of(to_content("hi", store)) == "hi"


def test_long_text_is_capped():
    out = text_of(to_content("x" * (MAX_TEXT + 10), HandleStore()))
    assert out.startswith("x" * MAX_TEXT) and "truncated 10 chars" in out
    assert cap_text("short") == "short"


def test_json_collections():
    assert '"a": 1' in text_of(to_content({"a": 1}, HandleStore()))


def test_small_dataframe_is_table_plus_handle():
    store = HandleStore()
    df = pd.DataFrame({"name": ["a", "b"], "value": [1, 2]})
    out = text_of(to_content(df, store))
    assert "| name | value |" in out
    assert "Handle: df#" in out
    assert len(store) == 1


def test_large_dataframe_is_preview_plus_handle():
    store = HandleStore()
    df = pd.DataFrame({"v": range(500)})
    out = text_of(to_content(df, store))
    assert "500 rows x 1 columns" in out
    assert out.count("\n| ") <= 12
    assert "Handle: df#" in out


def test_figure_becomes_png_image():
    fig, ax = plt.subplots()
    ax.plot([1, 2, 3])
    content = to_content(fig, HandleStore())
    assert isinstance(content[0], types.ImageContent)
    assert content[0].mimeType == "image/png"
    assert base64.b64decode(content[0].data)[:4] == b"\x89PNG"
    plt.close(fig)


def test_arrays_small_json_large_handle():
    store = HandleStore()
    assert text_of(to_content(np.arange(3), store)) == "[0, 1, 2]"
    out = text_of(to_content(np.zeros(1000), store))
    assert "arr#" in out and "shape=(1000,)" in out


def test_unserializable_object_becomes_handle():
    class Model:
        def __repr__(self):
            return "Model()"

    store = HandleStore()
    out = text_of(to_content(Model(), store))
    assert "obj#" in out and "Model()" in out


def test_content_list_passes_through():
    items = [types.TextContent(type="text", text="already content")]
    assert to_content(items, HandleStore()) == items


def test_markdown_table_escapes_pipes():
    table = markdown_table(pd.DataFrame({"a": ["x|y"]}))
    assert "x\\|y" in table
