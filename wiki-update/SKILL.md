---
name: wiki-update
description: 작업 단위가 끝난 뒤 프로젝트 Wiki(wiki/)를 실제 저장소 상태와 대조해 필요한 페이지만 증분 갱신하고, semantic·structural lint와 구조 유지보수 후 commit한다. 대화 요약이 아니다. 사용자가 /wiki-update를 명시적으로 요청할 때만 실행한다.
disable-model-invocation: true
triggers: [user]
---

# wiki-update

마지막 Wiki update 이후의 저장소 변화를 조사하고, 오래되었거나 새로 중요해진 지식만 Wiki에 반영한다. "이번 대화를 요약하라"가 아니라 "Wiki를 실제 저장소 상태와 맞춰라"가 목적이다. 대화 내용은 탐색의 힌트일 뿐이며, 저장소나 evidence와 충돌하면 버린다.

`<skill-dir>`은 이 파일이 있는 디렉터리다. 공유 자원은 `<skill-dir>/core/`에 있다. Harness가 이 경로를 알려 주지 않으면 `~/.agents/skills/wiki-update`, `~/.claude/skills/wiki-update`, `~/.config/devin/skills/wiki-update`, `~/.pi/agent/skills/wiki-update` 순서로 `SKILL.md`가 있는 곳을 확인한다. 파일 시스템 전체를 검색하지 않는다.

## 0. 준비

1. `python3 <skill-dir>/core/scripts/wiki_state.py self-update`를 실행한다. 결과 해석은 `core/protocol.md` §1을 따른다.
2. `<skill-dir>/core/protocol.md`를 읽는다. 이후 모든 단계는 이 절차를 따른다.

## 1. Preflight

1. `python3 <skill-dir>/core/scripts/wiki_state.py preflight .`를 실행한다.
2. `wiki_exists`가 false면 `/wiki-init`을 안내하고 멈춘다.
3. `blockers`가 있으면 중단한다. Host를 확인할 수 없으면 어떤 current 파일에도 쓰지 않고 사용자에게 묻는다.
4. `schema_version`과 `template_schema_version`의 major.minor가 다르면 사용자에게 알리기만 한다.
5. `dirty_source`가 있으면 `core/protocol.md` §5를 따른다.

## 2. 현재 Wiki 읽기

`wiki/SCHEMA.md`, `index.md`, `overview.md`, 그리고 자기 host의 current 파일(preflight `host.current_path`)을 읽는다. 최근 이력이 필요하면 `tail -n 60 wiki/log.md`만 읽는다. 다른 host의 current 파일과 archive는 읽지 않는다.

## 3. 변경 조사

1. 변경 범위는 preflight의 `anchor.anchor`..`head`이고, 목록은 `changed_source`다(`wiki/` 제외). Anchor가 없으면 저장소를 넓게 다시 조사한다(`/wiki-init` §5와 같은 순서).
2. 필요한 파일만 `git diff <anchor>..HEAD -- <file>`로 확인한다.
3. 변경을 분류한다: semantic implementation change, behavior 없는 refactor, test, configuration, documentation-only, experiment·evidence 추가, generated artifact, formatting.
4. 변경 경로마다 관련 페이지를 찾는다: `rg -n "<changed path>" wiki/`, index의 subsystem 구분, component와 architecture 관계, 테스트가 검증하는 기능.

## 4. Durable knowledge 판단

다음 질문에 답한다. 해당하는 것이 없으면 substantive 수정을 최소화한다.

- 무엇이 이제 실제로 가능해졌는가? 이전 Wiki에서 틀리게 된 내용은 무엇인가?
- Architecture, invariant, interface가 바뀌었는가?
- 중요한 decision이 내려졌는가? (A 대신 B, data format 고정, compatibility 정책, 의도적인 trade-off, workaround의 영구 채택, 기존 구조 폐기)
- 실험 결과가 이후 설계에 영향을 주는가? 가설을 확인하거나 반박했는가? (단순 smoke test는 experiment가 아니다)
- Blocker가 새로 생기거나 해결되었는가? 반복 가능한 절차가 생겼는가?

저장 여부가 애매하면 `core/protocol.md` §4의 질문으로 판단한다.

## 5. 페이지 수정

