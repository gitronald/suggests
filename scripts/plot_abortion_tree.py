#!/usr/bin/env python
"""Plot the abortion suggestion tree network from the test fixture."""

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import polars as pl
from suggests.nets import plot_network

FIXTURE_DIR = Path(__file__).parent.parent / "tests" / "fixtures"
EDGES_CSV = FIXTURE_DIR / "abortion-20260312-122801-edges.csv"
IMG_DIR = Path(__file__).parent.parent / "img"


def main(save_to: str = "") -> None:
    edges = pl.read_csv(EDGES_CSV)
    save_to = save_to or str(IMG_DIR / "abortion_plot_pagerank_python.png")
    fig = plot_network(
        edges,
        root="abortion",
        label_quantile=0.98,
        label_alpha=0.7,
        spacing=2.0,
        save_to=save_to,
    )
    print(f"Saved to {save_to} ({edges.shape[0]} edges, {len(fig.axes[0].texts)} labels)")


if __name__ == "__main__":
    main(save_to=sys.argv[1] if len(sys.argv) > 1 else "")
