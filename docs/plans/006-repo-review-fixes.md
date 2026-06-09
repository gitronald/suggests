---
status: draft
branch: claude/repo-code-review-9dELY
created: 2026-06-06T00:00:00-07:00
completed:
pr:
---

# Repo code review fixes

## Context

Full-repository code review (2026-06-06) on a clean tree (46 tests passing,
`ruff check` clean). The review surfaced several correctness bugs, dead code,
and packaging issues. This plan tracks the agreed-upon items for a follow-up
implementation pass. Nothing here is implemented yet — this file only captures
the plan.

Decisions baked in from review discussion:

- **Keep `source="bing"` as the default.** Bing's autocomplete endpoint has
  looser (possibly no) rate limiting compared to Google, which makes it the
  safer default for recursive crawling. The README/docstrings lean Google, but
  the default stays Bing. No code change — documentation alignment only (see
  item 6).
- **HTTP vs HTTPS for Bing needs empirical verification** before we change
  `get_bing_url`. We may not be able to use HTTPS. See item 1 for the full
  investigation + test design.
- **Move `scripts/` into a package module** so the `demo` entry point actually
  ships in the wheel. See item 3.

---

## Item 1: Bing HTTP vs HTTPS — investigate before changing 🔎

`suggests/suggests.py:66` — `get_bing_url` builds an `http://` URL while
`get_google_url` uses `https://`. The review initially flagged this as a
transport-security nit ("just upgrade to https"), but it may not be that simple:
the `http://www.bing.com/AS/Suggestions` endpoint is an older internal
autocomplete path and **HTTPS may redirect, 404, return a different payload
shape, or behave differently for rate limiting**. We must not blindly flip the
scheme.

### What we could NOT determine in-sandbox

The Claude Code remote environment's network policy blocks outbound hosts
(`requests.get(...)` to both `http://www.bing.com` and `https://www.bing.com`
returned `403 Host not in allowlist` from the proxy, not from Bing). So the
empirical comparison **must be run in an environment with network egress to
`www.bing.com`** — locally or in a CI job with an appropriate network policy.
This constraint is exactly why the test below is network-gated and skippable.

### Investigation steps (run with real network access)

1. Request the same query over both schemes with the package's user agent and
   `allow_redirects=False`. Record for each: status code, `Location` header,
   final URL, response length, and whether `parse_bing` extracts non-empty
   suggestions.
2. Repeat with `allow_redirects=True` to see where HTTPS lands (does it 301 to
   `http://`, to a different host/path, or serve directly?).
3. Compare parsed suggestion output (`parse_bing`) between the two to confirm the
   payload shape is identical (the parser keys on `div.sa_tm`).
4. Note any difference in throttling behavior across a short burst (e.g. 10
   sequential calls) — relevant to the "Bing has looser rate limits" assumption.

### Decision matrix

| HTTPS result | Action |
|---|---|
| 200 + identical parseable payload | Switch `get_bing_url` to `https://`; keep HTTP test as a regression guard. |
| 301/302 → `http://` (downgrade) | Keep `http://` to avoid an extra round-trip; document *why* with a code comment + this plan link. |
| 403/404/different payload | Keep `http://`; document that HTTPS is unsupported by this endpoint. |

### Test to add (`tests/test_integration.py` or a new `tests/test_network.py`)

Network-gated so it never breaks offline CI, but runnable on demand to answer
the question and guard against future endpoint changes:

```python
import pytest
import requests
from suggests.suggests import get_bing_url, prepare_qry
from suggests.parsing import parse_bing

# Opt-in marker; register in pyproject.toml [tool.pytest.ini_options] markers.
# Run with: uv run pytest -m network
pytestmark = pytest.mark.network

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:58.0) "
                    "Gecko/20100101 Firefox/58.0"}


def _fetch(scheme: str, qry: str = "dog", **kwargs):
    base = get_bing_url()  # builds http://... by default
    url = base.replace("http://", f"{scheme}://", 1) + prepare_qry(qry)
    return requests.get(url, headers=UA, timeout=10, **kwargs)


class TestBingScheme:
    def test_http_returns_suggestions(self):
        """Baseline: the shipped http:// endpoint works and parses."""
        r = _fetch("http")
        assert r.status_code == 200
        suggests = parse_bing(r.text, qry="dog")["suggests"]
        assert len(suggests) > 0

    def test_https_behavior_documented(self):
        """Characterize https:// so a scheme change is evidence-based.

        This test does not assert a fixed outcome — it records what https
        does. Tighten the assertions once item 1's decision matrix is
        resolved (e.g. assert 200 + parseable, or assert redirect-to-http).
        """
        r = _fetch("https", allow_redirects=False)
        # Document, don't dictate, until we have real data:
        assert r.status_code in (200, 301, 302, 403, 404)
        if r.status_code == 200:
            assert len(parse_bing(r.text, qry="dog")["suggests"]) > 0
        elif r.status_code in (301, 302):
            assert r.headers.get("Location") is not None
```

