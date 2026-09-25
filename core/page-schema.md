# Page Templates

Use these templates when creating pages. Delete sections that have no content. Section headings may be translated into the wiki language, but once chosen they stay fixed, like SCHEMA. Placeholder descriptions below are in English; write the actual content in the wiki language.

## index.md

```markdown
# Project Wiki

## Start Here

- [Overview](overview.md) — purpose, scope, hard constraints.
- [Current State](current.md) — current implementation state, blockers, next work.

## Architecture

- [<title>](architecture/<slug>.md) — <one-line summary>.

## Components
## Decisions
## Experiments
## Runbooks
```

- Every entry is a link plus a one-line summary. Do not write detailed explanations in the index itself.
- In multi-host repositories, list `current/<host>.md` for each host under Start Here.
- When there are more than 80–100 substantive pages or the index gets too long, create an `index.md` per category and turn the top-level index into a category router.

## overview.md

```markdown
---
title: Overview
type: overview
status: current
updated: YYYY-MM-DD
---

# Overview

## Purpose
## Primary Goal
## Non-goals
## Hard Constraints
## Canonical References
## High-level Architecture
## Terminology
## Quality Requirements
## Design Principles
```

Do not include today's work, recent commits, detailed TODOs, or transient blockers.

## current.md / current/<host>.md

```markdown
---
title: Current State
type: current
status: current
updated: YYYY-MM-DD
---

# Current State

## Working
## Partially Implemented
## Not Yet Implemented
## Current Blockers
## Active Risks / Unknowns
## Next Logical Work
```

- Working lists implemented behavior with its basis: a tool observation (with date), a user report marked `user-reported YYYY-MM-DD: <the user's own scope>` (never widened or turned into a test result), or `code read; not executed` when the implementation and its tests were read but nothing was run (`core/protocol.md` §3.2). Mismatches, warnings, and anything unverified go under Active Risks / Unknowns.
- Separate observation from inference. Mark interpretations drawn from observations with `Inference:` or `Hypothesis:` (or the wiki-language equivalent, e.g. `추정:`).
- A statement in `SCHEMA.md` that the code has made false goes here once, under Active Risks / Unknowns, with the confirmed fact. Keep SCHEMA unchanged until the user approves the fix (`core/protocol.md` §11).
- Record a reference to a file that does not exist once, under Active Risks / Unknowns, and do not repeat the path on other pages.
- Keep no history. Remove resolved blockers, and reflect finished work in Working or in the canonical page.
- Next Logical Work is where a new session with no past conversation starts: name concrete next steps, not "continue the work".
- Size the file to the budget before writing it (preflight `budget`; the estimate is a heuristic, not a model tokenizer count, and runs higher for non-ASCII text). Move detail to canonical pages; never delete durable knowledge to fit.
- Untracked local paths are not an inventory: keep only the boundaries a future session needs (a nested clone, a scratch path whose name carries a fact), write each as inline code followed by `<!-- wiki:local-path -->`, and never present them as evidence (`core/protocol.md` §7).
- Attach observation details to runtime facts in the form `(observed YYYY-MM-DD, host <host>, <method with secrets removed>, <result>)`, written in the wiki language (e.g. `(확인 YYYY-MM-DD, host <host>, <method>)`). Keep the original date on a result you did not re-check, and mark it "not re-checked this run".
- If the repository has a canonical document for configuration values (for example `hosts/<host>/README.md`), link to it instead of copying the values.

## architecture/<slug>.md

```markdown
---
title: <title>
type: architecture
status: current
updated: YYYY-MM-DD
---

# <title>

## Purpose
## Current Design
## Invariants
## Data Flow
## Important Trade-offs
## Relevant Implementation
## Validation
## Known Limitations
## Related Decisions
## Related Pages
```

## components/<slug>.md

```markdown
---
title: <title>
type: component
status: current
updated: YYYY-MM-DD
---

# <title>

## Responsibility
## Interface
## Current Implementation
## Important Invariants
## Relevant Paths
## Tests / Validation
## Known Limitations
## Related Pages
```

- If changing this component safely must go through an interface (API, migration command) rather than editing files, record that as an invariant, with the accessible code or document that proves it. Later sessions otherwise fall back to editing files directly.

## decisions/NNNN-<slug>.md

```markdown
---
title: <the decision>
type: decision
status: accepted
updated: YYYY-MM-DD
---

# <the decision>

## Context
## Decision
## Rationale
## Alternatives Considered
## Consequences
## Evidence
## Relevant Implementation
## Supersedes
## Superseded By
## Related Pages
```

The purpose is to preserve the "why" that `git log` alone cannot tell. Do not write a decision for every minor implementation choice.

## experiments/<slug>.md

```markdown
---
title: <experiment name>
type: experiment
status: completed
updated: YYYY-MM-DD
---

# <experiment name>

## Question
## Setup
## Host / Hardware
## Source Revision / Configuration
## Method
## Results
## Interpretation
## Conclusion
## Impact on Design
## Artifacts
## Limitations
```

- Results holds only measurements; Interpretation holds the interpretation. Start any interpretation that is not directly proven with `Hypothesis:`.
- A gitignored or untracked output is not evidence: keep the key numbers, conditions, and source revision in Results and Setup, and state in the text that the artifact is not preserved. If you still name the output path for reproduction, write it in inline code and put `<!-- wiki:not-preserved -->` directly after that code span; the marker applies to that notation only, not to the page or the Artifacts section.
- A plain smoke test does not get an experiment page.

## runbooks/<slug>.md

```markdown
---
title: <procedure name>
type: runbook
status: current
updated: YYYY-MM-DD
---

# Runbook: <procedure name>

## Purpose
## Preconditions
## Procedure
## Expected Output
## Verification
## Failure Modes
## Relevant Files
```

- Remote commands in a runbook are procedures for a separate operations task (`core/protocol.md` §3). A wiki run never executes them; it only records the procedure.

## log.md

```markdown
# Wiki Log

## [YYYY-MM-DD] init | initial project memory

Source HEAD: <the head this run reviewed, full 40-character SHA>
Wiki:
- created index.md, overview.md, current.md, ...
Validation:
- <checks this run actually ran only; user reports and earlier tool results stay on the pages that record them>
Open:
- <claims not yet verified>
```

Keep each entry at 5–15 lines. Do not write conversation summaries or list every edited file.
