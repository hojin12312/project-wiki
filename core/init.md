# wiki-init procedure

Read this after `core/protocol.md`; every step follows it. `<skill-dir>` is the directory of the running skill.

Build the project wiki for the current repository for the first time. The wiki is not a chat summary; it is long-term memory that compresses knowledge that is expensive to rediscover from the repository. The repository always outranks the wiki.

## 1. Lock and preflight

1. Take the run lock: `python3 <skill-dir>/core/scripts/wiki_state.py lock . --run wiki-init`. If `status` is `held`, stop and tell the user. Keep the `token`, and release it at every stop and before waiting for step 6's answer (protocol §5.1).
2. Run `python3 <skill-dir>/core/scripts/wiki_state.py preflight .`.
3. If there are `blockers`, stop. If the directory is not a Git repository or has no commits, stop and propose the procedure in protocol §5 "When the directory is not a Git repository" to the user.
4. Note `staged`, `dirty_source`, `dirty_wiki`, and `instruction_files` (with each file's Git state). Never commit these files. When adding the managed block to an instruction file, follow protocol §5 and §6.

## 2. Check for an existing wiki

If `wiki/` contains any of `SCHEMA.md`, `index.md`, `overview.md`, or a current file, the wiki is already initialized.

- Do not rebuild it. Do not overwrite existing content.
- Create only missing mandatory files, run lint, report "already initialized" with the lint result, and stop.
- Do not automatically migrate other documentation systems (such as `docs/`).

## 3. Read project instructions

1. Read `AGENTS.md`, `CLAUDE.md`, `AGENTS.override.md`, and the README.
2. Collect:
   - Protected paths: only paths that must not be read or modified, such as paths the instructions forbid, independent Git clones, and secret or credential stores. Put them in SCHEMA's Protected Paths. Do not protect a directory just because it is large or noisy (logs, traces, data dumps); read it selectively instead, because it may hold evidence.
   - Policies that conflict with the wiki, such as "do not create handoff documents" or "record status only in commit messages".
   - The documentation language rule. Use it as the wiki language; without a rule, use the main language of the existing docs.
   - Whether an instruction file is tracked, dirty, untracked, or ignored. A local-only file's managed block reaches only this checkout (protocol §6).
   - State descriptions mixed into instruction files (current model, current blockers, ...). Record them as migration candidates; they belong in `current` or a component page, never in SCHEMA (protocol §11).

## 4. Decide the host layout

Decide whether this repository is checked out on several machines whose hardware or runtime state differ. Look for evidence only inside the repository: per-machine docs such as `hosts/`, or instructions and READMEs describing several nodes or per-machine settings.

- Copies deployed to other machines (rsync, packages, build artifacts) are not checkouts. The host layout depends on where the repository itself is checked out and worked on.
- Without such evidence, do not ask; use the single-host layout (`wiki/current.md`). Say "single host" in the step-6 confirmation summary so the user can correct it.
- With evidence, confirm with the user. If confirmed, get from the user the host names (for example, `mbp`, `studio`) and each host's `hostname -s` value. This machine's value is preflight's `host.hostname`. Never find it out by accessing other machines.
- In the multi-host layout, shared pages hold host-independent knowledge and `current/<host>.md` holds each host's state. Machine-dependent facts must name their host (SCHEMA §6).
- If the user says the repository is not used on several machines, use the single-host layout.

## 5. Investigate the repository

Follow protocol §3; investigate only the current repository. Do not read everything; read as much as needed in this order:

1. Topology from `git ls-files`: subsystems, entry points, test locations, evidence and report locations
2. README, instruction files, `docs/`
3. Build, package, and config files
4. Core interfaces and data flow
5. Implementation state: distinguish implemented, partial, stub, TODO, disabled, experimental
6. Tests and evidence: read them, and do not run anything yet. A quick documented test command that would settle current-state claims is proposed in step 6 and run only after approval (step 7).
7. Git history only when needed: `git log --oneline -n 100`, `git log -- <file>`

Check claims in existing docs against the implementation and classify them as `Confirmed by implementation`, `Documentation-only claim`, `Outdated`, or `Unknown`. Use docs written by earlier agents and untracked skills (for example, `.claude/skills/`) as leads, but never copy unverified content as fact. While mapping subsystems, tell tightly coupled components apart from independent projects that only share the repository (protocol §3.5).

## 6. Confirm with the user

Before creating files, briefly report the following and get confirmation. No file is edited yet, so release the lock before waiting; after the answer, take it again and re-run preflight. When the user approved in advance, report the summary and continue.

- Structure: single or multi-host, the categories and pages to create
- Independent projects sharing this repository, if any, and the protocol §3.5 recommendation
- Conflicting policies and the proposed wording changes
- Source inventory: references to files that do not exist, duplicated descriptions, candidates to move into the wiki
- Instruction files that will get the managed block, with their Git state (protocol §6 placement rules). Say when a local-only file's block will not reach other checkouts.
- Budget: `budget.current_tokens` and the planned current-file size (the estimate is a heuristic, not a model tokenizer count; non-ASCII text estimates higher, protocol §2). If the default looks too small for this repository, propose a value; never raise it without approval.
- Local checks: the one documented quick test command you propose to run once to settle current-state claims, or "none" (protocol §3.2)
- If run from a subfolder: the wiki is built per repository only, so the target is the whole repository root; subsystems in subfolders become component pages.

Modify or delete existing docs or skills only for items the user approved.

## 7. Create the wiki

1. `wiki/SCHEMA.md`: copy `<skill-dir>/core/SCHEMA.template.md` and fill the placeholders.
   - `{{SCHEMA_VERSION}}`: preflight's `template_schema_version`
   - `{{WIKI_LANGUAGE}}`: for example, `ko (identifiers and paths stay in English)`
   - `{{HOSTS}}`: for multi-host, lines like `mbp: <hostname>`; for single host, an empty line
   - `{{PROTECTED_PATHS}}`: one path per line, or an empty line
2. If step 6 approved a local check, run it now, once (protocol §3.2). Otherwise run no project tests.
3. `overview.md`, the current file, `index.md`: follow the templates in `core/page-schema.md`.
   - Record goals and non-goals only as set by the user or the docs; never infer them from the implementation. Without a source, write `Unknown`.
   - The current file contains only state verified in this investigation, sized to preflight's `budget.current_tokens`. Add the observation date, host, and method to runtime facts. Its Next Logical Work must let a new session with no past conversation pick the next task.
   - Put policy and configuration in `SCHEMA.md` only. Test counts, implementation status, and other values that change with each work unit belong in `current` or a component page (protocol §11).
   - In the multi-host layout, create only this host's current file. Other hosts' files are created when `/wiki-update` runs on those hosts.
4. Create `architecture/`, `components/`, `decisions/`, `experiments/`, `runbooks/` pages only when needed. Never create one page per source file; organize by concept.
5. `log.md`: the init entry from `core/page-schema.md`. Copy preflight's `head` (the full 40-character SHA) verbatim into `Source HEAD`. In multi-host repositories, add a `Host:` line.
6. Add the managed block to the approved instruction files (protocol §6).

## 8. Verify

1. Run `python3 <skill-dir>/core/scripts/wiki_lint.py .` and resolve every ERROR. Encoding defects (invalid UTF-8, U+FFFD, control characters) are reported, never auto-repaired; fix them by hand against the source.
2. Check yourself:
   - Does the current file match the actual implementation? Did you record a TODO or stub as a finished feature?
   - Did you transcribe tests and results accurately? Did you record anything that did not pass as PASS?
   - Are there duplicate pages? Did transient content slip into the overview?
   - Did you copy any secrets, credential-store shapes, or unverified claims?

## 9. Commit and report

1. Run `python3 <skill-dir>/core/scripts/wiki_state.py preflight . --lock-token <token>`. If it has a blocker, stop without committing.
2. Commit exactly the files this run created or edited, following protocol §5, with the trailer `Project-Wiki-Run: wiki-init`. The message is `docs(wiki): initialize project memory`. Do not push.
3. Release the lock: `python3 <skill-dir>/core/scripts/wiki_state.py unlock . --token <token>`.
4. Report briefly in this format. `Skill feedback` is mandatory (protocol §9).

```text
Project Wiki initialized.

Package: <package_version> (self-update: <status>)
Created:
- wiki/index.md, overview.md, current.md
- <n> architecture / <n> component / <n> decision pages
Validation:
- structural lint: PASS
- unresolved claims: <n>
Commit: docs(wiki): initialize project memory

Skill feedback:
- <ambiguous instructions, skipped steps, detours; "none" if nothing>
```
