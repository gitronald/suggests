""" General network utility functions
"""

import pandas as pd
import networkx as nx

def set_node_attributes(g, root):
    """Add node attributes (inplace operation)"""
    set_attr = nx.set_node_attributes
    set_attr(g, dict(g.degree()), 'k')
    set_attr(g, dict(g.in_degree()), 'k_in')
    set_attr(g, dict(g.out_degree()), 'k_out')
    set_attr(g, nx.degree_centrality(g), 'degree_centrality')
    set_attr(g, nx.betweenness_centrality(g), 'betweenness_centrality')
    set_attr(g, nx.closeness_centrality(g), 'closeness_centrality')
    set_attr(g, nx.clustering(nx.Graph(g)), 'clustering')
    set_attr(g, nx.single_source_shortest_path_length(g, root), 'network_depth')

def set_edge_attributes(g):
    set_attr = nx.set_edge_attributes
    set_attr(g, 'betweenness_centrality', nx.edge_betweenness_centrality(g))

def nodes_to_df(g):
    """Convert nodes dictionary to df index=nodes, cols=attr"""
    node_df = pd.Series(dict(g.nodes())).apply(pd.Series)
    return node_df.reset_index().rename(columns={'index':'node'})

def get_root_component(g, root):
    # Get weakly connected component containing root node
    weak_subgraphs = (g.subgraph(c) for c in nx.weakly_connected_components(g))
    for subgraph in weak_subgraphs:
        if subgraph.has_node(root):
            return subgraph

def find_unreachable_nodes(g, root):
    # Find isolated nodes
    has_depth = nx.single_source_shortest_path_length(g, root).keys()
    return [n for n in g.nodes if n not in has_depth]
