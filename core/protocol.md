# Project Wiki Protocol

The rules shared by `wiki-init` and `wiki-update`. Each repository's `wiki/SCHEMA.md` is the source of truth for wiki *policy* (what to store and how); this file and the command's procedure file (`core/init.md` or `core/update.md`) define the *procedure* that carries out that policy. Each `SKILL.md` is only an entry point that leads here.

If the `SKILL.md` that brought you here lists numbered procedure steps of its own, it is an older copy loaded before the update: ignore those steps and follow `core/init.md` or `core/update.md`.

Below, `<skill-dir>` is the directory of the skill currently running (where its `SKILL.md` lives). Always reach shared resources as `<skill-dir>/core/...`; never build paths with `..`.

Write wiki content in the repository's wiki language (`wiki-language` in SCHEMA). These instructions are in English, but the pages you write follow the repository's language.

## 1. Self-update and reading order

```bash
python3 <skill-dir>/core/scripts/wiki_state.py self-update
```

- Run it first and by itself. Read this file and the procedure file only after it returns; a read issued in parallel can return the copy from before the update.
- `updated` or `current`: the files you read afterwards are the current version. `skipped` (uncommitted changes, diverged from remote, network failure, timeout): tell the user in one line and continue with the version on disk. Never reset, stash, or force the package repository.
- The report's `Package:` line states the version and self-update status the tools returned. It is not proof of which instructions you followed; do not present it as one.

## 2. Preflight

```bash
python3 <skill-dir>/core/scripts/wiki_state.py preflight <repo-root>
```

Interpret the JSON as follows.

