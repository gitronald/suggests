---
status: done
branch: update/pandas-to-polars
created: 2026-03-12T17:05:20-07:00
completed: 2026-03-12T18:04:12-07:00
pr: https://github.com/gitronald/suggests/pull/11
---

# Fix metanode processing bugs

## Context

`add_parent_nodes` concatenates multiple parent strings with spaces when a node is reachable via multiple paths. `add_metanodes` then splits on spaces assuming a single parent, corrupting the token-level diff logic. This produces duplicate tokens, incorrect "circle back" fallbacks, and nonsensical labels.

On the abortion test data (12,112 edges):
- 339 rows have repeated tokens in `source_add` (e.g. "farsi farsi", "sutter center sutter center")
- 78 rows have repeated tokens in `target_add`
- 716 rows have parent strings > 100 chars (multi-parent concatenation)
- 916 rows trigger the "circle back" fallback (target_add == source_add)
- 4 rows have null source_add

## Bug examples

### 1. Duplicate tokens from multi-parent concatenation

```
source:     "abortion in farsi"
parent:     "abortion meaning in farsi abortion definition in farsi"  (TWO parents concatenated)
grandparent: "abortion meaning in hebrew abortion meaning in greek ..."

source tokens: ["abortion", "in", "farsi"]
parent tokens: ["abortion", "meaning", "in", "farsi", "abortion", "definition", "in", "farsi"]

source_add = [t for t in source if t not in set(parent)]
           = []  (all source tokens appear in the bloated parent set)

Falls back to parent_add, which itself has duplicates -> "farsi farsi"
```

### 2. Oversized parent strings dilute the diff

```
source:     "abortion clinic open near me"
parent:     (713 chars! - many parents concatenated with spaces)
```

When the parent string is a concatenation of 10+ different parents, `set(parent.split(" "))` contains almost every common word, making `source_add` empty for most rows and triggering the circle-back fallback incorrectly.

### 3. Circle-back fallback masking real information loss

The fallback `if not target_add: target_add = source_add` (with `print("circle back: ...")`) fires 916 times (7.6% of edges). Many of these are legitimate (suggestion removes words), but many are caused by the inflated parent token set from bug #1.

## Root cause

In `add_parent_nodes()` (`suggests/parsing.py:222-235`):

```python
gb = edges.group_by("edge", maintain_order=True).agg(
    ...pl.col("parent").drop_nulls().str.join(" ")...
)
```

When a node has multiple parents (reachable via multiple paths), their names get joined into one string: `"parent1 parent2"`. This is then treated as a single space-delimited token list in `add_metanodes`, breaking the diff logic.

## Potential fixes

### Option A: Use first parent only
In the groupby aggregation, take `.first()` instead of `.str.join(" ")`. Simple but loses information about alternate paths.

### Option B: Deduplicate tokens after join
After joining, split and deduplicate: `" ".join(dict.fromkeys(parent.split(" ")))`. Preserves unique tokens but order may be wrong.

### Option C: Store parents as lists
Change parent/grandparent columns from strings to list columns. Update `add_metanodes` to work with lists instead of splitting strings. Most correct but changes the column schema.

### Option D: Pick the shortest parent
When multiple parents exist, use the shortest one (fewest tokens) as it's likely the most direct path. This preserves the simplest ancestry.

## Other potential issues in metanode processing

1. **The "circle back" print statement** (`parsing.py:246`) — should be a log message or removed, not a bare `print()`. It fires 900+ times on real data.

2. **Token diff is order-insensitive** — `[i for i in source if i not in set(parent)]` uses set membership, so word order doesn't matter. This is fine for bag-of-words but could produce odd results for phrases where word order matters.

3. **Null handling edge case** — When `source_add` is empty AND `parent_add` is also empty, `source_add` stays empty and gets written as `None`. Then `target_add` falls back to this empty `source_add`, potentially also becoming `None`. Only 4 rows are affected currently.

## Review (multi-expert, 2026-03-12)

Three parallel reviews evaluated the plan from correctness, API/schema, and testing perspectives.

### Option verdicts

| Option | Correctness | API/Schema | Verdict |
|--------|-------------|------------|---------|
| **A: First parent** | Fixes bug. Deterministic with `maintain_order=True`. | No schema/API change. CSV/parquet safe. | **Selected** |
| **B: Dedup tokens** | Does NOT fix bug — union of two parents still bloats the token set. Wrong layer. | No schema change. | Reject |
| **C: List columns** | Correct data model but incomplete — doesn't specify which parent to diff against. | Breaking: `Utf8` -> `List(Utf8)`. CSV serialization fails. `_compute_metanode` needs rewrite. | Reject |
| **D: Shortest parent** | Heuristic is wrong — shortest string != most direct path. Depth encodes distance, not token count. | No schema change. | Reject |

### Key findings

- Option B fails in the general case: joining `"abortion meaning in farsi"` + `"abortion clinic open"` and deduplicating still produces a 6-token superset, bloating diffs.
- Option D's "shortest = most direct" claim is incorrect: in a BFS tree, all parents at the same depth are equidistant. Token count doesn't model path distance.
- The `.first()` after `.str.join()` in the current code is a no-op — the `pl.when().then().otherwise()` inside `agg` already produces a scalar.
- No existing test constructs a multi-parent scenario, so the bug is invisible to current tests.
- A regression test should assert every non-null `parent` value exists in the `source` column (a concatenated parent won't).

### Implementation plan (Option A)

1. **Fix `add_parent_nodes`**: Replace `.str.join(" ")` with `.first()` for both `parent` and `grandparent` aggregations in the `group_by` block (lines 246-257).
2. **Replace `print()` with `log.debug()`**: Convert the bare `print(f"circle back: ...")` at line 277 to use the module-level logger.
3. **Add multi-parent fixture**: Create a synthetic tree where the same target is reachable from two different sources, producing multiple parents per edge.
4. **Add regression tests**:
   - Assert every non-null `parent` value appears in the `source` column of the original edges.
   - Assert no repeated tokens in `source_add` or `target_add`.
   - Test `_compute_metanode` directly for edge cases (no parent, parent == source, empty diffs).
5. **Update integration test fixture**: Regenerate the reference CSV with corrected output. Manually inspect previously-corrupted rows to confirm correctness.
6. **Add metric assertions**: Zero repeated tokens, zero oversized parent strings, reduced circle-back count.

## Log

- Implemented Option A: replaced `.str.join(" ")` with `.first()` in `add_parent_nodes` group_by aggregation (2 lines in `parsing.py:248,253`).
- Regenerated integration test reference CSV. All 43 tests pass.
- Post-fix metrics: repeated tokens in source_add dropped 339 -> 27, target_add 78 -> 58, oversized parents 716 -> 0, null source_add 4 -> 0. Remaining repeats are from legitimate query content (e.g., "what are the of the"), not the multi-parent bug.
- Data review uncovered a separate case-sensitivity issue in the token diff affecting 41 rows (Google entity suggestions with proper casing). Tracked in plan 006.
- Secondary items (print -> log.debug, regression tests, multi-parent fixture) deferred for follow-up.

## Next

- [006-case-sensitive-token-diff](006-case-sensitive-token-diff.md) — case-insensitive token diff for entity suggestions
