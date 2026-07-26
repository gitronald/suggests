"""Parsing functions for Google and Bing."""

import html
import re
from typing import Any

import polars as pl
from bs4 import BeautifulSoup

from . import logger

log = logger.Logger().start(__name__)


def strip_html(string: str) -> str:
    """Strip HTML tags from a string."""
    return re.sub("<[^<]+?>", "", string)


def parse_google(json_data: list[Any] | None, qry: str = "") -> dict[str, Any]:
    """Parse Google autocomplete API response.

    Args:
        json_data: Raw JSON response from Google autocomplete API
        qry: Original query string

    Returns:
        Dictionary with 'suggests', 'self_loops', and 'tags' keys
    """

    def google_parser(json_data: list[Any]) -> tuple[str, list[str], list[Any]]:

        def suggest_parser(s: str) -> str:
            return html.unescape(strip_html(s))

        qry = json_data[0]
        suggests = [
            suggest_parser(s[0] + " - " + s[3]["b"] if s[1] == 46 else s[0])
            for s in json_data[1]
        ]
        tags = json_data[2]
        return qry, suggests, tags

    parsed: dict[str, Any]
    try:
        if json_data is None:
            raise ValueError("json_data is None")
        qry, suggests, tags = google_parser(json_data)
        self_loops = [i for i, s in enumerate(suggests) if s == qry]
        parsed = {"suggests": suggests, "self_loops": self_loops, "tags": tags}
    except Exception:
        log.exception("ERROR PARSING GOOGLE:\n%s", json_data)
        parsed = {"suggests": [], "self_loops": [], "tags": []}
    return parsed


def parse_bing(raw_html: str, qry: str = "") -> dict[str, Any]:
    """Parse Bing autocomplete API response.

    Args:
        raw_html: Raw HTML response from Bing autocomplete API
        qry: Original query string

    Returns:
        Dictionary with 'suggests', 'self_loops', and 'tags' keys
    """

    def bing_parser(raw_html: str) -> list[str]:
        soup = BeautifulSoup(raw_html, "html.parser")
        return [
            html.unescape(div.text) for div in soup.find_all("div", {"class": "sa_tm"})
        ]

    parsed: dict[str, Any]
    try:
        suggests = bing_parser(raw_html)
        self_loops = [i for i, s in enumerate(suggests) if s == qry]
        parsed = {"suggests": suggests, "self_loops": self_loops, "tags": []}
    except Exception:
        log.exception("ERROR PARSING BING:\n%s", raw_html)
        parsed = {"suggests": [], "self_loops": [], "tags": []}
    return parsed


def to_edgelist(tree: list[dict[str, Any]], self_loops: bool = False) -> pl.DataFrame:
    """Convert suggestions tree to an edge list DataFrame.

    Args:
        tree: List of suggestion dictionaries from get_suggests_tree
        self_loops: Whether to include self-loop edges

    Returns:
        DataFrame with edge list columns (root, edge, source, target, rank, etc.)
    """
    assert isinstance(tree, list), "Must pass a list of dicts"

    schema = {
        "root": pl.String,
        "edge": pl.String,
        "source": pl.String,
        "target": pl.String,
        "rank": pl.Int64,
        "depth": pl.Int64,
        "search_engine": pl.String,
        "datetime": pl.String,
    }
    cols: dict[str, list[Any]] = {name: [] for name in schema}

    def append(
        root: str,
        edge: str | None,
        source: str,
        target: str | None,
        rank: int,
        depth: int,
        engine: str,
        dt: str,
    ) -> None:
        cols["root"].append(root)
        cols["edge"].append(edge)
        cols["source"].append(source)
        cols["target"].append(target)
        cols["rank"].append(rank)
        cols["depth"].append(depth)
        cols["search_engine"].append(engine)
        cols["datetime"].append(dt)

    for row in tree:
        if self_loops:
            suggests = row["suggests"]
        else:
            suggests = [s for s in row["suggests"] if s != row["qry"]]

        if suggests:
            for rank, s in enumerate(suggests):
                # s is already unescaped by parse_google/parse_bing
                append(
                    row["root"],
                    str((row["qry"], s)),
                    row["qry"],
                    s,
                    rank + 1,
                    row["depth"],
                    row["source"],
                    row["datetime"],
                )
        elif row["depth"] == 0:  # If no suggests at root, append empty root
            append(
                row["root"],
                None,
                row["qry"],
                None,
                1,
                row["depth"],
                row["source"],
                row["datetime"],
            )

    return pl.DataFrame(cols, schema=schema)


