# 60-second demo script

Six beats, ten seconds each. One speaker per beat, one action per beat. If a beat
runs long, cut narration — never cut the click that shows the feature.

Run this from the `examples/` directory so the notebook path is short on screen.

## Pre-flight (ten minutes before)

```bash
pip install --user -U laria-mcp
python -c "import laria_mcp; print(laria_mcp.__version__)"
hermes --version
```

1. Open `sales_demo.ipynb` and **Run All**. The last cells must print
   `EU 2026: ... orders, total ...` and show the table.
2. Keep a second terminal open in the same directory:
   `laria hermes-config sales_demo.ipynb --live --port 8765 --token demo123`
3. Start Hermes and send one throwaway question, so the model is warm and the
   tool list is loaded.
4. Close every other notebook tab, hide the file browser, raise the font size
   (Ctrl+Shift+Plus in JupyterLab), and put a visible 60-second timer on screen.
5. Rehearse twice with the timer. The second rehearsal is the one you keep.

## Beats

| Time | Speaker | Action | What the audience sees |
|---|---|---|---|
| 0:00–0:10 | Kerey | No typing. “Agents can drive a notebook. laria-mcp lets the notebook serve the agent.” | Title slide with `pip install laria-mcp`, repo and docs links |
| 0:10–0:20 | Member 6 | In the notebook: `%laria serve --approve --token demo123` | Call-log panel appears; cell prints the 5-tool list and a Hermes YAML block |
| 0:20–0:30 | Bibek | In Hermes: “Who are the top 3 customers in the US?” Click **Approve** | `top_customers` row in the panel; table plus `Handle: df#...` in Hermes |
| 0:30–0:40 | Matthias | Add and run the `best_month` cell (text below). In Hermes: “Which month had the highest EU revenue?” | Either the new tool appears automatically, or `/reload-mcp` does it — say which one out loud |
| 0:40–0:50 | Vladan | In Hermes: “Plot EU revenue by month.” Click **Deny**. Ask again, click **Approve** | Denial message, then the chart rendered in the chat |
| 0:50–1:00 | Daniil | In Hermes: “Re-run the sales report for APAC.” Then show PyPI + docs links | `run_sales_demo(region="APAC")` output; closing slide |

### Beat 2 — the one command

```python
%laria serve --approve --token demo123
```

Say: “HTTP on localhost, bearer token, approval on. The agent sees only the
functions in this notebook.”

### Beat 4 — the hot-reload cell

```python
def best_month(region: str = "EU") -> int:
    """Return the month with the highest revenue in a region."""
    monthly = orders[orders.region == region].groupby("month").amount.sum()
    return int(monthly.idxmax())
```

If Hermes lists tools only after `/reload-mcp`, that is the expected fallback;
say “clients that ignore the change notification use `/reload-mcp`” and move on.

### Beat 5 — deny, then approve

Ask the same chart question twice. The first call must be denied on purpose:
the point is that a human stays in the loop. Do not wait for the 60-second
timeout on stage.

### Beat 6 — close

> “Install it with `pip install laria-mcp`. Code and docs are on the slide.
> One notebook, five tools, no LLM inside the package.”

## Failure playbook

| Symptom | Fix on stage |
|---|---|
| `Address already in use` | `%laria stop`, then `%laria serve --port 8766 --approve --token demo123`; update the Hermes entry with `laria hermes-config ... --port 8766` and `/reload-mcp` |
| Hermes still shows the old tool list | `/reload-mcp` in Hermes |
| Table call takes a few seconds | Keep talking; the panel shows the duration |
| Wrong notebook path in Hermes | Use an absolute path in `laria hermes-config` |
| Approval buttons do not react | Click once, wait two seconds; if still stuck, `%laria stop` and restart with `--approval-timeout 30` |
| Chart missing | Run `%matplotlib inline` in the first cell and re-ask |
| Whole-notebook tool is slow | It re-executes the notebook; that is the point — narrate it, do not interrupt it |

## Do not

- Do not debug live. If a beat breaks twice in rehearsal, cut the beat and
  explain it on the closing slide instead.
- Do not run cells while Hermes is calling a tool; calls are serialized and the
  demo will look frozen.
- Do not claim Hermes auto-reloads unless the rehearsal showed it. Use the
  `/reload-mcp` wording from the playbook.
