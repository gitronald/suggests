---
id: 7
slug: migrate-to-planners-layout
status: active
branch: feature/migrate-to-planners-layout
created: 2026-06-10T09:12:23-07:00
concluded:
pr:
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
