# laria_mcp — Design Spec

**Date:** 2026-11-17 · **Due:** 2026-11-22 23:59 · **Team:** group27 (cs1302a)

## 1. Summary

`laria_mcp` turns a Jupyter notebook into an MCP (Model Context Protocol) server, so AI agents
such as Hermes, Claude Code or Claude Desktop can call the notebook's functions as typed tools.

Hermes Agent is our reference client.

- Install: `pip install laria-mcp`
- Import: `import laria_mcp`
- CLI: `laria serve analysis.ipynb`
- Notebook magic: `%load_ext laria_mcp` then `%laria serve`

**The package itself contains no LLM and makes no LLM calls.** The LLM lives in the MCP client
(the agent). laria_mcp is a server only.

## 2. Motivation and positioning

| Existing tool | What it does | Gap |
|---|---|---|
| Datalayer jupyter-mcp-server, mcp-jupyter-notebook, universal-notebook-mcp, nteract | Let an agent *drive* a notebook (edit/run cells) | Opposite direction: the notebook does not become an API |
| jupyter-server-mcp | Registers `module:function` strings from server config | Not notebook-native; needs config files and importable modules |
| marimo `--mcp` | Turns a marimo notebook into an MCP server | marimo only, not Jupyter |

Pitch: *marimo has this; Jupyter, which most people use, doesn't. laria_mcp adds it, plus live-kernel
serving, hot reload, object handles and human approval.*

## 3. Features (all in scope)

1. **CLI mode**: `laria serve <notebook>` executes the notebook and serves its tools over
   `stdio` (default) or HTTP (`--http --port N`).
2. **Live kernel mode**: `%laria serve [--port N] [--approve] [--token T]` serves tools from the
   *running* kernel over HTTP on `127.0.0.1`. Tools see live state (loaded data, trained models).
   Also `%laria stop` and `%laria status`.
3. **Call-log widget**: every agent call appears in the notebook: tool name, arguments, duration,
   result preview, error if any.
4. **Hot reload**: after each executed cell, tools are rediscovered; if the set or any signature
   changed, the server sends MCP `notifications/tools/list_changed`.
5. **Whole notebook as a tool**: if a cell is tagged `parameters` (papermill convention), the
   notebook is also exposed as one tool `run_<notebook_name>(**params)`, which re-executes a copy
   with injected values and returns its final outputs.
6. **Object handles**: large results (DataFrame over a configurable row limit, ndarray, models,
   any non-serializable object) are stored server-side and returned as a handle string such as
   `df#a3f9` plus a preview. Any tool argument whose value is a known handle string is replaced
   by the stored object before the call.
7. **Approval mode**: with `--approve`, each call shows Approve / Deny buttons in the notebook and
   blocks until clicked (timeout configurable, default 60 s, timeout = deny).
8. **Hermes integration**: `%laria serve` prints a ready-to-paste `mcp_servers` YAML block;
   `laria hermes-config <notebook> [--live --port N]` writes it into `~/.hermes/config.yaml`
   (creates a `.bak` first).

## 4. Tool discovery rules

- Candidates: top-level `def` functions defined in notebook code cells (found by `ast`).
- Exposed by default: names not starting with `_`.
- If any function is marked with the `@laria_mcp.tool` decorator or a `# @tool` comment on the
  line above it, **only** marked functions are exposed.
- Tool description = docstring (first paragraph; full docstring kept in description).
- Input schema = generated from type hints by the MCP SDK (`FastMCP`). Missing hints → `Any`.
- Functions imported from other modules are not exposed.
- Live mode has no `.ipynb` to parse: candidates are callables in the kernel's `user_ns` whose
  `__module__ == "__main__"`; markers are read from `inspect.getsource` when available.

## 5. Architecture

Package layout `src/laria_mcp/`:

| Module | Responsibility | Depends on |
|---|---|---|
| `loader.py` | Read `.ipynb` (`nbformat`), execute code cells in order into a namespace dict; on failure raise `NotebookLoadError(cell_index, exc)` | nbformat |
| `discovery.py` | From source cells + namespace, return `list[ToolSpec]` (name, callable, doc); find `parameters` cell | ast |
| `results.py` | Convert return values to MCP content: DataFrame → markdown table, matplotlib Figure → PNG image, str/number/dict/list → text/JSON; large or non-serializable objects → handle + `repr()` preview (capped at 4000 chars) | handles |
| `handles.py` | `HandleStore`: `put(obj) -> "type#id"`, `get(handle)`, `resolve_args(kwargs)` | — |
| `server.py` | `build_server(registry, *, approve_hook, log_hook) -> FastMCP`; run `stdio` or streamable HTTP; optional bearer token; serializes calls with a lock | mcp, results, handles |
| `magic.py` | IPython extension: `%laria` magic, server on background thread, wires hooks to widgets | server, discovery, widget, hotreload |
| `hotreload.py` | `post_run_cell` hook → rediscover from `user_ns` → diff → update registry → emit `tools/list_changed` | discovery, server |
| `widget.py` | `CallLog` and `ApprovalPrompt` (ipywidgets) | ipywidgets |
| `notebook_tool.py` | Build the `run_<name>` tool: inject params, execute copy with `nbclient`, collect outputs | nbclient, results |
| `cli.py` | `laria serve`, `laria hermes-config` | everything above |

