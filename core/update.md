# wiki-update procedure

Read this after `core/protocol.md`; every step follows it. `<skill-dir>` is the directory of the running skill.

Investigate how the repository changed since the last wiki update, and reflect only knowledge that became stale or newly important. The goal is not "summarize this conversation" but "reconcile the wiki with the actual repository state". The conversation is only a navigation hint; discard it when it conflicts with the repository or evidence.

## 1. Lock and preflight

1. Take the run lock: `python3 <skill-dir>/core/scripts/wiki_state.py lock . --run wiki-update`. If `status` is `held`, stop and tell the user. Keep the `token`; release it before every stop (protocol §5.1).
2. Run `python3 <skill-dir>/core/scripts/wiki_state.py preflight .`.
3. If `wiki_exists` is false, point the user to `/wiki-init` and stop.
4. If there are `blockers`, stop. If the host cannot be determined, write to no current file and ask the user.
5. Note `budget` (read it before step 6), `instruction_files`, `staged`, `dirty_source`, and `dirty_wiki`. Never commit files the user staged or files that were already dirty (protocol §5).
6. If the major.minor of `schema_version` and `template_schema_version` differ, handle it after the update as protocol §11 "Schema migration" says. It never blocks this run.
7. Stop early as a no-op when all of these hold: `changed_source` and `changed_wiki` are empty lists (not null, which means there is no anchor), `dirty_wiki`, `staged.wiki`, and `anchor.pending_source_head` are empty, and this work unit produced no new permitted evidence (protocol §3.2). The previous run already checked the wiki against this same code: change no files, release the lock, report "no change", and stop. A range that holds only earlier wiki runs' commits is empty in both lists. Otherwise continue with step 2; uncommitted wiki edits left by another or an interrupted run are inspected, reported, and asked about (protocol §5).

## 2. Read the current wiki

Read `wiki/SCHEMA.md`, `index.md`, `overview.md`, and this host's current file (preflight `host.current_path`). If recent history is needed, read only `tail -n 60 wiki/log.md`. Do not read other hosts' current files or the archive.

## 3. Investigate the changes

1. The change range is preflight's `anchor.anchor`..`head`. `changed_source` lists the changed source paths; `changed_wiki` lists wiki pages that commits other than wiki runs changed in the range (for example, a page edited together with a feature), with those commits. Earlier wiki runs' own edits appear in neither list. An `anchor.pending_source_head` from an uncommitted log is not a confirmed anchor (protocol §5). Without an anchor, investigate the repository broadly again (same order as `core/init.md` §5).
2. If `changed_source_truncated` is true, review the remainder with `changed_source_remainder.command` first. Never write a log entry that advances the anchor while part of the range is unreviewed.
3. For each `changed_wiki` entry, read `git show <commit> -- <path>` and check that edit against the code. An accurate edit stays exactly as it is; do not rewrite, reformat, or re-date it. Fix only what is wrong, and add only what is missing.
4. Look at individual source diffs only as needed: `git diff <anchor>..HEAD -- <file>`.
5. Classify each change: semantic implementation change, refactor without behavior change, test, configuration, documentation-only, experiment or evidence added, generated artifact, formatting.
6. Map each changed path to wiki pages: `rg -n "<changed path>" wiki/`, the subsystem grouping in the index, component and architecture relations, and the features that tests verify.
7. Changes to parts of the repository unrelated to this work unit still need review before the anchor advances; a short check is enough (protocol §3.5).

## 4. Judge durable knowledge

Answer these questions. If none applies, keep substantive edits to a minimum.

- What is now actually possible? What in the wiki became wrong?
- Did the architecture, an invariant, or an interface change?
- Was an important decision made? (B instead of A, a fixed data format, a compatibility policy, a deliberate trade-off, a workaround adopted permanently, an old structure abandoned)
- Does an experiment result affect later design? Did it confirm or refute a hypothesis? (A plain smoke test is not an experiment.)
- Did a blocker appear or get resolved? Did a repeatable procedure appear?

If you are unsure whether to store something, use the question in protocol §4. Results from earlier in this work unit, including what the user says they checked themselves, are recorded as protocol §3.2 says, without a new probe.

## 5. Edit pages

