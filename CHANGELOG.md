# Changelog

버전 규칙은 `core/protocol.md` §10을 따른다. `VERSION`은 skill package 버전이고, 괄호 안의 schema는 `core/SCHEMA_VERSION`(SCHEMA 정책 버전)이다.

## 0.4.1

- Issue template 2종(Skill feedback / 개선 제안, 버그)과 PR template을 추가했다.
- 바로 고치지 않는 개선 후보는 개인 환경 정보를 일반화해 Issue로 남긴다(`core/protocol.md` §10).
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
