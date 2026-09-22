# Project LLM Wiki Skills — Implementation Plan

> 이 문서는 `wiki-init`·`wiki-update`를 만들 때 쓴 초기 설계 명세다. 설계 의도와 판단 근거를 보여 주기 위해 포함했다. 구현이 이후에 개선되면서 달라진 부분이 있으며(예: `wiki_state.py`, `Skill feedback`, `core/review-checklist.md`, `core/SCHEMA_VERSION`), 이 문서와 구현이 다르면 `README.md`와 `core/`가 우선한다. 머신과 프로젝트 이름은 일반적인 예시로 바꿨다.

## 0. 구현 에이전트에게

이 문서는 장기 소프트웨어 개발 프로젝트에서 AI 에이전트가 여러 세션에 걸쳐 프로젝트 컨텍스트를 효율적으로 유지하기 위한 **Git-backed Project LLM Wiki 시스템**의 구현 명세다.

목표는 다음 두 명령을 제공하는 것이다.

```text
/wiki-init
/wiki-update
```

`/wiki-init`은 기존 저장소를 조사하여 최초 프로젝트 Wiki를 구축한다.

`/wiki-update`는 하나의 작업 단위가 끝난 시점에서 실제 저장소 상태와 새로 얻은 지식을 조사하고, 필요한 Wiki 문서만 증분 갱신한 뒤 검증하고 Git에 기록한다.

이 시스템에서 Chat history는 장기 기억의 source of truth가 아니다.

핵심 관계는 다음과 같다.

```text
Code / Tests / Evidence / Git
        │
        │ authoritative truth
        ▼
      Wiki
        │
        │ compressed semantic memory
        ▼
Future agent sessions
```

설계 시 다음 원칙을 가장 중요하게 유지한다.

1. Wiki는 채팅 기록의 요약본이 아니다.
2. Wiki는 저장소에서 다시 알아내기 어렵거나 비용이 큰 지식을 압축해 보존한다.
3. 실제 코드·테스트·실험 결과가 Wiki보다 항상 우선한다.
4. Wiki가 오래될수록 커지는 것이 아니라 **더 정확하고 더 잘 압축되어야 한다.**
5. 매 세션 전체 Wiki를 읽지 않는다.
6. 새 에이전트가 짧은 bootstrap context만으로 프로젝트 상태를 복구할 수 있어야 한다.
7. 특정 AI harness에 종속되는 구현을 피한다.
8. v1에서는 DB, vector DB, embeddings, daemon, MCP server 같은 별도 인프라를 만들지 않는다.
9. Markdown + Git + 작은 deterministic tooling만 사용한다.
10. Wiki 관리 자체가 프로젝트 개발보다 복잡해져서는 안 된다.

## 0.1 적용 범위와 전제

이 시스템은 한 사용자가 여러 머신에서 여러 저장소를 운영하는 환경을 대상으로 한다.

```text
머신 A (macOS) : 여러 머신에서 함께 쓰는 저장소, 개인 프로젝트
머신 B (macOS) : 다수 프로젝트
머신 C (Linux) : 서버 프로젝트
```

전제는 다음과 같다.

1. Wiki는 저장소마다 하나씩 두고, 프로젝트마다 독립적으로 운영한다. 여러 프로젝트를 하나의 Wiki로 관리하지 않는다. 머신 사이에 공유되는 것은 Wiki를 만들고 유지보수하는 skill package뿐이다. Skill은 현재 저장소만 조사하며, 다른 저장소나 다른 머신(SSH 등 원격 접속)을 조사하지 않는다.
2. Git repository를 필수 조건으로 한다 (§23).
3. 같은 저장소를 여러 머신에서 checkout할 수 있다. 이 경우 머신마다 하드웨어와 runtime 상태가 다를 수 있으므로 current 파일을 머신별로 나눌 수 있다 (§14).
4. v1에서 지원하는 harness는 Claude Code, Pi, Codex, Devin이다. 각 머신에는 실제로 설치된 harness에만 adapter를 설치한다 (§4).
5. Skill과 linter는 macOS 전용 명령에 의존하지 않고, Python 3 표준 라이브러리와 Git만 사용한다.
6. Wiki 본문의 언어는 저장소의 규칙을 따른다. 예를 들어 운영 기록을 한국어로 작성하는 저장소라면 Wiki 본문도 한국어로 쓰고, 코드 식별자와 경로는 원문을 유지한다. Frontmatter의 key와 `type`·`status` 값은 언어와 관계없이 영어 token으로 고정한다.
7. 이 문서에 나오는 특정 저장소의 예시(`hosts/` 문서, `upstream-*` 보호 경로 등)는 설명을 위한 것이다. Skill은 특정 저장소의 구조를 가정하지 않고, 각 저장소의 instruction 파일과 구조를 읽어서 적응한다.

이 문서에서 `/wiki-init`, `/wiki-update`라는 표기는 `wiki-init`·`wiki-update` skill을 해당 harness의 native 방식으로 호출한다는 뜻이다. 실제 호출 문법은 harness마다 다를 수 있다 (§4).

---

# 1. 최종 사용자 경험

## 프로젝트 최초 1회

사용자가 프로젝트 root에서 다음을 실행한다.

```text
/wiki-init
```

에이전트는 기존 repository를 조사한다.

```text
Repository tree
README / AGENTS / CLAUDE / docs
build/config files
main implementation
tests
important Git history
existing reports
benchmark/evidence artifacts
```

그 후 현재 프로젝트 상태를 재구성하고 `wiki/`를 생성한다.

예:

```text
wiki/
├── SCHEMA.md
├── index.md
├── overview.md
├── current.md
├── log.md
├── architecture/
├── components/
├── decisions/
├── experiments/
├── runbooks/
└── archive/
```

프로젝트 성격에 따라 필요하지 않은 category는 생략할 수 있다.

여러 머신에서 사용하는 저장소는 `current.md` 대신 `current/<host>.md`를 둘 수 있다 (§14).

완료 후 Wiki integrity를 검사하고 초기 Wiki를 Git에 기록한다.

---

# 2. 이후 일반적인 작업 흐름

새 AI agent session은 다음처럼 동작한다.

```text
New session
    │
    ▼
Read project instructions
    │
    ▼
Read:
wiki/index.md
wiki/overview.md
wiki/current.md  (multi-host: wiki/current/<this-host>.md only)
    │
    ▼
Select only task-relevant Wiki pages
    │
    ▼
Inspect actual source code as necessary
    │
    ▼
Perform requested work
    │
    ▼
Run tests / experiments / validation
    │
    ▼
/wiki-update
    │
    ▼
Reconcile Wiki against repository
    │
    ▼
Lint
    │
    ▼
Git commit
```

중요:

```text
새 session ≠ 이전 conversation 복원

새 session =
    작은 bootstrap Wiki
    +
    필요한 페이지 selective load
    +
    실제 repository inspection
```

세션을 시작할 때 Wiki를 읽는 동작은 skill이 아니라 project instruction 파일의 managed block이 안내한다 (§52). 따라서 사용자가 직접 실행하는 명령은 `/wiki-init`과 `/wiki-update` 두 개뿐이다. Wiki 구조의 유지보수(index 분할, archive, rename 등)도 `/wiki-update`가 담당한다 (§47).

---

# 3. 두 Skill과 공통 Core

가능하면 동일한 규칙을 `/wiki-init`과 `/wiki-update`에 각각 복사하지 않는다.

두 명령을 각각 노출해야 하므로 skill은 두 개로 나누고, 공유 자원은 `core/`에 둔다. Skill package는 독립 Git 저장소 하나로 관리한다.

```text
project-wiki/                  # 독립 Git 저장소 (예: ~/Projects/tools/project-wiki)
├── README.md                  # 설치·사용 방법
├── install.sh                 # 각 harness의 skill 위치에 symlink 생성
├── core/
│   ├── protocol.md            # 두 skill이 공유하는 규칙
│   ├── page-schema.md
│   ├── SCHEMA.template.md     # /wiki-init이 저장소에 설치하는 SCHEMA 원본
│   └── scripts/
│       └── wiki_lint.py
├── wiki-init/
│   ├── SKILL.md               # init workflow
│   └── core -> ../core        # 상대 symlink
└── wiki-update/
    ├── SKILL.md               # update workflow
    └── core -> ../core
```

규칙:

1. 각 skill 고유의 workflow는 해당 skill의 `SKILL.md`에 두고, 두 skill이 공유하는 규칙은 `core/`에 둔다.
2. 각 `SKILL.md`는 약 150줄 이하로 유지한다. 세부 규칙은 필요할 때만 `core/`에서 읽는다.
3. 이 구현 명세 문서는 runtime에 읽지 않는다.
4. Skill을 symlink로 설치하면, `../../core`처럼 경로 문자열을 조합하는 방식이 설치 위치를 기준으로 해석되어 잘못된 위치를 가리킬 수 있다. 따라서 공유 자원은 skill 디렉터리 안의 상대 symlink(`core -> ../core`)로 연결하고, skill은 `<skill-dir>/core/...` 경로만 사용한다.

논리적으로 중요한 것은 구조 자체가 아니라:

```text
wiki-init   ┐
            ├── same canonical protocol
wiki-update ┘
```

가 되도록 하는 것이다.

두 skill에 같은 장문의 규칙을 복제하지 않는다.

---

# 4. Harness Adapter

핵심 Wiki protocol은 특정 agent framework와 무관해야 한다.

구현 에이전트는 현재 환경을 확인하여 해당 환경의 native skill 또는 slash-command mechanism으로 다음 이름을 노출한다.

```text
/wiki-init
/wiki-update
```

