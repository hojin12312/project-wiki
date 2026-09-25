---
title: Current State
type: current
status: current
updated: 2026-09-25
---

# Current State

## Working

- Package version 0.8.0 / SCHEMA policy 0.3.2 (observed 2026-09-25,
  `VERSION`, `core/SCHEMA_VERSION`).
- `wiki_state.py` commands: `self-update`, `preflight`, `budget`, `host`,
  `anchor`, `lock`, `unlock` (code read; `self-update` returned `current`
  this run; `preflight` and `budget` exercised on fixtures and this repo).
- `wiki_lint.py` structural lint: frontmatter, page structure, broken links,
  inline-path roles (`wiki:not-preserved`, `wiki:local-path`), budgets,
  schema-version comparison (code read; exercised on fixtures).
- Test suite: 62 tests pass (observed 2026-09-25, this host,
  `python3 -m unittest discover -s tests`).
- Skills install via `install.sh` into `~/.claude/skills`,
  `~/.agents/skills`, `~/.config/opencode/skills` when present; this
  machine's links resolve into this repo (observed 2026-09-25).

## Partially Implemented

- None known.

## Not Yet Implemented

- None recorded in the code; per-file TODOs, if any, are tracked in source.

## Current Blockers

- None.

## Active Risks / Unknowns

- `docs/design.md` is the initial design spec and is partially superseded;
  README states README and `core/` win on disagreement. Treat `design.md`
  claims as leads, not facts.
- Open issues #19–#24 were addressed in 0.8.0 (`5711068`); their GitHub
  issues are not yet closed. Issue comments describing the resolution have
  not been posted (Not yet verified whether the user wants them closed).

## Next Logical Work

- Push `main` (1 commit ahead of origin) and create tag `v0.8.0` + GitHub
  release per `core/protocol.md` §12 step 8 — needs the user's go-ahead.
- Close or comment on issues #19–#24 once the user confirms the 0.8.0
  resolution scope.
