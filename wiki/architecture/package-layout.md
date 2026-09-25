---
title: Package Layout
type: architecture
status: current
updated: 2026-09-25
---

# Package Layout

## Purpose

How the skill package is organized so the same canonical procedure reaches
every supported harness without duplicating rules.

## Current Design

- `wiki-init/` and `wiki-update/` each contain a thin `SKILL.md`, an
  `agents/openai.yaml` (Codex adapter that disables implicit invocation), and
  a `core -> ../core` relative symlink.
- `core/` holds the shared contract: `protocol.md` (common rules), `init.md`
  and `update.md` (per-command procedures), `SCHEMA.template.md` +
  `SCHEMA_VERSION` (the policy template installed as `wiki/SCHEMA.md`),
  `page-schema.md` (page templates), `schema-migrations.md`,
  `review-checklist.md`, and `scripts/`.
- `install.sh` creates `<harness skills dir>/wiki-init` and `wiki-update`
  symlinks pointing into this repository, only for harnesses present on the
  machine (`~/.claude/skills`, `~/.agents/skills`, `~/.config/opencode/skills`).
  It never overwrites an existing file or a foreign link.
- Self-update (`wiki_state.py self-update`) fast-forwards the package repo
  from `origin` `main` at the start of every run; both `SKILL.md` files tell
  the agent to run it before reading any procedure. A serialized package
  lock prevents concurrent self-updates.

## Invariants

- `SKILL.md` stays an entry point: no procedure text is duplicated into it
  (see `decisions/0001-skill-md-entry-point-only.md`).
- Skills reference shared files only as `<skill-dir>/core/...`; never `..`
  path arithmetic, because the installed location resolves differently under
  a symlink.
- Two versions exist: `VERSION` (package) and `core/SCHEMA_VERSION` (SCHEMA
  policy); the latter bumps only when `SCHEMA.template.md` changes.

## Data Flow

Invocation → `SKILL.md` → `self-update` (package lock) → read
`core/protocol.md` + `core/init.md`/`update.md` → run lock in the target
repo's `.git` → `preflight` JSON → procedure → `wiki_lint.py` → pathspec
commit with `Project-Wiki-Run:` trailer.

## Important Trade-offs

- Symlink install means every harness on a machine sees edits to this repo
  immediately; the same mechanism means uncommitted local edits permanently
  skip self-update until resolved (self-update reports `skipped`).
- Self-update follows `main`, not releases; tags/`gh release` exist for
  pinning, not for the update path.

## Relevant Implementation

- `install.sh` (`targets()` chooses skill dirs)
- `wiki-init/SKILL.md`, `wiki-update/SKILL.md`
- `wiki-*/agents/openai.yaml`
- `core/scripts/wiki_state.py` (`self-update`, package lock)

## Validation

- Install state verified on this machine: links resolve into this repo
  (observed 2026-09-25). Multi-harness recognition was confirmed during
  earlier bring-up per README (user-maintained record; not re-checked).

## Known Limitations

- OpenCode has no disable-invocation flag; it relies on the SKILL.md
  description wording.
- Self-update requires a clean, non-diverged package checkout; otherwise it
  reports `skipped` and the run continues with the on-disk version.

## Related Decisions

- [SKILL.md Is an Entry Point Only](../decisions/0001-skill-md-entry-point-only.md)
- [Anchor and Lock Semantics](../decisions/0002-anchor-and-lock-semantics.md)

## Related Pages

- [wiki_state.py](../components/wiki-state.md)
