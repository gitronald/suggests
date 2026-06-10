---
id: 5
slug: case-sensitive-token-diff
status: draft
branch:
created: 2026-03-12T18:04:12-07:00
concluded:
pr:
---

# Metanode token diff quality issues

## Context

Post-fix data review from plan 005 surfaced several remaining quality issues in `_compute_metanode` (`parsing.py:261-283`). The multi-parent concatenation bug is fixed, but the token diff logic itself has gaps.

## Issues found (abortion test data, 12,112 edges)

### 1. Case-sensitive token diff (41 rows, 35 broken)

Google returns "entity suggestions" with proper casing (e.g., `"Tia Women's Health Clinic San Francisco, Mission Street, San Francisco, CA"`), but the source query is lowercase (`"tia women's health clinic san francisco"`). The token diff is case-sensitive, so `"tia" != "Tia"` — causing the entire target to appear as `target_add` with zero overlap.

- 41 rows have mixed-case entity-style targets
- 35 of those have `target_add == target` (complete diff failure)
- 100 total rows have `target_add == target`; most caused by this case mismatch

Root cause in `_compute_metanode`:

```python
source = row["source"].split(" ")
target = row["target"].split(" ")
target_add = [i for i in target if i not in set(source)]
```

The set membership check is case-sensitive. When source is `["tia", "women's", "health"]` and target is `["Tia", "Women's", "Health", ...]`, nothing matches.

### 2. Nonsense functional-word diffs (27 rows)

Queries like `"what are the long term effects of the abortion pill"` with parent `"abortion pill side effects long term"` produce `source_add = "what are the of the"`. The diff is technically correct (those tokens aren't in the parent), but the result is a meaningless stopword fragment. Inherent to the bag-of-words approach.

### 3. Stopword-only source_add (159 rows)

Cases like `source_add = "on"` (from source `"abortion pill on amazon"`, parent `"abortion pill online amazon"`) or `source_add = "in"`. The only tokens distinguishing source from parent are functional words. Technically correct but low semantic value.

### 4. Circle-back print statement (917 invocations)

The bare `print(f"circle back: {source_add}")` at line 277 fires 917 times on the test data. Should be `log.debug()` or removed. Deferred from plan 005.

### 5. Missing test coverage for metanode edge cases

No multi-parent fixture, no direct `_compute_metanode` unit tests, no regression tests for parent-is-valid-source invariant. Deferred from plan 005.

## Potential fixes for case sensitivity

### Option A: Lowercase comparison, preserve original case in output

Compare tokens case-insensitively but keep the original-case tokens in the output:

```python
source_lower = {t.lower() for t in source}
target_add = [t for t in target if t.lower() not in source_lower]
```

This correctly identifies shared tokens across case boundaries while preserving the entity casing in the output. Apply the same pattern to all four diff operations in the function.

### Option B: Lowercase everything

Normalize all inputs to lowercase before diffing. Simpler but loses the original entity casing in `target_add`.

### Option C: Normalize at ingestion

Lowercase all suggestion strings when building the edge list. Most consistent but changes the raw data representation.
