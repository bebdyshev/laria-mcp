# Hermes Agent setup

Hermes reads MCP servers from the `mcp_servers` section of `~/.hermes/config.yaml`.

## Option A: stdio, Hermes starts the notebook

```bash
laria hermes-config analysis.ipynb
```

This writes an entry like:

```yaml
mcp_servers:
  analysis:
    command: /path/to/python
    args:
    - -m
    - laria_mcp
    - serve
    - /abs/path/analysis.ipynb
```

Use `--print` to see the YAML without writing it. An existing config is backed up to `config.yaml.bak` first.

## Option B: live kernel, the notebook is running

In the notebook, run `%laria serve --token T`, then:

```bash
laria hermes-config analysis.ipynb --live --port 8765 --token T
```

The entry points at `http://127.0.0.1:8765/mcp` and includes the bearer token header.

## Applying the change

In Hermes, run `/reload-mcp`, or restart Hermes.

## Timeouts

Hermes stops a tool call after 120 seconds by default. Use `--timeout` to raise it for the whole-notebook tool, for example `--timeout 630` to match the default 600-second cell limit.
