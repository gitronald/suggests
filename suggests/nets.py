"""General network utility functions."""

import networkx as nx
import pandas as pd


def set_node_attributes(g: nx.DiGraph, root: str) -> None:
    """Add centrality and depth node attributes (inplace operation).

    Args:
        g: Directed graph to add attributes to
        root: Root node for computing network depth
    """
    set_attr = nx.set_node_attributes
    set_attr(g, dict(g.degree()), "k")
    set_attr(g, dict(g.in_degree()), "k_in")
    set_attr(g, dict(g.out_degree()), "k_out")
    set_attr(g, nx.degree_centrality(g), "degree_centrality")
    set_attr(g, nx.betweenness_centrality(g), "betweenness_centrality")
    set_attr(g, nx.closeness_centrality(g), "closeness_centrality")
    set_attr(g, nx.clustering(nx.Graph(g)), "clustering")
    set_attr(g, nx.single_source_shortest_path_length(g, root), "network_depth")


def set_edge_attributes(g: nx.DiGraph) -> None:
    """Add betweenness centrality edge attributes (inplace operation).

    Args:
        g: Directed graph to add edge attributes to
    """
    set_attr = nx.set_edge_attributes
    set_attr(g, "betweenness_centrality", nx.edge_betweenness_centrality(g))


def nodes_to_df(g: nx.DiGraph) -> pd.DataFrame:
    """Convert nodes dictionary to DataFrame with node attributes as columns.

    Args:
        g: Directed graph to extract node attributes from

    Returns:
        DataFrame with columns for node name and each attribute
    """
    node_df = pd.Series(dict(g.nodes())).apply(pd.Series)
    return node_df.reset_index().rename(columns={"index": "node"})


def get_root_component(g: nx.DiGraph, root: str) -> nx.DiGraph | None:
    """Get the weakly connected component containing the root node.

    Args:
        g: Directed graph to search
        root: Root node to find the component for

    Returns:
        Subgraph containing the root node, or None if not found
    """
    weak_subgraphs = (g.subgraph(c) for c in nx.weakly_connected_components(g))
    for subgraph in weak_subgraphs:
        if subgraph.has_node(root):
            return subgraph
    return None


def find_unreachable_nodes(g: nx.DiGraph, root: str) -> list[str]:
    """Find nodes not reachable from the root via directed paths.

    Args:
        g: Directed graph to search
        root: Root node to compute reachability from

    Returns:
        List of unreachable node names
    """
    has_depth = nx.single_source_shortest_path_length(g, root).keys()
    return [n for n in g.nodes if n not in has_depth]
