---
title: wiki_lint.py
type: component
status: current
updated: 2026-09-25
---

# wiki_lint.py

## Responsibility

Structural lint of an installed `wiki/`. Reports `ERROR` (exit code 1,
blocking) and `WARN` (judgment call for the run). Makes no semantic
judgments — contradictions with the code are `/wiki-update`'s job.

## Interface

`python3 <skill-dir>/core/scripts/wiki_lint.py <repo-root>` — text report on
stdout, exit 1 on any ERROR.

## Current Implementation

Checks: mandatory files, frontmatter (title/type/status/updated with the
status vocabulary), page reachability from `index.md`, `log.md` entry
structure and `Source HEAD` format, Markdown links, encoding defects
(invalid UTF-8/NUL → ERROR; U+FFFD/control chars → WARN), ignored wiki
files, inline-code repository path references, budgets (shared
`estimate_tokens` with `wiki_state.py`), and schema-version drift
(major.minor only).

Inline path mentions are classified `missing` / `untracked` / `ignored` /
`clone`. Two per-notation markers exist:

- `<!-- wiki:not-preserved -->` — reproduction outputs only; never applies
  to clones (a marked clone still warns).
- `<!-- wiki:local-path -->` — a location/boundary mention that is not
  evidence; also exempts clone notations.

`wiki/log.md` inline path mentions are historical and skipped; its Markdown
links, encoding, and entry structure are still checked.

## Important Invariants

- Markers must sit directly after the code span and cover that one
  notation; they never exempt a page, a section, a Markdown link, or a
  protected path.
- Encoding defects are reported, never auto-repaired.

## Relevant Paths

- `core/scripts/wiki_lint.py`

## Tests / Validation

- Covered by `tests/test_scripts.py` fixtures (62 tests pass; observed
  2026-09-25).

## Known Limitations

- Path detection ignores tokens containing spaces or shell metacharacters
  (`PATH_BAD_CHARS`), so a spaced path mention is never warned about.
- It cannot see semantics: a perfectly formatted but false page passes.

## Related Pages

- [wiki_state.py](wiki-state.md)
