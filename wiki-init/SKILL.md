---
name: wiki-init
description: Investigate the current Git repository and build its project wiki (wiki/) for the first time. Creates overview, current, and index from the repository structure, docs, tests, and Git history, runs structural lint, and commits. Run only when the user explicitly invokes /wiki-init.
disable-model-invocation: true
triggers: [user]
---

# wiki-init

This file is only an entry point. The procedure lives in the skill package on disk and may be newer than this copy, which the harness loaded before any update. Do not act on steps you remember from an earlier version of this skill.

`<skill-dir>` is the directory containing this file; shared resources live in `<skill-dir>/core/`. If the harness does not tell you this path, check for `SKILL.md` in `~/.claude/skills/wiki-init`, `~/.agents/skills/wiki-init`, `~/.config/opencode/skills/wiki-init`, `~/.config/devin/skills/wiki-init`, `~/.pi/agent/skills/wiki-init`, in that order. Never search the whole filesystem.

1. Run `python3 <skill-dir>/core/scripts/wiki_state.py self-update` by itself and wait for its result. Do not read or run anything else in the same step. If `status` is `busy`, another self-update is still replacing the files: read nothing, tell the user, and stop.
2. After it returns, read these files in full, in this order, one read per file: `<skill-dir>/core/protocol.md`, then `<skill-dir>/core/init.md`. If a read fails, stop and tell the user; never continue from memory.
3. Follow `core/init.md` from its first step.
