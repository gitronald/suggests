---
id: 1
slug: modernize-project
status: done
branch: dev
created: 2026-03-12T12:07:30-07:00
concluded: 2026-03-12T12:20:11-07:00
pr: https://github.com/gitronald/suggests/pull/10
---

# Modernize project: docstrings, type hints, ruff, tests, CI

Reference: `~/repos/tools` for patterns and conventions.

## 1. Docstrings and type hints

**Current state:** `suggests.py` has excellent docstrings and type hints. The other three modules (`parsing.py`, `nets.py`, `logger.py`) are missing most or all type hints and many docstrings.

**Changes:**

- `suggests/__init__.py` — add module docstring, add `__all__` for explicit public API
- `suggests/parsing.py` — add type hints to all 10 functions, add missing docstrings to `get_source_target_columns`, `parse_raw_data`, `get_edges`, `add_parent_nodes`; replace bare `except:` with `except Exception:`
- `suggests/nets.py` — add type hints to all 5 functions, add missing docstrings to `get_root_component`, `find_unreachable_nodes`, add explicit `return None`
- `suggests/logger.py` — add type hints to `Logger.__init__` and `Logger.start`, fix docstring (removed broken example, added Args), change `Logger(object)` to `Logger`, replace `type(x) is str` with `isinstance`, replace `formatters.keys()` membership test with `formatters`
- `suggests/suggests.py` — update type hints from `Optional[X]`/`Union[X, Y]` to modern `X | None`/`X | Y` syntax, remove `typing` imports, remove unused `Exception as e` binding, strip `(type)` from docstring Args
- `scripts/demo.py` — add module docstring, type hint on `main()`

**Style (matching tools):**
- Google-style docstrings with Args/Returns/Raises (no type in Args, just description)
- Modern union syntax (`X | Y`, `X | None`) instead of `Optional`/`Union`
- No `from __future__ import annotations` — requires `>=3.11` so modern syntax works natively

## 2. Ruff linting

**Current state:** No linting config exists.

**Changes to `pyproject.toml`:**

Added `[dependency-groups]` with dev dependencies (ruff, pytest, pytest-cov, networkx).

No explicit `[tool.ruff]` section — uses defaults (matches tools).

**Ruff fixes applied:**
- `__init__.py` — F401 unused imports: resolved with `__all__` (not the `as X` re-export pattern)
- `suggests.py` — F841 unused variable `e` in `except Exception as e`
- All files reformatted with `ruff format`

## 3. Tests

**Current state:** No tests exist.

**Structure:**

```
tests/
├── conftest.py          # shared fixtures
├── test_suggests.py     # test get_suggests, get_suggests_tree
├── test_parsing.py      # test parsing functions
└── test_nets.py         # test network functions
```

**Contents (36 tests, 65% coverage):**
- `conftest.py` — fixtures for Bing HTML, Google JSON, sample trees (with/without self-loops, empty suggests), temp dir
- `test_suggests.py` (8 tests) — `prepare_qry`, `get_google_url`, `get_bing_url`, `sleep_random` (mocked `time.sleep`), `get_suggests` (mocked `requester` + `parsing` for both sources)
- `test_parsing.py` (16 tests) — `strip_html`, `parse_google` (basic, entity annotation, invalid data, self-loops), `parse_bing` (basic, empty, self-loops), `to_edgelist` (conversion, self-loop filtering, empty root, ranks, invalid type), `add_parent_nodes` (parent column, depth-zero nulls)
- `test_nets.py` (7 tests) — `set_node_attributes` (centrality attrs, root depth), `nodes_to_df`, `get_root_component` (found, missing), `find_unreachable_nodes` (disconnected, connected); networkx added as dev dependency

**Key decisions:**
- Mock HTTP requests via `unittest.mock.patch` (no live API calls)
- Inline fixture data (not from `data/tests/`)
- Pytest class-based organization (matching tools)

## 4. GitHub Actions

**Current state:** No `.github/workflows/` directory.

**Create `.github/workflows/test.yml`** (matching tools pattern):

```yaml
name: Tests

on:
  push:
    branches: [dev, main]
  pull_request:
    branches: [dev, main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12", "3.13", "3.14"]

    steps:
    - uses: actions/checkout@v4

    - name: Install uv
      uses: astral-sh/setup-uv@v5

    - name: Set up Python ${{ matrix.python-version }}
      run: uv python install ${{ matrix.python-version }}

    - name: Install dependencies
      run: uv sync --all-groups --python ${{ matrix.python-version }}

    - name: Run tests with coverage
      run: uv run pytest -v --cov=suggests --cov-report=term-missing
```

**Notes:**
- Python matrix starts at 3.11 (matching `requires-python = ">=3.11"`)
- Same workflow structure as tools

## Files modified

- `pyproject.toml` — add dev dependency group, bump `requires-python` to `>=3.11`
- `suggests/__init__.py` — add module docstring, add `__all__`
- `suggests/suggests.py` — modernize type hint syntax, drop `typing` imports
- `suggests/parsing.py` — add type hints and docstrings, fix bare excepts
- `suggests/nets.py` — add type hints and docstrings
- `suggests/logger.py` — add type hints, fix docstring and class definition
- `scripts/demo.py` — add module docstring and type hint

## Files created

- `tests/conftest.py`
- `tests/test_suggests.py`
- `tests/test_parsing.py`
- `tests/test_nets.py`
- `.github/workflows/test.yml`

## Verification

1. `uv sync --all-groups` — install dev dependencies
2. `uv run ruff check suggests/ tests/` — lint passes
3. `uv run ruff format --check suggests/ tests/` — format passes
4. `uv run pytest -v --cov=suggests --cov-report=term-missing` — 36 passed, 65% coverage

## Log

- Ruff F401: resolved with `__all__` instead of `as X` re-export pattern
- `from __future__ import annotations` dropped; bumped to `>=3.11` so modern syntax works natively
- networkx added as dev dependency (used by `nets.py` but not in core deps)
