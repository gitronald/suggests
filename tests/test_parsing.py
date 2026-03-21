"""Tests for suggests.parsing module."""

import polars as pl
import pytest

from suggests.parsing import (
    add_metanodes,
    add_parent_nodes,
    parse_bing,
    parse_google,
    strip_html,
    to_edgelist,
)


class TestStripHtml:
    def test_removes_tags(self):
        assert strip_html("<b>hello</b>") == "hello"

    def test_removes_nested_tags(self):
        assert strip_html("<div><span>text</span></div>") == "text"

    def test_no_tags(self):
        assert strip_html("plain text") == "plain text"

    def test_empty_string(self):
        assert strip_html("") == ""


class TestParseGoogle:
    def test_basic_parse(self, google_json):
        result = parse_google(google_json, qry="dog")
        assert len(result["suggests"]) == 3
        assert "dog toys" in result["suggests"]
        assert isinstance(result["self_loops"], list)
        assert "tags" in result

    def test_entity_annotation(self, google_json_with_entity):
        result = parse_google(google_json_with_entity, qry="dog")
        assert any("Cryptocurrency" in s for s in result["suggests"])

    def test_invalid_data_returns_empty(self):
        result = parse_google(None, qry="dog")
        assert result["suggests"] == []
        assert result["self_loops"] == []

    def test_self_loop_detection(self):
        json_data = ["dog", [["dog", 0, []], ["dog food", 0, []]], {}]
        result = parse_google(json_data, qry="dog")
        assert 0 in result["self_loops"]


class TestParseBing:
    def test_basic_parse(self, bing_html):
        result = parse_bing(bing_html, qry="dog")
        assert len(result["suggests"]) == 3
        assert "dog toys" in result["suggests"]
        assert result["tags"] == []

    def test_empty_html(self, bing_html_empty):
        result = parse_bing(bing_html_empty, qry="dog")
        assert result["suggests"] == []

    def test_self_loop_detection(self):
        html = (
            '<ul><li><div class="sa_tm">dog</div></li>'
            '<li><div class="sa_tm">dog toys</div></li></ul>'
        )
        result = parse_bing(html, qry="dog")
        assert 0 in result["self_loops"]


class TestToEdgelist:
    def test_basic_conversion(self, sample_tree):
        edges = to_edgelist(sample_tree)
        assert isinstance(edges, pl.DataFrame)
        assert "source" in edges.columns
        assert "target" in edges.columns
        assert "rank" in edges.columns
        assert "depth" in edges.columns
        assert len(edges) == 4  # 2 suggests at depth 0 + 2 at depth 1

    def test_self_loops_excluded_by_default(self, sample_tree_with_self_loop):
        edges = to_edgelist(sample_tree_with_self_loop)
        # "dog" -> "dog" should be excluded, only "dog" -> "dog toys" remains
        assert len(edges) == 1
        assert edges[0, "target"] == "dog toys"

    def test_self_loops_included(self, sample_tree_with_self_loop):
        edges = to_edgelist(sample_tree_with_self_loop, self_loops=True)
        assert len(edges) == 2

    def test_no_suggests_at_root(self, sample_tree_no_suggests):
        edges = to_edgelist(sample_tree_no_suggests)
        assert len(edges) == 1
        assert edges[0, "target"] is None

    def test_ranks_start_at_one(self, sample_tree):
        edges = to_edgelist(sample_tree)
        assert edges["rank"].min() == 1

    def test_invalid_input_type(self):
        with pytest.raises(AssertionError):
            to_edgelist("not a list")


class TestAddParentNodes:
    def test_adds_parent_column(self, sample_tree):
        edges = to_edgelist(sample_tree)
        result = add_parent_nodes(edges)
        assert "parent" in result.columns
        assert "grandparent" in result.columns

    def test_depth_zero_has_no_parent(self, sample_tree):
        edges = to_edgelist(sample_tree)
        result = add_parent_nodes(edges)
        depth_zero = result.filter(pl.col("depth") == 0)
        assert depth_zero["parent"].is_null().all()


class TestAddMetanodes:
    def test_adds_metanode_columns(self, sample_tree):
        edges = to_edgelist(sample_tree)
        edges = add_parent_nodes(edges)
        result = add_metanodes(edges)
        assert "source_add" in result.columns
        assert "target_add" in result.columns

    def test_depth_zero_source_add_equals_source(self, sample_tree):
        edges = to_edgelist(sample_tree)
        edges = add_parent_nodes(edges)
        result = add_metanodes(edges)
        depth_zero = result.filter(pl.col("depth") == 0)
        assert depth_zero[0, "source_add"] == depth_zero[0, "source"]
