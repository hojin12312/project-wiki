# Wiki Log

## [2026-09-25] init | initial project memory

Source HEAD: 57110680e140ea92ce5606b87e892b8808dc8406
Wiki:
- created SCHEMA.md, index.md, overview.md, current.md
- created architecture/package-layout.md
- created components/wiki-state.md, components/wiki-lint.md
- created decisions/0001-skill-md-entry-point-only.md, decisions/0002-anchor-and-lock-semantics.md
- created AGENTS.md, CLAUDE.md (managed block)
Validation:
- python3 -m unittest discover -s tests: 62 tests OK (13.8s)
- structural lint: PASS
Open:
- none

## [2026-09-26] update | English-default language policy (package 0.9.0)

Source HEAD: 120ef49f0fea37abe60fdfcaed6759f98813643f
Wiki:
- updated current.md, overview.md, index.md
- created decisions/0003-english-default-wiki-language.md
- refreshed re-checked test-observation dates on the component pages
- SCHEMA migrated 0.3.2 → 0.4.0 (user-approved language-policy paragraph)
Validation:
- structural lint: PASS
Open:
- issues #19–#24 still open on GitHub; awaiting the user's call on closing or commenting
