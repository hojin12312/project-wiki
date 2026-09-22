---
name: wiki-update
description: After a work unit, reconcile the project wiki (wiki/) with the actual repository state, incrementally updating only the pages that need it, then run semantic and structural lint plus structural maintenance and commit. Not a conversation summary. Run only when the user explicitly invokes /wiki-update.
disable-model-invocation: true
triggers: [user]
---

# wiki-update

Investigate how the repository changed since the last wiki update, and reflect only knowledge that became stale or newly important. The goal is not "summarize this conversation" but "reconcile the wiki with the actual repository state". The conversation is only a navigation hint; discard it when it conflicts with the repository or evidence.

`<skill-dir>` is the directory containing this file; shared resources live in `<skill-dir>/core/`. If the harness does not tell you this path, check for `SKILL.md` in `~/.agents/skills/wiki-update`, `~/.claude/skills/wiki-update`, `~/.config/devin/skills/wiki-update`, `~/.pi/agent/skills/wiki-update`, in that order. Never search the whole filesystem.

## 0. Prepare

1. Run `python3 <skill-dir>/core/scripts/wiki_state.py self-update`. Interpret the result per `core/protocol.md` §1.
2. Read `<skill-dir>/core/protocol.md`. Every step below follows it.

## 1. Preflight

1. Run `python3 <skill-dir>/core/scripts/wiki_state.py preflight .`.
2. If `wiki_exists` is false, point the user to `/wiki-init` and stop.
3. If there are `blockers`, stop. If the host cannot be determined, write to no current file and ask the user.
4. If the major.minor of `schema_version` and `template_schema_version` differ, only tell the user.
5. If there is `dirty_source`, follow `core/protocol.md` §5.

## 2. Read the current wiki

Read `wiki/SCHEMA.md`, `index.md`, `overview.md`, and this host's current file (preflight `host.current_path`). If recent history is needed, read only `tail -n 60 wiki/log.md`. Do not read other hosts' current files or the archive.

## 3. Investigate the changes

1. The change range is preflight's `anchor.anchor`..`head`, and the list is `changed_source` (excluding `wiki/`). Without an anchor, investigate the repository broadly again (same order as `/wiki-init` §5).
2. Look at individual diffs only as needed: `git diff <anchor>..HEAD -- <file>`.
3. Classify each change: semantic implementation change, refactor without behavior change, test, configuration, documentation-only, experiment or evidence added, generated artifact, formatting.
4. Map each changed path to wiki pages: `rg -n "<changed path>" wiki/`, the subsystem grouping in the index, component and architecture relations, and the features that tests verify.

## 4. Judge durable knowledge

Answer these questions. If none applies, keep substantive edits to a minimum.

- What is now actually possible? What in the wiki became wrong?
- Did the architecture, an invariant, or an interface change?
- Was an important decision made? (B instead of A, a fixed data format, a compatibility policy, a deliberate trade-off, a workaround adopted permanently, an old structure abandoned)
- Does an experiment result affect later design? Did it confirm or refute a hypothesis? (A plain smoke test is not an experiment.)
- Did a blocker appear or get resolved? Did a repeatable procedure appear?

If you are unsure whether to store something, use the question in `core/protocol.md` §4.

## 5. Edit pages

- Minimum necessary edit: fix what conflicts with the facts, add what became durable, remove or archive obsolete details, update cross-references. Do not touch unrelated sentences.
- Create a new page only when it meets SCHEMA §5's criteria. Follow the templates in `core/page-schema.md`.
- Edit `overview.md` only when scope, hard constraints, high-level architecture, canonical references, or major subsystems change.
- Update `index.md` when pages are added, renamed, or archived, or a summary changes meaningfully.
- When renaming a page, fix every link to it.
- In multi-host repositories, machine-dependent facts must name their host. Do not edit other hosts' facts in shared pages; this host cannot verify them.
- Investigate only the current repository. Never access other machines (`core/protocol.md` §3).

## 6. Recompute the current file

Recompute only this host's current file. Never append.

- Re-sort Working, Partially Implemented, Not Yet Implemented, Current Blockers, Active Risks / Unknowns, and Next Logical Work to match the actual state.
- Remove resolved blockers. Reflect finished work in Working or in the canonical page. Delete stale next steps.
- Update the date of runtime facts you re-checked; keep the old date on those you could not re-check.
- Never change another host's current file, not even by one byte.

## 7. Semantic lint and structural maintenance

Check the following and, when a condition holds, handle it in this step. Do only as much as needed in one run.

| Condition | Action |
|---|---|
| The wiki contradicts the code | Fix the wiki to match the code |
| Resolved blockers or stale implementation state remain | Remove them or move them to the canonical page |
| The same concept is described differently on several pages | Pick one canonical page and turn the rest into links |
| A superseded structure is described as current | Mark the decision `superseded` or move it to the archive |
| An unsupported definitive claim | Change it to `Not yet verified` or similar |
| A runtime fact with an old observation date | Re-check it or mark it `Not yet verified` |
| The current file exceeds its budget | Move details to canonical pages |
| Current sections are misclassified (risks, mismatches, or unverified items under Working; observations mixed with inferences) | Move items to the right section and mark inferences (`Inference:` or the wiki-language equivalent, e.g. `추정:`) |
| The index is too long | Introduce category indexes |
| A contradiction between pages cannot be resolved | Mark it `Unresolved contradiction` |

## 8. log.md

Append one entry at the end (SCHEMA §13 format). Copy preflight's `head` (the full 40-character SHA) verbatim into `Source HEAD`, and add `Host:` in multi-host repositories. Under Validation, list only checks you actually ran.

- If source changed but there is no knowledge to reflect, add only a "no substantive change" entry to move the anchor forward.
- If there is no source change since the anchor and semantic lint finds nothing, change no files, report "no change", and stop.

## 9. Verify, commit, report

1. Run `python3 <skill-dir>/core/scripts/wiki_lint.py .` and resolve every ERROR.
2. Run preflight again and confirm `head` is unchanged. If it moved, restart from step 3.
3. Make a pathspec commit following `core/protocol.md` §5. The message is `docs(wiki): update project memory after <topic>`. Do not push.
4. Report briefly in the `core/protocol.md` §9 format. Do not hide failed checks or unresolved items. `Skill feedback` is mandatory.
