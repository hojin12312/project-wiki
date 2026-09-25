---
title: Anchor and Lock Semantics
type: decision
status: accepted
updated: 2026-09-25
---

# Anchor and Lock Semantics

## Context

`/wiki-update` needs to know which source range the wiki last reviewed, and
two wiki runs in one checkout must not interleave edits.

## Decision

- The anchor is the `Source HEAD` of the newest `wiki/log.md` entry whose
  commit carries the `Project-Wiki-Run:` trailer and touches only wiki +
  instruction files. Hand-written log entries never advance the anchor.
- The run lock (`.git/project-wiki.lock`) is created atomically and is never
  taken over automatically, however stale; only a user-confirmed
  `unlock --force --id <id>` removes a specific lock.
- The lock records a snapshot plus `dirty_baseline`; the pre-commit preflight
  compares `edits_since_lock` and real diffs against that baseline rather
  than against an empty tree.

## Rationale

- Attributing the anchor to run-trailer commits keeps hand edits to `log.md`
  from accidentally narrowing the review range.
- A stale lock more often means a crashed run than a live one, but
  auto-replacing it can interleave two writers; the conservative choice is
  to stop and show the holder.
- Baseline-relative dirty comparison removes false "another writer"
  re-approvals for the run's own edits without weakening detection of real
  outside edits.

## Alternatives Considered

- Auto-expiring lock (1 hour): rejected — removed in 0.7.0 after it proved
  able to mask a still-running run.
- Anchor from any committed log entry: rejected — a hand-written entry could
  skip unreviewed ranges.

## Consequences

- Every wiki commit goes through the fixed pathspec sequence with the
  trailer; `git show --name-only` verifies it touched only allowed paths.
- Mixed commits (source + wiki in one) are never wiki-run commits, so their
  wiki edits get reviewed like any other change.

## Evidence

- `core/scripts/wiki_state.py` (`is_run_commit`, `find_anchor`,
  `acquire_lock`, `edits_since`).
- `core/protocol.md` §2 anchor field, §5, §5.1.

## Relevant Implementation

- `core/scripts/wiki_state.py`

## Related Pages

- [wiki_state.py](../components/wiki-state.md)
- [Package Layout](../architecture/package-layout.md)