Also: register the `network` marker in `pyproject.toml` under
`[tool.pytest.ini_options]` so `-m network` / `-m "not network"` work and
unmarked CI stays offline:

```toml
[tool.pytest.ini_options]
markers = [
    "network: tests that require live outbound HTTP (deselect with -m 'not network')",
]
```

**Until this is resolved, leave `get_bing_url` on `http://`.**

---

## Item 2: `sleep=0` does not disable throttling 🔴

`suggests/suggests.py:105`

```python
time.sleep(sleep) if sleep else sleep_random()
```

`sleep` defaults to `None`, but the truthiness test routes `sleep=0` (the
natural "don't throttle" value) into the `else` branch, producing a random
0.7–1.4s sleep anyway. Propagates through `get_suggests` and
`get_suggests_tree`. Current tests miss it because they pass truthy values or
mock `sleep_random`.

**Fix:** change the guard to `if sleep is not None`.

```python
if sleep is not None:
    time.sleep(sleep)
else:
    sleep_random()
```

**Tests to add:**
- `requester(..., sleep=0)` patches `time.sleep` and `sleep_random`, asserts
  `sleep_random` is NOT called and `time.sleep(0)` IS called.
- `requester(..., sleep=None)` (default) asserts `sleep_random` IS called.

---

## Item 3: Move `scripts/` into a package module 📦

`pyproject.toml:20` declares `demo = 'scripts.demo:main'`, but `scripts/` has no
`__init__.py` and hatchling auto-detects only `suggests/`. Confirmed: `scripts/`
is **not included in the built wheel**, so the `demo` console script fails for
anyone who `pip install`s the package (`ModuleNotFoundError: scripts`).

**Plan:**
1. Create `suggests/scripts/__init__.py` (new subpackage).
2. Move `scripts/demo.py` → `suggests/scripts/demo.py` and
   `scripts/plot_abortion_tree.py` → `suggests/scripts/plot_abortion_tree.py`.
3. Update the entry point: `demo = 'suggests.scripts.demo:main'`.
4. Fix path-dependent references in `plot_abortion_tree.py` — it currently uses
   `Path(__file__).parent.parent` to find `tests/fixtures` and `img/`. After the
   move it's one level deeper (`suggests/scripts/`), so those need
   `.parent.parent.parent`, OR (better) make the fixture/img paths configurable
   via CLI args / packaged data so they don't reach outside the installed
   package. Note `tests/fixtures` won't exist in an installed wheel — decide
   whether `plot_abortion_tree` is a dev-only script (keep referencing repo
   paths, don't ship as entry point) or a real packaged command (bundle the
   data).
5. `demo.py` writes to `./data/tests/...` (cwd-relative) — fine for a CLI but
   note it assumes a writable cwd; consider `tempfile`/configurable output.
6. Remove the now-empty top-level `scripts/` dir.

**Decision needed:** is `plot_abortion_tree` a shipped command or a dev script?
That determines whether it moves into the package or stays repo-only. Default
recommendation: keep `demo` as the only console script; keep
`plot_abortion_tree` as a dev/repo script (it depends on test fixtures + dev-only
plotting deps).

---

## Item 4: Remove `print()` in `_compute_metanode` 🟠

`suggests/parsing.py:280` — bare `print(f"circle back: {source_add}")` fires
917× on the abortion fixture, polluting stdout for real crawls. Replace with
`log.debug(...)` (module logger already exists at `parsing.py:13`). Already noted
in plans 004 & 005 as deferred; consolidating here.

---

## Item 5: `parse_bing_qry` omits the parser argument 🔴

`suggests/parsing.py:114` — `BeautifulSoup(raw_html)` without `"html.parser"`
emits `GuessedAtParserWarning` and is non-deterministic across environments
depending on installed parsers. `parse_bing` does this correctly; make
`parse_bing_qry` consistent: `BeautifulSoup(raw_html, "html.parser")`.

Note this function is currently unexported and unused (see item 7) — decide
whether to fix-and-keep or remove.

---

## Item 6: Dead code & unused parameters 🟡

- `allow_zip` parameter (`suggests.py:74`) is declared + documented but never
  used in `requester`'s body. Implement gzip handling or drop the param.
