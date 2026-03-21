"""Integration tests using real suggestion tree data."""

import json
from pathlib import Path

import polars as pl
import pytest

from suggests.parsing import add_metanodes, add_parent_nodes, to_edgelist

DATA_DIR = Path(__file__).parent / "fixtures"
ABORTION_TREE = DATA_DIR / "abortion-20260312-122801.json"
ABORTION_EDGES = DATA_DIR / "abortion-20260312-122801-edges.csv"


@pytest.fixture
def abortion_tree():
    """Load the abortion suggestion tree from JSONL."""
    with open(ABORTION_TREE) as f:
        return [json.loads(line) for line in f]


@pytest.fixture
def abortion_edges_expected():
    """Load the expected edges CSV."""
    return pl.read_csv(ABORTION_EDGES)


class TestAbortionPipeline:
    def test_to_edgelist_shape(self, abortion_tree):
        edges = to_edgelist(abortion_tree)
        assert isinstance(edges, pl.DataFrame)
        assert edges.shape[0] > 0
        assert "source" in edges.columns
        assert "target" in edges.columns

    def test_add_parent_nodes(self, abortion_tree):
        edges = to_edgelist(abortion_tree)
        result = add_parent_nodes(edges)
        assert "parent" in result.columns
        assert "grandparent" in result.columns
        depth_zero = result.filter(pl.col("depth") == 0)
        assert depth_zero["parent"].is_null().all()

    def test_add_metanodes(self, abortion_tree):
        edges = to_edgelist(abortion_tree)
        edges = add_parent_nodes(edges)
        result = add_metanodes(edges)
        assert "source_add" in result.columns
        assert "target_add" in result.columns

    def test_full_pipeline_matches_expected(self, abortion_tree, abortion_edges_expected):
        edges = to_edgelist(abortion_tree)
        edges = add_parent_nodes(edges)
        edges = add_metanodes(edges)
        assert edges.shape[0] == abortion_edges_expected.shape[0]
        assert edges["source"].to_list() == abortion_edges_expected["source"].to_list()
        assert edges["target"].to_list() == abortion_edges_expected["target"].to_list()

    def test_metanode_values_match_expected(self, abortion_tree, abortion_edges_expected):
        edges = to_edgelist(abortion_tree)
        edges = add_parent_nodes(edges)
        edges = add_metanodes(edges)
        assert edges["source_add"].to_list() == abortion_edges_expected["source_add"].to_list()
        assert edges["target_add"].to_list() == abortion_edges_expected["target_add"].to_list()
