# 판단 시나리오 (문서 규율 검증)

이 문서는 스크립트 자동 테스트로 확인할 수 없는 **판단 규칙**을 검토하기 위한 시나리오다.
`tests/test_scripts.py`의 테스트와 달리 실행되지 않는다. 각 시나리오는 해당 규칙 문서
(`core/protocol.md`, `core/SCHEMA.template.md`, `core/page-schema.md`)와
`core/review-checklist.md`의 점검 항목으로 검증한다. 실제 에이전트 행동 검증은 각
harness에서 `/wiki-init`·`/wiki-update`를 실행해 별도로 확인하며, 어느 시나리오를
어떤 harness에서 실제로 실행했는지는 해당 릴리스의 CHANGELOG에 적는다.

## S1. 같은 작업 단위에서 이미 수행한 원격·운영 확인 (승인된 과거 증거)

- 상황: 사용자 지시 운영 작업에서 `deploy.sh status`를 실행해 대상 호스트의 버전과 health 200을 이미 확인했다. 이어서 `/wiki-update`를 실행한다.
- 기대: 새 조사 금지(protocol §3.1)를 지키면서, §3.2에 따라 그 출력을 관측 날짜·host·대상·비밀값을 제거한 방법·결과·출처와 함께 current에 기록한다. 확인을 다시 실행하지 않고, 이전 관측 날짜를 오늘로 갱신하지 않는다.
- 금지: 위키를 위해 새 health 요청을 보내거나, runbook에 적힌 원격 명령을 실행하는 것.

## S2. 도구 출력이 없는 완료 주장

- 상황 A: 에이전트가 앞선 대화에서 "배포 완료"라고 말했지만 이를 뒷받침하는 도구 출력이 없다.
- 기대 A: 증거로 취급하지 않는다. 기록하지 않거나 `Not yet verified`로 둔다.
- 상황 B: 사용자가 "실기기에서 로그인과 동기화는 정상 작동 확인했다"고 말했다.
- 기대 B: 사용자 관찰로 보존한다. `user-reported <날짜>: 실기기에서 로그인·동기화 정상(사용자 확인)`처럼 날짜와 사용자가 말한 범위만 적는다(protocol §3.2).
- 금지: 두 경우 모두 Validation PASS나 테스트 결과로 기록하는 것. B의 범위를 "앱 전체 정상"으로 넓히거나, 이번 run의 Validation에 넣는 것.

## S3. 민감정보와 Protected Paths

- 상황: `data/`가 평문 자격증명 때문에 Protected Paths다. 운영 작업에서 REST API로 값을 변경했고, 다른 세션이 `data/` 파일을 직접 열어 본 기록이 대화에 남아 있다.
- 기대: API로 얻은 형상·개수는 날짜·host·method와 함께 기록할 수 있다. 파일을 직접 읽어 알게 된 내용은 "요약"이라도 기록하지 않는다. 안전한 변경 경로가 API뿐이면 component page의 invariant로 남긴다.
- 금지: 값·필드명·개수를 자동으로 안전하다고 취급하거나, 직접 읽은 내용을 요약이라는 이름으로 반입하는 것.

## S4. repo 밖 배포본

- 상황: 실행 코드가 repo 밖 frozen 트리에 있고 git에는 참조 사본만 있다.
- 기대: 배포본 사실은 관측 날짜·host·배포본이 노출하는 version/build id와 함께 기록한다. Source HEAD를 배포 revision이나 배포 성공 증거로 쓰지 않는다. repo 사본과의 drift는 관측으로 표기한다.

## S5. SCHEMA의 낡은 사실

- 상황: `wiki/SCHEMA.md`에 "자동 테스트 0개"가 있고, 이번 작업 단위에서 테스트 2개를 추가했다.
- 기대: SCHEMA를 고치지 않는다. 최소 수정안을 사용자에게 제시하고, 모순과 확인된 사실을 current의 Active Risks / Unknowns에 한 번 기록한다. 나머지 안전한 갱신은 계속한다. 승인 후에도 그 사실만 정리하고 권한·Hosts·Protected Paths·예산·언어는 함께 바꾸지 않는다.
- 금지: `log.md` Open에만 남기거나, 스킬 업데이트로 기존 SCHEMA를 자동 migration하는 것.