가능하다면 skill 이름도 각각:

```text
wiki-init
wiki-update
```

로 한다.

Claude Code, Pi, Codex, Devin 등 환경별 파일 형식은 adapter 역할만 한다.

v1 대상 harness의 skill 위치, 호출 형태, instruction 파일은 다음과 같다. 2026-09-22에 확인했으며, Claude Code·Pi·Devin은 macOS 머신에 설치된 문서와 소스로, Codex는 공식 문서로 확인했다.

| Harness | User skill 위치 | 호출 형태 | Project instruction 파일 |
|---|---|---|---|
| Claude Code | `~/.claude/skills/` | `/wiki-init` | `CLAUDE.md` |
| Pi | `~/.agents/skills/` (또는 `~/.pi/agent/skills/`) | `/skill:wiki-init` | 디렉터리마다 하나만 읽는다: `AGENTS.override.md` → `AGENTS.md` → `CLAUDE.md` 순서로 처음 발견한 파일 |
| Devin CLI | `~/.agents/skills/` (또는 `~/.config/devin/skills/`) | `/wiki-init` | `AGENTS.md`와 `CLAUDE.md`를 모두 읽는다 |
| Codex | `~/.agents/skills/` | `$wiki-init` 또는 `/skills` | `AGENTS.override.md` → `AGENTS.md`. `CLAUDE.md`는 `project_doc_fallback_filenames`에 등록했을 때만, `AGENTS.md`가 없는 디렉터리에서 읽는다 |

설치 규칙:

1. 각 머신에 skill package를 clone하고, `install.sh`로 symlink를 만든다. 설치 대상은 머신당 두 곳이다: `~/.agents/skills/`(Pi, Devin, Codex가 함께 사용)와 `~/.claude/skills/`(Claude Code).
2. `install.sh`는 기존 파일이나 디렉터리가 같은 이름으로 있으면 덮어쓰지 않고 중단한다.
3. 설치한 뒤에는 그 머신에 설치된 harness마다 skill이 인식되는지, 그리고 `<skill-dir>/core/scripts/wiki_lint.py`가 실행되는지 확인한다. Harness 버전에 따라 skill 위치가 달라질 수 있으므로(예: 구버전 Codex의 `~/.codex/skills/`), 인식되지 않으면 그 harness의 문서를 다시 확인한다.
4. Skill을 갱신할 때는 각 머신에서 skill package 저장소를 `git pull`한다. 프로젝트마다 skill을 복사하지 않는다.
5. 위 표는 확인한 사실만 적는다. 추측한 호출 문법이나 경로를 문서나 skill에 적지 않는다.
6. Skill은 user 수준에만 설치한다. Codex와 Pi는 저장소 안의 `.agents/skills/`도 읽지만, `/wiki-init`은 저장소의 `.agents/skills/`나 `.claude/skills/`에 skill을 만들지 않는다. 그렇게 하면 프로젝트마다 skill 사본이 생기기 때문이다. 따라서 §30에서 commit하는 "adapter 파일"은 instruction 파일의 managed block 수정뿐이다.
7. 초기 검증에서는 macOS 머신 2대와 Linux 머신 1대에 이 구조로 설치했고, 모든 머신에서 네 harness가 두 skill을 인식하는 것을 확인했다(Codex 0.155.1도 `~/.agents/skills/`를 읽는다).

Instruction 파일을 읽는 방식이 harness마다 다르기 때문에 §52의 managed block 배치 규칙을 따른다.

환경별 command 파일에는 장문의 Wiki 규칙을 복제하지 않는다.

예:

```text
Execute the Project Wiki initialization protocol.
Read the shared Project Wiki protocol first.
```

정도의 thin wrapper로 유지한다.

---

# 5. Repository 내 Wiki 구조

기본 구조:

```text
wiki/
├── SCHEMA.md
├── index.md
├── overview.md
├── current.md
├── log.md
│
├── architecture/
├── components/
├── decisions/
├── experiments/
├── runbooks/
└── archive/
```

프로젝트에 맞지 않는 category는 생성하지 않아도 된다.

반대로 실제 프로젝트에서 반복적으로 필요한 명확한 category가 있으면 추가할 수 있다.

예:

```text
wiki/
├── models/
├── kernels/
├── protocols/
├── deployment/
└── benchmarks/
```

단, category를 즉흥적으로 계속 늘리지 않는다.

새 category를 만들기 전에 기존 category로 표현할 수 있는지 판단한다.

---

# 6. `wiki/SCHEMA.md`

이 파일은 repository 내 Wiki의 canonical operating contract다.

에이전트별 `AGENTS.md`, `CLAUDE.md`, command skill 등에 Wiki 규칙 전체를 반복해서 쓰지 않는다.

그 대신:

```text
wiki/SCHEMA.md
```

를 canonical schema로 사용한다.

SCHEMA에는 최소한 다음이 들어가야 한다.

```text
Purpose
Authority hierarchy
Page taxonomy
Page format
Update rules
Evidence rules
Context-loading rules
Anti-bloat rules
Lint rules
Git rules
Schema version
Wiki language
Size budgets
Host list and hostname mapping (여러 머신에서 사용하는 저장소만, §14)
```

`/wiki-update`는 일반적인 프로젝트 작업 때문에 `SCHEMA.md`를 자동 수정해서는 안 된다.

`/wiki-update`는 SCHEMA에 기록된 schema version과 설치된 skill의 version을 비교한다. 두 version이 다르면 사용자에게 알리기만 하고, SCHEMA를 자동으로 갱신하지 않는다. 저장소가 많아지면 저장소마다 다른 version의 SCHEMA가 남을 수 있기 때문에, 이 비교로 차이를 드러낸다.

SCHEMA 변경은 Wiki 시스템 자체의 정책 변경일 때만 한다.

---

# 7. Source-of-Truth hierarchy

모든 skill에 다음 hierarchy를 명시한다.

```text
1. Actual implementation
2. Tests and executable validation
3. Benchmark / experiment artifacts
4. Git history
5. Maintainer-authored project documentation
6. Wiki
7. Current conversation
```

충돌하는 경우 높은 단계가 우선한다.

5단계의 "Maintainer-authored"는 사람이 작성하거나 검토한 문서를 뜻한다. 이전 에이전트가 작성한 `docs/` 보고서, 인계 문서, project skill은 6단계(Wiki)와 같은 신뢰도로 취급하고, 저장소와 대조하기 전에는 authority로 인정하지 않는다.

### Runtime observation

운영 저장소에서는 서비스 상태, 설치된 모델 파일, launchd·systemd 상태 같은 runtime 사실도 중요한 evidence다. 이런 사실은 Git 변경이 없어도 바뀌기 때문에 다음 규칙을 따른다.

- runtime 사실에는 관측 날짜와 확인 방법을 함께 적는다.
- runtime 사실은 그 사실을 관측한 머신의 current 파일에만 기록한다 (§14).
- 관측 날짜가 오래된 runtime 사실은 `/wiki-update`의 semantic lint에서 재확인 대상으로 분류한다.

```text
- 서버는 떠 있지만 로드된 모델이 0개다. (확인 2026-09-22, `curl -sf http://127.0.0.1:8080/v1/models`)
```

예:

```text
wiki/current.md:
    "FP8 KV cache is implemented"

actual code:
    TODO only

→ Wiki가 틀린 것이다.
→ 코드를 Wiki에 맞추지 않는다.
→ Wiki를 수정한다.
```

절대 다음 행동을 하지 않는다.

```text
Wiki 내용과 일치하도록 코드를 변경
```

Wiki는 implementation을 설명해야 한다.

Implementation이 Wiki를 만족시키기 위해 존재하지 않는다.

---

# 8. 무엇을 Wiki에 저장할 것인가

Wiki에 저장해야 하는 정보는 **미래 에이전트가 다시 알아내기 비싸거나 위험한 정보**다.

대표적으로:

```text
Architecture rationale

Important invariants

Hard constraints

Non-obvious implementation behavior

Interfaces between subsystems

Why implementation A was chosen over B

Important rejected approaches and why

Verified experiment conclusions

Performance characteristics that affect design

Compatibility constraints

Known blockers

Important unresolved questions

Repeatable operational procedures

Current implementation maturity
```

---

# 9. 무엇을 저장하지 않을 것인가

다음은 기본적으로 Wiki에 저장하지 않는다.

```text
Chat transcript

Long session summary

Every code edit

Every commit

Every debugging attempt

Temporary hypotheses

One-off shell commands

Things trivially obvious from source code

Every class/function/file

Generic programming knowledge

Plans that were never executed

Speculation stated as fact
```

예:

나쁜 Wiki:

```text
Today we changed loader.py.
Then an error occurred.
We changed line 53.
Then test A failed.
After that we tried another implementation.
```

좋은 Wiki:

```text
The loader intentionally keeps expert weights in their checkpoint
layout rather than transposing them at load time.

Reason:
- avoids duplicate resident memory
- the fused kernel consumes checkpoint-native layout directly

Relevant implementation:
- src/runtime/loader.py
- src/kernels/moe.metal

Related decision:
- decisions/0012-checkpoint-native-weight-layout.md
```

---

# 10. Page Creation Rule

새 페이지를 만드는 것은 기본 동작이 아니다.

먼저 기존 페이지에 정보를 합칠 수 있는지 판단한다.

새 페이지는 다음 조건 중 하나 이상을 만족해야 한다.

```text
The concept has independent long-term importance.

Future tasks are likely to retrieve it independently.

It contains substantial rationale or evidence.

It would make an existing page too broad or difficult to navigate.

It represents a durable architectural decision.

It represents an experiment whose result affects later design.

