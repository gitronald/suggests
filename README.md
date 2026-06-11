# suggests

Tools for auditing search engine autocomplete.

Retrieves autocomplete suggestions from Google and Bing and recursively expands them into suggestion trees for algorithm audits. Convert trees to polars edge lists, reduce them to association networks, and plot them with the `suggests-plot` command or `plot_network()` in Python. A sleep timer is hard-coded into the recursive crawler (approx ~1 sec) based on my experience — you will get blocked if you do not restrict your crawling speed.

The functionality of this package was demonstrated in the paper listed below, if you use it in your work, please cite our paper!

Robertson R. E., Jiang, S., Lazer, D., & Wilson, C. (2019). Auditing autocomplete: Recursive algorithm interrogation and suggestion networks.
In _Proceedings of the 11th ACM Conference on Web Science (WebSci 2019)_. [PDF](https://cbw.sh/static/pdf/robertson-websci19.pdf)

```bibtex
@proceedings{robertson2019autocomplete,
  title = {Auditing autocomplete: Recursive algorithm interrogation and suggestion networks},
  author = {Robertson, Ronald E. and Jiang, Shan and Lazer, David and Wilson, Christo},
  booktitle = {Proceedings of the 11th International ACM Web Science Conference}
  series = {WebSci '19},
  doi = {10.1145/3292522.3326047},
}
```

## Project Structure

```
suggests/
├── suggests/              # Python library
│   ├── suggests.py        # Suggestion retrieval and recursive tree crawling
│   ├── parsing.py         # Response parsing, edge lists, and metanode extraction
│   ├── nets.py            # Network construction and plotting
│   ├── logger.py          # Package-scoped logging
│   └── scripts/           # CLI commands
│       ├── demo.py        # Demo crawl (`demo`)
│       └── plot.py        # Network plotting (`suggests-plot`)
├── tests/                 # Test suite
└── pyproject.toml         # Project configuration
```

## Installation

Install with uv:

```bash
uv add git+https://github.com/gitronald/suggests
```

Or with pip:

```bash
pip install git+https://github.com/gitronald/suggests
```

From source:

```bash
git clone https://github.com/gitronald/suggests.git
cd suggests
uv sync
```

Network plotting requires the `viz` extra:

```bash
pip install "suggests[viz] @ git+https://github.com/gitronald/suggests"
```

## CLI Commands

### demo

Run a depth-1 demo crawl (`dog` on Bing) and print the resulting suggestion tree and edge list:

```bash
demo
```

### suggests-plot

Render a network plot from any edge-list CSV (requires the `viz` extra). Wraps `plot_network()`:

```bash
suggests-plot --edges edges.csv --root dog --save-to plot.png
```

## Examples

### Getting suggestions

```python
import suggests
>>> s = suggests.get_suggests('geese are ', source='google')
2019-05-23 11:28:30,467 | 1897 | INFO | suggests.logger | google | geese are
>>> s['suggests']
['geese are evil', 'geese are mean', 'geese are aggressive', 'geese are jerks', 'geese are the worst', 'geese are scary', 'geese are dinosaurs', 'geese are protected', 'geese are annoying', 'geese are monogamous']
```

Use the `hl` parameter for Google (e.g. `'es'`, `'de'`, `'fr'`) to get suggestions in other languages:

```python
>>> s = suggests.get_suggests('los gansos son ', source='google', hl='es')
2026-03-12 11:40:41,677 | 26509 | INFO | suggests | google | los gansos son
>>> s['suggests']
['los gansos son territoriales', 'los gansos son monogamos', 'los gansos son patos', 'los gansos son comestibles', 'los gansos son aves']
```

For Bing, use the `mkt` parameter (e.g. `'es-es'`, `'de-de'`, `'fr-fr'`) to get suggestions in other languages:

```python
>>> s = suggests.get_suggests('los gansos son ', source='bing', mkt='es-es')
2026-03-12 11:40:43,764 | 26509 | INFO | suggests | bing | los gansos son
>>> s['suggests']
['los gansos son agresivos', 'que son los gansos', 'sonidos de gansos']
```

### Generating a suggestions tree

Below is a more involved example usage: creating a suggestions network for the query `'abortion'`, recursing to a maximum depth (breadth-first search steps) of 4.

```python
In [1]: tree = suggests.get_suggests_tree('abortion', source='google', max_depth=4)
2019-05-21 10:10:32,578 | 9943 | INFO | suggests.logger | google | abortion
2019-05-21 10:10:34,092 | 9943 | INFO | suggests.logger | google | abortion laws 2019
2019-05-21 10:10:35,172 | 9943 | INFO | suggests.logger | google | abortion pill
2019-05-21 10:10:36,323 | 9943 | INFO | suggests.logger | google | abortion law
2019-05-21 10:10:37,334 | 9943 | INFO | suggests.logger | google | abortion statistics
2019-05-21 10:10:38,426 | 9943 | INFO | suggests.logger | google | abortion definition
2019-05-21 10:10:39,473 | 9943 | INFO | suggests.logger | google | abortion clinic
2019-05-21 10:10:40,257 | 9943 | INFO | suggests.logger | google | abortion protest day
2019-05-21 10:10:41,439 | 9943 | INFO | suggests.logger | google | abortion facts
...
2019-05-21 10:23:54,633 | 9943 | INFO | suggests.logger | google | statistics on abortion 2019
2019-05-21 10:23:55,742 | 9943 | INFO | suggests.logger | google | statistics on abortion in nigeria
2019-05-21 10:23:57,002 | 9943 | INFO | suggests.logger | google | statistics on abortion uk
2019-05-21 10:23:58,094 | 9943 | INFO | suggests.logger | google | statistics on abortion in the philippines
2019-05-21 10:23:59,332 | 9943 | INFO | suggests.logger | google | statistics on abortion in ireland
2019-05-21 10:24:00,613 | 9943 | INFO | suggests.logger | google | gosnell' abortion doctor movie releases trailer
2019-05-21 10:24:02,088 | 9943 | INFO | suggests.logger | google | anti abortion movie unplanned trailer
2019-05-21 10:24:03,293 | 9943 | INFO | suggests.logger | google | who played the abortion doctor in the movie unplanned
2019-05-21 10:24:04,255 | 9943 | INFO | suggests.logger | google | cast of unplanned wedding
```

### Examining the data
```py
In [2]: tree[0]
Out[2]:
{'qry': 'abortion',
 'datetime': '2019-05-21 14:10:31.188217',
 'source': 'google',
 'data': ['abortion',
  [['abortion', 0, [131]],
   ['abortion<b> laws 2019</b>', 0, [131]],
   ['abortion<b> pill</b>', 0],
   ['abortion<b> law</b>', 0, [131]],
   ['abortion<b> statistics</b>', 0, [131]],
   ['abortion<b> definition</b>', 0, [131]],
   ['abortion<b> clinic</b>', 0, [131]],
   ['abortion<b> protest day</b>', 0, [131]],
   ['abortion<b> facts</b>', 0, [131]],
   ['abortion<b> movie</b>', 0]],
  {'q': 'VNgAJ8HR9ujuw-N-maKAjD15MEM', 't': {'bpc': False, 'tlw': False}}],
 'suggests': ['abortion',
  'abortion laws 2019',
  'abortion pill',
  'abortion law',
  'abortion statistics',
  'abortion definition',
  'abortion clinic',
  'abortion protest day',
  'abortion facts',
  'abortion movie'],
 'self_loops': [0],
 'tags': {'q': 'VNgAJ8HR9ujuw-N-maKAjD15MEM',
  't': {'bpc': False, 'tlw': False}},
 'crawl_id': '',
 'depth': 0,
 'root': 'abortion'}
```


### Converting to edge list
```py
In [3]: edges = suggests.to_edgelist(tree)

In [4]: edges.head()
Out[4]:
       root                             edge    source               target  \
0  abortion   (abortion, abortion laws 2019)  abortion   abortion laws 2019
1  abortion        (abortion, abortion pill)  abortion        abortion pill
2  abortion         (abortion, abortion law)  abortion         abortion law
3  abortion  (abortion, abortion statistics)  abortion  abortion statistics
4  abortion  (abortion, abortion definition)  abortion  abortion definition

   rank  depth search_engine                    datetime
0     1      0        google  2019-05-21 14:10:31.188217
1     2      0        google  2019-05-21 14:10:31.188217
2     3      0        google  2019-05-21 14:10:31.188217
3     4      0        google  2019-05-21 14:10:31.188217
4     5      0        google  2019-05-21 14:10:31.188217
```


### Extract association network

Reduce to new information obtained in suggestions. E.g. `abortion -> abortion laws 2019` becomes `abortion -> laws 2019`.

```py
In [5]: edges = suggests.add_parent_nodes(edges)
In [6]: edges = suggests.add_metanodes(edges)
In [7]: show_cols = ['source','target','grandparent','parent','source_add','target_add']
In [8]: edges[show_cols].head()
Out[9]:
               source                      target grandparent    parent source_add   target_add
0            abortion          abortion laws 2019         NaN       NaN   abortion    laws 2019
1            abortion               abortion pill         NaN       NaN   abortion         pill
2            abortion                abortion law         NaN       NaN   abortion          law
3            abortion         abortion statistics         NaN       NaN   abortion   statistics
4            abortion         abortion definition         NaN       NaN   abortion   definition
5            abortion             abortion clinic         NaN       NaN   abortion       clinic
6            abortion        abortion protest day         NaN       NaN   abortion  protest day
7            abortion              abortion facts         NaN       NaN   abortion        facts
8            abortion              abortion movie         NaN       NaN   abortion        movie
9  abortion laws 2019  abortion laws 2019 georgia         NaN  abortion  laws 2019      georgia
```

Plotted in [Gephi](https://gephi.org/) from an older dataset that is no longer available. The size of nodes corresponds to their PageRank, and node colors indicate communities that were determined using Gephi's default community detection algorithm, the Louvain method:

![Abortion Association Network (Gephi)](img/abortion_plot_pagerank_gephi.png?raw=true "Abortion Association Network (Gephi)")

The same network can be generated programmatically with `plot_network()`, using the test fixture dataset (`tests/fixtures/abortion-20260312-122801-edges.csv`). The `suggests-plot` command (requires the `viz` extra: `pip install "suggests[viz]"`) wraps `plot_network()` for any edge-list CSV; the image above was produced with:

```bash
suggests-plot \
  --edges tests/fixtures/abortion-20260312-122801-edges.csv \
  --root abortion --label-quantile 0.98 --label-alpha 0.7 --spacing 2.0 \
  --save-to img/abortion_plot_pagerank_python.png
```

Nodes represent unique search suggestions, and directed edges connect each suggestion to the suggestions it produced. Node sizes are proportional to squared degree (emphasizing highly connected hubs), and colors indicate communities detected using the Louvain method. Only nodes above the 98th percentile of PageRank are labeled, with font sizes scaled by degree. Layout uses igraph's Fruchterman-Reingold algorithm:

![Abortion Association Network (Python)](img/abortion_plot_pagerank_python.png?raw=true "Abortion Association Network (Python)")

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License
[MIT](https://choosealicense.com/licenses/mit/)