- Unused/unexported utilities, not in `__init__.__all__`, not called in package
  or tests: `get_source_target_columns`, `parse_raw_data`, `get_edges`,
  `parse_bing_qry` (`parsing.py`), `set_edge_attributes` (`nets.py`). For each:
  either (a) promote to public API — add to `__all__` + add tests, or (b) remove.
  - Note: `get_edges` → `parse_raw_data` → `parse_google(row)` passes `qry=""`,
    so `self_loops` is silently always empty on that path. If kept, fix or
    document.
- Align README/docstrings with the Bing default (item context) — currently
  Google-centric examples while the default `source` is `"bing"`.

---

## Item 7: Minor / nits 🟡

- **`to_edgelist` on empty input** (`parsing.py:204`): an all-empty `edge_list`
  yields a columnless `pl.DataFrame([])`, making downstream `add_parent_nodes`
  fail with a confusing error. Return an explicit empty frame with the known
  schema instead.
- **Type hint inaccuracy** (`parsing.py:78,105`): `parse_google -> dict[str,
  list]`, but `tags` is a `dict` on success and `[]` on failure. Tighten the
  annotation / normalize the shape.
- **Logging reconfigured on import**: module-level `logger.Logger().start()` in
  `suggests.py:14` and `parsing.py:13` calls `logging.config.dictConfig` at
  import time (harmless given `disable_existing_loggers: False`, but surprising
  for a library). Consider letting the application own logging config.
- **`plt.cm.tab20`** (`nets.py:201`): works today but the modern API is
  `matplotlib.colormaps["tab20"]`; `plt.cm.*` is on a slow deprecation path.
- **Stale TODO** (`TODO.md:3`): the `requester` `UnboundLocalError` item is
  already fixed (`response = None` initialized at `suggests.py:107`). Check it
  off / remove.

---

## Suggested implementation order

1. Item 2 (sleep footgun) — small, real, user-visible.
2. Item 4 (print → log.debug) — trivial, high annoyance.
3. Item 5 (BeautifulSoup parser arg) — trivial correctness.
4. Item 1 (HTTP/HTTPS) — needs networked run; add gated test, then decide.
5. Item 3 (scripts → package) — packaging fix; needs the dev-vs-shipped decision.
6. Items 6 & 7 (dead code, nits) — cleanup pass.

## Open questions

- Item 1: does Bing's `/AS/Suggestions` serve over HTTPS with an identical
  payload? (Requires networked verification.)
- Item 3: is `plot_abortion_tree` a shipped console command or a dev-only
  script?
- Item 6: promote the unused utilities to public API, or delete them?

---

## Item 8: Behavior-preserving optimizations (added 2026-06-06) ⚡

Efficiency review with the constraint: **no new dependencies (no cost) and no
functionality change.** Findings ranked by real-world payoff, not theoretical
FLOPs.

### Framing — where optimization actually matters

The codebase has two paths with opposite cost profiles:

- **Scrape path** (`suggests.py`) is deliberately **I/O-bound**: a ~1s
  `sleep_random()` per request throttles crawling to avoid blocks. CPU
  micro-opts here are swamped by sleep + network latency — low value *during a
  crawl*.
- **Offline analysis path** (`parsing.py` → `nets.py`) runs on already-collected
  data (the abortion fixture is **12,112 edges**) with no network and no sleep.
  This is where CPU shows up — and `test_integration.py::test_full_pipeline_matches_expected`
  is an **exact-match golden test**, so behavior-preserving rewrites here are
  *verifiable*, not faith-based.

So `parsing.py` findings are weighted highest.

### High payoff (offline, 12k+ rows, golden-test verifiable)

**8a. `add_metanodes` Python UDF → native Polars** — `parsing.py:301-308`
`map_elements(_compute_metanode, ...)` runs a pure-Python function once per row
(12k+ calls, each doing string splits + set builds) — the single largest CPU
cost in the pipeline. The token diff is expressible with native list expressions
(`str.split` → `list.set_difference`), running in compiled code.
**Highest value but the only item with real behavior risk** — gate it on an
exact match against the golden fixture before/after. If a faithful vectorization
proves awkward (the case-insensitive logic from item 5 / circle-back fallbacks
are fiddly), keep the UDF. Do NOT ship a version that changes any fixture row.

**8b. `to_edgelist`: `OrderedDict` row-by-row → columnar build** — `parsing.py:175-205`
Two safe wins, no behavior change:
- `OrderedDict` is pointless on Python 3.11+ (dicts are ordered) — use plain
  `dict`.
- Better: accumulate parallel column lists and build `pl.DataFrame({...})` once,
  instead of N dicts → DataFrame. Less allocation, more idiomatic, identical
  output.

