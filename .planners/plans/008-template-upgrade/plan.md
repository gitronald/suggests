---
id: 8
slug: template-upgrade
status: done
branch: feature/template-upgrade
created: 2026-06-10T14:10:06-07:00
concluded: 2026-06-10T14:47:33-07:00
pr: https://github.com/gitronald/suggests/pull/22
---

# Upgrade to the latest proj-template standard

## Plan

Sync this repo to the current proj-template standard via the
`install-template` skill's upgrade mode. Classification: **package**
(hatchling build backend, `[project.scripts]`, published-style metadata,
`tests/`), so the full sync matrix applies.

Sync decisions per matrix row:

- `pyproject.toml`: add `[tool.ruff]` + `[tool.ruff.lint]` (F, E, W, I, UP;
  target py311 to match `requires-python >= 3.11`), `[tool.pyrefly]` strict
  preset with a `tests/**` sub-config relaxing `implicit-any`, and
  `[tool.pytest.ini_options]`. Add `pyrefly` to the dev group. Add the sdist
  `only-include` block so plan files, tests, and tooling stay out of the
  published sdist.
- `.pre-commit-config.yaml`: add the ruff (format + fix) and pyrefly hooks
  ahead of the existing `planners-validate` hook.
- `.python-version`: already 3.14 — no change.
- `.gitignore`: merge template entries; fix the merged-line bug
  (`notebooks.worktrees/` is two entries collapsed into one).
- `.claude/` payload (`settings.json`, `hooks/lint-typecheck.sh`): copy to
  disk. `.claude` is already gitignored here, so the payload stays untracked
  (the template standard).
- `.github/workflows/test.yml`: sync to the template version — version-tag
  action pins, `permissions: contents: read`, and ruff + pyrefly steps ahead
  of pytest.
- `.github/workflows/publish.yml`: add (package row) — disabled by default
  behind the `PUBLISH_ENABLED` repo variable.
- `.github/dependabot.yml`: add (no update automation exists).
- `.planners/`: already migrated — no change.
- `suggests/`, `tests/`, `README.md`: untouched (never rows).

Verification gate: `uv sync --all-groups`, `ruff format --check`,
`ruff check`, `pyrefly check`, `pre-commit run --all-files`, and `pytest`
all green before the Stop hook lands.

## Log

**2026-06-10 — implementation.**

- Tooling: added `[tool.ruff]`/`[tool.ruff.lint]`, `[tool.pyrefly]` strict
  (tests sub-config relaxing `implicit-any`), `[tool.pytest.ini_options]`,
  sdist `only-include`, and `pyrefly` dev dep. Synced the template pre-commit
  hooks ahead of `planners-validate`.
- CI: synced `test.yml` to the template (version-tag pins, permissions
  block, ruff + pyrefly steps; kept `--cov=suggests`); added `publish.yml`
  (disabled behind `PUBLISH_ENABLED`) and `dependabot.yml`.
- `.gitignore`: merged template entries and fixed a merged-line bug
  (`notebooks.worktrees/` was two entries collapsed into one).
- Code: ruff autofixes plus type annotations across `logger.py`, `nets.py`,
  `parsing.py`, `suggests.py`, and tests. `parse_google` now accepts
  `list[Any] | None` with an explicit None guard (matches the existing
  graceful-failure test). networkx stub false positives scoped out via a
  `suggests/nets.py` sub-config (overload/argument-type kinds only).
- Gate: ruff check + format, pyrefly (0 errors), pytest (52 passed), and
  pre-commit all green.

## Retrospective

- The package classification made the sync matrix mechanical — every row landed
  as specced, with the only real judgment calls in the pyrefly sub-configs.
- The template's CI matrix had a latent no-op: `uv run` steps ignored the matrix
  python and every cell ran `.python-version` (3.14). Pinning the matrix
  interpreter here exposed a real bug the green matrix had been hiding.
- That bug — `nx.DiGraph[str]` raising `TypeError` at import on 3.11–3.13 — was
  masked on 3.14 by deferred annotation evaluation. Lesson: a matrix is only as
  trustworthy as the interpreter each cell actually runs; verify it in the logs.
- Template side effects gate on the default branch: `dependabot.yml` grouping
  and `publish.yml` stayed inert until a release carried them to `main`. Worth
  stating in the plan when the payoff arrives a release later.
