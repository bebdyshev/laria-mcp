"""Generate examples/sales_demo.ipynb (run: python examples/make_examples.py)."""

from pathlib import Path

import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

cells = [
    new_markdown_cell("# Sales demo\nServe this notebook to an AI agent with `%laria serve`."),
    new_code_cell("%load_ext laria_mcp\nimport numpy as np\nimport pandas as pd\nimport matplotlib.pyplot as plt"),
    new_code_cell("region = 'EU'\nyear = 2026", metadata={"tags": ["parameters"]}),
    new_code_cell(
        "rng = np.random.default_rng(7)\n"
        "orders = pd.DataFrame({\n"
        "    'customer': rng.choice(['Acme', 'Globex', 'Initech', 'Umbrella', 'Hooli', 'Stark'], 2000),\n"
        "    'region': rng.choice(['EU', 'US', 'APAC'], 2000),\n"
        "    'month': rng.integers(1, 13, 2000),\n"
        "    'amount': rng.gamma(2.0, 150.0, 2000).round(2),\n"
        "})"
    ),
    new_code_cell(
        "def top_customers(n: int = 5, region: str = 'EU') -> pd.DataFrame:\n"
        "    \"\"\"Return the n customers with the highest total revenue in a region (EU, US or APAC).\"\"\"\n"
        "    sub = orders[orders.region == region]\n"
        "    return sub.groupby('customer', as_index=False).amount.sum().nlargest(n, 'amount')\n"
        "\n"
        "def orders_for(region: str = 'EU', min_amount: float = 0.0) -> pd.DataFrame:\n"
        "    \"\"\"Return all orders in a region with amount >= min_amount (returns a handle for large results).\"\"\"\n"
        "    return orders[(orders.region == region) & (orders.amount >= min_amount)]\n"
        "\n"
        "def summarize(df: pd.DataFrame) -> dict:\n"
        "    \"\"\"Summarize an orders DataFrame (pass a df# handle): count, total and mean amount.\"\"\"\n"
        "    return {'orders': int(len(df)), 'total': float(df.amount.sum()), 'mean': float(df.amount.mean())}\n"
        "\n"
        "def revenue_chart(region: str = 'EU'):\n"
        "    \"\"\"Plot monthly revenue for a region and return the chart.\"\"\"\n"
        "    monthly = orders[orders.region == region].groupby('month').amount.sum()\n"
        "    fig, ax = plt.subplots(figsize=(6, 3))\n"
        "    monthly.plot(kind='bar', ax=ax, title=f'{region} revenue by month')\n"
        "    plt.close(fig)\n"
        "    return fig"
    ),
    new_code_cell(
        "report = orders[orders.region == region]\n"
        "print(f'{region} {year}: {len(report)} orders, total {report.amount.sum():,.2f}')\n"
        "top_customers(3, region)"
    ),
    new_code_cell("# %laria serve --approve"),
]

nb = new_notebook(cells=cells)
nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
out = Path(__file__).with_name("sales_demo.ipynb")
nbformat.write(nb, out)
print(f"wrote {out}")
