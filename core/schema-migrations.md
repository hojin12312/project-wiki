# SCHEMA migrations

Read this only when a repository's `wiki/SCHEMA.md` `schema-version` differs in major.minor from `core/SCHEMA_VERSION`. The procedure is `core/protocol.md` §11 "Schema migration": propose only the missing items, apply only what the user approves, and never replace the file with the template.

Most rules live in `core/protocol.md` and lint, so they apply as soon as the package updates. A migration only brings the repository's own contract text up to date; skipping it disables no rule.

Each entry names the template section and the intent of the change. An installed SCHEMA may be in another language (templates before package 0.4.2 were Korean) or phrased differently: look for the intent, not the English sentence, and write what is missing in the SCHEMA's own language and style.

Never change as part of a migration: `wiki-language`, the contents of the budgets, hosts, and protected blocks, the existing text of header comments (an item below may add a sentence), local categories, or any local rule that is stricter or additional.

## 0.3.2 (patch: lint does not warn)

- §6 Evidence Rules: the `<!-- wiki:local-path -->` marker for an inline-code path cited as a local location or boundary rather than as evidence; the current file keeps only the boundaries a future session needs, not an inventory of untracked paths; `log.md` inline path mentions are historical and not re-checked.
- §13 Git Rules: a pathspec commit records working-tree content and is not a partial-commit mechanism.

## 0.3.1 (patch: lint does not warn)

- §13 Git Rules: the example commit named the whole directory (`git commit ... -- wiki/ <edited instruction files>`). It now names the exact files the run edited. Correct the example if the local SCHEMA still has the old one.

## 0.3.0

- Header comment: SCHEMA holds policy and configuration only. Mutable facts (test counts, implementation status, versions) belong in the current file or a component page. A SCHEMA fact the code has made false is handled by `core/protocol.md` §11.
- §2 Authority Hierarchy: keep the goal or contract, the committed source, and an observed deployment state apart. `Source HEAD` is a revision of this repository, never a deployment revision or proof that a deployment succeeded.
- §5 Update Rules: do not edit SCHEMA to correct an ordinary fact; propose the fix and record the contradiction once in the current file.
- §6 Evidence Rules, replacing the older bullets about gitignored artifacts and secrets:
  - Evidence links must resolve again in another checkout: tracked files or stable external references.
  - A reproduction output path (exists only after re-running something) is written as inline code followed by `<!-- wiki:not-preserved -->`, with the key numbers, conditions, command, and revision in the page body. The marker covers that one notation only.
  - Never record secrets or personal data, however obtained. Counts, field names, and shapes of a credential store are not automatically safe.
  - An observation record carries date, observing host, target, method (secrets removed), and result. Earlier verification keeps its original date and is marked "not re-checked this run".
- §9 Budgets: the explanation that preflight and lint share one estimate heuristic, which is not a model tokenizer count. Text only; the local budget numbers stay.
- §11 Protected Paths: facts learned by reading these paths directly are never recorded; facts from a permitted interface (API, CLI, service response) may be recorded with date, host, and method, and an interface that is the only safe write path becomes a component invariant; lint cannot check this rule.
- §13 Git Rules: `Source HEAD` is the head the run actually reviewed. It does not advance past an unreviewed remainder, and an uncommitted entry is not a confirmed anchor.

## 0.2.2

- §11 Protected Paths: what belongs there (paths the instructions forbid, independent Git clones, secret or credential stores) and what does not (large or noisy directories such as logs, traces, and data dumps, which are read selectively).

## 0.2.1

- §13 Git Rules: `Source HEAD` in log entries is preflight's full 40-character SHA.
