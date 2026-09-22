---
name: wiki-init
description: 현재 Git 저장소를 조사해 프로젝트 Wiki(wiki/)를 처음 구축한다. 저장소 구조, 문서, 테스트, Git history를 근거로 overview·current·index를 만들고 structural lint 후 commit한다. 사용자가 /wiki-init을 명시적으로 요청할 때만 실행한다.
disable-model-invocation: true
triggers: [user]
---

# wiki-init

현재 저장소에 프로젝트 Wiki를 처음 만든다. Wiki는 채팅 요약이 아니라, 저장소에서 다시 알아내기 비싼 지식을 압축한 장기 기억이다. 저장소가 항상 Wiki보다 우선한다.

`<skill-dir>`은 이 파일이 있는 디렉터리다. 공유 자원은 `<skill-dir>/core/`에 있다. Harness가 이 경로를 알려 주지 않으면 `~/.agents/skills/wiki-init`, `~/.claude/skills/wiki-init`, `~/.config/devin/skills/wiki-init`, `~/.pi/agent/skills/wiki-init` 순서로 `SKILL.md`가 있는 곳을 확인한다. 파일 시스템 전체를 검색하지 않는다.

## 0. 준비

1. `python3 <skill-dir>/core/scripts/wiki_state.py self-update`를 실행한다. 결과 해석은 `core/protocol.md` §1을 따른다.
2. `<skill-dir>/core/protocol.md`를 읽는다. 이후 모든 단계는 이 절차를 따른다.

## 1. Preflight

1. `python3 <skill-dir>/core/scripts/wiki_state.py preflight .`를 실행한다.
2. `blockers`가 있으면 중단한다. Git 저장소가 아니면 `git init`을 제안하고 멈춘다.
3. `staged`, `dirty_source`, `dirty_instruction_files`, `untracked_entries`를 기록해 둔다. 이 파일들은 commit하지 않는다. `dirty_instruction_files`에 managed block을 넣는 경우는 `core/protocol.md` §5를 따른다.

## 2. 기존 Wiki 확인

`wiki/`에 `SCHEMA.md`, `index.md`, `overview.md`, current 파일 중 하나라도 있으면 이미 초기화된 것으로 본다.

- 전체를 다시 만들지 않는다. 기존 내용을 덮어쓰지 않는다.
- 빠진 필수 파일만 만들고, lint를 실행한 뒤 "already initialized"와 lint 결과를 보고하고 끝낸다.
- 다른 형식의 문서 체계(`docs/` 등)를 자동으로 migration하지 않는다.

## 3. Project instruction 확인

1. `AGENTS.md`, `CLAUDE.md`, `AGENTS.override.md`와 README를 읽는다.
2. 다음을 찾아 둔다.
   - 보호 경로: 읽거나 수정하지 말라고 지정된 경로(독립 Git 저장소인 clone 등). SCHEMA의 Protected Paths에 넣는다.
   - Wiki와 충돌하는 정책: 예를 들어 "인계 문서를 만들지 않는다", "상태는 commit message로만 남긴다".
   - 문서 언어 규칙: Wiki 언어로 사용한다. 규칙이 없으면 기존 문서의 주 언어를 따른다.
   - Instruction 파일에 섞인 상태 서술(현재 모델, 현재 blocker 등): 이전 후보로 기록한다.

## 4. Host 구조 결정

이 저장소를 여러 머신에서 checkout해서 쓰고, 머신마다 하드웨어나 runtime 상태가 다른지 판단한다. 근거는 저장소 안에서만 찾는다: `hosts/` 같은 머신별 문서, 여러 노드나 머신별 설정을 설명하는 instruction·README.

- 이런 근거가 없으면 묻지 않고 단일 host 구조(`wiki/current.md`)를 사용한다. 6단계의 확인 요약에 "단일 host"라고 적어 사용자가 바로잡을 수 있게 한다.
- 근거가 있으면 사용자에게 확인한다. 확인되면 host 이름(예: `mbp`, `studio`)과 각 host의 `hostname -s` 값을 사용자에게 받는다. 현재 머신의 값은 preflight의 `host.hostname`이다. 다른 머신에 원격 접속해서 알아내지 않는다.
- 여러 host 구조에서는 공통 지식을 공유 페이지에, host별 현재 상태를 `current/<host>.md`에 둔다. 머신에 따라 달라지는 사실에는 host 이름을 붙인다(SCHEMA §6).
- 사용자가 여러 머신에서 쓰지 않는다고 답하면 단일 host 구조를 사용한다.

