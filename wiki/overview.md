---
title: Overview
type: overview
status: current
updated: 2026-09-25
---

# Overview

## Purpose

`project-wiki` is a skill package that gives AI coding agents long-term project
memory: each repository gets a `wiki/` directory, so knowledge survives session
boundaries. The two user-facing commands are `/wiki-init` (build the wiki once)
and `/wiki-update` (reconcile the wiki with the repository after a work unit).

## Primary Goal

Reduce the cost of resuming long-running work: repeated investigation,
re-discovered pitfalls, and lost rationale. A new session should recover project
state from a small bootstrap (index + overview + current file) plus selectively
loaded pages.

## Non-goals

- No chat-history summaries, session logs, or per-commit records (Git history
  already covers those).
- No new infrastructure: no database, vector store, embeddings, daemon, or MCP
  server. Markdown + Git + small deterministic tooling only.
- The wiki never drives the repository; the repository always outranks it.
- Skill commands run only when the user invokes them (per-harness flags keep
  models from auto-invoking).

## Hard Constraints

- Python 3.8+ standard library and Git only; must work on macOS and Linux.
- `wiki-init/` and `wiki-update/` SKILL.md files are entry points only; all
  procedure lives in `core/` and is read from disk after self-update.
- One wiki per repository; the package itself is shared across machines via
  per-machine clones plus `install.sh` symlinks.

## Canonical References

- `README.md` — install, usage, harness table (Korean, human-facing).
- `docs/design.md` — the initial design specification (Korean). Parts are
  superseded by later changes; where it disagrees with README or `core/`,
  README and `core/` win.
- `core/protocol.md` — the shared operating rules for both commands.
- `core/schema-migrations.md` — per-version SCHEMA policy changes.

## High-level Architecture

- `wiki-init/` and `wiki-update/`: thin entry points (`SKILL.md` +
  `agents/openai.yaml` + `core -> ../core` symlink).
- `core/`: shared procedure and policy documents.
- `core/scripts/wiki_state.py`: deterministic state tooling — self-update,
  preflight, budget, host, anchor, lock/unlock (JSON on stdout).
- `core/scripts/wiki_lint.py`: structural lint for an installed `wiki/`.
- `install.sh`: links the two skills into each present harness's skill dir.
- `tests/`: `unittest` suite over local Git fixtures plus `scenarios.md`
  judgment scenarios.

## Terminology

- *Skill package*: this repository, installed per machine by symlink.
- *Wiki run*: one `/wiki-init` or `/wiki-update` execution.
- *Anchor*: the last confirmed `Source HEAD` in a committed `wiki/log.md`
  entry written by a run-trailer commit.
- *Run lock*: cooperative per-checkout lock in `.git/project-wiki.lock`.

## Quality Requirements

- Evidence discipline: distinguish user requirements, user observations, tool
  observations, and unverified claims; keep observation dates.
- Git safety: pathspec commits of exactly the files a run edited; a fixed
  forbidden-command list.
- Tests must pass on macOS and Linux with the standard library only.

## Design Principles

Compress rather than accumulate; the wiki should get more accurate and smaller
as it ages. Keep rules in one canonical place (`core/`, SCHEMA) and link
elsewhere. Prefer deterministic tooling over agent judgment where possible.
