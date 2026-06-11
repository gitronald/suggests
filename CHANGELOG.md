# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.0] - 2026-06-10

### Added

- `suggests-plot` command for rendering a network plot from any edge-list CSV (requires the `viz` extra); demo and plot scripts moved into the package as `suggests.scripts`
- PyPI publish workflow (tag-triggered, gated on the `PUBLISH_ENABLED` repository variable) and Dependabot configuration

### Changed

- `get_google_url()` and `get_bing_url()` results are cached, and the requester's URL caches are bounded
- `to_edgelist()` uses a faster columnar build

### Fixed

- Import error in the `nets` module on Python 3.11 (deferred annotations)
- `sleep=0` no longer falls back to the default throttle delay

### Removed

- Unused functions `set_edge_attributes`, `get_source_target_columns`, `parse_raw_data`, `get_edges`, and `parse_bing_qry`

## [0.3.1] - 2026-03-21

### Added

- `plot_network()` for rendering suggestion networks with an igraph layout, Louvain communities, and adjustText labels, plus `spacing` and `label_alpha` parameters
- Test suite with pytest, coverage, integration-test fixture data, and a GitHub Actions CI workflow
- Type hints and docstrings across all modules

### Changed

- **Breaking:** migrated data operations from pandas and numpy to polars
- **Breaking:** requires Python >= 3.11
- New `add_metanodes()` API
- Replaced deprecated `str.concat` with `str.join`

### Fixed

- Bugs in the requester, `set_edge_attributes()`, and `parse_bing_qry()`
- Multi-parent concatenation in `add_parent_nodes()`
- Demo script handling of mixed-type Google data

## [0.3.0] - 2026-03-12

### Added

- Language support: `hl` parameter for Google and `mkt` parameter for Bing, with encoding-aware result decoding

### Changed

- API parameters are URL-encoded for Google and Bing
- Removed `sclient` from the public API (still used internally by `get_google_url`)
- Migrated packaging from Poetry to uv

## [0.2.0] - 2025-02-04

### Added

- Argument for setting session headers
- Demo script

### Changed

- Requires pandas and numpy >= 2
- Switched to a Poetry v2 setup
- Replaced deprecated `datetime.utcnow()` usage

### Removed

- Unused general utilities

## [0.1.3] - 2024-11-12

### Changed

- Cleanup, docstrings, and type hints across modules

### Removed

- bumpversion configuration

## [0.1.2] - 2024-10-29

First tagged release.

### Changed

- Replaced the root logger with a package-scoped logger
- Use the full `beautifulsoup4` package name in dependencies

[Unreleased]: https://github.com/gitronald/suggests/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/gitronald/suggests/compare/v0.3.1...v0.4.0
[0.3.1]: https://github.com/gitronald/suggests/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/gitronald/suggests/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/gitronald/suggests/compare/v0.1.3...v0.2.0
[0.1.3]: https://github.com/gitronald/suggests/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/gitronald/suggests/releases/tag/v0.1.2
