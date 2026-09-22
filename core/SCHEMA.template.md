# Wiki Schema

<!--
This file is the operating contract for this repository's wiki.
/wiki-update never edits it because of ordinary project work.
Edit it only when the wiki policy itself changes, with the user's approval.
-->

schema-version: {{SCHEMA_VERSION}}
wiki-language: {{WIKI_LANGUAGE}}

Wiki pages are written in the wiki language above. This contract is in English.

## 1. Purpose

This wiki is compressed semantic memory that helps future agent sessions understand the project without past conversations. It keeps only knowledge that is hard or expensive to rediscover from the repository. It is not a summary of chat history.

## 2. Authority Hierarchy

When sources conflict, the higher one wins.

1. Actual implementation
2. Tests and executable validation
3. Benchmark / experiment artifacts
4. Git history
5. Documentation written or reviewed by people
6. The wiki, and documents or skills written by earlier agents
7. The current conversation

- If the wiki differs from the code, fix the wiki. Never change code to match the wiki.
- Runtime facts (service state, model files, launchd/systemd state) carry the observation date and the method, and live only in the current file of the host where they were observed.
- Goals and requirements are set by the user and maintainers. Never infer goals from the current implementation alone.

## 3. Page Taxonomy

| Path | Purpose |
|---|---|
| `index.md` | Router. Lists every substantive page as a link plus a one-line summary |
| `overview.md` | Stable long-term context: purpose, non-goals, hard constraints, high-level architecture, terminology |
| `current.md` or `current/<host>.md` | Snapshot of the current state. Not a handoff note |
| `log.md` | Audit trail of updates. Not read during bootstrap |
| `architecture/` | Structure and rationale |
| `components/` | Responsibilities, interfaces, and invariants of subsystems |
| `decisions/NNNN-<slug>.md` | ADRs, numbered with four digits |
| `experiments/` | Experiments that influenced later design decisions |
| `runbooks/` | Repeatable procedures |
| `archive/` | Superseded records. Not read during bootstrap |

Do not create categories you do not need. Add a new category only when no existing one fits, and add it to this table (a policy change).

## 4. Page Format

- File names are English kebab-case. Never use a name matched by `.gitignore` patterns (for example `*token*`, `*secret*`).
- Every page except `index.md`, `log.md`, and `SCHEMA.md` has frontmatter.

  ```yaml
  ---
  title: <title>
  type: overview | current | architecture | component | decision | experiment | runbook
  status: <vocabulary below>
  updated: YYYY-MM-DD
  ---
  ```

- Status vocabulary:
  - overview, current, architecture, component, runbook: `current`, `partial`, `deprecated`, `archived`
  - decision: `proposed`, `accepted`, `rejected`, `superseded`
  - experiment: `planned`, `running`, `completed`, `inconclusive`
- Update `updated` only when the content actually changes.
- Page bodies follow `core/page-schema.md` in the skill package.
- Write paths relative to the repository root. Do not record line numbers; name symbols when useful.

## 5. Update Rules

- Prefer editing an existing page over creating a new one. Content that fits in 3–5 bullets, a description of a single file, or a one-off debugging record does not get its own page.
- Make the minimum necessary edit. Do not touch unrelated sentences or formatting.
- Never append to the current file; recompute it each time. Remove resolved items or move them to the canonical page.
- Edit `overview.md` only when scope, hard constraints, high-level architecture, canonical references, or major subsystems change.
- Update `index.md` when pages are added, renamed, or archived, or a summary changes meaningfully.
- Resolve contradictions between pages by investigating the repository and fixing the canonical page. If you cannot decide, mark it `Unresolved contradiction`.
- Explain each concept on one canonical page and link to it elsewhere. If an existing document is canonical, link to it instead of copying it.

## 6. Evidence Rules

- Give the source location (implementation path, test, artifact) for important claims.
- When unsure, mark claims `Unknown`, `Not yet verified`, `Hypothesis`, or `Partially validated`.
- Experiments separate measurement from interpretation and record the host and hardware. Do not generalize results before verifying them on other hosts.
- If artifacts live in gitignored or untracked paths, write the key numbers, the command, and the source revision on the page itself. Never link untracked paths as evidence.
- Never record secrets (API keys, tokens, passwords, private keys, credential file contents).
- In multi-host repositories, machine-dependent facts (model file paths, runnable models, memory limits, service names, benchmark numbers, ...) must name their host. A statement without a host is treated as true for all hosts.

## 7. Context-loading Rules

When starting new work, read in this order:

1. `index.md`
2. `overview.md`
3. `current.md` (in multi-host repositories, only this host's `current/<host>.md`)
4. Only the pages relevant to the task

Do not read all decisions, experiments, or runbooks, the whole `log.md`, or `archive/`. For recent history, read only `tail -n 60 wiki/log.md`.

## 8. Anti-bloat Rules

1. Do not store chat transcripts or session summaries.
2. Do not repeat trivial changes that Git already explains.
3. Prefer editing existing pages over creating new ones.
4. The current file is not append-only; remove resolved items.
5. Move historical detail to the archive or decision history.
6. Do not create a file-per-page structure.
7. Do not copy long code blocks; write the source path.
8. Keep only information that lowers the cost of future decisions.

## 9. Budgets

Token counts are estimates. Exceeding them produces a lint warning.

<!-- wiki:budgets:start -->
current_tokens: 2000
bootstrap_tokens: 6000
<!-- wiki:budgets:end -->

## 10. Hosts

Fill this only for repositories used on several machines. If it is empty, the repository is single-host and uses `current.md`.

Format: `<host-name>: <hostname -s value>[, <other value>...]`

<!-- wiki:hosts:start -->
{{HOSTS}}
<!-- wiki:hosts:end -->

- Shared pages (overview, architecture, components, decisions, experiments, runbooks) hold knowledge common to all hosts. Each host's current state lives in `current/<host>.md`.
- An agent edits only shared pages and its own host's current file. It never changes another host's current file, not even by one byte. It leaves other hosts' facts in shared pages as they are, because this host cannot verify them.
- If the current hostname is not in the table, write to no current file, stop, and ask the user.

## 11. Protected Paths

Wiki work never inspects or modifies these paths. One path per line.

<!-- wiki:protected:start -->
{{PROTECTED_PATHS}}
<!-- wiki:protected:end -->

## 12. Lint Rules

- Structural lint: `python3 <skill-dir>/core/scripts/wiki_lint.py <repo-root>`. Structural errors make the exit code 1; resolve them all before committing.
- Semantic lint is done by `/wiki-update` (contradictions with the code, stale state, duplication, current-file bloat, ...).

## 13. Git Rules

- Wiki commits are pathspec commits: `git commit -m "docs(wiki): ..." -- wiki/ <edited instruction files>`.
- Forbidden: `git add -A`, `git commit -a`, `git reset --hard`, `git checkout -- .`, `git clean`, `git stash`, force push.
- Push only when the user asks.
- Commit messages: `docs(wiki): initialize project memory`, `docs(wiki): update project memory after <topic>`.
- `log.md` entries use this format. Every entry must have a `Source HEAD:` line.

  ```markdown
  ## [YYYY-MM-DD] update | <topic>

  Host: <host-name>              (multi-host repositories only)
  Source HEAD: <preflight head, full 40-character SHA>
  Wiki:
  - updated <page>
  Validation:
  - <checks actually run and their results>
  Open:
  - <remaining work>
  ```
