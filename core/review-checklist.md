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

- [ ] Did it investigate only the current repository, without other repositories or other machines (SSH, or network requests such as health checks to services on other machines)?
- [ ] Did it avoid pages describing other projects or a whole fleet of machines? Are other systems mentioned only at the connection points this repository's code touches?
- [ ] Did it leave Protected Paths and independent Git clones unread and unmodified?
- [ ] If run from a subfolder of a Git repository, did the target scope (the whole repository) match the user's intent?

## 2. Git safety

- [ ] Does the commit contain only `wiki/` and the instruction files that received the managed block?
- [ ] Was none of the user's uncommitted work (especially `dirty_instruction_files`) mixed into the commit?
- [ ] Are files the user staged beforehand still staged?
- [ ] Did it avoid pushing and forbidden commands (`git add -A`, `reset --hard`, `stash`, ...)?

## 3. Factual accuracy

- [ ] Does the current file match the actual implementation? Were TODOs or stubs recorded as finished?
- [ ] Were tests or checks that did not run recorded as PASS?
- [ ] Are unverified claims marked `Unknown`, `Not yet verified`, or `Hypothesis`?
- [ ] Do runtime facts carry the observation date and method?
- [ ] In multi-host repositories, do machine-dependent facts name their host? Were other hosts' current files left unchanged?
- [ ] Were goals and non-goals taken from the user or the docs rather than inferred from the implementation?
- [ ] Were secrets kept out?

## 4. Compression and structure

- [ ] Is the bootstrap (index, overview, current) within budget, and does it alone tell what the project is and where it stands?
- [ ] Is the page count reasonable, with no file-per-page structure and no trivial decision or experiment pages?
- [ ] Were canonical documents linked instead of copied? Is each concept explained on only one page?
- [ ] For `/wiki-update`: were unrelated pages left untouched? Was the current file recomputed rather than appended to?
- [ ] Were conversation summaries and work narratives kept out of the wiki?

## 5. Procedure

- [ ] Did it run self-update and preflight at the start?
- [ ] For `/wiki-init`: did it get user confirmation before creating files, with the host layout, page list, conflicting policies, and managed-block placement in the summary?
- [ ] Is the structural lint PASS, and were the remaining warnings reported?
- [ ] Does the report include `Skill feedback`?

## Handling the results

- Problems in wiki content: fix them in that repository directly, or in the next `/wiki-update`.
- Problems in the skill: when the user asks for an improvement, apply it to the skill package per `core/protocol.md` §10.
- If the same review keeps repeating, consider turning this checklist into a separate skill.
