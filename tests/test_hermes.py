import sys

import yaml

from laria_mcp.cli import main
from laria_mcp.hermes import http_entry, stdio_entry, to_yaml, write_config


def test_stdio_entry_uses_current_python_and_absolute_path(tmp_path):
    nb = tmp_path / "a.ipynb"
    entry = stdio_entry(nb, timeout=700)
    assert entry == {"command": sys.executable, "args": ["-m", "laria_mcp", "serve", str(nb.resolve())], "timeout": 700}


def test_http_entry_with_token():
    entry = http_entry("http://127.0.0.1:8765/mcp", token="t")
    assert entry == {"url": "http://127.0.0.1:8765/mcp", "headers": {"Authorization": "Bearer t"}}


def test_to_yaml_round_trips():
    text = to_yaml("sales", {"url": "u"})
    assert yaml.safe_load(text) == {"mcp_servers": {"sales": {"url": "u"}}}


def test_write_config_merges_and_backs_up(tmp_path):
    config = tmp_path / "config.yaml"
    config.write_text("model: hermes-4\nmcp_servers:\n  github:\n    command: npx\n")
    write_config("sales", {"url": "u"}, config)
    data = yaml.safe_load(config.read_text())
    assert data["model"] == "hermes-4"
    assert set(data["mcp_servers"]) == {"github", "sales"}
    assert (tmp_path / "config.yaml.bak").exists()


def test_write_config_creates_missing_file(tmp_path):
    config = tmp_path / "new" / "config.yaml"
    write_config("x", {"url": "u"}, config)
    assert yaml.safe_load(config.read_text()) == {"mcp_servers": {"x": {"url": "u"}}}


def test_cli_print_live(tmp_path, capsys):
    nb = tmp_path / "Sales Demo.ipynb"
    nb.write_text("{}")
    assert main(["hermes-config", str(nb), "--live", "--port", "9000", "--print"]) == 0
    data = yaml.safe_load(capsys.readouterr().out)
    assert data == {"mcp_servers": {"sales_demo": {"url": "http://127.0.0.1:9000/mcp"}}}


def test_cli_writes_config(tmp_path, capsys):
    nb = tmp_path / "a.ipynb"
    nb.write_text("{}")
    config = tmp_path / "config.yaml"
    assert main(["hermes-config", str(nb), "--config", str(config)]) == 0
    assert yaml.safe_load(config.read_text())["mcp_servers"]["a"]["args"][-1] == str(nb.resolve())
