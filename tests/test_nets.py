"""Tests for suggests.nets module."""

import networkx as nx
import polars as pl
import pytest

from suggests.nets import (
    find_unreachable_nodes,
    get_root_component,
    nodes_to_df,
    set_node_attributes,
)


@pytest.fixture
def sample_graph():
    """Create a small directed graph for testing."""
    g = nx.DiGraph()
    g.add_edges_from(
        [("dog", "dog toys"), ("dog", "dog food"), ("dog toys", "dog toys amazon")]
    )
    return g


@pytest.fixture
def disconnected_graph():
    """Create a graph with a disconnected component."""
    g = nx.DiGraph()
    g.add_edges_from([("dog", "dog toys"), ("cat", "cat food")])
    return g


class TestSetNodeAttributes:
    def test_adds_centrality_attributes(self, sample_graph):
        set_node_attributes(sample_graph, "dog")
        attrs = sample_graph.nodes["dog"]
        assert "k" in attrs
        assert "k_in" in attrs
        assert "k_out" in attrs
        assert "degree_centrality" in attrs
        assert "betweenness_centrality" in attrs
        assert "closeness_centrality" in attrs
        assert "clustering" in attrs
        assert "network_depth" in attrs

    def test_root_has_zero_depth(self, sample_graph):
        set_node_attributes(sample_graph, "dog")
        assert sample_graph.nodes["dog"]["network_depth"] == 0


class TestNodesToDF:
    def test_returns_dataframe(self, sample_graph):
        set_node_attributes(sample_graph, "dog")
        df = nodes_to_df(sample_graph)
        assert isinstance(df, pl.DataFrame)
        assert "node" in df.columns


class TestGetRootComponent:
    def test_returns_component_with_root(self, disconnected_graph):
        component = get_root_component(disconnected_graph, "dog")
        assert component is not None
        assert component.has_node("dog")
        assert component.has_node("dog toys")
        assert not component.has_node("cat")

    def test_returns_none_for_missing_root(self, disconnected_graph):
        result = get_root_component(disconnected_graph, "nonexistent")
        assert result is None


class TestFindUnreachableNodes:
    def test_finds_unreachable(self, disconnected_graph):
        unreachable = find_unreachable_nodes(disconnected_graph, "dog")
        assert "cat" in unreachable
        assert "cat food" in unreachable

    def test_no_unreachable_in_connected(self, sample_graph):
        unreachable = find_unreachable_nodes(sample_graph, "dog")
        assert len(unreachable) == 0
