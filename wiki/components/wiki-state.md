---
title: wiki_state.py
type: component
status: current
updated: 2026-09-25
---

# wiki_state.py

## Responsibility

Deterministic state tooling for both wiki commands. Prints JSON on stdout so
the procedure documents stay declarative and the Git interrogation lives in
one tested place.

## Interface

Subcommands (each prints JSON): `self-update`, `preflight <repo>`, `budget
<repo>`, `host <repo>`, `anchor <repo>`, `lock <repo>`, `unlock <repo>`.
`preflight` accepts `--host` and `--lock-token`.

`preflight` reports the fields `core/protocol.md` §2 documents: `head`,
`anchor` (+ `pending_source_head`, `ignored_entries`), `changed_source` /
`changed_wiki` (run commits excluded), `budget` (incl. `current_sections`),
`staged`, `dirty_*` lists, `instruction_files`, `untracked_entries` +
`untracked_basis`, `protected_paths`, `encoding_errors`, `upstream`,
`blockers`, `run_lock`.

`budget` returns the `budget` object alone — for re-measuring a rewritten
current file without repeating the Git investigation.

## Current Implementation

- Standard library only; shells out to `git` for every repository fact.
- Path lists are parsed with `-z` (NUL) throughout — dirty/staged/changed
  lists, run-commit paths, untracked entries — so spaces, non-ASCII, and
  newline characters in names survive.
- Untracked aggregation:
  `git ls-files -z --others --exclude-standard --directory --no-empty-directory`,
  matching `git status --porcelain`'s `??` entries; empty and ignored-only
  directories are not counted.
- Lock: `.git/project-wiki.lock` created with `O_CREAT|O_EXCL`; records a
  snapshot of `wiki/` + instruction files and `dirty_baseline` (paths dirty
  when the lock was taken). `edits_since_lock` diff is exposed via
  `preflight --lock-token`.
- Anchor: last `Source HEAD` in a committed `wiki/log.md` entry whose commit
  carries the `Project-Wiki-Run:` trailer and touches only wiki/instruction
  paths; older entries still count.
- Token estimate heuristic: ASCII four chars/token, others one each; shared
  with `wiki_lint.py` so both report the same numbers.

## Important Invariants

- The lock is never replaced automatically, however old; `unlock --force
  --id <id>` removes exactly one lock after user confirmation.
- `preflight` is read-only; `lock`/`unlock` are the only state writers.
- A wiki-run commit is identified by the trailer plus a wiki/instruction-only
  path set — a hand-made commit that edits `log.md` never sets the anchor.

## Relevant Paths

- `core/scripts/wiki_state.py`

## Tests / Validation

- `tests/test_scripts.py` exercises it against local Git fixtures
  (62 tests pass; observed 2026-09-26,
  `python3 -m unittest discover -s tests`).

## Known Limitations

- The token estimate is a heuristic, not a tokenizer count; non-ASCII text
  estimates higher.
- The lock is cooperative: it cannot stop a writer that ignores it; the
  pre-commit `edits_since_lock` + diff check is the real guard.

## Related Pages

- [Package Layout](../architecture/package-layout.md)
- [Anchor and Lock Semantics](../decisions/0002-anchor-and-lock-semantics.md)
- [wiki_lint.py](wiki-lint.md)
