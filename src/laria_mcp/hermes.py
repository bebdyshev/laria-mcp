"""Generate Hermes Agent `mcp_servers` config entries."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG = Path("~/.hermes/config.yaml")


def stdio_entry(notebook: Path, *, timeout: int | None = None) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "command": sys.executable,
        "args": ["-m", "laria_mcp", "serve", str(Path(notebook).resolve())],
    }
    if timeout:
        entry["timeout"] = timeout
    return entry


def http_entry(url: str, *, token: str | None = None, timeout: int | None = None) -> dict[str, Any]:
    entry: dict[str, Any] = {"url": url}
    if token:
        entry["headers"] = {"Authorization": f"Bearer {token}"}
    if timeout:
        entry["timeout"] = timeout
    return entry


def to_yaml(name: str, entry: dict[str, Any]) -> str:
    return yaml.safe_dump({"mcp_servers": {name: entry}}, sort_keys=False)


def write_config(name: str, entry: dict[str, Any], path: Path = DEFAULT_CONFIG) -> Path:
    path = Path(path).expanduser()
    data: dict[str, Any] = {}
    if path.exists():
        shutil.copy2(path, path.with_name(path.name + ".bak"))
        data = yaml.safe_load(path.read_text()) or {}
    servers = data.get("mcp_servers") or {}
    servers[name] = entry
    data["mcp_servers"] = servers
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False))
    return path
