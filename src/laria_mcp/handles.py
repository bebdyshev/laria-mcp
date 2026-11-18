"""Keep large or non-serializable results server-side and refer to them by handle."""

from __future__ import annotations

import re
import secrets
from typing import Any, Mapping

HANDLE_RE = re.compile(r"^(df|series|arr|obj)#[0-9a-f]{4}$")

_PREFIXES = {"DataFrame": "df", "Series": "series", "ndarray": "arr"}


class UnknownHandleError(KeyError):
    def __init__(self, handle: str):
        super().__init__(handle)
        self.handle = handle

    def __str__(self) -> str:
        return f"Unknown handle '{self.handle}'"


class HandleStore:
    def __init__(self) -> None:
        self._objects: dict[str, Any] = {}

    def put(self, obj: Any) -> str:
        prefix = _PREFIXES.get(type(obj).__name__, "obj")
        while True:
            handle = f"{prefix}#{secrets.token_hex(2)}"
            if handle not in self._objects:
                break
        self._objects[handle] = obj
        return handle

    def get(self, handle: str) -> Any:
        try:
            return self._objects[handle]
        except KeyError:
            raise UnknownHandleError(handle) from None

    def __contains__(self, handle: object) -> bool:
        return handle in self._objects

    def __len__(self) -> int:
        return len(self._objects)

    def resolve(self, value: Any) -> Any:
        if isinstance(value, str) and HANDLE_RE.match(value):
            return self.get(value)
        return value

    def resolve_args(self, kwargs: Mapping[str, Any]) -> dict[str, Any]:
        return {key: self.resolve(value) for key, value in kwargs.items()}