**8c. Redundant double `html.unescape` on `target`** — `parsing.py:181`
Confirmed empirically: `parse_google`/`parse_bing` already unescape every
suggestion, then `to_edgelist` unescapes `target` *again* (while leaving
`source` untouched). Removing the second call drops 12k redundant calls and
makes `source`/`target` symmetric. Idempotent for normal entities → verify no
change against the golden fixture. (Borderline correctness improvement too.)

**8d. Drop the unnecessary `.clone()`** — `parsing.py:217`
Polars never mutates in place and `edges` is only rebound by joins, so
`edges_original = edges` suffices instead of `edges.clone()`. Removes a copy.

### Modest payoff (scrape path — minor, sleep dominates)

**8e. Fuse `parse_google`'s two passes** — `parsing.py:95-98`
Builds the suggest list, then rebuilds it applying `suggest_parser`. Combine into
one comprehension — one list instead of two, identical result.

**8f. Hoist URL base out of the request loop** — `suggests.py:100-103`
`get_bing_url(...)`/`get_google_url(...)` re-`urlencode` static params on every
call. Negligible vs the sleep, but trivially computed once.

**8g. `parse_bing` double tree-walk on empty check** — `parsing.py:137-140`
`if not soup.text:` materializes all text just to test emptiness, then
`find_all` re-traverses. Check `raw_html` emptiness before building the soup to
skip both on empty responses.

### Examined and deliberately NOT touched

- **Import cost** — already optimal. Verified `import suggests` pulls only `bs4`
  + `polars`; matplotlib/igraph/networkx/scipy/numpy stay lazy behind
  `suggests.nets`. A real strength — do **not** regress it by importing `nets`
  from `__init__.py`.
- **Centralities** (`nets.py:19-27`) — betweenness is O(V·E) but it *is* the
  output; can't cut without changing functionality.
- **bs4 `html.parser`** — `lxml` would be faster but adds a dependency (= cost).
- **The `sleep`** — it's the anti-blocking mechanism. Off-limits.

### Not a perf fix — readability/scaling hygiene only

**8h. BFS rescan** — `suggests.py:208`:
`{d["qry"]: d["suggests"] for d in tree if d["depth"] == depth}` rescans the
whole accumulated `tree` every depth (O(depth·N)). A frontier list makes it
O(N), **but** each node costs ~1s of network+sleep, so this is pure noise in
practice. File as hygiene, not performance — do not over-claim a speedup.

### Optimization implementation order

1. 8d, 8b (OrderedDict→dict), 8e, 8f, 8g — trivial, safe, no fixture risk.
2. 8c — verify against golden fixture (expected: no diff).
3. 8b (columnar build) — moderate, no behavior change.
4. 8a — highest value, gated strictly on golden-fixture exact match; abandon if
   it can't reproduce output faithfully.

---

## Implementation log

### 2026-06-06 — safe quick-win batch (implemented)

Implemented and verified (48 tests pass incl. the exact-match golden
integration test; `ruff check` clean):

- **Item 2** — `requester` now uses `if sleep is not None` so `sleep=0` disables
  throttling instead of falling through to `sleep_random()`
  (`suggests.py:107-110`). Added two regression tests
  (`test_sleep_zero_disables_random_sleep`, `test_sleep_none_uses_random_sleep`).
- **Item 4** — `print("circle back: ...")` → `log.debug("circle back: %s", ...)`
  (`parsing.py`).
- **Item 5** — `parse_bing_qry` now passes `"html.parser"` to `BeautifulSoup`
  (`parsing.py`).
- **Item 8d** — dropped redundant `edges.clone()` → `edges_original = edges`
  (`parsing.py`).
- **Item 8e** — fused `parse_google`'s two list comprehensions into one pass.
- **Item 8f** — `@functools.lru_cache` on `get_google_url` / `get_bing_url` so
  the static URL base is built once per unique args instead of every request.
- **Item 8g** — `bing_parser` drops the redundant `soup.text` double-walk and
  fuses the `html.unescape` pass; None/empty-input behavior preserved (verified
  by `test_empty_html`).

### Still deferred (not in this batch)

- **Item 1** — Bing HTTP/HTTPS: needs a networked run (sandbox blocks egress).
- **Item 3** — scripts → package module: blocked on the dev-vs-shipped decision.
- **Item 6 / 7** — dead-code removal, type-hint/empty-frame nits, stale TODO.
- **Item 8a** — native-Polars metanode rewrite (highest value, golden-test gated).
- **Item 8b** — `to_edgelist` columnar build / `OrderedDict`→`dict`.
- **Item 8c** — remove redundant double `html.unescape` on `target`.
