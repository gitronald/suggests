""" Parsing functions for Google and Bing
"""

import re
import html
import pandas as pd
import urllib.parse
from bs4 import BeautifulSoup
from collections import OrderedDict

from . import logger
log = logger.Logger().start(__name__)

def get_source_target_columns(edges):
    edge_details = edges.edge.apply(pd.Series)
    edge_details.columns = ['source','target']
    return pd.concat([edges, edge_details], axis=1)

def parse_raw_data(raw_data, source):
    # Parse raw aggregated data from `clean` into edge lists
    parser = parse_google if source=='google' else parse_bing
    return pd.concat([raw_data, raw_data.data.apply(parser).apply(pd.Series)], axis=1)
    
def get_edges(data):
    clean_data = [parse_raw_data(df, k) for k, df in data.groupby('source')]
    return pd.concat([to_edgelist(df) for df in clean_data])

def strip_html(string):
    """Strips HTML <tags>"""
    return re.sub('<[^<]+?>', '', string)

def parse_google(json_data, qry=''):
    
    def google_parser(json_data):

        def suggest_parser(s):
            return html.unescape(strip_html(s))

        qry = json_data[0]
        suggests = [s[0]+' - '+s[3]['b'] if s[1]==46 else s[0] for s in json_data[1]]
        suggests = [suggest_parser(s) for s in suggests]
        tags = json_data[2]
        return qry, suggests, tags
    
    try:
        qry, suggests, tags = google_parser(json_data)
        self_loops = [i for i, s in enumerate(suggests) if s == qry]
        parsed = {'suggests': suggests, 'self_loops':self_loops, 'tags': tags}
    except:
        log.exception('ERROR PARSING GOOGLE:\n%s', json_data)
        parsed = {'suggests':[], 'self_loops':[], 'tags':[]}
    return parsed

def parse_bing_qry(raw_html, qry=''):
    """Recover query from bing response html"""
    url = BeautifulSoup(raw_html).find('li')['url']
    if url:
        return str(urllib.parse.parse_qs(urllib.parse.urlparse().query)['pq'][0])
    else:
        return None

def parse_bing(raw_html, qry=''):
    
    def bing_parser(raw_html):
        soup = BeautifulSoup(raw_html, 'html.parser')
        if not soup.text:
            # No suggestions
            return []
        suggests = [div.text for div in soup.find_all('div', {'class':'sa_tm'})]
        suggests = [html.unescape(s) for s in suggests]
        return suggests

    try:
        suggests = bing_parser(raw_html)
        self_loops = [i for i, s in enumerate(suggests) if s == qry]
        parsed = {'suggests':suggests, 'self_loops':self_loops, 'tags':[]}
    except:
        log.exception('ERROR PARSING BING:\n%s', raw_html)
        parsed = {'suggests':[], 'self_loops':[], 'tags':[]}
    return parsed

def to_edgelist(tree, self_loops=False):
    """Convert suggestions tree (df) to edgelist (df)"""
    edge_list = []
    assert type(tree) == list or type(tree) == pd.np.recarray, \
        "Must pass records or a list of dicts"

    for row in tree:

        if self_loops:
            suggests = row['suggests'] 
        else:
            suggests = [s for s in row['suggests'] if s != row['qry']]
            
        if suggests:
            for rank, s in enumerate(suggests):
                edge = OrderedDict([
                    ('root', row['root']), 
                    ('edge', (row['qry'], s)), 
                    ('source', row['qry']),
                    ('target', html.unescape(s)),
                    ('rank', rank + 1), 
                    ('depth', row['depth']),
                    ('search_engine', row['source']),
                    ('datetime', row['datetime'])
                ])
                edge_list.append(edge)
        else: # If no suggests at root, append empty root
            if row['depth'] == 0:
                no_edges = OrderedDict([
                    ('root', row['root']), 
                    ('edge', None), 
                    ('source', row['qry']),
                    ('target', None),
                    ('rank', 1), 
                    ('depth', row['depth']),
                    ('search_engine', row['source']),
                    ('datetime', row['datetime'])
                ])
                edge_list.append(no_edges)
                
    edge_df = pd.DataFrame(edge_list)
    return edge_df

def add_parent_nodes(edges):
    edges_original = edges.copy()

    # Get parent node
    parent = edges.rename(columns={"source": "parent", "target": "source"})
    parent["depth"] = parent["depth"] + 1
    parent = parent[["root", "parent", "source", "depth", "search_engine"]]
    edges = edges.merge(parent, on = ["root", "source", "depth", "search_engine"], how = "left")

    # Get grandparent node
    grandparent = edges.rename(columns={"parent": "grandparent", "source": "parent", "target": "source"})
    grandparent["depth"] = grandparent["depth"] + 1
    grandparent = grandparent[["root", "grandparent", "parent", "source", "depth", "search_engine"]]
    edges = edges.merge(grandparent, on = ["root", "parent", "source", "depth", "search_engine"], how = "left")

    # Resolve merge points
    gb = edges.groupby('edge')
    merged_parents = pd.DataFrame({
        'grandparent': gb.grandparent.apply(lambda col: col.str.cat(sep=' ') if col.any() else None),
        'parent': gb.parent.apply(lambda col: col.str.cat(sep=' ') if col.any() else None)
    }).reset_index()
    edges = edges_original.merge(merged_parents, on='edge', how='left')
    return edges

def add_metanodes(row):
    # Get memory from two steps back
    grandparent = list() if row.isna()["grandparent"] else row["grandparent"].split(" ")
    parent = list() if row.isna()["parent"] else row["parent"].split(" ")

    # Set current row source and target nodes
    source = row["source"].split(" ")
    target = row["target"].split(" ")

    # Calculate differences 
    source_add = [i for i in source if i not in set(parent)]
    target_add = [i for i in target if i not in set(source)]

    # Track difference in previous step
    parent_add = [i for i in parent if i not in set(grandparent)]

    if not source_add: # information removed
        source_add = parent_add
    # If target adds nothing nothing, circle back
    if not target_add: 
        print(f'circle back: {source_add}')
        target_add = source_add

    row["source_add"] = " ".join(source_add)
    row["target_add"] = " ".join(target_add)
    return row
