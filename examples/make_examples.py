"""Generate examples/sales_demo.ipynb.

Run from anywhere:  python examples/make_examples.py
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

OUT_PATH = Path(__file__).resolve().with_name("sales_demo.ipynb")


def code(src: str, **kwargs):
    """Code cell from an indented triple-quoted string."""
    return new_code_cell(dedent(src).strip("\n"), **kwargs)


def build_notebook() -> nbformat.NotebookNode:
    cells = [
        new_markdown_cell(
            "# Sales demo\n"
            "Serve this notebook to an AI agent with `%laria serve`."
        ),
        code(
            """
            %load_ext laria_mcp
            import numpy as np
            import pandas as pd
            import matplotlib.pyplot as plt
            """
        ),
        # Tagged so tools like papermill can inject parameters here.
        code(
            """
            region = 'EU'
            year = 2026
            """,
            metadata={"tags": ["parameters"]},
        ),
        code(
            """
            REGIONS = ['EU', 'US', 'APAC']
            CUSTOMERS = ['Acme', 'Globex', 'Initech', 'Umbrella', 'Hooli', 'Stark']
            N_ORDERS = 2000

            rng = np.random.default_rng(7)
            orders = pd.DataFrame({
                'customer': rng.choice(CUSTOMERS, N_ORDERS),
                'region': rng.choice(REGIONS, N_ORDERS),
                'month': rng.integers(1, 13, N_ORDERS),
                'amount': rng.gamma(2.0, 150.0, N_ORDERS).round(2),
            })
            """
        ),
        code(
            '''
            def _check_region(region: str) -> None:
                if region not in REGIONS:
                    raise ValueError(f"Unknown region {region!r}; expected one of {REGIONS}")


            def top_customers(n: int = 5, region: str = 'EU') -> pd.DataFrame:
                """Return the n customers with the highest total revenue in a region (EU, US or APAC)."""
                _check_region(region)
                sub = orders[orders.region == region]
                return sub.groupby('customer', as_index=False).amount.sum().nlargest(n, 'amount')


            def orders_for(region: str = 'EU', min_amount: float = 0.0) -> pd.DataFrame:
                """Return all orders in a region with amount >= min_amount (returns a handle for large results)."""
                _check_region(region)
                return orders[(orders.region == region) & (orders.amount >= min_amount)]


            def summarize(df: pd.DataFrame) -> dict:
                """Summarize an orders DataFrame (pass a df# handle): count, total and mean amount."""
                return {
                    'orders': int(len(df)),
                    'total': float(df.amount.sum()),
                    'mean': float(df.amount.mean()) if len(df) else 0.0,
                }


            def revenue_chart(region: str = 'EU'):
                """Plot monthly revenue for a region and return the chart."""
                _check_region(region)
                monthly = (
                    orders[orders.region == region]
                    .groupby('month').amount.sum()
                    .reindex(range(1, 13), fill_value=0.0)  # always show all 12 months
                )
                fig, ax = plt.subplots(figsize=(6, 3))
                monthly.plot(kind='bar', ax=ax, title=f'{region} revenue by month')
                ax.set_xlabel('Month')
                ax.set_ylabel('Revenue')
                fig.tight_layout()
                plt.close(fig)  # avoid a duplicate inline render; the caller gets the figure
                return fig
            '''
        ),
        code(
            """
            report = orders[orders.region == region]
            print(f'{region} {year}: {len(report)} orders, total {report.amount.sum():,.2f}')
            top_customers(3, region)
            """
        ),
        code("# %laria serve --approve"),
    ]

    nb = new_notebook(cells=cells)
    nb.metadata["kernelspec"] = {
        "name": "python3",
        "display_name": "Python 3",
        "language": "python",
    }
    nb.metadata["language_info"] = {"name": "python"}
    return nb


def main() -> None:
    nb = build_notebook()
    nbformat.validate(nb)  # fail loudly on a malformed notebook
    nbformat.write(nb, OUT_PATH)
    print(f"wrote {OUT_PATH}")


if __name__ == "__main__":
    main()