# Project Wiki Protocol

The procedure shared by `wiki-init` and `wiki-update`. Each repository's `wiki/SCHEMA.md` is the source of truth for wiki *policy* (what to store and how); this file defines the *procedure* that carries out that policy.

Below, `<skill-dir>` is the directory of the skill currently running (where its `SKILL.md` lives). Always reach shared resources as `<skill-dir>/core/...`; never build paths with `..`.

Write wiki content in the repository's wiki language (`wiki-language` in SCHEMA). These instructions are in English, but the pages you write follow the repository's language.

## 1. Self-update the skill

Run this first, before anything else.

```bash
python3 <skill-dir>/core/scripts/wiki_state.py self-update
```

- If `status` is `updated` and `changed` lists `SKILL.md` or files under `core/`, what you already read has changed. Re-read those files and follow the new content.
- If `status` is `skipped` (uncommitted changes, diverged from remote, network failure, timeout), tell the user in one line and continue with the current version. Never reset, stash, or force the package repository.

## 2. Preflight

```bash
python3 <skill-dir>/core/scripts/wiki_state.py preflight <repo-root>
```

Interpret the JSON as follows.

| Field | Meaning and action |
|---|---|
| `blockers` | If non-empty, stop and tell the user. |
| `host` | If `mode` is `multi`, read and edit only `current_path`. If `error` is set, stop and ask which host this is. |
| `staged` | Files the user staged beforehand. Do not touch them; the pathspec commit keeps them out of the wiki commit. |
| `dirty_source` | Uncommitted source changes. Follow §5. |
| `dirty_instruction_files` | Instruction files carrying the user's uncommitted changes. Add the managed block but keep the file out of the commit (§5, §6). |
| `untracked_entries` | Ignore them unless relevant to the update. Do not read or modify them. |
| `ignored_wiki_files` | Wiki files that Git ignores. Rename them or tell the user. Never edit `.gitignore`. |
| `anchor`, `changed_source` | The range of source changes since the last wiki update. |
| `schema_version`, `template_schema_version` | If major.minor differ, only tell the user. Never auto-migrate SCHEMA. Ignore patch differences. |
| `upstream` | If `behind` > 0 (as of the last fetch), tell the user. |

## 3. Investigation rules

- Investigate only the current repository. Do not inspect other repositories, other machines, or user data outside the repository. "Other machines" covers any remote access: SSH, and also network requests to services running on other machines (for example, HTTP health checks of deployed instances). Record other machines' state as not observed, or as a documentation-only claim. Ask the user for anything this machine cannot know, such as another host's hostname.
- Each project wiki is operated independently per repository; only this skill package is shared between machines. Do not create pages describing other projects or a whole fleet of machines. Mention other systems only at the connection points this repository's code and scripts actually touch.
- Follow the authority order in SCHEMA §2. The repository outranks both the wiki and the conversation.
- Use `git ls-files` for tracked files. Do not read `node_modules/`, `vendor/`, `dist/`, `build/`, caches, generated output, model weights, binaries, or benchmark output.
- Do not inspect or modify SCHEMA's Protected Paths or anything project instructions mark as protected (for example, independent Git clones).
- For large files, read structure, entry points, and interfaces first instead of the whole file.
- Never copy secrets into the wiki. If you find secrets in the repository, report only their location to the user.

## 4. What is worth storing

When unsure whether to store something, ask:

> Would a new agent next month waste time or compute, or make a wrong design decision, without this information?

If yes, store it. If no, leave it to Git history and the source. High-value information includes architecture rationale, invariants, hard constraints, behavior not obvious from the code, interfaces between subsystems, why A was chosen over B, rejected approaches and why, verified experiment conclusions, known blockers, repeatable procedures, and current implementation maturity.

## 5. Git safety

- Never use: `git add -A`, `git commit -a`, `git reset --hard`, `git checkout -- .`, `git clean`, `git stash`, force push, destructive rebase.
- When there are uncommitted source changes (`dirty_source`):
  - If you changed those files yourself in this work unit and the scope is clear, ask the user whether to commit them first.
  - Otherwise reflect only the committed state in the wiki, and do not record uncommitted changes as facts.
