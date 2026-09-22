---
name: wiki-init
description: Investigate the current Git repository and build its project wiki (wiki/) for the first time. Creates overview, current, and index from the repository structure, docs, tests, and Git history, runs structural lint, and commits. Run only when the user explicitly invokes /wiki-init.
disable-model-invocation: true
triggers: [user]
---

# wiki-init

Build the project wiki for the current repository for the first time. The wiki is not a chat summary; it is long-term memory that compresses knowledge that is expensive to rediscover from the repository. The repository always outranks the wiki.

`<skill-dir>` is the directory containing this file; shared resources live in `<skill-dir>/core/`. If the harness does not tell you this path, check for `SKILL.md` in `~/.agents/skills/wiki-init`, `~/.claude/skills/wiki-init`, `~/.config/devin/skills/wiki-init`, `~/.pi/agent/skills/wiki-init`, in that order. Never search the whole filesystem.

## 0. Prepare

1. Run `python3 <skill-dir>/core/scripts/wiki_state.py self-update`. Interpret the result per `core/protocol.md` §1.
2. Read `<skill-dir>/core/protocol.md`. Every step below follows it.

## 1. Preflight

1. Run `python3 <skill-dir>/core/scripts/wiki_state.py preflight .`.
2. If there are `blockers`, stop. If the directory is not a Git repository or has no commits, stop and propose the procedure in `core/protocol.md` §5 "When the directory is not a Git repository" to the user.
3. Note `staged`, `dirty_source`, `dirty_instruction_files`, and `untracked_entries`. Never commit these files. When adding the managed block to a file in `dirty_instruction_files`, follow `core/protocol.md` §5.

## 2. Check for an existing wiki

If `wiki/` contains any of `SCHEMA.md`, `index.md`, `overview.md`, or a current file, the wiki is already initialized.

- Do not rebuild it. Do not overwrite existing content.
- Create only missing mandatory files, run lint, report "already initialized" with the lint result, and stop.
- Do not automatically migrate other documentation systems (such as `docs/`).

## 3. Read project instructions

1. Read `AGENTS.md`, `CLAUDE.md`, `AGENTS.override.md`, and the README.
2. Collect:
   - Protected paths: paths the instructions say not to read or modify (for example, independent Git clones). Put them in SCHEMA's Protected Paths.
   - Policies that conflict with the wiki, such as "do not create handoff documents" or "record status only in commit messages".
   - The documentation language rule. Use it as the wiki language; without a rule, use the main language of the existing docs.
   - State descriptions mixed into instruction files (current model, current blockers, ...). Record them as migration candidates.

## 4. Decide the host layout

Decide whether this repository is checked out on several machines whose hardware or runtime state differ. Look for evidence only inside the repository: per-machine docs such as `hosts/`, or instructions and READMEs describing several nodes or per-machine settings.

- Without such evidence, do not ask; use the single-host layout (`wiki/current.md`). Say "single host" in the step-6 confirmation summary so the user can correct it.
- With evidence, confirm with the user. If confirmed, get from the user the host names (for example, `mbp`, `studio`) and each host's `hostname -s` value. This machine's value is preflight's `host.hostname`. Never find it out by accessing other machines.
- In the multi-host layout, shared pages hold host-independent knowledge and `current/<host>.md` holds each host's state. Machine-dependent facts must name their host (SCHEMA §6).
- If the user says the repository is not used on several machines, use the single-host layout.

## 5. Investigate the repository

Follow `core/protocol.md` §3; investigate only the current repository. Do not read everything; read as much as needed in this order:

1. Topology from `git ls-files`: subsystems, entry points, test locations, evidence and report locations
2. README, instruction files, `docs/`
3. Build, package, and config files
4. Core interfaces and data flow
5. Implementation state: distinguish implemented, partial, stub, TODO, disabled, experimental
6. Tests and evidence
7. Git history only when needed: `git log --oneline -n 100`, `git log -- <file>`

Check claims in existing docs against the implementation and classify them as `Confirmed by implementation`, `Documentation-only claim`, `Outdated`, or `Unknown`. Use docs written by earlier agents and untracked skills (for example, `.claude/skills/`) as leads, but never copy unverified content as fact.

## 6. Confirm with the user

Before creating files, briefly report the following and get confirmation:

- Structure: single or multi-host, the categories and pages to create
- Conflicting policies and the proposed wording changes
- Source inventory: references to files that do not exist, duplicated descriptions, candidates to move into the wiki
- Instruction files that will get the managed block (`core/protocol.md` §6 placement rules)
- If run from a subfolder: the wiki is built per repository only, so the target is the whole repository root; subsystems in subfolders become component pages.

Modify or delete existing docs or skills only for items the user approved.

## 7. Create the wiki

1. `wiki/SCHEMA.md`: copy `<skill-dir>/core/SCHEMA.template.md` and fill the placeholders.
   - `{{SCHEMA_VERSION}}`: preflight's `template_schema_version`
   - `{{WIKI_LANGUAGE}}`: for example, `ko (identifiers and paths stay in English)`
   - `{{HOSTS}}`: for multi-host, lines like `mbp: <hostname>`; for single host, an empty line
   - `{{PROTECTED_PATHS}}`: one path per line, or an empty line
2. `overview.md`, the current file, `index.md`: follow the templates in `core/page-schema.md`.
   - Record goals and non-goals only as set by the user or the docs; never infer them from the implementation. Without a source, write `Unknown`.
   - The current file contains only state verified in this investigation. Add the observation date and the command to runtime facts.
   - In the multi-host layout, create only this host's current file. Other hosts' files are created when `/wiki-update` runs on those hosts.
3. Create `architecture/`, `components/`, `decisions/`, `experiments/`, `runbooks/` pages only when needed. Never create one page per source file; organize by concept.
4. `log.md`: the init entry from `core/page-schema.md`. Copy preflight's `head` (the full 40-character SHA) verbatim into `Source HEAD`. In multi-host repositories, add a `Host:` line.
5. Add the managed block to the approved instruction files (`core/protocol.md` §6).

## 8. Verify

1. Run `python3 <skill-dir>/core/scripts/wiki_lint.py .` and resolve every ERROR.
2. Check yourself:
   - Does the current file match the actual implementation? Did you record a TODO or stub as a finished feature?
   - Did you transcribe tests and results accurately? Did you record anything that did not pass as PASS?
   - Are there duplicate pages? Did transient content slip into the overview?
   - Did you copy any secrets?

## 9. Commit and report

1. Make a pathspec commit following `core/protocol.md` §5. The message is `docs(wiki): initialize project memory`.
2. Do not push.
3. Report briefly in this format:

```text
Project Wiki initialized.

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

`Skill feedback` is mandatory (`core/protocol.md` §9).
