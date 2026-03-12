"""Parsing functions for Google and Bing."""

import html
import re
import urllib.parse
from collections import OrderedDict

import polars as pl
from bs4 import BeautifulSoup

from . import logger

log = logger.Logger().start(__name__)


def get_source_target_columns(edges: pl.DataFrame) -> pl.DataFrame:
    """Extract source and target columns from edge tuples.

    Args:
        edges: DataFrame with an 'edge' column of string tuple representations

    Returns:
        DataFrame with source and target columns appended
    """
    edge_details = (
        edges.select(
            pl.col("edge")
            .str.strip_chars("()")
            .str.splitn(", ", 2)
            .struct.rename_fields(["source", "target"])
        )
        .unnest("edge")
        .with_columns(
            pl.col("source").str.strip_chars("'\""),
            pl.col("target").str.strip_chars("'\""),
        )
    )
    return pl.concat([edges, edge_details], how="horizontal")


def parse_raw_data(raw_data: pl.DataFrame, source: str) -> pl.DataFrame:
    """Parse raw aggregated data into edge lists.

    Args:
        raw_data: DataFrame with a 'data' column of raw API responses
        source: Search engine name ('google' or 'bing')

    Returns:
        DataFrame with parsed suggestion columns appended
    """
    parser = parse_google if source == "google" else parse_bing
    parsed = [parser(row) for row in raw_data["data"].to_list()]
    parsed_df = pl.DataFrame(parsed)
    return pl.concat([raw_data, parsed_df], how="horizontal")


def get_edges(data: pl.DataFrame) -> pl.DataFrame:
    """Parse raw data grouped by source and convert to edge lists.

    Args:
        data: DataFrame with 'source' and 'data' columns

    Returns:
        Combined edge list DataFrame
    """
    clean_data = [
        parse_raw_data(group_df, source_name)
        for source_name, group_df in data.group_by("source", maintain_order=True)
    ]
    return pl.concat([to_edgelist(df.to_dicts()) for df in clean_data])


def strip_html(string: str) -> str:
    """Strip HTML tags from a string."""
    return re.sub("<[^<]+?>", "", string)


def parse_google(json_data: list, qry: str = "") -> dict[str, list]:
    """Parse Google autocomplete API response.

    Args:
        json_data: Raw JSON response from Google autocomplete API
        qry: Original query string

    Returns:
        Dictionary with 'suggests', 'self_loops', and 'tags' keys
    """

    def google_parser(json_data: list) -> tuple[str, list[str], list]:

        def suggest_parser(s: str) -> str:
            return html.unescape(strip_html(s))

        qry = json_data[0]
        suggests = [
            s[0] + " - " + s[3]["b"] if s[1] == 46 else s[0] for s in json_data[1]
        ]
        suggests = [suggest_parser(s) for s in suggests]
        tags = json_data[2]
        return qry, suggests, tags

    try:
        qry, suggests, tags = google_parser(json_data)
        self_loops = [i for i, s in enumerate(suggests) if s == qry]
        parsed = {"suggests": suggests, "self_loops": self_loops, "tags": tags}
    except Exception:
        log.exception("ERROR PARSING GOOGLE:\n%s", json_data)
        parsed = {"suggests": [], "self_loops": [], "tags": []}
    return parsed


def parse_bing_qry(raw_html: str, qry: str = "") -> str | None:
    """Recover query from Bing response HTML."""
    url = BeautifulSoup(raw_html).find("li")["url"]
    if url:
        return str(urllib.parse.parse_qs(urllib.parse.urlparse().query)["pq"][0])
    else:
        return None


