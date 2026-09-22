# Page Templates

페이지를 새로 만들 때 아래 template을 사용한다. 내용이 없는 section은 지운다. Section 제목은 저장소의 Wiki 언어로 옮겨도 되지만, 한 번 정한 제목은 SCHEMA처럼 고정해서 쓴다.

## index.md

```markdown
# Project Wiki

## Start Here

- [Overview](overview.md) — 목적, 범위, hard constraint.
- [Current State](current.md) — 현재 구현 상태, blocker, 다음 작업.

## Architecture

- [<제목>](architecture/<slug>.md) — <한 줄 요약>.

## Components
## Decisions
## Experiments
## Runbooks
```

- 모든 entry는 link와 한 줄 요약으로 구성한다. Index 자체에 상세 설명을 쓰지 않는다.
- 여러 host 저장소는 Start Here에 `current/<host>.md`를 host마다 나열한다.
- Substantive page가 80~100개를 넘거나 index가 지나치게 길어지면 category별 `index.md`를 만들고, top-level index는 category router로 바꾼다.

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

오늘의 작업, 최근 commit, 세부 TODO, 일시적인 blocker는 넣지 않는다.

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

- Working에는 동작을 확인한 것만 넣는다. 불일치, 경고, 확인하지 못한 것은 Active Risks / Unknowns에 넣는다.
- 관측과 추론을 구분한다. 관측에서 이끌어 낸 해석은 `추정:` 또는 `Hypothesis:`로 표시한다.
- 과거 기록을 남기지 않는다. 해결된 blocker는 제거하고, 완료된 작업은 Working이나 정본 페이지에 반영한다.
- Runtime 사실은 `(확인 YYYY-MM-DD, <확인 명령>)` 형식으로 관측 정보를 붙인다.
- 저장소에 설정값의 정본 문서가 있으면(예: `hosts/<host>/README.md`) 설정값을 복사하지 않고 link한다.

## architecture/<slug>.md

```markdown
---
title: <제목>
type: architecture
status: current
updated: YYYY-MM-DD
---

# <제목>

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
title: <제목>
type: component
status: current
updated: YYYY-MM-DD
---

# <제목>

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
title: <결정 내용>
type: decision
status: accepted
updated: YYYY-MM-DD
---

# <결정 내용>

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

`git log`만으로 알 수 없는 "왜"를 보존하는 것이 목적이다. 사소한 구현 선택마다 decision을 만들지 않는다.

## experiments/<slug>.md

```markdown
---
title: <실험 이름>
type: experiment
status: completed
updated: YYYY-MM-DD
---

# <실험 이름>

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

- Results에는 측정값만 적고, Interpretation에는 해석을 적는다. 직접 증명되지 않은 해석은 `Hypothesis:`로 시작한다.
- 결과물이 gitignored 경로에 있으면 핵심 수치, 실행 명령, source revision을 Results와 Setup에 직접 적는다.
- 단순 smoke test는 experiment 페이지로 만들지 않는다.

## runbooks/<slug>.md

```markdown
---
title: <절차 이름>
type: runbook
status: current
updated: YYYY-MM-DD
---

# Runbook: <절차 이름>

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

Source HEAD: <sha>
Wiki:
- created index.md, overview.md, current.md, ...
Validation:
- structural lint: PASS
Open:
- <확인하지 못한 주장>
```

Entry 하나는 5~15줄로 유지한다. 대화 요약이나 모든 수정 파일 목록을 쓰지 않는다.
