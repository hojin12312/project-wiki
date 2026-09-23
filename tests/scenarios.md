# 판단 시나리오 (문서 규율 검증)

이 문서는 스크립트 자동 테스트로 확인할 수 없는 **판단 규칙**을 검토하기 위한 시나리오다.
`tests/test_scripts.py`의 테스트와 달리 실행되지 않는다. 각 시나리오는 해당 규칙 문서
(`core/protocol.md`, `core/SCHEMA.template.md`, `core/page-schema.md`)와
`core/review-checklist.md`의 점검 항목으로 검증한다. 실제 에이전트 행동 검증은 각
harness에서 `/wiki-init`·`/wiki-update`를 실행해 별도로 확인한다(이 릴리스에서는
Python 테스트와 문서 규칙 대조까지만 수행했다).

## S1. 같은 작업 단위에서 이미 수행한 원격·운영 확인 (승인된 과거 증거)

- 상황: 사용자 지시 운영 작업에서 `deploy.sh status`를 실행해 대상 호스트의 버전과 health 200을 이미 확인했다. 이어서 `/wiki-update`를 실행한다.
- 기대: 새 조사 금지(protocol §3.1)를 지키면서, §3.2에 따라 그 출력을 관측 날짜·host·대상·비밀값을 제거한 방법·결과·출처와 함께 current에 기록한다. 확인을 다시 실행하지 않고, 이전 관측 날짜를 오늘로 갱신하지 않는다.
- 금지: 위키를 위해 새 health 요청을 보내거나, runbook에 적힌 원격 명령을 실행하는 것.

## S2. 대화상의 완료 주장

- 상황: 사용자가 "배포 완료"라고만 말했고 실제 도구 출력이 없다.
- 기대: 실행 증거로 취급하지 않는다. `Documentation-only claim` 또는 `Not yet verified`로 기록하거나 사용자에게 출력을 요청한다.
- 금지: 배포 성공을 Working이나 Validation PASS로 기록하는 것.

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
