"""General network utility functions."""

import random

import igraph as ig
import matplotlib.pyplot as plt
import networkx as nx
import polars as pl
from adjustText import adjust_text


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


def nodes_to_df(g: nx.DiGraph) -> pl.DataFrame:
    """Convert nodes dictionary to DataFrame with node attributes as columns.

    Args:
        g: Directed graph to extract node attributes from

    Returns:
        DataFrame with columns for node name and each attribute
    """
    records = [{"node": node, **attrs} for node, attrs in g.nodes(data=True)]
    return pl.DataFrame(records)


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


def plot_network(
    edges: pl.DataFrame,
    root: str,
    label_col: str = "target_add",
    layout: str = "fr",
    size_scale: float = 500,
    label_quantile: float = 0.99,
    label_alpha: float = 1.0,
    spacing: float = 1.0,
    seed: int = 42,
    figsize: tuple[int, int] = (14, 14),
    font_size: float = 1,
    save_to: str = "",
) -> plt.Figure:
    """Plot a suggestion network with degree sizing and Louvain community colors.

    Uses igraph for fast graph layout and adjustText for label deoverlapping.
    Node sizes are proportional to squared degree (emphasizing hubs) and
    node colors indicate communities detected using the Louvain method.
    Only nodes above the label_quantile of PageRank are labeled.

    Args:
        edges: Edge list DataFrame with 'source' and 'target' columns
        root: Root node for extracting the main component
        label_col: Column to use for node labels. Use 'target_add' for short
            metanode labels or 'target' for full suggestion text.
        layout: igraph layout algorithm ('fr' for Fruchterman-Reingold,
            'drl' for DrL/distributed recursive layout)
        size_scale: Multiplier for degree-based node sizes
        label_quantile: PageRank quantile threshold for showing labels (0-1)
        label_alpha: Opacity for node labels (0-1)
        spacing: Multiplier for layout coordinates to increase node separation
        seed: Random seed for layout and community detection
        figsize: Figure dimensions (width, height)
        font_size: Base label font size (scales with degree)
        save_to: Optional file path to save the plot

    Returns:
        Matplotlib Figure object
    """
    # Build networkx graph and extract main component
    g = nx.DiGraph(zip(edges["source"].to_list(), edges["target"].to_list()))
    component = get_root_component(g, root)
    if component is not None:
        g = component

    # Degree for node sizing (squared for aggressive scaling)
    degree = dict(g.degree())
    max_deg = max(degree.values()) or 1
    node_sizes = [(degree[n] / max_deg) ** 2 * size_scale + 5 for n in g.nodes()]

    # PageRank for label selection
    pagerank = nx.pagerank(g)

    # Louvain communities for node coloring
    communities = nx.community.louvain_communities(g.to_undirected(), seed=seed)
    node_to_community = {}
    for i, comm in enumerate(communities):
        for node in comm:
            node_to_community[node] = i
    node_colors = [node_to_community[n] for n in g.nodes()]

    # Build short label mapping from edges if label_col is available
    node_labels = {}
    if label_col in edges.columns:
        for target, label in zip(
            edges["target"].to_list(), edges[label_col].to_list()
        ):
            if label is not None and target not in node_labels:
                node_labels[target] = label
        if "source_add" in edges.columns:
            for source, label in zip(
                edges["source"].to_list(), edges["source_add"].to_list()
            ):
                if label is not None and source not in node_labels:
                    node_labels[source] = label

    # Labels for nodes above the PageRank quantile threshold
    pr_values = sorted(pagerank.values())
    threshold_idx = min(int(len(pr_values) * label_quantile), len(pr_values) - 1)
    threshold = pr_values[threshold_idx]
    labels = {}
    for n, pr in pagerank.items():
        if pr >= threshold and degree[n] > 1:
            labels[n] = node_labels.get(n, n)

    # igraph layout (much faster than networkx for large graphs)
    node_list = list(g.nodes())
    node_idx = {n: i for i, n in enumerate(node_list)}
    ig_edges = [(node_idx[u], node_idx[v]) for u, v in g.edges()]
    ig_graph = ig.Graph(n=len(node_list), edges=ig_edges, directed=True)

    random.seed(seed)
    if layout == "drl":
        ig_layout = ig_graph.layout_drl()
    else:
        ig_layout = ig_graph.layout_fruchterman_reingold()

    pos = {
        node_list[i]: (ig_layout[i][0] * spacing, ig_layout[i][1] * spacing)
        for i in range(len(node_list))
    }

    fig, ax = plt.subplots(figsize=figsize)

    # Draw edges
    nx.draw_networkx_edges(
        g, pos, ax=ax, edge_color="#cccccc", alpha=0.3,
        arrows=True, arrowsize=3, width=0.3,
    )

    # Draw nodes
    nx.draw_networkx_nodes(
        g,
        pos,
        ax=ax,
        node_size=node_sizes,
        node_color=node_colors,
        cmap=plt.cm.tab20,
        alpha=0.85,
        linewidths=0.3,
        edgecolors="white",
    )

    # Draw labels scaled by degree, then deoverlap with adjustText
    texts = []
    for node, (x, y) in pos.items():
        if node in labels:
            scale = (degree[node] / max_deg) ** 0.5
            size = font_size * (1 + 9 * scale)
            t = ax.text(
                x, y, labels[node],
                fontsize=size, fontweight="bold", ha="center", va="center",
                alpha=label_alpha,
            )
            texts.append(t)

    if texts:
        adjust_text(texts, ax=ax)

    ax.set_axis_off()
    fig.tight_layout()

    if save_to:
        fig.savefig(save_to, dpi=150, bbox_inches="tight")

    return fig
