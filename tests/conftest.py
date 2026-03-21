"""Shared test fixtures."""

import tempfile

import pytest


@pytest.fixture
def bing_html():
    """Sample Bing autocomplete HTML response."""
    return (
        '<ul class="sa_drw">'
        '<li class="sa_sg"><div class="sa_tm"><span class="sa_tm_text">dog toys</span></div></li>'
        '<li class="sa_sg"><div class="sa_tm"><span class="sa_tm_text">dog food</span></div></li>'
        '<li class="sa_sg"><div class="sa_tm"><span class="sa_tm_text">dog breeds</span></div></li>'
        "</ul>"
    )


@pytest.fixture
def bing_html_empty():
    """Empty Bing autocomplete HTML response."""
    return ""


@pytest.fixture
def google_json():
    """Sample Google autocomplete JSON response."""
    return [
        "dog",
        [["dog toys", 0, []], ["dog food", 0, []], ["dog breeds", 0, []]],
        {"t": {}},
    ]


@pytest.fixture
def google_json_with_entity():
    """Google autocomplete response with entity annotation (type 46)."""
    return [
        "dog",
        [
            ["dog toys", 0, []],
            ["Dogecoin", 46, [], {"b": "Cryptocurrency"}],
        ],
        {"t": {}},
    ]


@pytest.fixture
def sample_tree():
    """Sample suggestion tree (list of dicts) for testing to_edgelist."""
    return [
        {
            "qry": "dog",
            "suggests": ["dog toys", "dog food"],
            "root": "dog",
            "depth": 0,
            "source": "bing",
            "datetime": "2026-01-01 00:00:00",
        },
        {
            "qry": "dog toys",
            "suggests": ["dog toys amazon", "dog toys chewy"],
            "root": "dog",
            "depth": 1,
            "source": "bing",
            "datetime": "2026-01-01 00:00:01",
        },
    ]


@pytest.fixture
def sample_tree_with_self_loop():
    """Sample suggestion tree with a self-loop."""
    return [
        {
            "qry": "dog",
            "suggests": ["dog", "dog toys"],
            "root": "dog",
            "depth": 0,
            "source": "bing",
            "datetime": "2026-01-01 00:00:00",
        },
    ]


@pytest.fixture
def sample_tree_no_suggests():
    """Sample suggestion tree with no suggestions at root."""
    return [
        {
            "qry": "xyzabc123",
            "suggests": [],
            "root": "xyzabc123",
            "depth": 0,
            "source": "bing",
            "datetime": "2026-01-01 00:00:00",
        },
    ]


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir
