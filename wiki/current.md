---
title: Current State
type: current
status: current
updated: 2026-09-26
---

# Current State

## Working

- Package version 0.9.0 / SCHEMA policy 0.4.0 (observed 2026-09-26,
  `VERSION`, `core/SCHEMA_VERSION`).
- `wiki_state.py` commands: `self-update`, `preflight`, `budget`, `host`,
  `anchor`, `lock`, `unlock` (code read; `self-update` returned `current`,
  `preflight` and `budget` exercised this run on this repo).
- `wiki_lint.py` structural lint: frontmatter, page structure, broken links,
  inline-path roles (`wiki:not-preserved`, `wiki:local-path`), budgets,
  schema-version comparison (code read; exercised this run).
- Test suite: 62 tests pass (observed 2026-09-26, this host,
  `python3 -m unittest discover -s tests`).
- Skills install via `install.sh` into `~/.claude/skills`,
  `~/.agents/skills`, `~/.config/opencode/skills` when present; this
  machine's links resolve into this repo (observed 2026-09-26, self-update
  `package_dir`).

## Partially Implemented

- None known.

## Not Yet Implemented

- None recorded in the code; per-file TODOs, if any, are tracked in source.

## Current Blockers

- None.

## Active Risks / Unknowns

- `docs/design.md` is the initial design spec and is partially superseded —
  including its wiki-language passages, now superseded by `core/protocol.md`
  §10. README states README and `core/` win on disagreement. Treat
  `design.md` claims as leads, not facts.
- Open issues #19–#24 were addressed in 0.8.0 (`5711068`); their GitHub
  issues are not yet closed and no resolution comments have been posted
  (not yet verified whether the user wants them closed).
- No `v0.8.0` tag or release exists; 0.8.0's changes shipped under `v0.9.0`
  (observed 2026-09-26, `git tag` / `gh release` output this work unit).

## Next Logical Work

- Close or comment on issues #19–#24 once the user confirms the 0.8.0
  resolution scope.