- Minimum necessary edit: fix what conflicts with the facts, add what became durable, remove or archive obsolete details, update cross-references. Do not touch unrelated sentences.
- Create a new page only when it meets SCHEMA §5's criteria. Follow the templates in `core/page-schema.md`.
- Edit `overview.md` only when scope, hard constraints, high-level architecture, canonical references, or major subsystems change.
- Update `index.md` when pages are added, renamed, or archived, or a summary changes meaningfully. When renaming a page, fix every link to it.
- In multi-host repositories, machine-dependent facts must name their host. Do not edit other hosts' facts in shared pages; this host cannot verify them.
- Never edit `wiki/SCHEMA.md` to fix an ordinary fact (protocol §11).

## 6. Recompute the current file

Recompute only this host's current file. Never append.

- Check preflight's `budget.current_tokens` and `budget.current_estimate` first, and size the result to the budget. The estimate is a heuristic, not a model tokenizer count.
- Re-sort Working, Partially Implemented, Not Yet Implemented, Current Blockers, Active Risks / Unknowns, and Next Logical Work to match the actual state. Next Logical Work is what a new session with no past conversation will start from: name concrete next steps.
- Remove resolved blockers. Reflect finished work in Working or in the canonical page. Delete stale next steps.
- Update the date of runtime facts you re-checked; keep the old date on those you could not re-check.
- Never change another host's current file, not even by one byte.

## 7. Semantic lint and structural maintenance

Check the following and, when a condition holds, handle it in this step. Do only as much as needed in one run.

| Condition | Action |
|---|---|
| The wiki contradicts the code (outside SCHEMA) | Fix the wiki to match the code |
| Resolved blockers or stale implementation state remain | Remove them or move them to the canonical page |
| The same concept is described differently on several pages | Pick one canonical page and turn the rest into links |
| A superseded structure is described as current | Mark the decision `superseded` or move it to the archive |
| An unsupported definitive claim | Change it to `Not yet verified` or similar |
| A runtime fact with an old observation date | Re-check it or mark it `Not yet verified`; never refresh the date without re-checking |
| A fact in `wiki/SCHEMA.md` is false | Keep SCHEMA, propose the minimal fix, and record the contradiction and confirmed fact once under `current`'s Active Risks / Unknowns (protocol §11) |
| A reproduction output path (exists only after re-running something) | Keep the key numbers, conditions, and revision in the body, and mark that path notation with `<!-- wiki:not-preserved -->` right after the code span. Uncommitted source and local clones are not reproduction outputs; never mark them |
| The current file exceeds its budget | Move details to canonical pages |
| Current sections are misclassified (risks, mismatches, or unverified items under Working; observations mixed with inferences) | Move items to the right section and mark inferences (`Inference:` or the wiki-language equivalent, e.g. `추정:`) |
| The index is too long | Introduce category indexes |
| A contradiction between pages cannot be resolved | Mark it `Unresolved contradiction` |

## 8. log.md

Append one entry at the end (SCHEMA §13 format). Copy preflight's `head` (the full 40-character SHA) verbatim into `Source HEAD`, and add `Host:` in multi-host repositories. Under Validation, list only checks this run actually ran. User reports and earlier tool results are not listed there at all, not even with a note; they live, with their own dates, on the pages that record them.

- The anchor moves only when the whole change range was reviewed. If part of it is unreviewed, keep the previous Source HEAD, list the remainder in Open, and tell the user.
- If the range had changes (`changed_source` or `changed_wiki`) but nothing needed editing, append only a short "no substantive change" entry, so the next run does not review the same range again. A page already made accurate by a reviewed commit can be noted as `already in <commit>`.
- Re-processing the same evidence with no new conclusion is also a no-op: change nothing and report "no change" (step 1.7).

## 9. Verify, commit, report

1. Run `python3 <skill-dir>/core/scripts/wiki_lint.py .` and resolve every ERROR, then add its actual result to the log entry's Validation. Encoding defects are reported, never auto-repaired: fix them by hand against the source.
2. Run `python3 <skill-dir>/core/scripts/wiki_state.py preflight . --lock-token <token>`. If it has a blocker, stop without committing. If `head` moved, restart from step 3. Confirm the target paths and index state are as expected.
3. Commit exactly the files this run edited, following protocol §5. The message is `docs(wiki): update project memory after <topic>`. Do not push.
4. Release the lock: `python3 <skill-dir>/core/scripts/wiki_state.py unlock . --token <token>`.
5. Report briefly in the protocol §9 format, including the current budget line, staged files left untouched, and any unreviewed remainder. Do not hide failed checks or unresolved items. `Skill feedback` is mandatory.
