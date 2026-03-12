"""Algorithm auditing tools for search engine autocomplete."""

__version__ = "0.3.1a0"

from .parsing import (
    add_metanodes,
    add_parent_nodes,
    parse_bing,
    parse_google,
    to_edgelist,
)
from .suggests import get_suggests, get_suggests_tree

__all__ = [
    "add_metanodes",
    "add_parent_nodes",
    "get_suggests",
    "get_suggests_tree",
    "parse_bing",
    "parse_google",
    "to_edgelist",
]
