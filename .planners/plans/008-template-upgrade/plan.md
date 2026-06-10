---
id: 8
slug: template-upgrade
status: active
branch: feature/template-upgrade
created: 2026-06-10T14:10:06-07:00
concluded:
pr:
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