- Minimum necessary edit: 사실과 충돌하는 부분을 고치고, 새로 durable해진 내용을 더하고, 오래된 세부 사항을 제거하거나 archive하고, cross-reference를 갱신한다. 관련 없는 문장은 바꾸지 않는다.
- 새 페이지는 SCHEMA §5의 기준을 만족할 때만 만든다. Template은 `core/page-schema.md`를 따른다.
- `overview.md`는 scope, hard constraint, 상위 구조, canonical reference, 주요 subsystem이 바뀔 때만 수정한다.
- `index.md`는 페이지를 추가·rename·archive했거나 요약이 의미 있게 바뀌었을 때 갱신한다.
- 페이지를 rename하면 그 페이지를 가리키는 모든 link를 고친다.
- 여러 host 저장소에서는 머신에 따라 달라지는 사실에 host 이름을 붙인다. 공유 페이지에 있는 다른 host의 사실은 이 host에서 검증할 수 없으므로 수정하지 않는다.
- 조사 범위는 현재 저장소뿐이다. 다른 머신에 원격 접속하지 않는다(`core/protocol.md` §3).

## 6. Current 재계산

자기 host의 current 파일만 다시 계산한다. Append하지 않는다.

- Working, Partially Implemented, Not Yet Implemented, Current Blockers, Active Risks / Unknowns, Next Logical Work를 실제 상태에 맞게 다시 정리한다.
- 해결된 blocker는 제거한다. 완료된 작업은 Working이나 정본 페이지에 반영한다. 지난 next step은 지운다.
- Runtime 사실은 이번에 다시 확인했으면 날짜를 갱신하고, 확인하지 못했으면 기존 날짜를 유지한다.
- 다른 host의 current 파일은 byte 단위로도 바꾸지 않는다.

## 7. Semantic lint와 구조 유지보수

다음을 점검하고, 조건에 해당하면 이 단계에서 처리한다. 한 번에 필요한 만큼만 한다.

| 조건 | 처리 |
|---|---|
| Wiki와 코드가 모순됨 | 코드를 기준으로 Wiki를 고친다 |
| 해결된 blocker나 오래된 구현 상태가 남아 있음 | 제거하거나 정본 페이지로 옮긴다 |
| 같은 개념이 여러 페이지에서 다르게 설명됨 | 정본 하나를 정하고 나머지는 link로 바꾼다 |
| Superseded 구조가 현재처럼 서술됨 | decision을 `superseded`로 바꾸거나 archive로 옮긴다 |
| 근거 없는 확정 표현 | `Not yet verified` 등으로 바꾼다 |
| 관측 날짜가 오래된 runtime 사실 | 재확인하거나 `Not yet verified`로 표시한다 |
| Current 파일이 예산을 넘음 | 세부 사항을 정본 페이지로 옮긴다 |
| Current의 절 분류가 틀림(Working에 위험·불일치·미확인 항목, 관측과 추론이 섞임) | 알맞은 절로 옮기고 추론에는 `추정:`을 붙인다 |
| Index가 지나치게 길어짐 | category index를 도입한다 |
| 페이지 사이의 모순을 판단할 수 없음 | `Unresolved contradiction`으로 표시한다 |

## 8. log.md

마지막에 entry 하나를 append한다(SCHEMA §13 형식). `Source HEAD`에는 preflight의 `head`(40자 전체 SHA)를 그대로 복사하고, 여러 host면 `Host:`를 적는다. Validation에는 실제로 실행한 검증만 적는다.

- Source 변경이 있었지만 Wiki에 반영할 지식이 없으면, "no substantive change" entry만 남겨 anchor를 앞으로 옮긴다.
- Anchor 이후 source 변경이 전혀 없고 semantic lint에서도 고칠 것이 없으면, 아무 파일도 바꾸지 않고 "no change"로 보고하고 끝낸다.

## 9. 검증, commit, 보고

1. `python3 <skill-dir>/core/scripts/wiki_lint.py .`를 실행하고 ERROR를 모두 해결한다.
2. Preflight를 다시 실행해 `head`가 처음과 같은지 확인한다. 다르면 3단계부터 다시 한다.
3. `core/protocol.md` §5의 순서로 pathspec commit한다. 메시지는 `docs(wiki): update project memory after <topic>`이다. Push하지 않는다.
4. `core/protocol.md` §9 형식으로 짧게 보고한다. 실패한 검증이나 해소하지 못한 항목은 숨기지 않는다. `Skill feedback` 절을 반드시 넣는다.
