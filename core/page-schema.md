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

- Working lists only behavior you verified. Mismatches, warnings, and anything unverified go under Active Risks / Unknowns.
- Separate observation from inference. Mark interpretations drawn from observations with `Inference:` or `Hypothesis:` (or the wiki-language equivalent, e.g. `추정:`).
- Keep no history. Remove resolved blockers, and reflect finished work in Working or in the canonical page.
- Attach observation details to runtime facts in the form `(observed YYYY-MM-DD, <command>)`, written in the wiki language (e.g. `(확인 YYYY-MM-DD, <command>)`).
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
- If artifacts are in gitignored paths, write the key numbers, the command, and the source revision directly in Results and Setup.
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

## log.md

```markdown
# Wiki Log

## [YYYY-MM-DD] init | initial project memory

Source HEAD: <preflight head, full 40-character SHA>
Wiki:
- created index.md, overview.md, current.md, ...
Validation:
- structural lint: PASS
Open:
- <claims not yet verified>
```

Keep each entry at 5–15 lines. Do not write conversation summaries or list every edited file.
