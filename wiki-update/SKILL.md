---
name: wiki-update
description: After a work unit, reconcile the project wiki (wiki/) with the actual repository state, incrementally updating only the pages that need it, then run semantic and structural lint plus structural maintenance and commit. Not a conversation summary. Run only when the user explicitly invokes /wiki-update.
disable-model-invocation: true
triggers: [user]
---

# wiki-update

This file is only an entry point. The procedure lives in the skill package on disk and may be newer than this copy, which the harness loaded before any update. Do not act on steps you remember from an earlier version of this skill.

`<skill-dir>` is the directory containing this file; shared resources live in `<skill-dir>/core/`. If the harness does not tell you this path, check for `SKILL.md` in `~/.claude/skills/wiki-update`, `~/.agents/skills/wiki-update`, `~/.config/opencode/skills/wiki-update`, `~/.config/devin/skills/wiki-update`, `~/.pi/agent/skills/wiki-update`, in that order. Never search the whole filesystem.

1. Run `python3 <skill-dir>/core/scripts/wiki_state.py self-update` by itself and wait for its result. Do not read or run anything else in the same step. If `status` is `busy`, another self-update is still replacing the files: read nothing, tell the user, and stop.
2. After it returns, read these files in full, in this order, one read per file: `<skill-dir>/core/protocol.md`, then `<skill-dir>/core/update.md`. If a read fails, stop and tell the user; never continue from memory.
3. Follow `core/update.md` from its first step.
