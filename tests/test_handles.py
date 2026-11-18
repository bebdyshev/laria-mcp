import pandas as pd
import pytest

from laria_mcp.handles import HANDLE_RE, HandleStore, UnknownHandleError


def test_put_returns_typed_handle_and_get_returns_object():
    store = HandleStore()
    df = pd.DataFrame({"a": [1]})
    handle = store.put(df)
    assert handle.startswith("df#") and HANDLE_RE.match(handle)
    assert store.get(handle) is df
    assert handle in store and len(store) == 1


def test_other_objects_use_obj_prefix():
    assert HandleStore().put(object()).startswith("obj#")


def test_handles_are_unique():
    store = HandleStore()
    handles = {store.put(object()) for _ in range(200)}
    assert len(handles) == 200


def test_resolve_args_replaces_known_handles_only():
    store = HandleStore()
    obj = object()
    handle = store.put(obj)
    resolved = store.resolve_args({"data": handle, "n": 3, "label": "hello#world"})
    assert resolved == {"data": obj, "n": 3, "label": "hello#world"}


def test_unknown_handle_raises():
    with pytest.raises(UnknownHandleError) as info:
        HandleStore().resolve("df#abcd")
    assert str(info.value) == "Unknown handle 'df#abcd'"
