# Changelog

버전 규칙은 `core/protocol.md` §12를 따른다. `VERSION`은 skill package 버전이고, 괄호 안의 schema는 `core/SCHEMA_VERSION`(SCHEMA 정책 버전)이다.

## 0.6.0 (schema 0.3.1)

- 새 저장소에서 `/wiki-init`의 preflight가 `wiki/SCHEMA.md`가 없다는 이유로 blocker를 내던 0.5.0의 회귀를 고쳤다. 파일이 없는 상태는 읽기 오류가 아니다.
- 두 `SKILL.md`를 진입점으로 줄였다. self-update를 단독으로 먼저 실행한 뒤 `core/protocol.md`와 명령별 절차(`core/init.md`, `core/update.md`)를 순서대로 읽는다. 업데이트 전에 주입된 `SKILL.md`에 오래된 절차가 남지 않는다.
- 같은 checkout의 Wiki 실행을 잠금(`wiki_state.py lock`/`unlock`, Git 디렉터리 안)으로 직렬화한다. 커밋 직전 `preflight --lock-token`으로 소유를 확인하고, 커밋·no-op·중단·사용자 질문 전에 해제한다. 중단된 실행의 잠금은 1시간 뒤 교체되고, 사용자가 확인하면 `--force`로 지운다.
- preflight가 기능 커밋에 섞인 Wiki 수정을 `changed_wiki`(경로와 커밋)로 보여 준다. 직전 Wiki 실행의 커밋(페이지, log, managed block)은 검토 범위에서 빠지므로 init 직후와 반복 update가 no-op이 된다. 이미 정확한 페이지는 다시 쓰지 않는다.
- 사용자 요구, 사용자 관찰(`user-reported <날짜>: <사용자가 말한 범위>`), 도구 관찰, 도구 출력 없는 에이전트 주장을 구분한다. 사용자 확인을 PASS나 이번 run의 검증으로 올리지 않는다. 커밋 경로는 명령마다 독립 인자로 적고, 커밋 뒤 `git show --name-only`와 staged 목록으로 확인한다.
- SCHEMA 정책 버전 차이는 update를 막지 않는다. `core/schema-migrations.md`의 버전별 요약으로 빠진 항목만 최소 패치로 제안하고, 언어·Hosts·Protected Paths·예산·로컬 규칙을 보존한다. 보류는 log에 남겨 반복해서 묻지 않는다. 독립 프로젝트가 섞인 저장소의 운영 지침(protocol §3.5)을 추가했고, lint는 미커밋 소스·clone에 not-preserved marker를 권하지 않는다. schema 0.3.1은 SCHEMA §13 커밋 예시의 `-- wiki/`를 고친 patch라 기존 Wiki에 경고가 생기지 않는다.
- 검증: Python 테스트 외에 Claude Code headless 실행으로 임시 저장소에서 새 init, init 직후·반복 no-op, 기능 커밋에 섞인 Wiki 수정과 사용자 확인 보존(S2·S7), 동시 실행 2개(S8), 한국어 0.2.1 SCHEMA의 승인 이전·보류·보류 유지(S9), 과거 대화 없는 새 세션의 다음 작업 찾기를 확인했다. S10(독립 프로젝트 혼합 저장소)과 오래된 잠금 교체, 다른 harness는 에이전트로 실행하지 않았다.

## 0.5.0 (schema 0.3.0)

- 같은 작업 단위에서 사용자가 지시해 이미 수행한 운영·원격 확인은 새 조사 없이 요약해 기록할 수 있다. 관측 날짜·host·대상·비밀값을 제거한 방법·증거 출처를 남기고, 직접 읽은 Protected Paths 내용은 요약이라는 이름으로도 기록하지 않으며, 재검증하지 않은 결과의 날짜·현재 상태 주장은 갱신하지 않는다. committed source와 관측된 배포 상태, Source HEAD와 배포 revision을 구분한다.
- instruction 파일의 tracked-clean/tracked-dirty/untracked/ignored 상태를 구분해 managed block을 다룬다. 로컬 전용 파일은 커밋하거나 ignore 규칙을 우회하지 않고, 다른 checkout에 안내가 전달되지 않음을 보고한다.
- 미보존 산출물은 본문에 핵심 수치·조건·revision을 남기고 `<!-- wiki:not-preserved -->`를 해당 경로 표기 바로 뒤에만 붙여 lint 경고를 좁게 면제한다. lint는 invalid UTF-8·NUL을 ERROR로, U+FFFD·제어문자를 위치·개수와 함께 WARN으로 보고하며 자동 복구하지 않는다.
- preflight가 current/bootstrap 예산과 추정 토큰, 적용 current 경로, 누락 상태를 JSON으로 노출한다. lint와 같은 추정 함수를 쓰며, 실제 모델 tokenizer의 정확한 값이라고 주장하지 않는다.
- SCHEMA에는 정책·설정만 두고 테스트 개수·구현 상태 같은 가변 사실은 current/component로 둔다. 기존 SCHEMA의 낡은 사실은 승인 전에 수정하지 않고 current의 Active Risks / Unknowns에 모순과 확인된 사실을 한 번 기록한다.
- Git 안전: 실행이 편집한 정확한 파일만 커밋하고, 미커밋 log의 Source HEAD를 확정 anchor로 쓰지 않으며, 200개 초과 변경 목록은 잘림을 명시하고 남은 범위를 검토하기 전에는 anchor를 전진시키지 않는다. OpenCode native 경로(`~/.config/opencode/skills`)를 두 SKILL의 fallback 탐색 순서에 맞췄다(0.4.4의 미릴리스 변경 포함).