| Field | Meaning and action |
|---|---|
| `blockers` | If non-empty, stop and tell the user. |
| `host` | If `mode` is `multi`, read and edit only `current_path`. If `error` is set, stop and ask which host this is. |
| `budget` | Budgets and estimates you must read before editing: `current_tokens`, `bootstrap_tokens`, `current_estimate`, `bootstrap_estimate`, `applied_current_path`, `missing`, and the over-budget flags. The estimate is a heuristic, never a model tokenizer count. Size the current file to the budget before writing it. |
| `staged` | Files the user staged beforehand, split into `all`, `wiki`, `wiki_other_hosts`, `instruction_files`, and `other`. Do not touch or commit any of them. Report `other` (the user's staged source changes) without treating them as reviewed source. |
| `dirty_source` | Uncommitted source changes. Follow §5. |
| `dirty_wiki` | Wiki files already modified before this run. Do not auto-commit them; inspect, report, and ask (§5). |
| `instruction_files` | Instruction files with state `tracked-clean`, `tracked-dirty`, `untracked`, or `ignored`, plus whether they already carry a managed block. Follow §6. `dirty_instruction_files` lists the `tracked-dirty` ones. |
| `untracked_entries` | Ignore them unless relevant to the update. Do not read or modify them. `untracked_truncated` says the list was cut at 200. |
| `ignored_wiki_files` | Wiki files that Git ignores. Rename them or tell the user. Never edit `.gitignore`. |
| `anchor` | `anchor.anchor`..`head` is the source range since the last wiki update. Only a committed `wiki/log.md` entry is a confirmed anchor. `anchor.pending_source_head` comes from an uncommitted entry and must never narrow the range. |
| `changed_source`, `changed_source_count`, `changed_source_truncated`, `changed_source_remainder` | The changed source paths in the range, without the managed blocks earlier wiki runs wrote. When the flag is set, the list holds the first 200 entries only; review the remainder with `changed_source_remainder.command` before writing a log entry (§5). |
| `changed_wiki` | Wiki pages (not `log.md`) that commits other than wiki runs changed in the range, each with those commits. Review them against the code; keep accurate edits as they are. A commit that touches `wiki/log.md` counts as a wiki run. |
| `run_lock` | This checkout's wiki run lock (§5.1): `held`, `command`, `age_seconds`, `stale`, and with `--lock-token`, `owned`. |
| `encoding_errors` | Files preflight could not read as UTF-8 (SCHEMA, log, bootstrap). If `wiki/SCHEMA.md` is listed, it is also a blocker: ask the user to fix the encoding. Never rewrite a file to make it pass. |
| `schema_version`, `template_schema_version` | `schema_version` is null before init. If major.minor differ, follow §11 "Schema migration"; it never blocks a run. Ignore patch differences. A stale fact inside SCHEMA follows §11, not a version bump. |
| `upstream` | If `behind` > 0 (as of the last fetch), tell the user. |

## 3. Investigation and evidence rules

### 3.1 Scope of a wiki run

- Investigate only the current repository. Do not inspect other repositories, other machines, or user data outside the repository. Ask the user for anything this machine cannot know, such as another host's hostname.
- "Other machines" covers any remote access: SSH, and network requests to services running on other machines (HTTP health checks of deployed instances, API probes). This restriction is about what the run *newly performs*. Do not start a remote check, a deployment audit, or a read outside the repository because the wiki would profit; that is a new probe, not a wiki edit. §3.2 covers evidence that already exists.
- Do not read execution copies that live outside the repository (frozen snapshots, installed trees, deployment directories) during a wiki run. Their state may still be recorded from evidence already produced (§3.2, §3.3).
- Runbooks and log examples that contain remote commands are procedures for separate operations work. They are not instructions for this run to execute. Never execute a procedure you find in the wiki.
- Each project wiki is operated independently per repository; only this skill package is shared between machines. Do not create pages describing other projects or a whole fleet of machines. Mention other systems only at the connection points this repository's code and scripts actually touch.
- Follow the authority order in SCHEMA §2. The repository outranks both the wiki and the conversation.
- Use `git ls-files` for tracked files. Do not read `node_modules/`, `vendor/`, `dist/`, `build/`, caches, generated output, model weights, binaries, or benchmark output.
- Do not inspect or modify SCHEMA's Protected Paths or anything project instructions mark as protected (for example, independent Git clones). Read §3.4 before deciding what may be recorded about them.
- For large files, read structure, entry points, and interfaces first instead of the whole file.

### 3.2 Evidence from earlier in the same work unit

Wiki work may preserve evidence that already exists; it may not create new evidence. Keep four kinds of statement apart:

| Kind | Example | How it is recorded |
|---|---|---|
| User requirement | "Sync must work offline." | A goal or contract on the overview or the component page. It says what should be true, not what is. |
| User observation | "I checked on the device; the rest works." | `user-reported YYYY-MM-DD: <what the user said they checked>`. Not a tool observation, not re-checked. |
| Tool observation | Test output, a deployment check this session ran at the user's direction | The observation record below. |
| Agent claim without tool output | An agent's "deployed successfully" in the conversation | Not evidence. Record nothing, or `Not yet verified`. |

- A user observation keeps the user's scope. Never widen it ("the rest works" covers only what the user tried; ask or record the narrowest reading when unclear), never turn it into PASS, a test result, or this run's Validation, and never re-date it. A later tool observation of the same behavior replaces it.
- Allowed without new investigation: real tool output from work the user directed in this same work unit (a deployment check, an API call, a test run), and verification records the project instructions let this session read. Summarize them; do not re-run them to "confirm". Re-running is a new probe when it targets another machine, a deployment, or a protected path.
- Not allowed: anything obtained by a forbidden direct read (for example opening a protected credential store during unrelated work and relabeling the contents as a "summary"). A summary is not a way to launder a forbidden read.
- Record a tool observation, as far as it applies, with: observation date, observing host, target (host, service, path), the method with secrets removed, the result, and where the evidence came from (tool output in this session, a committed log or document, a test run). A claim with no method is a documentation-only claim, not an observation.
- Keep this run's checks apart from earlier operational verification. Never refresh the date of a result you did not re-check, and never restate an old observation as the current state. Mark it with its original date and "not re-checked this run".
- A run may update the wiki even when `changed_source` is empty, when it has new permitted evidence or a contradiction with the wiki. Re-processing the same evidence with no new conclusion is a no-op: change nothing, report "no change", and stop.

### 3.3 Source, deployment, and goals

- Keep three layers apart: the goal or contract (what the user and maintainers require), the committed source implementation (what `HEAD` contains), and the observed deployment state (what a machine is running now).
- A Source HEAD is a Git revision of this repository. It is never the revision or build identifier of an external deployment, and never proof that a deployment succeeded.
- When execution happens outside this repository (frozen snapshot, installed tree, container image), record the observation date, host, and the identifier the deployment itself exposes (version command, build id, image digest). Record drift between the repository copy and the deployed copy as an observation with its date, never as a source change.
- Committed state is the wiki's baseline. Record dirty working-tree state only after the user commits it (§5). Never write dirty state as if it were committed, and never cite HEAD as if it contained uncommitted changes.

### 3.4 Secrets and protected paths

- Never record secrets or personal data, no matter how they were obtained. Values are always forbidden; counts, field names, and shapes are not automatically safe either, because the schema of a credential store can itself be sensitive. If you find secrets in the repository, report only their location to the user.
- A fact learned by reading a Protected Path directly is not recorded at all, in any form. A "summary" does not make it allowed.
- A fact obtained through a permitted interface without reading protected files (API, CLI, service response) may be recorded as an observation with the date, host, and method. Keep only what the interface exposes, and go through the interface again rather than reading files.
- If the only safe way to change a protected or secret-bearing store is such an interface (API, migration command), record that as an invariant on the canonical component page, based on accessible code or instructions, so later sessions do not fall back to editing files directly.
- A repository's SCHEMA may be stricter than this file. The stricter local policy wins; a skill update never loosens it.

### 3.5 One wiki per repository

The wiki and its anchor cover the whole repository. Tell two cases apart:

- Tightly coupled components (shared build, deployment, interfaces, or data): component pages of one wiki. This is the normal case.
- Independent projects that only share the repository (separate lifecycles, no code or interface between them, often worked on by separate sessions): every `/wiki-update` still reviews all of them, and their sessions edit the same wiki.

For independent projects, tell the user once (at init, or when you first notice it) that separate repositories are the clean fix; do not invent a sub-wiki or per-path anchor layout. Until the user splits the repository:

- Review an unrelated project's changes briefly (classify, map to its page, check whether a wiki claim became false), but never skip them. A log entry advances the anchor for the whole repository, so write a normal entry only after the whole range was reviewed.
- Keep each project's state in its own section of the current file or on its own component pages, so runs for different projects edit different text.

## 4. What is worth storing

When unsure whether to store something, ask:

> Would a new agent next month waste time or compute, or make a wrong design decision, without this information?

If yes, store it. If no, leave it to Git history and the source. High-value information includes architecture rationale, invariants, hard constraints, behavior not obvious from the code, interfaces between subsystems, why A was chosen over B, rejected approaches and why, verified experiment conclusions, known blockers, repeatable procedures, and current implementation maturity.

## 5. Git safety

- Never use: `git add -A`, `git commit -a`, `git reset --hard`, `git checkout -- .`, `git clean`, `git stash`, force push, destructive rebase.
- Commit only the files this run edited. Keep that list explicit; never commit `wiki/` as a whole.
- When there are uncommitted source changes (`dirty_source`):
  - If you changed those files yourself in this work unit and the scope is clear, ask the user whether to commit them first.
  - Otherwise reflect only the committed state in the wiki, and do not record uncommitted changes as facts. Never cite HEAD as if it contained them.
- Never include in the commit: a file in `staged` (report `staged.other` as the user's staged source work that was left untouched), `wiki/current/<other-host>.md`, a `wiki/current.md` that is not this host's file, an `untracked` or `ignored` instruction file, or any file that was already dirty before the run (`dirty_wiki`, `dirty_source`, an instruction file in state `tracked-dirty`). A pathspec commit records the whole file, so it would also record work you did not author. Show the diff and ask instead.
- Commit sequence. Write every path as its own literal argument in each command, and quote a path that contains spaces. Never collect the paths in one shell variable or string: zsh does not split an unquoted variable, so the list becomes a single pathspec, and a check that received the wrong argument can look as if it passed. Include deleted pages and both the old and new path of a renamed page. For example, for a run that edited `wiki/current.md` and `wiki/log.md`:

  ```bash
  git status --porcelain -- wiki/current.md wiki/log.md      # only this run's edits, no surprise content
  git check-ignore -v -- wiki/current.md wiki/log.md         # must print nothing (exit code 1 is the expected result)
  git add -- wiki/current.md wiki/log.md
  git commit -m "docs(wiki): <message>" -- wiki/current.md wiki/log.md
  git show --name-only --format= HEAD                        # must list exactly these paths
  git diff --cached --name-only                              # must still equal preflight's staged.all
  ```

  A pathspec commit records only the given paths, so files the user staged beforehand stay staged; the last command confirms it. State in the report that they were left untouched. If either check differs, stop and tell the user; do not amend or reset.
- If a file you must edit was already dirty before this run, do not auto-commit it. Summarize `git diff -- <file>` for the user and ask whether to commit that work separately first. If the user agrees, make the source commit first and the wiki commit afterwards. This also covers instruction files in state `tracked-dirty`: leave the managed block uncommitted and say so in the report.
- `anchor.pending_source_head` (from a dirty `wiki/log.md`) is not a confirmed anchor. Never use it to narrow the change range or skip review; reconcile the uncommitted log entry instead of appending a duplicate.
- If `changed_source_truncated` is true, review the remainder first; the command is in `changed_source_remainder`. Do not append a normal log entry, which advances the anchor, while part of the range is unreviewed. Record what you reviewed and what remains, and tell the user.
- Immediately before committing, run `preflight . --lock-token <token>`, confirm it has no blocker and `head` has not moved, and confirm the target paths and the index state. If HEAD moved (for example, another agent committed), restart from the change review.
- Push only when the user asks.

### 5.1 One run per checkout

Two wiki runs in the same checkout would edit the same pages and append duplicate log entries. A small cooperative lock prevents that. It lives in the Git directory (per worktree) and never appears in the working tree. It does not coordinate other clones, other machines, or agents that are not running a wiki command.

- Take it before preflight: `python3 <skill-dir>/core/scripts/wiki_state.py lock . --run <command>`, and keep the returned `token`. If `status` is `held`, stop and tell the user which command holds it and for how long. Do not wait or retry in a loop.
- Release it before every stop: after the commit, a no-op, a blocker, or an error, and before you wait for an answer from the user: `python3 <skill-dir>/core/scripts/wiki_state.py unlock . --token <token>`. After the user answers, take it again and re-run preflight before editing further.
- A lock left by an interrupted run is `stale` after one hour, and the next `lock` replaces it (`replaced-stale`). The interrupted run then fails its pre-commit `--lock-token` check and must stop without committing. If the user confirms the holder is gone sooner, remove it with `unlock . --force`; never force it on your own.

### When the directory is not a Git repository

Preflight blocks a directory that is not a Git repository or has no commits. Stop and propose the following steps to the user; proceed only after the user approves.

1. Write `.gitignore` first and show it to the user. Exclude secrets (`.env`, key and credential files), runtime state (databases, logs, caches), model weights, and large artifacts.
2. Summarize the files and sizes that the baseline would include, and scan them for secret patterns (`api_key`, `token`, `password`, `secret`, private keys). Exclude what you find, or ask the user how to handle it.
3. Run `git init` and make a baseline commit (for example, `chore: initial baseline`), separate from the wiki commit.
4. Run preflight again and continue the `/wiki-init` procedure.
5. For items that need action outside the repository, such as secrets left on disk, report them only; do not fix them yourself.

## 6. Instruction files and the managed block

Harnesses read project instruction files differently.

- Claude Code reads only `CLAUDE.md`.
- Codex reads `AGENTS.md`. It reads `CLAUDE.md` only if configured in `project_doc_fallback_filenames`, and only in directories without `AGENTS.md`.
- Pi reads, per directory, only the first file found in the order `AGENTS.override.md` → `AGENTS.md` → `CLAUDE.md`.
- Devin reads both `AGENTS.md` and `CLAUDE.md`.

Placement rules:

1. If both files exist, put the same block in both. The only exception is when `CLAUDE.md` actually imports `AGENTS.md` with an import syntax such as `@AGENTS.md`; then put it only in `AGENTS.md`. A sentence that refers to the other file is not an import.
2. If only `CLAUDE.md` exists, put the block only there. Do not create `AGENTS.md`: once it exists, Pi stops reading `CLAUDE.md`. If the user uses Codex, point them to the `project_doc_fallback_filenames` setting.
3. If only `AGENTS.md` exists, put the block there, and if the user uses Claude Code, ask whether to create `CLAUDE.md`.
4. If neither exists, ask the user which file to create.
5. Never overwrite a whole file. Manage only the text between `<!-- project-wiki:start -->` and `<!-- project-wiki:end -->`; if the block exists, update only that span. If an existing block already says the same thing in another language, leave it as is.
6. If the target file is in state `tracked-dirty` (also listed in preflight's `dirty_instruction_files`), say in the confirmation summary (`core/init.md` §6) that the block in that file will not be committed because of uncommitted changes (§5).
7. If an instruction file has a policy that conflicts with the wiki (for example, "do not create handoff documents" or "record status only in commit messages"), confirm with the user, then change only that wording so the wiki is an exception.

Instruction file states (preflight `instruction_files`):

| State | Managed block | Commit |
|---|---|---|
| `tracked-clean` | Add or update the block | Include the file in the commit |
| `tracked-dirty` | Add or update the block, but keep the file out of the commit | Never auto-commit |
| `untracked` | Keep an existing block; ask before adding one | Never |
| `ignored` | Keep an existing block; never edit `.gitignore` and never force-add; ask before adding one | Never |

- A local-only (`untracked` or `ignored`) instruction file reaches only this checkout. Say so in the report: the wiki pointer stays on this machine and other checkouts will not see it, so a future session there will not know the wiki exists.
- Never create an instruction file just to hold the block, and never create one that changes which file a harness reads first (rules 2 and 4). If no instruction file exists, ask the user which one to create.
- The managed block is the only text wiki work writes into an instruction file. Do not restructure or migrate the rest of the file.

Block content (canonical English text; write it in the wiki language):

```markdown
<!-- project-wiki:start -->
## Project Wiki

This repository uses `wiki/` as the project's long-term memory.

Before substantial work:
1. Read `wiki/index.md` and `wiki/overview.md`.
2. Read `wiki/current.md`.
3. Read only the pages linked from the index that are relevant to the task.
4. Verify important claims against the actual code. The repository outranks the wiki.

The current file is not a handoff note; it is a state snapshot that `/wiki-update` recomputes against the repository. Progress history stays in commit messages.
When a meaningful work unit is finished, suggest running `/wiki-update` to the user.
<!-- project-wiki:end -->
```

In multi-host repositories replace item 2 with: "Determine this host with `hostname -s` and the Hosts table in `wiki/SCHEMA.md`, and read only `wiki/current/<host>.md`." If the repository has its own convention for progress records (for example, a `CONTINUE.md` log), adapt the sentence "Progress history stays in commit messages." to that convention. Do not change the other sentences.

## 7. Lint

```bash
python3 <skill-dir>/core/scripts/wiki_lint.py <repo-root>
```

- Any `ERROR` makes the exit code 1. Resolve all of them before committing.
- Use judgment on `WARN`. Include warnings you leave unfixed in the report.
- The script makes no semantic judgments. Contradictions with the code, stale state, and duplication are for you to judge.
- Encoding defects are reported, never repaired: invalid UTF-8 and NUL are `ERROR`, U+FFFD and other disallowed control characters are `WARN` with line/column positions. Fix the file by hand against its source; do not normalize the damage away.
- A `WARN` about an inline-code path that is missing, ignored, or untracked can be resolved with `<!-- wiki:not-preserved -->` right after that code span only when the path is a reproduction output (it exists only after re-running something) and the page body carries the key numbers, conditions, revision, and a statement that the artifact was not preserved. Uncommitted source and local Git clones are not reproduction outputs: leave their warning until the source is committed, or describe them without citing them as evidence. The marker covers one notation, never a page or section, and never silences a Markdown link, a protected path, or a broken link.

## 8. Failure and uncertainty

- Never pretend success when there are failing tests, inconclusive benchmarks, unresolved contradictions, unreadable files, or an unsafe Git state.
- Write the real state in the wiki (for example, `Partially implemented. Validation currently fails at ...`). Never record as PASS anything that did not pass.
- Never present a partially reviewed change range as fully reviewed, and never imply checks that did not run.
- If the repository has its own commit policy, that policy takes precedence.

## 9. Reporting to the user

Keep it short. Do not retell the whole session.

```text
Project Wiki updated.

Package: <package_version> (self-update: <status>)
Source changes reviewed: <anchor>..<head> (<n> paths; if truncated, say "reviewed m of n, remainder unreviewed")
Wiki:
- updated components/<page>.md
- updated current.md
Current: ~<estimate>/<budget> tokens (estimate, not a model tokenizer count)
Validation:
- structural lint: PASS
- stale claims corrected: <n>
- unresolved items: <n>
Git:
- staged before the run, left untouched: <n>
- commit: docs(wiki): <message>
- push: not run

Skill feedback:
- <instructions that were ambiguous so you had to guess>
- <steps you could not follow or skipped, and why>
- <where you had to hunt for information>
```

Every `/wiki-init` and `/wiki-update` report must include `Skill feedback`. It records clues for improving the skill itself from this run.

- Write 2–5 lines of facts, not evaluations ("it worked well"). Examples: "Did not receive the `<skill-dir>` path, so checked the install locations in order", "SCHEMA §5's new-page criteria were ambiguous, so merged the component pages".
- If there is nothing to report, write `- none`.
- Do not fix the skill yourself. If the user asks for an improvement, follow §12. To review a run, use `core/review-checklist.md`.

## 11. SCHEMA: policy versus mutable facts

SCHEMA holds policy and configuration: authority order, page taxonomy, page format, evidence rules, context loading, budgets, hosts, protected paths, lint, and Git rules.

Mutable project facts do not belong there: test counts, "there are no automated tests yet", implementation status, dependency or model versions, and any value a normal work unit changes. Those belong in the current file or the canonical component page, with their observation date.

When a run finds an existing SCHEMA statement the code has made false:

1. Do not edit SCHEMA. Propose the minimal fix or move to the user, naming the exact sentence.
2. Record the contradiction and the confirmed fact once in this host's current file under Active Risks / Unknowns. A line in `log.md`'s Open is not a substitute; the next bootstrap must see it.
3. Continue the rest of the update. A pending SCHEMA approval never blocks unrelated safe wiki edits.
4. After the user approves, change only the approved facts. Do not change authority, hosts, protected paths, budgets, wiki-language, or other policy in the same edit; propose those separately.

A skill update never edits an existing SCHEMA by itself. A policy version difference is handled below, with the user's approval.

### Schema migration

When `schema_version` and `template_schema_version` differ in major.minor, lint warns. Most rules live in this file and in lint, so they already apply; a migration only brings the repository's own contract text up to date. It is optional and never blocks a run.

1. Finish the normal update first. Propose a migration only in a run that writes a log entry; a no-op run mentions the difference in one report line.
2. If the tail of `wiki/log.md` has an Open line saying the user deferred the migration to this template version, mention it in one report line and stop there.
3. Otherwise read `<skill-dir>/core/schema-migrations.md` for the versions after the local one. Compare each item's intent with the local SCHEMA, which may be in another language or phrased differently, and propose only the missing items as a minimal patch written in the SCHEMA's own language. Never propose replacing the file with the template.
4. Preserve local policy exactly: `wiki-language`, the budgets, hosts, and protected blocks, the existing text of header comments (a migration item may add a sentence to them), local categories, and every local rule that is stricter or additional. Changing any of them is a separate proposal.
5. After approval, apply only the approved items and set `schema-version` to the newest version whose items are now all present. Run lint, and confirm with preflight that `protected_paths`, the budget numbers, and `host` are unchanged. Note it in this run's log entry (`SCHEMA migrated <from> → <to>`), or in a `maintenance` entry that repeats the current anchor as Source HEAD, since no source was reviewed.
6. If the user defers or declines, add `SCHEMA migration to <version> deferred by the user (YYYY-MM-DD)` under Open in this run's log entry, and carry that line into the Open of each later entry until the migration is applied or the template version changes, so later runs find it and do not ask again.

## 12. Improving the skill itself

When the user asks for an improvement to the wiki skills during use, apply it to the skill package repository and share it. Such a request authorizes commits and pushes to the package repository.

1. Find the package: `package_dir` in the output of `python3 <skill-dir>/core/scripts/wiki_state.py self-update`. Edit the real repository the symlinks point to.
2. Before editing, update with `git -C <package_dir> pull --ff-only`.
3. Change only what was requested. Keep each `SKILL.md` an entry point: procedure goes into `core/`, never into `SKILL.md`.
4. Run the tests: `python3 -m unittest discover -s <package_dir>/tests`.
5. Bump the version. There are two versions:
   - `VERSION` (skill package): patch for changes without functional change (wording, typos, bug fixes), minor for new behavior, major for incompatible changes.
   - `core/SCHEMA_VERSION` (SCHEMA policy): bump only when `core/SCHEMA.template.md` changes, and add the change by section and intent to `core/schema-migrations.md`. Each repository's SCHEMA `schema-version` is compared with it by major.minor only, so skill-only releases and patch corrections cause no warnings in existing wikis.
   - Never change the SCHEMA of repositories that already have a wiki.
   - Add a section for the new version at the top of `CHANGELOG.md` with 2–6 user-facing lines. The CHANGELOG is written in Korean.
6. Commit only the files you changed, then push: `git -C <package_dir> commit -m "<type>: <summary>" -- <files>` → `git -C <package_dir> push`.
7. If the push is rejected, replay only your commits with `git -C <package_dir> pull --rebase`, then push. If there is a conflict, stop and tell the user.
   If the error says you lack push permission (the original repository was cloned instead of forked), stop after the commit and tell the user to fork and point `origin` at their fork (see the installation section of the README).
8. After pushing, create the version tag and release.

   ```bash
   git -C <package_dir> tag -a v<VERSION> -m "v<VERSION>"
   git -C <package_dir> push origin v<VERSION>
   gh release create v<VERSION> --repo <origin owner/repo> --title "v<VERSION>" --notes "<the CHANGELOG section>"
   ```

   If `gh` is missing or unauthenticated, stop after the tag and tell the user.
9. Other machines pick up the new version on their next `/wiki-init` or `/wiki-update`. Self-update follows the latest commit on `main`, not releases.

### Improvement candidates not fixed now

If you decide not to fix an improvement candidate from `Skill feedback` or a run review right away, ask the user and record it as an Issue in the package repository.

- Use a template from `.github/ISSUE_TEMPLATE/` ("Skill feedback / 개선 제안" or "버그"): `gh issue create --repo <origin owner/repo> --template <file> ...`
- The repository may be public, so generalize machine names, hostnames, internal project names, user paths, domains, and IPs (for example, "an operations repository with several subsystems", "a Linux machine"). Never include secrets in any form.
- Close the Issue from the commit or PR that applies the fix (`Fixes #<number>`).
- External contributions come in as PRs from forks. During the experimental phase, the owner's own improvements are pushed directly to `main`.
