# Quickstart

## Install

```bash
pip install laria-mcp
```

Requires Python 3.10 or newer.

## Serve a notebook over stdio

Most MCP clients, including Hermes, start the server themselves:

```bash
laria serve analysis.ipynb
```

Status messages go to stderr, because stdout is the MCP channel. If a cell fails while the notebook loads, the command exits with `Cell N failed: ...` and serves nothing.

Options:

| Flag | Meaning |
|---|---|
| `--http` | Serve over HTTP instead of stdio |
| `--port N` | HTTP port (default 8765) |
| `--token T` | Require `Authorization: Bearer T` (HTTP only) |
| `--name NAME` | Server name shown to agents (default: notebook name) |
| `--notebook-timeout S` | Per-cell timeout for `run_<notebook>` (default 600) |
| `--no-notebook-tool` | Don't expose the whole-notebook tool |

## Which functions become tools

- Top-level `def` functions defined in the notebook.
- Names starting with `_` are skipped. Async functions are skipped.
- If any function is marked, only marked functions are exposed. Mark a function with `@laria_mcp.tool`, or put `# @tool` on the line above it.
- The type hints become the input schema, and the docstring becomes the description.
- Functions imported from other modules are not exposed.

## Try the demo notebook

```bash
python examples/make_examples.py   # writes examples/sales_demo.ipynb
laria serve examples/sales_demo.ipynb
```

The demo exposes `top_customers`, `orders_for`, `summarize`, `revenue_chart`, and `run_sales_demo`.
