# How laria-mcp compares

| Tool | What it does | Gap it leaves |
|---|---|---|
| Datalayer jupyter-mcp-server, mcp-jupyter-notebook, universal-notebook-mcp, nteract | Let an agent *drive* a notebook: edit and run cells | The notebook's functions are not served as tools |
| jupyter-server-mcp | Registers `module:function` strings from server config | Needs config files and importable modules; not notebook-native |
| marimo `--mcp` | Turns a marimo notebook into an MCP server | Only for marimo notebooks, not Jupyter |
| **laria-mcp** | Serves a Jupyter notebook's own functions as MCP tools | Live kernel, hot reload, handles, approval, and whole-notebook runs for Jupyter |

Use the driving servers when an agent should edit notebooks for you. Use laria-mcp when a notebook's analysis should be a tool an agent calls.
