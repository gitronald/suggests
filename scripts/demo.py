import json
import datetime
import suggests
import pandas as pd

def main():
    crawl_id = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    get_suggests_tree_args = {
        'root': 'dog',
        'source': 'bing',
        'max_depth': 1,
        'crawl_id': crawl_id,
        'save_to': f'./data/tests/suggests-{crawl_id}.json',
        'sesh_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:58.0) Gecko/20100101 Firefox/58.0'
        }
    }
    print(json.dumps(get_suggests_tree_args, indent=2))
    tree = suggests.get_suggests_tree(**get_suggests_tree_args)
    tree_df = pd.DataFrame(tree)
    print(f"\nSuggestion Tree: ({tree_df.shape[0]:,}, {tree_df.shape[1]})")
    print(tree_df.head())

    edges = suggests.to_edgelist(tree)
    print(f"Suggestion Network Edges: ({edges.shape[0]:,}, {edges.shape[1]})")
    print(edges.head())

if __name__ == "__main__":
    main()