- Commit sequence:

  ```bash
  git diff --cached --name-only                                  # staged files (same as preflight)
  git add wiki/ <edited instruction files>
  git ls-files --others --ignored --exclude-standard -- wiki/    # must print nothing
  git commit -m "docs(wiki): <message>" -- wiki/ <edited instruction files>
  ```

  A pathspec commit records only the given paths, so other files the user staged stay staged.
- A pathspec commit records the **entire change** of each given file. Therefore never put a file listed in preflight's `dirty_instruction_files` (an instruction file the user is working on) in the commit paths. Leave the managed block you added there uncommitted, and state in the report: "the managed block in `<file>` was not committed because it is mixed with the user's uncommitted changes".
  - If it is unclear who made those uncommitted changes (the agent in this session or the user), summarize `git diff -- <file>` for the user and ask whether to commit it separately first. If the user agrees, make that source commit first and the wiki commit afterwards.
- Push only when the user asks.
- If HEAD moved during the run (for example, another agent committed), do not commit on stale assumptions. Run preflight again.

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
6. If the target file is in preflight's `dirty_instruction_files`, say in the step-6 confirmation summary that the block in that file will not be committed because of uncommitted changes (§5).
7. If an instruction file has a policy that conflicts with the wiki (for example, "do not create handoff documents" or "record status only in commit messages"), confirm with the user, then change only that wording so the wiki is an exception.

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

## 8. Failure and uncertainty

- Never pretend success when there are failing tests, inconclusive benchmarks, unresolved contradictions, unreadable files, or an unsafe Git state.
- Write the real state in the wiki (for example, `Partially implemented. Validation currently fails at ...`). Never record as PASS anything that did not pass.
- If the repository has its own commit policy, that policy takes precedence.

## 9. Reporting to the user

Keep it short. Do not retell the whole session.

```text
Project Wiki updated.

Source changes reviewed: <anchor>..<head>
Wiki:
- updated components/<page>.md
- updated current.md
Validation:
- structural lint: PASS
- stale claims corrected: <n>
- unresolved items: <n>
Commit: docs(wiki): <message>

Skill feedback:
- <instructions that were ambiguous so you had to guess>
- <steps you could not follow or skipped, and why>
- <where you had to hunt for information>
```

Every `/wiki-init` and `/wiki-update` report must include `Skill feedback`. It records clues for improving the skill itself from this run.

- Write 2–5 lines of facts, not evaluations ("it worked well"). Examples: "Did not receive the `<skill-dir>` path, so checked the install locations in order", "SCHEMA §5's new-page criteria were ambiguous, so merged the component pages".
- If there is nothing to report, write `- none`.
- Do not fix the skill yourself. If the user asks for an improvement, follow §10. To review a run, use `core/review-checklist.md`.

## 10. Improving the skill itself

When the user asks for an improvement to the wiki skills during use, apply it to the skill package repository and share it. Such a request authorizes commits and pushes to the package repository.

1. Find the package: `package_dir` in the output of `python3 <skill-dir>/core/scripts/wiki_state.py self-update`. Edit the real repository the symlinks point to.
2. Before editing, update with `git -C <package_dir> pull --ff-only`.
3. Change only what was requested. Keep each `SKILL.md` at or under 150 lines.
4. Run the tests: `python3 -m unittest discover -s <package_dir>/tests`.
5. Bump the version. There are two versions:
   - `VERSION` (skill package): patch for changes without functional change (wording, typos, bug fixes), minor for new behavior, major for incompatible changes.
   - `core/SCHEMA_VERSION` (SCHEMA policy): bump only when the policy in `core/SCHEMA.template.md` changes. Each repository's SCHEMA `schema-version` is compared with it by major.minor only, so skill-only releases cause no warnings in existing wikis.
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
