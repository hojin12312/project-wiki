# Project Wiki

## Start Here

- [Overview](overview.md) — purpose, non-goals, hard constraints.
- [Current State](current.md) — implementation state, blockers, next work.

## Architecture

- [Package Layout](architecture/package-layout.md) — entry points, shared core, install and self-update mechanics.

## Components

- [wiki_state.py](components/wiki-state.md) — deterministic state tooling: preflight, budget, anchor, lock.
- [wiki_lint.py](components/wiki-lint.md) — structural lint checks and path markers.

## Decisions

- [SKILL.md Is an Entry Point Only](decisions/0001-skill-md-entry-point-only.md) — why procedure lives in `core/`, read after self-update.
- [Anchor and Lock Semantics](decisions/0002-anchor-and-lock-semantics.md) — run-trailer commits set the anchor; the lock is never auto-replaced.