def add_parent_nodes(edges: pl.DataFrame) -> pl.DataFrame:
    """Add parent and grandparent node columns to an edge list.

    Args:
        edges: Edge list DataFrame from to_edgelist

    Returns:
        DataFrame with 'parent' and 'grandparent' columns added
    """
    edges_original = edges

    # Get parent node
    parent = edges.select(
        "root",
        pl.col("source").alias("parent"),
        pl.col("target").alias("source"),
        (pl.col("depth") + 1).alias("depth"),
        "search_engine",
    )
    edges = edges.join(
        parent,
        on=["root", "source", "depth", "search_engine"],
        how="left",
    )

    # Get grandparent node
    grandparent = edges.select(
        "root",
        pl.col("parent").alias("grandparent"),
        pl.col("source").alias("parent"),
        pl.col("target").alias("source"),
        (pl.col("depth") + 1).alias("depth"),
        "search_engine",
    )
    edges = edges.join(
        grandparent,
        on=["root", "parent", "source", "depth", "search_engine"],
        how="left",
    )

    # Resolve merge points
    merged_parents = edges.group_by("edge", maintain_order=True).agg(
        pl.when(pl.col("grandparent").is_not_null().any())
        .then(pl.col("grandparent").drop_nulls().first())
        .otherwise(pl.lit(None))
        .first()
        .alias("grandparent"),
        pl.when(pl.col("parent").is_not_null().any())
        .then(pl.col("parent").drop_nulls().first())
        .otherwise(pl.lit(None))
        .first()
        .alias("parent"),
    )
    return edges_original.join(merged_parents, on="edge", how="left")


def _compute_metanode(row: dict[str, Any]) -> dict[str, str | None]:
    """Compute source_add and target_add for a single row."""
    grandparent: list[str] = (
        [] if row["grandparent"] is None else row["grandparent"].split(" ")
    )
    parent: list[str] = [] if row["parent"] is None else row["parent"].split(" ")

    source = row["source"].split(" ")
    target = row["target"].split(" ")

    source_add = [i for i in source if i not in set(parent)]
    target_add = [i for i in target if i not in set(source)]

    parent_add = [i for i in parent if i not in set(grandparent)]

    if not source_add:  # information removed
        source_add = parent_add
    if not target_add:
        log.debug("circle back: %s", source_add)
        target_add = source_add

    return {
        "source_add": " ".join(source_add) if source_add else None,
        "target_add": " ".join(target_add) if target_add else None,
    }


def add_metanodes(edges: pl.DataFrame) -> pl.DataFrame:
    """Compute association metanodes by diffing parent/grandparent tokens.

    Adds 'source_add' and 'target_add' columns representing the new
    information contributed at each step in the suggestion tree.

    Args:
        edges: Edge list DataFrame with parent/grandparent columns

    Returns:
        DataFrame with 'source_add' and 'target_add' columns added
    """
    meta = edges.select(
        pl.struct(["source", "target", "parent", "grandparent"])
        .map_elements(
            _compute_metanode,
            return_dtype=pl.Struct({"source_add": pl.String, "target_add": pl.String}),
        )
        .alias("_meta")
    ).unnest("_meta")
    return edges.hstack(meta)