## 5. 저장소 조사

`core/protocol.md` §3을 따른다. 조사 범위는 현재 저장소뿐이다. 전체를 읽지 않고 다음 순서로 필요한 만큼만 읽는다.

1. `git ls-files`로 topology 파악: subsystem, entry point, 테스트 위치, evidence·report 위치
2. README, instruction 파일, `docs/`
3. Build·package·config 파일
4. 핵심 interface와 data flow
5. 구현 상태: implemented, partial, stub, TODO, disabled, experimental을 구분한다
6. 테스트와 evidence
7. 필요할 때만 Git history: `git log --oneline -n 100`, `git log -- <file>`

기존 문서의 주장은 구현과 대조하여 `Confirmed by implementation`, `Documentation-only claim`, `Outdated`, `Unknown`으로 구분한다. 이전 에이전트가 작성한 문서와 untracked skill(예: `.claude/skills/`)은 참고하되, 검증하지 않은 내용은 사실로 옮기지 않는다.

## 6. 사용자 확인

파일을 만들기 전에 다음을 짧게 보고하고 확인을 받는다.

- 만들 구조: 단일 또는 여러 host, 만들 category와 페이지 목록
- 충돌하는 정책과 제안하는 문구 수정
- Source inventory: 존재하지 않는 파일을 가리키는 참조, 중복 서술, Wiki로 옮길 후보
- Managed block을 넣을 instruction 파일(`core/protocol.md` §6 배치 규칙)

기존 문서나 skill의 수정·삭제는 사용자가 승인한 항목만 실행한다.

## 7. Wiki 생성

1. `wiki/SCHEMA.md`: `<skill-dir>/core/SCHEMA.template.md`를 복사하고 placeholder를 채운다.
   - `{{SCHEMA_VERSION}}`: preflight의 `template_schema_version` 값
   - `{{WIKI_LANGUAGE}}`: 예) `ko (identifiers and paths stay in English)`
   - `{{HOSTS}}`: 여러 host면 `mbp: <hostname>` 형식, 단일 host면 빈 줄
   - `{{PROTECTED_PATHS}}`: 한 줄에 경로 하나, 없으면 빈 줄
2. `overview.md`, current 파일, `index.md`: `core/page-schema.md`의 template을 따른다.
   - 목표와 non-goal은 사용자나 문서가 정한 것만 적는다. 구현에서 추론하지 않는다. 출처가 없으면 `Unknown`이다.
   - Current 파일은 이번 조사로 검증한 상태만 담는다. Runtime 사실에는 관측 날짜와 확인 명령을 붙인다.
   - 여러 host면 자기 host의 current 파일만 만든다. 다른 host의 파일은 그 host에서 `/wiki-update`를 실행할 때 만든다.
3. 필요할 때만 `architecture/`, `components/`, `decisions/`, `experiments/`, `runbooks/` 페이지를 만든다. Source 파일마다 페이지를 만들지 않는다. 구조는 개념 단위로 나눈다.
4. `log.md`: `core/page-schema.md`의 init entry. `Source HEAD`에는 preflight의 `head`를 적는다. 여러 host면 `Host:` 줄을 넣는다.
5. 승인받은 instruction 파일에 managed block을 넣는다(`core/protocol.md` §6).

## 8. 검증

1. `python3 <skill-dir>/core/scripts/wiki_lint.py .`를 실행하고 ERROR를 모두 해결한다.
2. 스스로 점검한다.
   - `current`가 실제 구현과 맞는가? TODO나 stub을 완료된 기능으로 적지 않았는가?
   - 테스트와 결과를 정확히 옮겼는가? PASS하지 않은 것을 PASS로 적지 않았는가?
   - 중복 페이지가 없는가? `overview`에 일시적인 내용이 섞이지 않았는가?
   - 비밀값을 옮기지 않았는가?

## 9. Commit과 보고

1. `core/protocol.md` §5의 순서로 pathspec commit한다. 메시지는 `docs(wiki): initialize project memory`다.
2. Push하지 않는다.
3. 다음 형식으로 짧게 보고한다.

```text
Project Wiki initialized.

Created:
- wiki/index.md, overview.md, current.md
- <n> architecture / <n> component / <n> decision pages
Validation:
- structural lint: PASS
- unresolved claims: <n>
Commit: docs(wiki): initialize project memory

Skill feedback:
- <모호했던 지침, 건너뛴 단계, 헤맨 부분. 없으면 "없음">
```

`Skill feedback`은 반드시 넣는다(`core/protocol.md` §9).