## 0.4.3 (schema 0.2.2)

- lint가 없는 경로·untracked 경로를 가리키는 참조를 경로마다 한 줄로 묶어 경고한다. 없는 파일에 대한 언급은 current의 Active Risks에 한 번만 적는다.
- 다른 머신에 복사해 배포한 것(rsync, 패키지)은 checkout이 아니므로 host 구조 판단에 쓰지 않는다.
- Protected Paths는 읽으면 안 되는 경로(지침이 금지한 경로, 독립 Git 저장소, 비밀값 저장소)에만 쓴다. 크기만 큰 로그·데이터 폴더는 필요한 부분만 골라 읽는다.
- 원격 접속 금지에 다른 머신의 서비스에 대한 HTTP 요청(health check 등)도 포함된다고 명시했다.

## 0.4.2

- 에이전트가 읽는 문서(`SKILL.md`, `core/protocol.md`, `core/SCHEMA.template.md`, `core/page-schema.md`, `core/review-checklist.md`)를 영어로 다시 썼다. 규칙은 바뀌지 않았다.
- 각 저장소의 Wiki 본문은 계속 그 저장소의 `wiki-language`로 작성한다. 이미 설치된 한국어 `wiki/SCHEMA.md`는 그대로 둔다.
- README를 읽기 쉽게 다시 썼다.

## 0.4.1

- Issue template 2종(Skill feedback / 개선 제안, 버그)과 PR template을 추가했다.
- 바로 고치지 않는 개선 후보는 개인 환경 정보를 일반화해 Issue로 남긴다(`core/protocol.md` §12).
- 하위 폴더에서 `/wiki-init`을 실행하면 대상이 저장소 전체라는 것을 확인 요약에 밝힌다. Wiki는 저장소 단위로만 만든다.

## 0.4.0 (schema 0.2.1)

- Git 저장소가 아니거나 commit이 없는 저장소에서 `/wiki-init`을 실행할 때의 절차를 추가했다: `.gitignore`와 비밀값 검사를 먼저 하고, baseline commit을 Wiki commit과 분리한다.
- 미커밋 instruction 파일의 변경을 누가 만들었는지 불분명하면 diff를 보여 주고 먼저 commit할지 묻는다.
- `log.md`의 `Source HEAD`는 40자 전체 SHA로 적는다. 짧은 SHA는 lint가 경고한다.
- `/wiki-update`의 semantic lint가 current의 절 분류 오류(Working에 위험 항목 등)를 바로잡는다.
- managed block의 진행 기록 문장은 저장소 관례에 맞게 바꿀 수 있다.
- 버전마다 git tag와 GitHub Release를 만든다.

## 0.3.2

- 공개 준비: MIT 라이선스, fork 기반 설치 안내, 일반화한 설계 명세(`docs/design.md`).
- Push 권한이 없으면 commit까지만 하고 fork를 안내한다.

## 0.3.1

- 보호 경로는 Markdown 링크로 가리킬 때만 lint가 경고한다. 경계를 설명하는 언급은 경고하지 않는다.
- Current의 Working에는 확인된 동작만 넣고, 관측에서 이끌어 낸 해석은 `추정:`으로 표시한다.

## 0.3.0

- `/wiki-init`·`/wiki-update` 보고에 `Skill feedback` 절을 넣는다.
- 실행 결과 검토용 `core/review-checklist.md`를 추가했다.
- SCHEMA 정책 버전(`core/SCHEMA_VERSION`)을 package 버전과 분리했다.

## 0.2.2

- Harness가 skill 경로를 알려 주지 않으면 알려진 설치 위치를 순서대로 확인한다.
- 사용자의 미커밋 변경이 있는 instruction 파일은 Wiki commit에서 뺀다(`dirty_instruction_files`).

## 0.2.1

- 여러 host 여부는 저장소 안에 근거가 있을 때만 묻는다.
- SCHEMA 버전은 major.minor만 비교한다.

## 0.2.0 (schema 0.2.0)

- 조사 범위를 현재 저장소로 한정하고 원격 접속을 금지했다.
- 여러 host 저장소는 공통 지식을 공유 페이지에, host별 상태를 `current/<host>.md`에 둔다. 머신에 따라 달라지는 사실에는 host를 표시한다.

## 0.1.0

- `wiki-init`, `wiki-update` 첫 버전: 공통 절차, SCHEMA·페이지 template, preflight·lint 스크립트와 테스트, 설치 script.
