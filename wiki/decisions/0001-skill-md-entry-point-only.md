---
title: SKILL.md Is an Entry Point Only
type: decision
status: accepted
updated: 2026-09-25
---

# SKILL.md Is an Entry Point Only

## Context

Each harness loads `SKILL.md` when the skill is invoked — potentially before
the package self-updates. If the file carried the real procedure, a stale
copy would drive the run.

## Decision

`wiki-init/SKILL.md` and `wiki-update/SKILL.md` contain only: run
`self-update` first, then read `core/protocol.md` and the command's
procedure file from disk, then follow it. All procedure lives in `core/`.

## Rationale

The file read after self-update is guaranteed current; the file loaded by
the harness is not. Keeping procedure out of `SKILL.md` makes "the version
on disk" always authoritative and removes two copies to keep in sync.

## Alternatives Considered

- Full procedure in `SKILL.md` (older design): rejected because the harness
  may hold the pre-update copy.
- Separate copies per skill: rejected — `core/` shared by both skills keeps
  one canonical protocol.

## Consequences

- The README's "modify here" section documents that procedure goes into
  `core/`, never `SKILL.md`.
- `install.sh` verifies each linked skill exposes `SKILL.md` and the core
  procedure files.

## Evidence

- `wiki-init/SKILL.md`, `wiki-update/SKILL.md` (three numbered lines each).
- `docs/design.md` §3 (entry-point design) — partially superseded but the
  intent holds.

## Relevant Implementation

- `wiki-init/`, `wiki-update/` directories; `install.sh` reachability check.

## Related Pages

- [Package Layout](../architecture/package-layout.md)