It represents a repeatable operational procedure.
```

다음 상황에서는 새 페이지를 만들지 않는다.

```text
3-5 bullet 정도면 기존 페이지에 들어갈 수 있음

특정 파일 하나를 설명하는 것뿐임

일회성 디버깅 기록임

현재 세션에서만 필요한 계획임
```

---

# 11. `index.md`

`index.md`는 Wiki 전체를 agent가 매번 읽지 않게 하기 위한 router다.

예:

```markdown
# Project Wiki

## Start Here

- [Overview](overview.md) — Project goals, scope, and hard constraints.
- [Current State](current.md) — Current implementation status, blockers, and next work.

## Architecture

- [Runtime Architecture](architecture/runtime.md) — Runtime data flow and subsystem boundaries.
- [SSD Offload](architecture/ssd-offload.md) — Weight residency and offload architecture.

## Components

- [Model Loader](components/model-loader.md) — Checkpoint loading and tensor layout.
- [KV Cache](components/kv-cache.md) — Cache representation and lifecycle.

## Decisions

- [Checkpoint-native Layout](decisions/0012-checkpoint-native-layout.md) — Why runtime retains the original weight layout.

## Experiments

- [64Ki Prefill Baseline](experiments/64ki-prefill-baseline.md) — Verified baseline and interpretation.
```

각 entry는 반드시:

```text
link
+
one-line purpose/summary
```

를 포함한다.

index 자체가 상세 문서가 되어서는 안 된다.

---

# 12. Wiki가 커졌을 때 Index Scaling

처음에는 단일 `index.md`를 사용한다.

다음 중 하나가 발생하면 category index를 도입할 수 있다.

```text
index.md가 지나치게 길어짐

80~100개 이상의 substantive pages

agent가 index를 읽는 것만으로 context 비용이 커짐
```

그 경우:

```text
wiki/index.md

wiki/architecture/index.md
wiki/components/index.md
wiki/decisions/index.md
wiki/experiments/index.md
```

구조로 확장할 수 있다.

top-level `index.md`는 category router가 된다.

하지만 v1부터 미리 이 구조를 강제하지 않는다.

---

# 13. `overview.md`

`overview.md`는 프로젝트에서 가장 안정적인 장기 context다.

포함할 내용:

```text
Project purpose

Primary user-visible goal

Non-goals

Hard technical constraints

Canonical external/reference implementation if any

High-level architecture

Terminology

Quality requirements

Major design principles
```

다음은 넣지 않는다.

```text
오늘의 작업

최근 commit 목록

세부 TODO

transient blocker
```

`overview.md`는 자주 바뀌지 않아야 한다.

Project purpose, goals, non-goals는 사용자와 maintainer가 정한 내용을 기록한다. 현재 구현만 보고 목표를 추론하지 않는다. 출처가 불분명한 목표는 `Unknown`으로 표시하고 사용자에게 확인한다.

여러 머신에서 사용하는 저장소에서는 머신에 관계없이 성립하는 상태(공통 패치의 방향, 프로젝트 전체의 제약 등)도 `overview.md` 또는 해당 architecture·decision 페이지에 둔다 (§14).

---

# 14. `current.md`

새 agent session bootstrap에서 가장 중요한 파일이다.

항상 작고 최신이어야 한다.

권장 구조:

```markdown
# Current Project State

## Working

...

## Partially Implemented

...

## Not Yet Implemented

...

## Current Blockers

...

## Active Risks / Unknowns

...

## Next Logical Work

...
```

목표:

```text
약 2,000 tokens 이하 (영어 기준 약 1,500 words)
```

한국어 본문은 단어 수와 token 수의 비율이 영어와 다르므로, 단어 수가 아니라 token 추정치를 기준으로 한다. 예산은 SCHEMA에 기록하고, linter는 추정치를 보고하며 예산을 넘으면 warning을 낸다 (§46).

`current.md`를 chronological log로 만들지 않는다.

`current.md`는 이전 세션이 다음 세션에 남기는 인계 문서(handoff)가 아니다. `/wiki-update`가 매번 저장소와 runtime을 대조해서 다시 계산하는 검증된 snapshot이다. 작업 진행 기록은 계속 Git commit message가 담당한다.

작업이 끝나면:

```text
resolved blocker → 삭제 또는 관련 canonical page로 이동
finished task → Working 또는 architecture page에 반영
old next step → 제거
```

한다.

즉 `current.md`는 누적되는 파일이 아니라 **계속 압축되는 현재 상태 snapshot**이다.

## 여러 머신에서 사용하는 저장소

기본값은 `wiki/current.md` 하나다. 한 머신에서만 사용하는 저장소는 이 기본값을 사용한다.

같은 저장소를 여러 머신에서 checkout하고, 머신마다 하드웨어나 runtime 상태가 다른 경우에는 머신별 current 파일을 둔다.

```text
wiki/current/mbp.md
wiki/current/studio.md
```

규칙:

1. `/wiki-init`은 사용자에게 확인한 뒤에만 이 구조를 만든다.
2. SCHEMA에 host 목록과 hostname 대응표를 선언한다. 예를 들어 `hostname -s` 결과를 `mbp`, `studio` 같은 이름에 대응시킨다. 다른 host의 값은 사용자에게 받고, 원격 접속으로 알아내지 않는다. macOS 전용 명령(`scutil` 등)은 사용하지 않는다.
3. 현재 hostname이 대응표에 없으면 새 host 파일을 만들거나 기존 파일에 쓰지 않는다. 작업을 중단하고 사용자에게 어느 host인지 묻는다.
4. 에이전트는 자기 머신의 current 파일만 읽고 갱신한다. 다른 머신의 current 파일은 수정하지 않는다 (§61). 각 머신에서 검증할 수 있는 것은 자기 머신의 runtime 상태뿐이기 때문이다.
5. 머신에 관계없이 성립하는 상태는 `overview.md` 또는 해당 architecture·decision 페이지에 둔다.
6. 저장소에 머신별 설정 문서가 이미 있으면(예: `hosts/<host>/README.md`) 설정값의 정본은 그 문서로 유지한다. Current 파일은 현재 상태(동작하는 기능, blocker, 다음 작업)만 담고, 설정값은 복사하지 않고 링크한다.

7. 머신에 따라 달라지는 사실(모델 파일 경로, 구동 가능한 모델, 메모리 한도, 서비스 이름, 벤치마크 수치 등)에는 공유 페이지에서도 반드시 host 이름을 붙인다. Host가 적혀 있지 않은 서술은 모든 host에 공통인 사실로 간주한다. 공유 페이지에 있는 다른 host의 사실은 이 host에서 검증할 수 없으므로 수정하지 않는다.

정리하면 여러 머신 저장소의 Wiki는 일부를 공유하고 일부를 분리한다.

| 구분 | 내용 | 위치 |
|---|---|---|
| 공유 | 모든 host에 공통인 지식: 설계 결정, 패치 계보, 운영 규칙, 연구 결론 | `overview.md`, `architecture/`, `components/`, `decisions/` 등 |
| 분리 | host별 현재 상태: 로드된 모델, 모델 파일 경로, blocker, 다음 작업 | `current/<host>.md` |
| 공유하되 host 명시 | host에 따라 결과가 다른 기록: 벤치마크, 실험 결과 | `experiments/` 등 (측정 host와 하드웨어 필수) |

이 문서의 다른 절에서 `current.md`라고 쓴 부분은, 여러 머신에서 사용하는 저장소의 경우 "자기 머신의 `current/<host>.md`"로 읽는다.

---

# 15. Architecture Page

권장 template:

```markdown
---
title: SSD Offload Architecture
type: architecture
status: current
updated: YYYY-MM-DD
---

# SSD Offload Architecture

## Purpose

## Current Design

## Invariants

## Data Flow

## Important Trade-offs

## Relevant Implementation

- `src/...`
- `src/...`

## Validation

## Known Limitations

## Related Decisions

## Related Pages
```

페이지는 코드 문서 자동 생성물이 아니다.

구조와 rationale을 설명해야 한다.

---

# 16. Component Page

권장 template:

```markdown
---
title: KV Cache
type: component
status: current
updated: YYYY-MM-DD
---

# KV Cache

## Responsibility

## Interface

## Current Implementation

## Important Invariants

## Relevant Paths

## Tests / Validation

## Known Limitations

## Related Pages
```

---

# 17. Decision Page

중요한 design decision은 ADR과 유사하게 기록한다.

파일 이름 예:

```text
decisions/0012-checkpoint-native-layout.md
```

template:

```markdown
---
title: Keep Checkpoint-native Weight Layout
type: decision
status: accepted
updated: YYYY-MM-DD
---

# Keep Checkpoint-native Weight Layout

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

상태:

```text
proposed
accepted
rejected
superseded
```

중요:

`git log`만으로 알아낼 수 없는 **왜**를 보존하는 것이 목적이다.

---

# 18. Experiment Page

모든 benchmark를 Wiki page로 만들지 않는다.

미래 설계 판단에 영향을 주는 experiment만 기록한다.

template:

```markdown
---
title: 64Ki Prefill Baseline
type: experiment
status: completed
updated: YYYY-MM-DD
---

# 64Ki Prefill Baseline

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

반드시:

```text
measurement
```

와

```text
interpretation
```

을 분리한다.

예:

```text
Measured:
412 tok/s

