# Course JupyterHub

Hermes is preinstalled in the course pod. Hermes runs in the same pod as your notebook, so it connects to `localhost`.

## Install

In a JupyterHub terminal:

```bash
pip install --user laria-mcp
pip check
laria --help
```

The package needs `mcp` 1.x (`>=1.20,<2`). Record the Python, Hermes and `mcp` versions here after the first check on the hub.

## Run

1. Open a notebook and run `%load_ext laria_mcp`, then `%laria serve --token <random string>`.
2. In a pod terminal, run `laria hermes-config <notebook>.ipynb --live --token <same string>`.
3. Start Hermes and ask it a question about the notebook.

The server listens only on `127.0.0.1`, and the token keeps other users on a shared node out.
