---
id: 7
slug: migrate-to-planners-layout
status: done
branch: feature/migrate-to-planners-layout
created: 2026-06-10T09:12:23-07:00
concluded: 2026-06-10T09:13:17-07:00
pr: https://github.com/gitronald/suggests/pull/21
---

# Migrate plans to the .planners layout

## Plan

Migrate this repo from the legacy `docs/plans/` + `TODO.md` layout to the
`planners` package's `.planners/` layout, following the fleet rollout runbook
(quipus plan 033, `planners-migration` skill).

Scope:

- Standardize frontmatter on all 7 legacy plans (000-006): add `id`/`slug`
  and rename the terminal field `completed` -> `concluded`. All done plans
  already carry branch + PR.
- Author plan 000's placeholder title (`# Plan`) from its TODO entry:
  "Add language parameter" (established fleet pattern).
- Move each plan to `.planners/plans/<NNN>-<slug>/plan.md` and repoint any
  in-repo references to the old paths.
- Retire `TODO.md` — every item already links a plan (no `(no plan)` items;
  the single open item's plan 005 is `draft`, so its open work survives).
- Remove the boilerplate `docs/README.md` (fleet-confirmed).
- Install the planners holder, wire and activate the pre-commit validate
  hook, generate the index, and validate.

## Log
**2026-06-10 — migration run (review list + decisions).**

- **Frontmatter pass (7 legacy plans, 000-006):** added `id`/`slug`; renamed
  `completed:` -> `concluded:`. All done plans already carried branch + PR;
  no enum or empty-vs-null fixes needed.
- **Plan 000 placeholder title:** `# Plan` -> "Add language parameter",
  authored from its TODO entry (established fleet pattern).
- **TODO.md retired with no stubs:** every item linked a plan; the single
  open item's plan (005) remains `draft`, so its open work survives in the
  index.
- **docs/README.md removed:** boilerplate plans-pointer only
  (fleet-confirmed).
- **Hook:** wired and activated; passes on all 8 plans. Installed from the
  worktree — re-install from the main checkout after merge.
- **Review follow-up:** review posted to PR #21 — no findings. Check gate:
  pytest 52 passed; `planners validate` ok (8 plans).
- **Out of scope:** GitHub reported 11 dependabot vulnerabilities on the
  default branch at push time — pre-existing, not touched by this migration.

## Retrospective

- The simplest sweep repo so far: a fully plan-linked TODO means the
  reconciliation step reduces to `git rm`.
- Placeholder `# Plan` titles resolve directly from the TODO entry wording
  when the slug matches it — third occurrence of the pattern.