Interpretation:
The current path appears memory-bandwidth limited.
```

두 번째 내용이 직접 증명되지 않았다면:

```text
Hypothesis:
The current path may be memory-bandwidth limited.
```

로 기록한다.

측정한 머신(host)과 하드웨어는 반드시 기록한다. 머신마다 하드웨어가 다르면 같은 실험을 재현할 수 없으므로, 다른 머신에서 검증하기 전에는 결과를 일반화하지 않는다.

결과물이 Git에 남지 않는 경로(예: gitignored `results/`)에 있으면, 그 결과물은 다른 checkout에서 볼 수 없고 언제든 삭제될 수 있다. 이 경우 핵심 측정값, 실행 명령, source revision을 페이지에 직접 기록한다.

---

# 19. Runbook Page

반복 수행하는 작업을 저장한다.

예:

```text
How to run reference benchmark

How to regenerate converted checkpoint

How to deploy server

How to reproduce validation

How to recover corrupted cache
```

template:

```markdown
# Runbook: Reference Benchmark

## Purpose

## Preconditions

## Procedure

## Expected Output

## Verification

## Failure Modes

## Relevant Files
```

---

# 20. Archive

정보를 가능한 한 삭제하지 않되, 오래된 정보를 현재 문서에 계속 남겨두지도 않는다.

정보가 완전히 superseded 되었지만 역사적 가치가 있으면:

```text
wiki/archive/
```

로 이동할 수 있다.

또는 decision page의 status를:

```text
superseded
```

로 바꾼다.

현재 agent bootstrap에서는 archive를 읽지 않는다.

archive는 필요할 때만 조회한다.

---

# 21. `log.md`

`log.md`는 상세 세션 기록이 아니다.

Wiki가 언제 어떤 source state를 기반으로 갱신되었는지를 남기는 작은 append-only audit trail이다.

예:

```markdown
## [2026-09-22] update | KV cache implementation

Host: mbp
Source HEAD: abc1234
Changes:
- Updated `components/kv-cache.md`
- Added `decisions/0017-int4-cache-layout.md`
- Updated `current.md`

Validation:
- unit tests passed
- 32Ki smoke benchmark passed

Open:
- 64Ki performance validation remains
```

모든 entry에는 `Source HEAD: <sha>` 줄이 반드시 있어야 한다. `/wiki-update`는 이 값을 다음 update window의 anchor로 사용한다 (§33). `Host:` 줄은 여러 머신에서 사용하는 저장소에서만 기록한다.

여러 머신에서 동시에 append하여 merge 충돌이 생기면, 양쪽 entry를 모두 보존하고 날짜순으로 정렬한다.

한 entry는 가능한 한 짧게 유지한다.

권장:

```text
5~15 lines
```

금지:

```text
전체 세션 요약
대화 복사
모든 수정 파일 나열
```

일반 session bootstrap에서는 `log.md` 전체를 읽지 않는다.

최근 history가 필요할 경우에만 tail을 읽는다.

예:

```bash
tail -n 100 wiki/log.md
```

---

# 22. Wiki Claims의 정확성

중요한 사실에는 가능한 경우 근거 위치를 남긴다.

예:

```markdown
Relevant implementation:
- `src/cache/kv_cache.py`

Validation:
- `tests/test_kv_cache.py`
- `reports/kv-cache-64k.json`
```

Wiki에서 근거 없는 확정 표현을 생성하지 않는다.

확실하지 않다면 명시한다.

```text
Unknown

Not yet verified

Hypothesis

Partially validated
```

Wiki에 추측을 사실처럼 저장하면 이후 agent가 그것을 authoritative context로 재사용하므로 특히 위험하다.

---

# 23. `/wiki-init` 상세 동작

## Phase 1 — Preconditions

먼저 repository root를 결정한다.

예:

```bash
git rev-parse --show-toplevel
```

Git repository가 아니면 작업을 중단하고 사용자에게 `git init`을 제안한다. Update window, 안전한 commit, 동시성 제어가 모두 Git에 의존하므로, v1에서는 Git 없이 동작하는 모드를 지원하지 않는다.

이어서 project instruction 파일(`AGENTS.md`, `CLAUDE.md` 등)을 읽고, 보호 경로와 Wiki와 충돌하는 정책이 있는지 확인한다 (§30, §52).

---

# 24. `/wiki-init` — Existing Wiki Detection

다음을 검사한다.

```text
wiki/
wiki/index.md
wiki/overview.md
wiki/current.md
wiki/SCHEMA.md
```

이미 Project Wiki가 존재하면 destructive reinitialization을 하지 않는다.

기본 동작:

```text
Validate existing wiki
Create only missing mandatory files
Run lint
Report "already initialized"
```

기존 Wiki를 모두 다시 생성하지 않는다.

기존의 전혀 다른 문서 시스템을 자동 migration 하지 않는다.

---

# 25. `/wiki-init` — Repository Inventory

전체 repository를 무조건 읽지 않는다.

우선:

```bash
git ls-files
```

를 사용해 tracked files를 조사한다.

다음은 기본적으로 제외한다.

```text
.git/
node_modules/
vendor/
dist/
build/
cache/
generated/
large model weights
binary artifacts
temporary benchmark output
```

`.gitignore`도 존중한다.

Project instruction이 보호 대상으로 지정한 경로(예: 사용자 자산인 독립 Git 저장소 `upstream-*` clone)는 inventory에서 제외한다.

`git ls-files`는 tracked 파일만 보여 준다. Git에 추적되지 않는 에이전트 지식 저장소(project `.claude/skills/` 등)는 §27에 따라 별도로 확인한다.

초기 탐색 순서는 대략 다음과 같다.

```text
1. root files
2. README
3. AGENTS / CLAUDE / project instructions
4. docs
5. package/build/config
6. source tree structure
7. tests
8. important execution entry points
9. reports/evidence
10. Git history
```

---

# 26. `/wiki-init` — Progressive Inspection

대형 repository에서 모든 파일을 읽지 않는다.

다음 순서로 progressive discovery한다.

### Pass A — Topology

이해해야 할 것:

```text
어떤 subsystem이 존재하는가?
어디가 entry point인가?
tests는 어디 있는가?
evidence/report는 어디 있는가?
```

### Pass B — Architecture

핵심 interface와 data flow를 조사한다.

### Pass C — Current State

실제 구현 여부를 조사한다.

```text
implemented
partial
stub
TODO
disabled
experimental
```

등을 구분한다.

### Pass D — History

필요할 경우 Git history를 조사하여 코드만으로 알기 어려운 이유를 복원한다.

예:

```bash
git log --oneline --decorate -n 100
git log -- <important-file>
git blame <important-file>
```

history 전체를 무조건 읽지 않는다.

---

# 27. `/wiki-init` — Existing Documentation의 취급

기존:

```text
README
docs/
reports/
design documents
handoff documents
```

는 유용한 source지만 무조건 사실이라고 가정하지 않는다.

가능하면 actual implementation과 비교한다.

다음 상태를 구분한다.

```text
Confirmed by implementation

Documentation-only claim

Outdated

