---
title: English Is the Default Wiki Language
type: decision
status: accepted
updated: 2026-09-26
---

# English Is the Default Wiki Language

## Context

The earlier policy derived a new wiki's language from the repository: an
explicit documentation-language rule won, otherwise the dominant language of
the existing docs did. That produced Korean wikis in Korean-documented
projects by default.

## Decision

New wikis default to `wiki-language: en`; another language is chosen only on
an explicit user or repository-instruction requirement. An existing wiki
keeps its language and switches only through a user-approved incremental
migration.

## Rationale

- The wiki's primary reader is a future agent session, not a person; English
  is the language the procedure files and templates are written and reviewed
  in.
- A repository's human-facing language (for example a Korean README or docs)
  is not evidence about what serves later agent sessions, so it no longer
  drives the default.
- Bulk-translating an existing wiki spends effort and loses meaning on pages
  agents rarely load. Converting the bootstrap set (index, overview,
  current) first and other canonical pages only when they are substantively
  rewritten delivers most of the benefit without translation-only churn or
  re-dating untouched pages.

## Alternatives Considered

- Keep the repo-language default: rejected; it conflates human-facing docs
  with agent-facing memory.
- Bulk-translate existing wikis on the policy change: rejected; pure
  translation churn, cost, and semantic loss in cold pages such as `archive/`
  and old `log.md` entries.

## Consequences

- `core/init.md` collects an explicit language requirement instead of
  inferring one from the docs, and the confirmation summary reports the
  chosen language.
- `core/protocol.md` §10 carries the full policy: migration order
  (bootstrap → substantively rewritten pages → cold records), semantic
  preservation, source-wording retention, and no new language infrastructure.
- SCHEMA 0.4.0 adds the language-policy paragraph and the §5 update rule;
  `core/schema-migrations.md` describes it as a minimal patch in the SCHEMA's
  own language.

## Evidence

- `core/protocol.md` §10, `core/init.md` §3/§6/§7,
  `core/SCHEMA.template.md`, `core/update.md` §5/§7, `tests/scenarios.md` S14.
- Manual fixture check (observed 2026-09-26, this host): a Korean fixture
  wiki migrated bootstrap-only to English with `wiki-language: en`; a Korean
  component page was converted on a substantive edit; `archive/` and the
  Korean decision page stayed; lint PASS; a repeated update reported no
  changes.

## Relevant Implementation

- `core/protocol.md`, `core/init.md`, `core/update.md`,
  `core/SCHEMA.template.md`, `core/schema-migrations.md`

## Related Pages

- [Package Layout](../architecture/package-layout.md)
