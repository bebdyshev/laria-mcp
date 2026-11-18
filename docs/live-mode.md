# Live kernel mode

Live mode serves the functions of the notebook you are running, so agents use the data already loaded in the kernel.

```python
%load_ext laria_mcp
%caduceus serve
```

Commands:

| Command | What it does |
|---|---|
| `%laria serve [--port N] [--token T] [--approve] [--approval-timeout S] [--notebook PATH] [--notebook-timeout S] [--name N]` | Start an HTTP server on `127.0.0.1` and print a Hermes config block |
| `%laria status` | Show the URL and tool names |
| `%laria stop` | Stop the server |

Notes:

- Only `127.0.0.1` is used. Add `--token` on shared machines.
- A panel shows each agent call, with arguments, duration and result preview.
- **Hot reload:** after each cell you run, the tool list is refreshed and connected clients are told it changed. Failed cells are ignored.
- Agent tool calls run one at a time. A call does not wait for a cell you are running, so avoid running a cell that changes shared state while an agent is calling.
- If your client ignores the change notification, run `/reload-mcp` in Hermes.
