#!/usr/bin/env python
"""Plot a suggestion network from an edge-list CSV.

Generic CLI wrapper around ``suggests.nets.plot_network``. Reads an edge list
(as produced by ``suggests.to_edgelist`` / ``add_metanodes``) and renders a
community-colored, degree-sized network plot.

Examples:
    python -m suggests.scripts.plot --edges edges.csv --root abortion
    suggests-plot --edges edges.csv --root abortion --save-to out.png

Plotting requires the optional visualization dependencies (matplotlib,
igraph, networkx, adjustText). Install them with the ``viz`` extra:
    pip install "suggests[viz]"
"""

import argparse
import sys

import polars as pl


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="suggests-plot",
        description="Plot a suggestion network from an edge-list CSV.",
    )
    p.add_argument(
        "--edges",
        required=True,
        help="Path to an edge-list CSV with 'source' and 'target' columns.",
    )
    p.add_argument(
        "--root",
        required=True,
        help="Root node used to extract the main connected component.",
    )
    p.add_argument(
        "--save-to",
        default="",
        help="Output image path. If omitted, the figure is not written to disk.",
    )
    p.add_argument(
        "--label-col",
        default="target_add",
        help="Column for node labels ('target_add' for metanode labels, "
        "'target' for full suggestion text).",
    )
    p.add_argument(
        "--layout",
        default="fr",
        choices=["fr", "drl"],
        help="igraph layout algorithm.",
    )
    p.add_argument("--size-scale", type=float, default=500)
    p.add_argument("--label-quantile", type=float, default=0.99)
    p.add_argument("--label-alpha", type=float, default=1.0)
    p.add_argument("--spacing", type=float, default=1.0)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--font-size", type=float, default=1.0)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        import matplotlib

        matplotlib.use("Agg")

        from suggests.nets import plot_network
    except ImportError as e:
        print(
            f"Plotting requires the visualization dependencies ({e.name or e}). "
            'Install them with: pip install "suggests[viz]"',
            file=sys.stderr,
        )
        return 1

    edges = pl.read_csv(args.edges)
    fig = plot_network(
        edges,
        root=args.root,
        label_col=args.label_col,
        layout=args.layout,
        size_scale=args.size_scale,
        label_quantile=args.label_quantile,
        label_alpha=args.label_alpha,
        spacing=args.spacing,
        seed=args.seed,
        font_size=args.font_size,
        save_to=args.save_to,
    )
    n_labels = len(fig.axes[0].texts) if fig.axes else 0
    dest = args.save_to or "(not saved; pass --save-to to write a file)"
    print(f"Plotted {edges.shape[0]} edges, {n_labels} labels -> {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
