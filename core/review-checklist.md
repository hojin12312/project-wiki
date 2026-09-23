# Wiki Run Review Checklist

Use this after `/wiki-init` or `/wiki-update` to review whether the run served the wiki's purpose. The review is done by the user or another agent, not by the session that ran it, because the running agent rarely notices problems in its own judgment.

Evidence to use:

- The wiki commit: `git show --stat HEAD`, `git show HEAD`
- `python3 <skill-dir>/core/scripts/wiki_lint.py <repo>`
- The last entry of `wiki/log.md`
- The run report and its `Skill feedback`
- The run's session transcript when needed (its location differs per harness)

For each item with a problem, record the evidence (file, line, command output).

## 1. Scope

- [ ] Did it avoid *new* remote access (SSH, health checks or API probes to other machines) and new reads of protected paths or out-of-repository deployments?
- [ ] For evidence from an earlier operation in the same work unit: does it name the real tool output, date, observing host, and method (secrets removed)? Was an agent's claim without tool output kept out?
- [ ] Is a result the user said they checked recorded as `user-reported` with its date and the user's own scope, not widened and not listed as PASS or as this run's Validation?
- [ ] Is that earlier evidence kept apart from this run's checks (original date kept, `not re-checked this run` where applicable)?
- [ ] Is a Source HEAD kept apart from deployment revisions, and committed state apart from dirty working-tree state?
- [ ] Was protected-path knowledge kept out of the wiki unless it came through a permitted interface? If an interface is the only safe write path, is it recorded as a component invariant?
- [ ] Did it avoid pages describing other projects or a whole fleet of machines? Are other systems mentioned only at the connection points this repository's code touches?
- [ ] Did it leave Protected Paths and independent Git clones unread and unmodified?
- [ ] If run from a subfolder of a Git repository, did the target scope (the whole repository) match the user's intent?

## 2. Git safety

- [ ] Was the committed set exactly the files this run edited (no whole-directory add, no pre-existing dirty file, no other host's current file, no untracked or ignored instruction file)?
- [ ] Were HEAD, the index state, and lock ownership (`preflight --lock-token`) re-checked immediately before the commit? Did `edits_since_lock` list exactly the run's edits, and were their diffs read? Was the run lock released at the end, including on a no-op or a stop?
- [ ] If a lock was held, did the run stop instead of waiting, retrying, or removing it? Was `unlock --force --id` used only after the user confirmed the holder was gone?
- [ ] Does the wiki commit carry the `Project-Wiki-Run:` trailer, and does no hand-made commit carry it?
- [ ] Were commit paths passed as separate literal arguments, and did `git show --name-only HEAD` list exactly the intended files?
- [ ] Was none of the user's uncommitted work (especially `dirty_instruction_files`) mixed into the commit?
- [ ] Are files the user staged beforehand still staged, and were they reported as left untouched?
- [ ] If more than 200 paths changed, was the remainder reviewed before the anchor advanced?
- [ ] Did it avoid pushing and forbidden commands (`git add -A`, `reset --hard`, `stash`, ...)?

## 3. Factual accuracy

- [ ] Does the current file match the actual implementation? Were TODOs or stubs recorded as finished?
- [ ] Were tests or checks that did not run recorded as PASS? Did the run avoid re-running project tests, builds, and benchmarks outside the small-check rule (protocol §3.2)?
- [ ] Are unverified claims marked `Unknown`, `Not yet verified`, or `Hypothesis`?
- [ ] Do runtime facts carry the observation date, host, and method?
- [ ] Were secrets, personal data, and credential-store shapes kept out regardless of how they were obtained? Was nothing laundered from a forbidden read?
- [ ] Was a SCHEMA fact contradicted by the code left in SCHEMA and recorded once under the current file's Active Risks / Unknowns (`core/protocol.md` §11)?
- [ ] In multi-host repositories, do machine-dependent facts name their host? Were other hosts' current files left unchanged?
- [ ] Were goals and non-goals taken from the user or the docs rather than inferred from the implementation?

## 4. Compression and structure

- [ ] Is the bootstrap (index, overview, current) within budget, and does it alone tell what the project is and where it stands? If it was over budget, was detail moved rather than durable knowledge deleted, and was the budget left unchanged unless the user approved?
- [ ] Was the current file's budget checked before editing it (preflight `budget.current_tokens` / `current_estimate`)?
- [ ] Are unpreserved output paths marked narrowly (`<!-- wiki:not-preserved -->` on the notation), not by exempting a page or section?
- [ ] Is the page count reasonable, with no file-per-page structure and no trivial decision or experiment pages?
- [ ] Were canonical documents linked instead of copied? Is each concept explained on only one page?
- [ ] For `/wiki-update`: were unrelated pages left untouched? Was the current file recomputed rather than appended to?
- [ ] Were conversation summaries and work narratives kept out of the wiki?

## 5. Procedure

- [ ] Did it run self-update by itself first, and only then read `core/protocol.md` and the procedure file (`core/init.md` or `core/update.md`)?
- [ ] Were wiki edits already committed in the range (`changed_wiki`) reviewed and, when accurate, left as they were?
- [ ] For `/wiki-init`: did it get user confirmation before creating files, with the host layout, page list, conflicting policies, and managed-block placement in the summary?
- [ ] Is the structural lint PASS, and were the remaining warnings reported? Are encoding findings (invalid UTF-8, U+FFFD, control characters) explained?
- [ ] If `changed_source` and `changed_wiki` were both empty with no new evidence, did it stop as a no-op instead of editing? Did the previous run's own commit stay out of the review?
- [ ] If the SCHEMA version differed, did the run still finish the normal update, and propose only missing items while keeping language, hosts, protected paths, and budgets unchanged?
- [ ] Does the report include `Skill feedback`?

## Handling the results

- Problems in wiki content: fix them in that repository directly, or in the next `/wiki-update`.
- Problems in the skill: when the user asks for an improvement, apply it to the skill package per `core/protocol.md` §12.
- If the same review keeps repeating, consider turning this checklist into a separate skill.