def parse_bing(raw_html: str, qry: str = "") -> dict[str, list]:
    """Parse Bing autocomplete API response.

    Args:
        raw_html: Raw HTML response from Bing autocomplete API
        qry: Original query string

    Returns:
        Dictionary with 'suggests', 'self_loops', and 'tags' keys
    """

    def bing_parser(raw_html: str) -> list[str]:
        soup = BeautifulSoup(raw_html, "html.parser")
        if not soup.text:
            # No suggestions
            return []
        suggests = [div.text for div in soup.find_all("div", {"class": "sa_tm"})]
        suggests = [html.unescape(s) for s in suggests]
        return suggests

    try:
        suggests = bing_parser(raw_html)
        self_loops = [i for i, s in enumerate(suggests) if s == qry]
        parsed = {"suggests": suggests, "self_loops": self_loops, "tags": []}
    except Exception:
        log.exception("ERROR PARSING BING:\n%s", raw_html)
        parsed = {"suggests": [], "self_loops": [], "tags": []}
    return parsed


def to_edgelist(tree: list[dict], self_loops: bool = False) -> pl.DataFrame:
    """Convert suggestions tree to an edge list DataFrame.

    Args:
        tree: List of suggestion dictionaries from get_suggests_tree
        self_loops: Whether to include self-loop edges

    Returns:
        DataFrame with edge list columns (root, edge, source, target, rank, etc.)
    """
    edge_list = []
    assert isinstance(tree, list), "Must pass a list of dicts"

    for row in tree:
        if self_loops:
            suggests = row["suggests"]
        else:
            suggests = [s for s in row["suggests"] if s != row["qry"]]

        if suggests:
            for rank, s in enumerate(suggests):
                edge = OrderedDict(
                    [
                        ("root", row["root"]),
                        ("edge", str((row["qry"], s))),
                        ("source", row["qry"]),
                        ("target", html.unescape(s)),
                        ("rank", rank + 1),
                        ("depth", row["depth"]),
                        ("search_engine", row["source"]),
                        ("datetime", row["datetime"]),
                    ]
                )
                edge_list.append(edge)
        else:  # If no suggests at root, append empty root
            if row["depth"] == 0:
                no_edges = OrderedDict(
                    [
                        ("root", row["root"]),
                        ("edge", None),
                        ("source", row["qry"]),
                        ("target", None),
                        ("rank", 1),
                        ("depth", row["depth"]),
                        ("search_engine", row["source"]),
                        ("datetime", row["datetime"]),
                    ]
                )
                edge_list.append(no_edges)

    edge_df = pl.DataFrame(edge_list)
    return edge_df


def add_parent_nodes(edges: pl.DataFrame) -> pl.DataFrame:
    """Add parent and grandparent node columns to an edge list.

    Args:
        edges: Edge list DataFrame from to_edgelist

    Returns:
        DataFrame with 'parent' and 'grandparent' columns added
    """
    edges_original = edges.clone()

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
        .then(pl.col("grandparent").drop_nulls().str.concat(" "))
        .otherwise(pl.lit(None))
        .first()
        .alias("grandparent"),
        pl.when(pl.col("parent").is_not_null().any())
        .then(pl.col("parent").drop_nulls().str.concat(" "))
        .otherwise(pl.lit(None))
        .first()
        .alias("parent"),
    )
    return edges_original.join(merged_parents, on="edge", how="left")


def _compute_metanode(row: dict) -> dict:
    """Compute source_add and target_add for a single row."""
    grandparent = [] if row["grandparent"] is None else row["grandparent"].split(" ")
    parent = [] if row["parent"] is None else row["parent"].split(" ")

    source = row["source"].split(" ")
    target = row["target"].split(" ")

    source_add = [i for i in source if i not in set(parent)]
    target_add = [i for i in target if i not in set(source)]

    parent_add = [i for i in parent if i not in set(grandparent)]

    if not source_add:  # information removed
        source_add = parent_add
    if not target_add:
        print(f"circle back: {source_add}")
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
    meta = (
        edges.select(
            pl.struct(["source", "target", "parent", "grandparent"])
            .map_elements(_compute_metanode, return_dtype=pl.Struct({"source_add": pl.String, "target_add": pl.String}))
            .alias("_meta")
        )
        .unnest("_meta")
    )
    return pl.concat([edges, meta], how="horizontal")