**Data flow (live mode):** agent → HTTP → `server.py` → (approval hook → widget) → resolve handles
→ call function under run lock → `results.py` → MCP response; log hook → `CallLog` widget.

**Concurrency:** tool calls run on the server thread while the user may run cells. A single
`threading.Lock` serializes tool calls; v1 does not try to interleave with user cells.

**Security:** HTTP binds to `127.0.0.1` only. Optional `--token`; when set, requests without
`Authorization: Bearer <token>` get 401. Needed on the shared JupyterHub.

## 6. Error handling

| Situation | Behaviour |
|---|---|
| Tool raises | MCP error result: exception type, message, traceback trimmed to last 5 frames. Server stays up. |
| Notebook cell fails at load (CLI) | Exit non-zero with `Cell N failed: <error>`. No partial serving. |
| Result not convertible | Stored as a handle; response is the handle plus a `repr()` preview capped at 4000 chars. |
| Unknown handle in arguments | Error result `Unknown handle 'df#xxxx'`. |
| Approval denied or timed out | Error result `Call denied by user` / `Approval timed out`. |
| Whole-notebook run exceeds timeout | Per-cell timeout (default 600 s) stops the run; error result names the timeout. Generated Hermes config sets `timeout` to 630 s. |
| Port in use | `%laria serve` reports it and suggests `--port`. |

## 7. Environments and demo

- **Laptop:** local Jupyter + local Hermes. CLI mode via `command:`; live mode via `url:`.
- **Course JupyterHub:** Hermes is preinstalled in the pod. Run `%laria serve` in a notebook,
  open a pod terminal, Hermes connects to `http://127.0.0.1:<port>/mcp`.
- **Requirements:** Python ≥ 3.10. Dependencies: `mcp>=1.20,<2` (1.x `FastMCP`; 2.x renamed it and
  the hub/Hermes use 1.x), `nbformat`, `nbclient`, `ipywidgets`, `ipython`, `pyyaml`. Optional extras: `pandas`, `matplotlib` (handled if present, not required).
- **Day-1 checks on JupyterHub:** `pip install laria-mcp` has no conflicts; record Hermes version;
  test whether Hermes honours `tools/list_changed` (fallback: `/reload-mcp`).

**60-second demo (one beat per member):** open notebook → `%laria serve` → paste config into
Hermes → ask a data question → call appears in the call-log widget → edit a function and rerun →
Hermes uses the new version → whole-notebook report tool → approval mode deny → close.

## 8. Testing

- `pytest`; test notebooks are generated per test by a `make_notebook` fixture (no committed fixture files).
- Server tests use the MCP SDK in-memory client session: real protocol, no network, no LLM.
- Magic/hot-reload tests use IPython's `InteractiveShell`.
- Widget tests check state transitions (pending → approved/denied) without a browser.
- CI: GitHub Actions, Python 3.10, 3.11, 3.12. Release workflow publishes to PyPI on tag `v*`.

## 9. Team ownership

| Owner | Area |
|---|---|
| Kerey | Release & publishing: `pyproject.toml`, CI, PyPI releases, docs site (Jupyter Book on GitHub Pages), example notebooks, demo script |
| Member 6 | Core engine: `loader.py`, `discovery.py` |
| Bibek | Server & data: `server.py`, `results.py`, `handles.py` |
| Matthias | Live kernel: `magic.py`, `hotreload.py` |
| Vladan | Notebook UI: `widget.py` |
| Daniil | Notebook-as-tool & Hermes: `notebook_tool.py`, `cli.py hermes-config`, Hermes compatibility testing |

Everyone writes tests for their own module and commits daily.

## 10. Schedule

| Day | Date | Milestone |
|---|---|---|
| 1 | Nov 18 | loader + discovery + server + `laria serve` (stdio) working; **v0.1.0 on PyPI**; repo homepage set; JupyterHub install check |
| 2 | Nov 19 | results + handles; `%laria serve` live mode over HTTP |
| 3 | Nov 20 | hot reload; call-log widget; approval mode |
| 4 | Nov 21 | whole-notebook tool; `hermes-config`; docs site live |
| 5 | Nov 22 | JupyterHub end-to-end test; final release; demo rehearsal; submit |

## 11. Out of scope

- Running agents or LLMs inside the package.
- Exposing notebook *editing* to agents (other tools do this).
- Remote access from outside the JupyterHub pod (no proxying).
- Interleaving tool calls with user cell execution.
