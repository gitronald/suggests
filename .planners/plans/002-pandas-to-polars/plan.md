---
id: 2
slug: pandas-to-polars
status: done
branch: dev/polars-migration
created: 2026-03-12T13:19:16-07:00
concluded: 2026-03-13T01:23:46Z
pr: https://github.com/gitronald/suggests/pull/11
---

# Migrate pandas to polars

## Context

The `suggests` package currently depends on pandas and numpy. Per project rules (polars over pandas), migrate all DataFrame operations to polars. Also replace the sole numpy usage (`numpy.random.uniform`) with stdlib `random.uniform`. Add integration tests using the `data/tests/abortion-*` files.

Breaking API change: `add_metanodes` changes from row-wise `edges.apply(suggests.add_metanodes, axis=1)` to DataFrame-level `suggests.add_metanodes(edges)`.

## Files to modify

1. `pyproject.toml` - swap pandas/numpy for polars
2. `suggests/suggests.py` - replace numpy.random with stdlib random
3. `suggests/parsing.py` - core migration (heaviest changes)
4. `suggests/nets.py` - migrate `nodes_to_df`
5. `scripts/demo.py` - update to polars
6. `tests/test_parsing.py` - update assertions to polars API
7. `tests/test_nets.py` - update assertions to polars API
8. `tests/test_integration.py` - new file with abortion data tests
9. `README.md` - update usage examples for new `add_metanodes` API

## Implementation

### 1. `pyproject.toml`
- Remove `pandas>=2.0` and `numpy>=2.0` from dependencies
- Add `polars>=1.0`

### 2. `suggests/suggests.py`
- Replace `from numpy import random` with `import random`
- `random.uniform(x, y)` call on line 24 is already compatible (same signature)

### 3. `suggests/parsing.py` (function-by-function)

Replace `import pandas as pd` with `import polars as pl`.

**`to_edgelist()`** - `pl.DataFrame(edge_list)` is a drop-in for `pd.DataFrame(edge_list)`. The `edge` column stores Python tuples which become polars `Object` type. Convert to string repr for groupby compatibility: use `str((row["qry"], s))` instead of the tuple literal.

**`get_source_target_columns()`** - Rewrite to parse string edge tuples. Use `pl.concat([edges, edge_details], how="horizontal")` pattern. Since `to_edgelist` already produces source/target columns, this is mainly for loading external data.

**`parse_raw_data()`** - Replace `apply(parser).apply(pd.Series)` with Python list comprehension + `pl.DataFrame(parsed)` + `pl.concat(..., how="horizontal")`.

**`get_edges()`** - Use `data.group_by("source")` iteration. Fix the existing bug where it passes a DataFrame to `to_edgelist` (which expects `list[dict]`) by converting with `.to_dicts()`.

**`add_parent_nodes()`** - Key translations:
- `edges.copy()` -> `edges.clone()`
- `edges.rename(columns={...})` -> `edges.rename({...})`
- Column selection: `edges.select([cols])`
- `edges.merge(..., on=..., how="left")` -> `edges.join(..., on=..., how="left")`
- `edges.groupby("edge")` -> `edges.group_by("edge")`
- `col.str.cat(sep=" ")` -> `col.str.concat(delimiter=" ")`
- `col.any()` -> `col.is_not_null().any()`
- `pd.DataFrame({...}).reset_index()` -> just build the DataFrame directly

**`add_metanodes(edges: pl.DataFrame) -> pl.DataFrame`** - Change from row-wise Series to DataFrame-level. Use `pl.struct([cols]).map_elements(_compute_metanode)` + `.unnest()` to compute source_add/target_add. Extract the row logic into a private `_compute_metanode(row: dict) -> dict` helper.

### 4. `suggests/nets.py`
- Replace `pd.Series(dict(...)).apply(pd.Series)` with list comprehension:
  ```python
  records = [{"node": n, **attrs} for n, attrs in g.nodes(data=True)]
  return pl.DataFrame(records)
  ```

### 5. `scripts/demo.py`
- `pd.DataFrame(tree)` -> `pl.DataFrame(tree)` (`.shape` and `.head()` are the same)

### 6. `tests/test_parsing.py`
- `pd.DataFrame` -> `pl.DataFrame` in isinstance checks
- `edges.iloc[0]["target"]` -> `edges[0, "target"]`
- `edges["rank"].min()` -> same (works in polars)
- `result[result["depth"] == 0]` -> `result.filter(pl.col("depth") == 0)`
- `.isna().all()` -> `.is_null().all()`
- Update `add_metanodes` test to use new DataFrame API

### 7. `tests/test_nets.py`
- `pd.DataFrame` -> `pl.DataFrame` in isinstance checks

### 8. `tests/test_integration.py` (new)
Load `data/tests/abortion-20260312-122801.json` (JSONL) and `abortion-20260312-122801-edges.csv`. Test the full pipeline:
- `to_edgelist` produces correct row count
- `add_parent_nodes` adds parent/grandparent columns, depth 0 has null parents
- `add_metanodes` adds source_add/target_add columns
- Full pipeline output matches the expected edges CSV (row count, column values)

### 9. `README.md`
- Update line 158: `edges = edges.apply(suggests.add_metanodes, axis=1)` -> `edges = suggests.add_metanodes(edges)`

## Verification

1. `uv run pytest tests/ -v` - all existing + new tests pass
2. `uv run ruff check suggests/ tests/ scripts/` - no lint errors
3. Verify no pandas/numpy imports remain: `grep -r "import pandas\|import numpy" suggests/ scripts/ tests/`
