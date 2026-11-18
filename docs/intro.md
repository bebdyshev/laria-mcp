# laria-mcp

Turn any Jupyter notebook into an MCP server, so AI agents can call its functions as tools.

## Motivation

Agents can already *drive* notebooks: they add cells, run them and read the output. What they can't do is use the analysis *inside* a notebook as a typed API. Today that means rewriting the functions into a package or a server first. laria-mcp serves the notebook's own functions, with the data already loaded.

## What's new

- **Jupyter-native.** Works on a `.ipynb` file from the command line, or from the notebook you're already running.
- **Live kernel.** `%laria serve` exposes functions over the running kernel, so agents see the data you have loaded right now.
- **Hot reload.** Edit a function and rerun its cell. Connected agents get a tool-list update.
- **Object handles.** Big results (tables, arrays, models) stay in the notebook as `df#a3f9`-style handles that other tools accept.
- **Approval mode.** `--approve` shows Approve / Deny buttons for every agent call.
- **Whole-notebook tool.** Tag a cell `parameters` and the notebook becomes one tool that re-runs it with new values.
- **No LLM inside.** The package makes no model calls. The agent is the client.

## The name

Hermes Agent is our reference client. laria-mcp is what lets an agent carry a notebook's functions with it.

## Example

```python
def top_customers(n: int = 5, region: str = "EU") -> pd.DataFrame:
    """Return the n customers with the highest revenue in a region."""
    ...
```

An agent connected to this notebook sees a `top_customers` tool with an integer `n` and a string `region`. It can call it and get back a table. See [](quickstart.md) to try the bundled `sales_demo.ipynb`.