Unknown
```

## 기존 문서·지식 저장소와의 관계

1. 하나의 사실은 정본 위치를 한 곳만 가진다. 기존 문서가 어떤 사실의 정본이면(예: 머신별 운영값을 정리한 `hosts/<host>/README.md`) Wiki는 그 내용을 복사하지 않고 링크한다.
2. `docs/`의 상세 연구·벤치마크 보고서는 evidence로 계속 사용한다. Wiki 페이지는 결론, 해석, 설계 영향만 압축하고 해당 보고서를 링크한다.
3. 이전 에이전트가 작성한 문서와 skill은 Wiki와 같은 신뢰도로 취급한다 (§7).
4. Git에 추적되지 않는 에이전트 지식 저장소(project `.claude/skills/`, harness의 auto-memory 등)도 조사 후보로 사용하되 반드시 검증한다. 그런 경로는 다른 checkout에 존재하지 않으므로, Wiki가 evidence로 참조하지 않는다.
5. `/wiki-init`은 조사 결과로 source inventory를 작성하여 사용자에게 보고한다.
   - 존재하지 않는 파일을 가리키는 참조
   - 여러 문서에 중복된 서술
   - Wiki로 이전할 후보 (instruction 파일에 섞인 상태 서술, untracked skill에 남은 유효한 결론 등)
6. 이전은 제안만 한다. 기존 문서나 skill을 수정·삭제하는 작업은 사용자가 승인한 뒤에만 실행한다.

---

# 28. `/wiki-init` — Initial Wiki Synthesis

Repository inspection이 충분히 끝난 뒤:

```text
overview.md
current.md
index.md
SCHEMA.md
```

를 생성한다.

그리고 필요할 때만:

```text
architecture/*
components/*
decisions/*
experiments/*
runbooks/*
```

를 만든다.

초기 Wiki를 만들기 위해 source file마다 page 하나를 생성해서는 안 된다.

Wiki 구조는 conceptual structure를 반영해야 한다.

---

# 29. `/wiki-init` — Initial Quality Check

생성 후 다음을 검사한다.

```text
Does every indexed page exist?

Does every substantive page appear in index?

Are there broken relative links?

Are important architecture claims supported?

Does current.md match actual implementation?

Are TODOs being mistaken for completed features?

Are tests/results represented accurately?

Are duplicated pages present?

Is current.md concise?

Is overview.md stable rather than session-oriented?
```

---

# 30. `/wiki-init` — Git Behavior

초기화 전:

```bash
git status --short
```

를 검사한다.

기존 사용자 변경사항을 절대 덮어쓰지 않는다.

다음 command를 금지한다.

```bash
git reset --hard
git checkout -- .
git clean -fd
git add -A
```

기본적으로 Wiki와 Wiki adapter에서 자신이 만든 파일만 명시적으로 stage한다.

단, `git add wiki/` 다음에 `git commit`을 실행하면 사용자가 이미 stage해 둔 다른 파일까지 commit에 포함된다. 따라서 다음 순서를 따른다.

```bash
git diff --cached --name-only                              # 사용자가 미리 stage한 파일 확인
git add wiki/ <adapter files>
git commit -m "docs(wiki): ..." -- wiki/ <adapter files>   # pathspec commit
```

Pathspec을 지정한 commit은 지정한 경로의 변경만 기록한다. 사용자가 미리 stage한 다른 파일은 commit되지 않고 staged 상태로 남는다(2026-09-22 테스트 저장소에서 확인).

Commit하기 전에 Git이 무시하는 Wiki 파일이 없는지 확인한다.

```bash
git ls-files --others --ignored --exclude-standard -- wiki/   # 출력이 있으면 무시되는 파일이 있다
```

`.gitignore`에 `*token*`, `*secret*` 같은 넓은 패턴이 있으면 `wiki/components/token-logging.md` 같은 페이지가 무시된다. 이때 `git add wiki/`는 경고 없이 그 파일을 건너뛴다. 무시되는 Wiki 파일이 있으면 페이지 이름을 바꾸거나 사용자에게 알린다. `.gitignore`는 자동으로 수정하지 않는다.

commit message 예:

```text
docs(wiki): initialize project memory
```

기존 unrelated dirty files를 포함하지 않는다.

---

# 31. `/wiki-update` 목적

`/wiki-update`는:

```text
"이번 대화를 요약하라"
```

가 아니다.

정확한 정의는:

```text
Reconcile the durable project Wiki with the actual repository state
after the current work unit.
```

이다.

이 정의에는 Wiki 구조의 유지보수도 포함된다 (§47). 구조 유지보수를 담당하는 별도 명령은 만들지 않는다.

---

# 32. `/wiki-update` 입력 Source

다음 정보를 사용한다.

```text
Current Git state

Changes since the previous Wiki update

Current source implementation

Tests

Experiment / benchmark results

Existing Wiki

Current conversation only as a navigation hint
```

Conversation에서 주장된 내용은 repository/evidence와 충돌하면 버린다.

---

# 33. Update Window 결정

가능하면 마지막 Project Wiki update 이후 변경만 조사한다.

Anchor는 다음 순서로 결정한다.

1. 마지막 `log.md` entry에 기록된 `Source HEAD`를 사용한다. 이 SHA가 현재 HEAD의 조상인지 확인한다.

   ```bash
   git merge-base --is-ancestor <source-head> HEAD
   ```

2. 해당 SHA가 사라졌다면(rebase, squash 등), `log.md`를 마지막으로 수정한 commit을 사용한다.

   ```bash
   git log -1 --format=%H -- wiki/log.md
   ```

3. 둘 다 없으면 broader inspection을 수행한다.

`git log -- wiki/`처럼 Wiki 디렉터리 전체의 마지막 commit을 anchor로 쓰지 않는다. 사람이 Wiki를 직접 수정한 commit이 anchor가 되면, 그 사이의 source 변경이 조사 범위에서 빠지기 때문이다.

그 후:

```bash
git diff <anchor>..HEAD
```

를 기준으로 변화 범위를 좁힌다.

Wiki 자체 변화는 source change detection에서 제외할 수 있다.

예:

```text
wiki/**
```

exclude.

최초 update라 anchor가 없으면 broader inspection을 수행한다.

---

# 34. Working Tree 처리

먼저:

```bash
git status --short
```

를 확인한다.

세 가지 상태를 구분한다.

### A. Source changes already committed

가장 이상적이다.

Wiki를 갱신하고 Wiki commit을 만든다.

### B. Current task의 source changes가 아직 uncommitted

현재 agent가 이번 work unit에서 자신이 변경한 파일 집합을 명확히 알고 있고, unrelated changes가 없다고 확인 가능한 경우에만 source changes와 Wiki를 함께 final commit할 수 있다.

### C. Dirty tree에 unrelated/pre-existing changes가 섞여 있음

자동으로 전부 commit하면 안 된다.

특히 금지:

```bash
git add -A
git commit -am ...
```

scope를 증명할 수 없으면 unrelated changes를 건드리지 않는다.

Wiki가 uncommitted source를 durable truth로 기록한 뒤 source가 discard되는 상황도 피해야 한다.

따라서 ambiguous dirty state에서는 안전성을 우선한다.

### 판단 기준

- Update window와 관계없는 untracked 파일, nested Git repository(예: 사용자 자산인 `upstream-*` clone), 사용자가 작업 중인 다른 파일은 ambiguous 상태로 보지 않는다. 이런 파일은 건드리지 않고 그대로 두며, Wiki commit은 §30의 pathspec commit으로 진행한다.
- 판단이 필요한 경우는 Wiki가 서술해야 할 source 파일 자체에 미커밋 변경이 있을 때뿐이다. 이때는 커밋된 상태만 Wiki에 반영하거나, 사용자에게 먼저 commit할지 묻는다.

이 기준이 없으면, 사용자 자산이 항상 untracked로 표시되는 저장소에서는 update가 매번 중단된다.

---

# 35. 권장 Commit Model

가장 안전한 기본 workflow는:

```text
agent completes implementation
        ↓
implementation commit
        ↓
/wiki-update
        ↓
wiki reconciliation
        ↓
wiki commit
```

즉 source commit과 Wiki memory commit을 분리한다.

예:

```text
feat(runtime): add int4 kv cache path

docs(wiki): update project memory after kv cache work
```

장점:

```text
Wiki update window가 명확함
source state가 durable함
unrelated dirty changes를 실수로 commit할 위험이 낮음
Git history에서 memory update를 쉽게 찾을 수 있음
```

현재 harness가 명확한 work-unit change set을 보존하는 경우에는 하나의 commit으로 합치는 mode를 지원해도 되지만 v1의 기본값으로 만들 필요는 없다.

---

# 36. `/wiki-update` — Change Discovery

변경된 파일을 찾는다.

예:

```bash
git diff --name-status <anchor>..HEAD
```

그리고 필요한 경우:

```bash
git diff <anchor>..HEAD -- <file>
```

를 확인한다.

모든 diff를 같은 중요도로 보지 않는다.

분류한다.

```text
Semantic implementation change

Refactor without behavioral change

Test change

Configuration change

Documentation-only change

Experiment/evidence addition

Generated artifact

Formatting
```

---

# 37. Wiki Impact Mapping

변경 file → Wiki page를 찾는다.

다음 방법을 조합한다.

1. Wiki에서 changed path 검색
2. index에서 관련 subsystem 확인
3. component / architecture 관계 확인
4. 새 concept인지 판단
5. tests/evidence가 어떤 feature를 검증하는지 확인

예:

```text
src/runtime/cache.py changed
tests/test_cache.py changed

→ components/kv-cache.md
→ architecture/runtime.md
→ maybe current.md
→ possibly a decision page
```

전체 Wiki를 무조건 rewrite하지 않는다.

---

# 38. Durable Knowledge Extraction

이번 변경에서 다음 질문을 한다.

```text
무엇이 이제 실제로 가능해졌는가?

이전 Wiki에서 틀리게 된 내용은 무엇인가?

중요한 architecture가 바뀌었는가?

미래 agent가 알아야 할 새로운 invariant가 생겼는가?

중요한 design decision이 내려졌는가?

실험 결과로 기존 가설이 확인/반박되었는가?

새 blocker가 생겼는가?

기존 blocker가 해결되었는가?

재현 가능한 operational procedure가 생겼는가?
```

이 중 아무 것도 없다면 substantive Wiki update는 최소화한다.

---

# 39. Semantic Update Rule

기존 page를 전체 재작성하지 않는다.

원칙:

```text
minimum necessary edit
```

즉:

```text
현재 사실과 충돌하는 부분 수정
새로 durable해진 내용 추가
obsolete detail 제거 또는 archive
cross-reference 갱신
```

한다.

관련 없는 wording/style을 매번 바꾸지 않는다.

Wiki diff가 작고 검토 가능해야 한다.

---

# 40. Decision Detection

다음과 같은 변화가 있으면 decision page가 필요한지 검토한다.

```text
A 대신 B를 사용하기로 함

data format을 고정함

compatibility policy를 결정함

quality/performance trade-off를 의도적으로 선택함

important workaround를 permanent architecture로 채택함

기존 architecture를 폐기함
```

단순 구현 선택 하나하나에 ADR을 만들지 않는다.

---

# 41. Experiment Detection

다음 조건이면 experiment page를 고려한다.

```text
결과가 이후 design choice에 영향을 줌

baseline으로 계속 참조될 가능성이 높음

특정 hypothesis를 확인/반박함

재현 조건이 중요함

costly experiment라 반복하기 싫음
```

단순 smoke test는 experiment page가 아니다.

---

# 42. `current.md` Update Algorithm

항상 마지막에 현재 상태를 다시 계산한다.

단순 append를 금지한다.

작업 후:

```text
Working

Partially Implemented

Not Implemented

Blockers

Unknowns

Next Work
```

각 section을 실제 상태에 맞게 재조정한다.

예:

이전:

```text
## Current Blockers
- INT4 cache write kernel is missing.
```

이번에 구현 및 validation 완료:

```text
→ blocker 제거
→ Working에 INT4 cache path 반영
→ component page에 details 기록
```

지난 기록을 current.md에 남겨두지 않는다.

Git history가 과거를 보존한다.

---

# 43. `overview.md` Update Rule

다음에 해당하지 않으면 수정하지 않는다.

```text
project scope changed

hard constraint changed

high-level architecture changed

canonical reference changed

major subsystem introduced/removed
```

작은 feature가 추가될 때마다 overview를 수정하지 않는다.

---

# 44. `index.md` Update Rule

다음이 발생하면 갱신한다.

```text
new page

renamed page

archived page

summary meaningfully changed

category added/removed
```

index entry가 actual page set과 일치해야 한다.

---

# 45. `log.md` Update

마지막에 compact entry 하나를 append한다.

예:

```markdown
## [2026-09-22] update | SSD prefetch scheduler

Host: studio
Source HEAD: def456 (reviewed from abc123)

Wiki:
- updated architecture/ssd-offload.md
- updated components/prefetcher.md
- updated current.md

Validation:
- scheduler unit tests passed

Open:
- 64Ki steady-state benchmark remains
```

conversation summary를 쓰지 않는다.

---

# 46. Deterministic Lint

가능하면 작은 script를 제공한다.

```text
scripts/wiki_lint.py
```

Python standard library만으로 구현하는 것을 우선한다.

검사 대상:

```text
Broken relative Markdown links

Index entries pointing to missing pages

Substantive pages missing from index

Duplicate index entries

Duplicate page titles where problematic

Invalid page metadata if metadata is used

References to obviously missing repository paths

Orphan pages

Illegal path depth if schema restricts it

Wiki files ignored by .gitignore (structural error, §30)

References to untracked or gitignored paths (warning, §27)

Bootstrap size budget report (warning, §14, §50)
```

script는 수정 가능한 safe issue에 대해서만 auto-fix를 선택적으로 할 수 있다.

semantic contradiction은 script가 판단하지 않는다.

---

# 47. Semantic Lint

LLM이 추가로 검사한다.

```text
Wiki vs actual code contradiction

Stale implementation status

Old blocker already resolved

Same concept described inconsistently

Superseded architecture presented as current

Unsupported factual claim

Duplicate conceptual pages

Missing cross-reference

Current.md bloat

Overview polluted with transient details
```

이 검사는 `/wiki-update`의 기본 단계다.

Semantic lint에서 다음 조건이 확인되면 `/wiki-update`가 구조 유지보수도 함께 수행한다. 이 작업들이 어느 명령에도 속하지 않으면 실행되지 않고 Wiki가 비대해지므로, `/wiki-update`의 책임으로 명시한다.

| 조건 | 작업 | 관련 절 |
|---|---|---|
| index가 지나치게 길어짐 | category index 도입 | §12 |
| 완전히 superseded 되었지만 역사적 가치가 있는 페이지가 있음 | archive로 이동 | §20 |
| Wiki 페이지 사이에 모순이 있음 | 저장소를 조사하여 정본 페이지 수정 | §48 |
| 페이지 이름 변경이 필요함 | rename과 모든 link 수정 | §58 |
| current 파일이 크기 예산을 넘음 | 해결된 항목을 정본 페이지로 이동 | §14 |
| 관측 날짜가 오래된 runtime 사실이 있음 | 재확인하거나 `Not yet verified`로 표시 | §7 |

구조 유지보수는 한 번의 update에서 필요한 만큼만 수행하고, 수행한 내용을 `log.md` entry에 기록한다.

별도 `/wiki-lint` command는 v1에서 만들 필요 없다.

필요해질 경우 나중에 추가한다.

---

# 48. Contradiction 처리

Wiki 내부에서 두 문서가 충돌할 경우:

1. actual repository를 조사한다.
2. tests/evidence를 확인한다.
3. 어느 쪽이 현재 상태인지 결정한다.
4. 현재 canonical page를 수정한다.
5. 역사적으로 중요하면 old decision을 `superseded` 처리한다.

결론을 낼 수 없으면:

```text
Unknown / unresolved contradiction
```

으로 명시한다.

억지로 하나를 선택하지 않는다.

---

# 49. Context Loading Protocol

새로운 substantive 작업을 시작할 때 agent는 다음을 우선 읽는다.

```text
wiki/index.md
wiki/overview.md
wiki/current.md
```

그 다음 이번 task와 관련된 page만 선택적으로 읽는다.

예:

```text
User task:
Optimize KV-cache decode path.

Read:
index
overview
current
components/kv-cache
architecture/runtime
related decisions
recent relevant experiment
```

읽지 않을 것:

```text
all decisions
all experiments
all runbooks
entire log
archive
```

---

# 50. Session Bootstrap Context Budget

Wiki의 목적은 context를 줄이는 것이다.

따라서 기본 bootstrap:

```text
index
overview
current
```

이 과도하게 커지면 설계 실패로 간주한다.

권장 예산은 bootstrap 세 파일의 합계 약 6,000 tokens 이하다. 예산은 SCHEMA에 기록하고, linter는 token 추정치를 보고한다.

목표는 프로젝트가 수개월 성장하더라도 이 세 파일만으로:

```text
프로젝트가 무엇인지
지금 어디까지 왔는지
어디에서 추가 정보를 찾을지
```

를 알 수 있게 하는 것이다.

상세 지식은 selective retrieval한다.

---

# 51. Search Strategy

초기 Wiki 규모에서는 별도 vector search를 사용하지 않는다.

우선:

```text
index.md
ripgrep
find
Git grep
```

로 충분하다.

예:

```bash
rg "KV cache" wiki/
rg "src/runtime/cache.py" wiki/
```

Wiki가 실제로 커져 retrieval 문제가 측정된 뒤에만 BM25/vector/qmd 등을 검토한다.

v1에서 미리 search infrastructure를 만들지 않는다.

---

# 52. Agent Instruction Integration

새 세션의 agent가 Wiki 존재를 알 수 있도록 현재 harness의 project instruction에 짧은 adapter를 추가할 수 있다.

예:

```markdown
## Project Wiki

This repository uses `wiki/` as durable project memory.

Before substantial work:
1. Read `wiki/index.md`.
2. Read `wiki/overview.md`.
3. Read `wiki/current.md` (multi-host repos: only `wiki/current/<this-host>.md`).
4. Load only task-relevant pages linked from the index.
5. Verify important claims against actual source code when needed.

The repository is authoritative over the Wiki.
The current file is a verified state snapshot, not a hand-off note;
progress history stays in Git commit messages.

After completing a meaningful work unit, `/wiki-update` is used to
reconcile durable project memory.
```

Block의 언어는 저장소의 규칙을 따른다 (§0.1).

중요:

기존 `AGENTS.md` 또는 `CLAUDE.md`를 통째로 덮어쓰지 않는다.

가능하면 명확한 managed block을 사용한다.

예:

```text
<!-- project-wiki:start -->
...
<!-- project-wiki:end -->
```

이미 동일 block이 있으면 중복 삽입하지 않는다.

### 충돌하는 정책 확인

Managed block을 삽입하기 전에 instruction 파일에 Wiki와 충돌하는 정책이 있는지 확인한다. 예를 들어 "인계 문서를 만들지 않는다", "진행 상태는 commit message로만 남긴다" 같은 규칙이 있으면, current 파일이 그 규칙을 어기는 것으로 해석될 수 있다. 이런 충돌이 있으면 사용자에게 확인한 뒤, Wiki를 예외로 두도록 해당 문구를 수정한다. 확인 없이 기존 정책을 바꾸지 않는다.

### 역할 분리

- Instruction 파일: 에이전트의 행동 규칙
- Wiki: 프로젝트 상태와 지식

두 곳 모두 세션마다 로드될 수 있으므로, 같은 상태를 양쪽에 두면 context 비용이 이중으로 들고 서로 어긋나기 쉽다. Instruction 파일에 상태 서술이 섞여 있으면 `/wiki-init`이 Wiki로 옮기자고 제안한다 (§27).

### Managed block 배치

Harness마다 instruction 파일을 읽는 방식이 다르다 (§4).

- Claude Code는 `CLAUDE.md`만 읽는다.
- Codex는 `AGENTS.md`를 읽는다.
- Pi는 디렉터리마다 `AGENTS.md`와 `CLAUDE.md` 중 먼저 발견한 파일 하나만 읽는다.
- Devin은 두 파일을 모두 읽는다.

따라서 다음 규칙으로 배치한다.

1. `AGENTS.md`와 `CLAUDE.md`가 모두 있으면 두 파일에 같은 block을 둔다. Devin은 block을 두 번 읽게 되지만, block이 짧으므로 허용한다. 예외는 `CLAUDE.md`가 `@AGENTS.md` 같은 import 문법으로 `AGENTS.md`를 실제로 불러오는 경우뿐이며, 이때는 `AGENTS.md`에만 둔다. "상세 규칙은 `CLAUDE.md`를 따른다"처럼 문장으로 다른 파일을 가리키는 것은 import가 아니므로 예외에 해당하지 않는다.
2. `CLAUDE.md`만 있으면 `CLAUDE.md`에만 둔다. 이때 `AGENTS.md`를 새로 만들지 않는다. `AGENTS.md`를 만들면 Pi가 그때부터 `CLAUDE.md`를 읽지 않게 되어, 기존 규칙이 Pi에서 조용히 사라진다. Codex를 이 저장소에서 사용한다면, 사용자에게 Codex 설정의 `project_doc_fallback_filenames`에 `CLAUDE.md`를 추가하도록 안내한다.
3. `AGENTS.md`만 있으면 `AGENTS.md`에 두고, Claude Code를 사용한다면 `CLAUDE.md`를 만들지 사용자에게 묻는다.
4. 두 파일이 모두 없으면 어느 파일을 만들지 사용자에게 묻는다.

---

# 53. Anti-Bloat Rules

반드시 SCHEMA에 넣는다.

### Rule 1

Chat transcript를 저장하지 않는다.

### Rule 2

Git이 이미 설명하는 trivial change를 Wiki에 반복하지 않는다.

### Rule 3

새 page보다 기존 page update를 우선한다.

### Rule 4

`current.md`는 append-only가 아니다.

### Rule 5

Resolved item은 current에서 제거한다.

### Rule 6

Historic detail은 필요하면 archive 또는 decision history로 이동한다.

### Rule 7

한 concept가 여러 page에서 동일하게 설명되지 않게 한다.

Canonical page 하나를 두고 다른 page는 link한다.

### Rule 8

Source code documentation generator처럼 file-per-page 구조를 만들지 않는다.

### Rule 9

Long code blocks를 Wiki에 복사하지 않는다.

실제 source path를 link/reference한다.

### Rule 10

Wiki에는 미래 판단 비용을 줄이는 정보만 보존한다.

---

# 54. No-Raw-Session Policy

v1에서는 다음을 생성하지 않는다.

```text
wiki/sessions/
raw/sessions/
conversation-dumps/
```

Chat transcript를 durable storage에 dump하지 않는다.

개발 프로젝트의 primary raw truth는 이미 다음에 존재한다.

```text
Git
code
tests
configs
reports
evidence
```

대화에서만 존재하고 프로젝트에 정말 중요한 결정이라면 `/wiki-update` 시 decision 또는 architecture page로 **semantic compression**해서 저장한다.

원문 대화 자체를 저장하지 않는다.

---

# 55. External Information

프로젝트가 외부 specification, model card, official reference implementation 등에 의존할 수 있다.

Wiki는 외부 정보를 다음처럼 기록할 수 있다.

```text
Canonical upstream
Relevant version / commit
Why it matters
Local implementation relationship
```

가능하면 repository에 이미 존재하는 evidence/report/reference를 연결한다.

외부 정보가 검증되지 않았다면 확정적 사실처럼 durable Wiki에 넣지 않는다.

`/wiki-update` 자체가 매번 인터넷 research를 수행할 필요는 없다.

---

# 56. Secrets / Sensitive Data

Wiki에 다음을 기록하지 않는다.

```text
API keys
passwords
tokens
private credentials
secret environment values
SSH private material
```

Repo에 accidental secret이 보여도 Wiki로 복제하지 않는다.

---

# 57. Concurrent / Multiple Agent Safety

두 agent가 동시에 Wiki를 수정할 가능성을 고려한다.

기본 정책:

```text
Git is concurrency control.
```

update 전에:

```bash
git status
git log
```

를 다시 확인한다.

작업 중 HEAD가 예상과 달라졌다면:

```text
stale assumptions로 Wiki를 commit하지 않는다.
```

최신 diff를 다시 조사한다.

자동 force push, destructive rebase를 하지 않는다.

Push는 사용자가 요청할 때만 한다. 같은 저장소를 여러 머신에서 사용한다면, update 전에 로컬 branch가 remote보다 뒤처졌는지 확인할 수 있을 때 확인하고, 뒤처졌으면 사용자에게 알린다.

---

# 58. Rename / Delete

Wiki page rename 시 모든 Markdown link를 갱신한다.

삭제는 신중하게 한다.

현재 가치가 없지만 history가 필요한 page:

```text
archive
```

로 이동한다.

명백한 duplicate/stub이며 아무 정보도 없다면 제거할 수 있지만, Git history로 복구 가능해야 한다.

---

# 59. `/wiki-update`가 실패해도 해야 할 일

다음과 같은 상태에서는 성공을 가장하지 않는다.

```text
tests failed
benchmark inconclusive
source/evidence contradiction unresolved
required file unavailable
Git state unsafe
```

Wiki에는 실제 상태를 기록한다.

예:

```text
Partially implemented

Validation currently fails at ...
```

"완료"라고 쓰지 않는다.

---

# 60. Validation 결과와 Wiki Update

Validation이 실패했다고 해서 Wiki update 자체를 무조건 금지하지 않는다.

실패가 현재 실제 상태라면 그것도 durable context일 수 있다.

단:

```text
PASS하지 않은 것을 PASS로 기록 금지
```

repository 자체의 commit policy가 별도로 존재하면 그것을 우선한다.

---

# 61. Idempotency

`/wiki-init`:

같은 repository에서 두 번 실행해도 기존 Wiki가 파괴되거나 duplicate structure가 생겨서는 안 된다.

`/wiki-update`:

같은 source HEAD에 대해 다시 실행했을 때 substantive state change가 없다면 불필요하게 모든 Wiki page를 rewrite하면 안 된다.

가능하면 no-op에 가깝게 동작한다.

여러 머신에서 사용하는 저장소에서는 다음을 불변 조건으로 지킨다.

```text
한 머신에서 /wiki-update를 실행해도,
다른 host의 current 파일은 byte 단위로 변경되지 않는다.
```

모든 current 파일을 읽고 "조정"한 뒤 함께 다시 쓰는 구현을 허용하지 않는다.

---

# 62. Deterministic Output

LLM의 wording은 다소 달라질 수 있지만 Wiki topology가 매번 흔들리면 안 된다.

따라서:

```text
page taxonomy
frontmatter fields
index format
log format
status vocabulary
```

는 SCHEMA에서 고정한다.

---

# 63. Frontmatter

권장하지만 과도하게 복잡하게 만들지 않는다.

기본:

```yaml
---
title: KV Cache
type: component
status: current
updated: 2026-09-22
---
```

필요한 필드만 사용한다.

금지:

```text
자동 생성된 의미 없는 tag 20개
임의의 confidence 점수 0.83
수십 개 metadata field
```

---

# 64. Status Vocabulary

가능하면 제한된 vocabulary를 사용한다.

일반 page:

```text
current
partial
deprecated
archived
```

decision:

```text
proposed
accepted
rejected
superseded
```

experiment:

```text
planned
running
completed
inconclusive
```

동의어를 계속 만들지 않는다.

---

# 65. Path References

가능하면 repository-root relative path를 사용한다.

예:

```text
src/runtime/cache.py
tests/test_cache.py
reports/cache-64k.json
```

line number는 코드 변경으로 쉽게 stale해지므로 반드시 필요한 경우가 아니라면 durable Wiki에 고정하지 않는다.

symbol name은 유용하면 기록할 수 있다.

---

# 66. Semantic Compression 기준

`/wiki-update`가 정보를 저장할지 고민될 때 다음 질문을 사용한다.

> 다음 달 새 agent가 이 정보를 몰라서 실제 시간이나 compute를 낭비하거나, 잘못된 architecture 결정을 할 가능성이 있는가?

Yes라면 저장 가능성이 높다.

No라면 Git/history/source에 맡긴다.

---

# 67. Implementation Deliverables

구현 완료 시 최소한 다음을 제공한다.

```text
1. /wiki-init entrypoint
2. /wiki-update entrypoint
3. shared Project Wiki protocol
4. Wiki page templates
5. deterministic wiki linter
6. harness integration/adaptor
7. minimal usage documentation
8. tests or fixture-based validation
9. install script for each machine (§4)
```

---

# 68. Linter 구현 요구

가능하면 dependency-free Python으로 구현한다.

예:

```text
python3 <skill-path>/scripts/wiki_lint.py <repo-root>
```

exit code:

```text
0 = no structural errors
1 = structural errors found
```

semantic warnings는 stdout/stderr report로 표현할 수 있다.

script가 LLM semantic reasoning을 흉내 내려 하지 않는다.

---

# 69. 테스트 Fixture

작은 fixture repository를 만들어 skill을 검증한다.

예:

```text
fixture/
├── README.md
├── src/
│   ├── loader.py
│   └── cache.py
├── tests/
│   └── test_cache.py
└── reports/
    └── baseline.json
```

실제 사용자 repository를 망가뜨리며 테스트하지 않는다.

---

# 70. 필수 Acceptance Tests

## Test 1 — Fresh Init

Wiki가 없는 repo에서 `/wiki-init`.

기대:

```text
core Wiki 생성
index 유효
current 실제 코드와 대체로 일치
broken links 없음
commit 가능
```

---

## Test 2 — Init Idempotency

`/wiki-init` 재실행.

기대:

```text
duplicate page 없음
existing content overwrite 없음
unnecessary rewrite 없음
```

---

## Test 3 — Small Semantic Change

component behavior를 실제로 변경.

`/wiki-update`.

기대:

```text
관련 component page 수정
current 필요 시 수정
log append
관련 없는 page untouched
```

---

## Test 4 — Pure Refactor

behavior 변화 없는 rename/refactor.

기대:

```text
필요한 path reference만 수정
새 decision/experiment page 없음
```

---

## Test 5 — Important Decision

architecture choice를 변경.

기대:

```text
decision page 생성 또는 기존 decision superseded
architecture update
current update
```

---

## Test 6 — Experiment

새 benchmark artifact 추가.

기대:

```text
설계에 영향을 주는 결과라면 experiment page 생성
measurement와 interpretation 분리
```

---

## Test 7 — Stale Wiki

Wiki에는 feature complete라고 되어 있지만 실제 code는 stub.

기대:

```text
code wins
Wiki corrected
```

---

## Test 8 — Broken Link

Wiki page rename 후 link 미수정.

기대:

```text
wiki_lint detects broken link
```

---

## Test 9 — Missing Index Entry

page를 직접 추가.

기대:

```text
lint detects page absent from index
```

---

## Test 10 — Current Bloat

resolved blockers가 계속 current에 존재.

기대:

```text
semantic lint removes or relocates stale information
```

---

## Test 11 — Dirty Unrelated Worktree

사용자 unrelated edit가 존재한 상태에서 update.

기대:

```text
unrelated file not staged
not reverted
not overwritten
```

---

## Test 12 — No Unsupported Claim

문서에서 주장하지만 code/evidence로 확인되지 않는 feature.

기대:

```text
"unverified" 또는 "unknown"
완료라고 단정하지 않음
```

---

## Test 13 — Large Repository

vendor/generated/model artifacts가 다량 존재.

기대:

```text
git-aware inventory 사용
irrelevant files 전체 read 하지 않음
```

---

## Test 14 — Selective Context

task가 특정 component에만 관련됨.

기대:

```text
index + overview + current
+
relevant pages only

entire Wiki not loaded
```

---

## Test 15 — Pre-staged User File

사용자가 unrelated 파일을 미리 stage해 둔 상태에서 `/wiki-update`.

기대:

```text
Wiki commit에는 Wiki·adapter 파일만 포함
사용자 파일은 staged 상태로 남음
```

---

## Test 16 — Nested Untracked Repositories

독립 Git 저장소인 untracked 디렉터리가 저장소 안에 여러 개 존재.

기대:

```text
update가 중단되지 않음
해당 디렉터리를 읽거나 수정하지 않음
```

---

## Test 17 — Ignored Wiki Page

`.gitignore`에 `*token*`이 있는 상태에서 `wiki/components/token-logging.md` 생성.

기대:

```text
lint가 ignored Wiki 파일을 structural error로 보고
```

---

## Test 18 — Manual Wiki Edit Before Update

source commit → 사람이 Wiki만 직접 수정한 commit → `/wiki-update`.

기대:

```text
anchor가 마지막 log entry의 Source HEAD로 결정됨
사이의 source 변경이 조사 범위에 포함됨
```

---

## Test 19 — Multi-host Current

host가 두 개 선언된 저장소에서 한 host로 `/wiki-update`.

기대:

```text
자기 host의 current 파일만 변경
다른 host의 current 파일은 byte 단위로 동일
hostname 대응이 없으면 중단하고 사용자에게 질문
```

---

## Test 20 — Instruction File Placement

`CLAUDE.md`만 있는 저장소에서 `/wiki-init`.

기대:

```text
CLAUDE.md에만 managed block 삽입
AGENTS.md를 새로 만들지 않음
```

---

# 71. Performance / Context Acceptance Criteria

이 시스템의 성공은 Wiki page 개수가 많아지는 것이 아니다.

성공 기준:

```text
새 session이 과거 chat 없이 프로젝트를 이해할 수 있음

bootstrap context가 작음

필요한 상세 정보를 빠르게 찾을 수 있음

오래된 사실이 Wiki에 남아 agent를 오도하지 않음

매 session의 update cost가 repository 전체 재분석보다 훨씬 작음

Wiki diff가 human-reviewable함
```

---

# 72. 금지할 Overengineering

v1에서 만들지 않는다.

```text
Vector database

Embedding pipeline

Background daemon

Database server

MCP memory server

Graph database

Automatic chat capture

Session transcript ingestion pipeline

Complex ontology

Web dashboard

Agent-to-agent synchronization service
```

실제 사용 중 Markdown/Git만으로 부족하다는 문제가 측정된 뒤 추가한다.

---

# 73. 구현 순서

## Phase 1 — Canonical Protocol

먼저 공통 Wiki protocol과 page schema를 작성한다.

아직 command adapter를 만들지 않는다.

---

## Phase 2 — `/wiki-init`

다음을 구현한다.

```text
repo detection
existing wiki detection
inventory
progressive analysis
initial synthesis
lint
safe Git handling
```

fixture에서 검증한다.

---

## Phase 3 — `/wiki-update`

다음을 구현한다.

```text
anchor detection
change discovery
impact mapping
durable-knowledge classification
incremental page update
current reconciliation
index update
log append
lint
safe commit
```

---

## Phase 4 — Deterministic Linter

Markdown link/index/path consistency 검사를 구현한다.

---

## Phase 5 — Harness Adapter

현재 사용 중인 agent environment에서:

```text
/wiki-init
/wiki-update
```

가 실행되도록 연결한다.

공통 protocol을 복사하지 말고 참조하게 한다.

사용하는 각 머신에 skill package를 설치하고, 그 머신에 설치된 harness마다 skill이 인식되는지 확인한다 (§4).

---

## Phase 6 — Fixture Validation

앞의 acceptance tests를 수행한다.

---

## Phase 7 — Real Repository Dry Run

사용자의 실제 repository에서 우선 `/wiki-init`을 수행하되:

```text
생성 예정 구조
핵심 Wiki pages
potential conflicts
```

를 점검한다.

기존 파일을 파괴하지 않는 것을 확인한다.

Dry run 대상은 세 종류로 한다.

```text
1. 여러 머신에서 사용하는 저장소 1개 : current/<host>.md 구조 (macOS)
2. 단일 머신 프로젝트 1개           : 기본 구조 (macOS, current.md)
3. Linux 머신의 프로젝트 1개        : Linux 환경
```

두 가지 current 구조와 두 OS를 모두 검증하기 위해서다. 각 dry run은 먼저 `git worktree`로 만든 별도 작업 디렉터리에서 수행하고, 사용자가 결과를 검토한 뒤 본 checkout에 적용한다.

---

# 74. `/wiki-init` 실행 결과 형식

사용자에게 불필요하게 긴 report를 출력하지 않는다.

예:

```text
Project Wiki initialized.

Created:
- wiki/index.md
- wiki/overview.md
- wiki/current.md
- 4 architecture pages
- 3 component pages
- 2 decision pages

Validation:
- index consistency: PASS
- broken links: 0
- unresolved claims: 2

Commit:
docs(wiki): initialize project memory
```

---

# 75. `/wiki-update` 실행 결과 형식

예:

```text
Project Wiki updated.

Source changes reviewed:
abc123..def456

Wiki:
- updated components/kv-cache.md
- added decisions/0017-int4-cache-layout.md
- updated current.md

Validation:
- structural lint: PASS
- stale claims corrected: 1
- unresolved items: 1

Commit:
docs(wiki): update project memory after KV-cache work
```

세션 전체를 다시 설명하지 않는다.

---

# 76. Important Behavioral Rule

Skill은 Wiki를 유지하는 문서 작성 assistant가 아니라:

```text
repository-aware semantic memory compiler
```

처럼 동작해야 한다.

즉 다음 transformation이 핵심이다.

```text
Repository state
+
new verified knowledge
+
important rationale
        │
        ▼
small durable semantic representation
```

---

# 77. 최종 설계 원칙

항상 다음 문장을 기준으로 구현을 검토한다.

### Authority

```text
The repository is truth.
The Wiki is memory.
```

### Compression

```text
Preserve conclusions and rationale,
not the entire path taken to reach them.
```

### Retrieval

```text
Read broadly only once during initialization.
After that, retrieve selectively.
```

### Updating

```text
Update only what became stale or newly important.
```

### Current State

```text
current.md describes now, not history.
```

### History

```text
Git stores history.
Wiki stores durable meaning.
```

### Context

```text
A new session should not need an old conversation.
```

---

# 78. 완료 조건

구현은 다음이 모두 성립할 때 완료로 간주한다.

```text
[ ] /wiki-init works in a fresh Git repository
[ ] /wiki-init is idempotent
[ ] /wiki-update is incremental
[ ] Wiki uses actual repository as authority
[ ] current.md remains bounded
[ ] index provides selective navigation
[ ] important rationale can survive session replacement
[ ] chat transcripts are not stored
[ ] unrelated user changes are never destroyed or silently committed
[ ] structural lint exists
[ ] semantic lint is part of update
[ ] Git commits are safe and reviewable
[ ] core protocol is harness-independent
[ ] entrypoints are thin harness adapters
[ ] no unnecessary background infrastructure exists
[ ] fixture tests pass
[ ] pre-staged user files are never included in Wiki commits
[ ] Wiki files ignored by .gitignore are detected
[ ] conflicting instruction policies are confirmed with the user before changes
[ ] multi-host repos never modify another host's current file
[ ] managed blocks are placed without changing which file each harness loads
[ ] skills are installed and verified on each machine's harnesses
```

이 상태가 되면 실제 장기 프로젝트에서 사용을 시작한다.

그 이후 기능 추가는 **실제 사용 중 확인된 문제에 대해서만** 진행한다.

## Implementation Discretion

This document defines the required behavior, invariants, and acceptance criteria of the Project Wiki system. It does **not** prescribe every internal implementation detail.

Before implementation, inspect the current agent environment, its native skill/command mechanism, repository conventions, Git workflow, and available tooling.

You MAY improve or adapt:

* skill/command file layout
* slash-command registration
* internal script structure
* metadata representation
* lint implementation
* Git integration details
* harness-specific adapters
* naming of internal implementation files
* implementation techniques that make the system simpler, safer, or more native to the current environment

Prefer native mechanisms of the current environment over unnecessary custom infrastructure.

You MUST preserve the behavioral invariants of this specification, especially:

* the Wiki is durable semantic memory, not a chat transcript
* current implementation state must be verified against repository evidence
* target requirements must not be inferred solely from current implementation
* context loading must remain selective
* updates must be incremental
* `current.md` must remain bounded and represent the present, not history
* unrelated user changes must never be overwritten or silently committed
* unsupported claims must not be promoted to verified facts
* the system must remain lightweight and Git-native
* `/wiki-init` and `/wiki-update` remain the primary user-facing operations

If you materially deviate from this implementation plan because the current environment supports a safer or simpler design, do so rather than mechanically following the document.

For every material deviation:

1. preserve the original behavioral intent,
2. document the reason briefly,
3. validate the replacement behavior against the acceptance criteria.

Do not introduce additional infrastructure merely because it is available.

When multiple implementations are possible, prefer the smallest design that reliably satisfies the contract.