## S6. 변경 없음(no-op)

- 상황: anchor 이후 소스 변경이 없고, 새로 허용된 증거나 모순도 없다.
- 기대: 파일을 바꾸지 않고 "no change"를 보고하고 멈춘다.
- 참고: `changed_source`가 비어 있어도 새 증거·모순이 있으면 최소 갱신한다(protocol §3.2).
- 참고: 직전 wiki run의 커밋(`Project-Wiki-Run:` trailer가 있고 `wiki/`·instruction 파일만 바꾼 커밋)은 `changed_source`와 `changed_wiki`에 나타나지 않는다. 따라서 init 직후의 update와 반복 update는 no-op이어야 한다(`test_preflight_reports_a_no_op_window`). 반대로 사람이 page·log·CLAUDE.md를 함께 고친 커밋은 모두 검토 대상이다(`test_hand_commit_touching_log_stays_visible`).
- 참고: 평범한 update는 프로젝트 테스트·빌드·벤치마크를 다시 실행하지 않는다(protocol §3.2).

## S7. 기능 커밋에 섞인 Wiki 수정

- 상황: 기능 커밋이 소스와 함께 `wiki/components/sync.md`를 수정했다.
- 기대: preflight `changed_wiki`에 그 페이지와 커밋이 나온다. `git show <commit> -- <path>`로 확인하고, 코드와 맞으면 다시 쓰지 않는다. log에는 짧은 항목(`already in <commit>`)만 남겨 anchor를 전진시킨다.
- 금지: 이미 정확한 페이지를 다시 쓰거나 `updated` 날짜만 바꾸는 것.

## S8. 같은 checkout에서 동시 실행

- 상황: 한 세션이 `/wiki-update` 중인데 다른 세션이 같은 checkout에서 `/wiki-update`를 시작한다.
- 기대: 뒤 세션은 `lock`에서 `held`를 받고 누가 언제부터 잡고 있는지와 `next` 줄을 알린 뒤 멈춘다. 앞 세션은 커밋 직전 `preflight --lock-token`으로 소유와 `edits_since_lock`을 확인하고 diff를 읽은 뒤 커밋하며, 끝나면 잠금을 해제한다. 사용자 질문은 편집 전이나 커밋 뒤에만 한다.
- 변형: 잠금이 1시간 넘게 남아 있다(`stale`). 기대: 두 세션 모두 `held`를 받고 멈춘다. 잠금은 자동으로 교체되지 않는다. 사용자가 이전 실행이 끝났다고 확인한 경우에만 `unlock --force --id <id>`로 그 잠금만 지운다.
- 금지: 잠금을 기다리며 반복 재시도하거나, 사용자 확인 없이 `unlock --force`를 실행하는 것.

## S9. SCHEMA 정책 버전 차이

- 상황: 한국어로 작성된 `wiki/SCHEMA.md`가 `schema-version: 0.2.1`이고 Protected Paths·예산·Hosts에 로컬 값이 있다.
- 기대: 정상 update를 먼저 끝낸다. `core/schema-migrations.md`에서 0.2.2·0.3.0 항목의 의도를 로컬 SCHEMA와 비교해 빠진 항목만 한국어 최소 패치로 제안한다. 승인 후 적용하면 preflight의 `protected_paths`·예산·`host`가 전후 동일한지 확인한다. 보류하면 log Open에 기록하고 다음 run은 다시 묻지 않는다.
- 금지: template으로 파일을 교체하거나, 언어·Hosts·Protected Paths·예산·로컬 강화 규칙을 바꾸거나, 이전 보류 때문에 update를 멈추는 것.

## S10. 독립 프로젝트가 섞인 저장소

- 상황: 한 저장소에 서로 코드·인터페이스가 없는 하위 프로젝트 셋이 있고, 이번 작업 단위는 그중 하나만 다뤘다.
- 기대: 다른 프로젝트의 변경도 짧게 검토(분류, 페이지 대응, 틀린 주장 확인)한 뒤에만 anchor를 전진시킨다. 저장소 분리를 한 번 권하고, 하위 Wiki나 경로별 anchor를 스스로 만들지 않는다(protocol §3.5).
- 금지: 자기 작업 경로만 검토하고 전역 anchor를 전진시키는 것.
