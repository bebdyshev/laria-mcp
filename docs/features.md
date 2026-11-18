# Features

## Result conversion

| Returned value | What the agent gets |
|---|---|
| `None` | `(no return value)` |
| text | the text, capped at 4000 characters |
| numbers and booleans | JSON |
| `pandas.DataFrame` / `Series` | a Markdown table (up to 50 rows, or a 10-row preview) plus a handle |
| matplotlib figure or axes | a PNG image |
| NumPy array | JSON if 100 items or fewer, otherwise a handle |
| dict, list, tuple | pretty JSON, if serializable |
| anything else | a handle and a `repr()` preview |

Anything the function prints is returned after its result as `stdout:`.

## Object handles

Large or non-serializable results stay in the notebook under a handle such as `df#a3f9`. The agent can pass that string to any other tool, and laria-mcp swaps in the stored object before the call.

Example chain: `orders_for(region="EU")` returns `Handle: df#a3f9`, then `summarize(df="df#a3f9")` returns the totals. An unknown handle gives an error result.

## Approval mode

In live mode, `%laria serve --approve` shows **Approve** and **Deny** for each call. The `laria serve` command has no approval prompt. A call waits until a button is clicked. If nobody clicks within `--approval-timeout` seconds (default 60), it is denied with `Approval timed out`. A denied call returns `Call denied by user` to the agent.

## Whole-notebook tool

Tag one code cell `parameters`. In JupyterLab, open the Property Inspector, then Cell Tags, and add `parameters`. Assignments in that cell become the tool's arguments:

```python
region = "EU"   # tag this cell: parameters
year: int = 2026
```

laria-mcp exposes `run_<notebook>(region="EU", year=2026)`. It re-runs a copy of the notebook with those values and returns the printed text, results, and up to five charts. Assignments that aren't simple literals are ignored. Pass `--no-notebook-tool` to disable it.

## Errors

- A tool that raises returns an error with the exception type, message and the last five frames. The server keeps running.
- A failing notebook cell at load time stops `laria serve` with the cell number.
