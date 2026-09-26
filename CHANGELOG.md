# Changelog

버전 규칙은 `core/protocol.md` §12를 따른다. `VERSION`은 skill package 버전이고, 괄호 안의 schema는 `core/SCHEMA_VERSION`(SCHEMA 정책 버전)이다.

## 0.9.0 (schema 0.4.0)

- 새 Wiki의 `wiki-language` 기본값이 `en`으로 바뀐다. Wiki는 다음 에이전트 세션이 읽는 장기 기억이므로, README·docs가 한국어라는 이유만으로 Wiki를 한국어로 만들지 않는다. 사용자가 Wiki 언어를 명시하거나 저장소 지침이 Wiki 언어를 요구하거나, 프로젝트 성격상 원언어 유지가 실질적인 요구사항일 때만 다른 언어를 쓴다. `/wiki-init`의 확인 요약에 언어 결정을 보고한다.
- 기존 비영어 Wiki는 skill 갱신이나 `/wiki-update`가 자동 번역하지 않는다. 사용자가 승인한 English-first migration에서는 bootstrap(`index.md`·`overview.md`·이 host의 current)만 먼저 영어화하고 `wiki-language`를 `en`으로 바꾸며, architecture·components·decisions·experiments 같은 페이지는 실질적으로 수정되거나 bootstrap에 편입될 때 점진적으로 전환한다. `archive/`·과거 `log.md`·superseded 기록은 그대로 두고, "한국어 페이지가 남아 있다"는 이유만으로 실행이 편집을 만들지 않으므로 반복 `/wiki-update`는 no-op이 될 수 있다.
- 번역은 literal translation이 아니라 의미 보존이 목표다. 조건·불확실성·범위·예외·부정·trade-off의 강도와 관찰/추정 구분을 유지하고, `may`→`will`, `partially validated`→`validated`, 사용자 선호→hard requirement, 가설→사실 같은 승격을 금지한다. 번역이 불확실하면 원문과 `Translation note:`를 남긴다. 정확한 wording이 정보를 담는 경우(사용자 인용, 요구사항 문구, UI 문자열, 오류 메시지, 명령 출력, 법률·도메인 용어)에는 영어 요약과 함께 원문을 유지한다(protocol §10).
- schema 0.4.0은 SCHEMA의 `wiki-language` 아래와 §5 Update Rules에 이 언어 정책을 설명하는 문단을 더한다. 기존 Wiki에는 승인 기반 최소 패치로 제안되며, 그 SCHEMA의 언어로 적고 `wiki-language` 값 자체는 바꾸지 않는다.
- 검증: Python 테스트 전부 통과. `tests/scenarios.md`에 S14(언어 정책)를 추가했고, 한국어 fixture Wiki에서 승인된 bootstrap-only 영어화(`wiki-language` `ko`→`en`, index·overview·current 전환, components·decisions·archive는 한국어 유지)와 조건부 rationale의 의미 보존을 수동 확인했다. 영어 Wiki에서는 언어 정책 때문에 새로 생기는 편집이 없다.

## 0.8.0 (schema 0.3.2)

- `preflight`의 untracked 집계를 `git ls-files -z --others --exclude-standard --directory --no-empty-directory`로 고쳐, 빈 디렉터리와 내용 전부가 제외된 디렉터리를 더 이상 세지 않는다. `untracked_basis`가 기준 명령과 집계 단위(축약 디렉터리/개별 파일)를 명시하며, 결과는 `git status --porcelain`의 `??` 항목과 같다(#21). 같은 이유로 dirty 목록과 staged 목록의 경로 파싱도 `-z`로 바꿔 공백·한글·개행이 있는 경로를 보존한다.
- 인라인 코드 경로 표기의 역할이 셋으로 나뉜다: evidence 링크, 재현 산출물(`<!-- wiki:not-preserved -->`), 로컬 위치·경계의 비증거 표기(`<!-- wiki:local-path -->`, 한 표기에만 적용)(#19, #22, #23). local-path는 접근이나 비밀값 기록 허가가 아니며 실제 Markdown 링크·보호 경로 링크를 면제하지 않는다. `not-preserved`를 clone·미커밋 소스에 붙여도 clone 경고는 사라지지 않는다. `log.md`의 과거 항목이 인용한 경로는 역사 기록이므로 현재 존재 여부로 다시 경고하지 않는다(링크·인코딩·Source HEAD·구조 검사는 유지). current에는 모든 untracked가 아니라 다음 작업에 필요한 경계만 남긴다.
- current 파일이 예산을 초과하거나 초과가 예상되면, 유지할 것과 정본 페이지로 옮길 것을 먼저 결정하고 스냅샷으로 한 번 다시 쓴 뒤 한 번만 측정한다(#24). `budget.current_sections`가 `## ` 섹션별 추정 토큰(제목·숫자만)을 보여 주고, `wiki_state.py budget .`이 Git 조사 없이 예산만 다시 측정한다. 예산 안의 작은 변경과 no-op에 재작성 의례를 강제하지 않으며, 중요한 요구사항·위험·결정 이유를 지우거나 예산을 임의로 올리지 않는다.
- dirty 상태의 기준선을 첫 preflight와 잠금의 `run_lock.dirty_baseline`이 함께 보존한다(#22, #23). 커밋 직전 dirty 목록은 baseline과 비교한다: baseline ∪ 이번 실행 편집만 남아 있고 diff가 자기 편집뿐이면 재승인 없이 진행하고, 둘 다 아닌 경로나 남이 쓴 diff는 멈춘다. `dirty_source`가 이번 작업 단위의 편집이면 편집 전에 선커밋 여부를 묻고, 승인된 소스 커밋 뒤 `head`·baseline·anchor를 다시 잡는다. 혼합 파일의 부분 커밋은 wiki 커밋이 아니라 별도의 검증된 Git 작업으로 먼저 처리하며, pathspec 커밋(`git commit -- <paths>`)은 index가 아니라 working tree를 기록하므로 부분 커밋 수단이 아님을 명시한다(#20).
- `changed_source`가 비어 있어도 이번 작업 단위의 산출물이 anchor 커밋 안에 들어갔을 수 있다는 점과 그 확인 절차를 `core/update.md` §3에 명시했다. 비대화형 이슈 생성은 `gh issue create --title ... --body-file ... --label ...`로 고쳤다(`--template`은 저장소 템플릿 이름이지 파일이 아니다)(#22). log Validation(이번 run의 검사)과 페이지의 검증 기록(같은 작업 단위의 도구 출력)의 구분과, 합의로 바뀐 보호 경로의 기록 경계를 공통 규칙에 명시했다(#23).
- schema 0.3.2는 §6 증거 규칙의 `wiki:local-path` 표기와 §13의 pathspec 커밋 설명을 더한 patch라 기존 Wiki에 경고가 생기지 않는다.

## 0.7.0 (schema 0.3.1)

- 잠금은 오래되어도 자동으로 교체하지 않는다. 0.6.0의 "1시간 뒤 교체"를 없앴다. `stale`은 사용자에게 알릴 표시일 뿐이며, 사용자가 이전 실행이 끝났다고 확인하면 `unlock --force --id <id>`로 그 잠금만 지운다(다른 잠금은 지우지 않는다). 사용자 질문은 편집 전이나 커밋 뒤에만 한다.
- 잠금을 잡을 때 `wiki/`와 instruction 파일의 스냅샷을 남기고, 커밋 직전 `preflight --lock-token`이 `edits_since_lock`으로 그 뒤 바뀐 파일을 보고한다. 목록이 이번 실행의 편집과 정확히 같고 diff에 자기 편집만 있을 때만 커밋한다. 같은 파일 안의 혼입은 diff 검토로만 찾을 수 있다고 명시했다.
- Wiki 실행 커밋은 `Project-Wiki-Run:` trailer가 있고 `wiki/`와 instruction 파일만 바꾼 커밋으로만 판정한다. `log.md`를 함께 고친 수동 커밋의 페이지·log·managed block도 검토 대상이 된다. 업그레이드 뒤 첫 update는 trailer 없는 이전 실행 커밋을 한 번 검토하고, 그 뒤로는 no-op이 된다.
- anchor는 Wiki 실행 커밋이 쓴 log 항목만 설정한다. 손으로 쓴 log 항목은 anchor를 옮기지 않고 `anchor.ignored_entries`로 보고되며, 검토 범위는 넓어지기만 한다. trailer 도입 전의 항목은 그대로 인정한다. 중단된 실행이 남긴 untracked Wiki 파일도 `dirty_wiki`에 포함한다.
- 검증: Python 테스트 55개와 동시 self-update 경합 실험(잠금 없이 24회 중 24회 skipped, 잠금 적용 시 0회) 외에 Claude Code headless 실행으로 새 init, 반복 no-op, trailer 없는 수동 page·log·CLAUDE.md 커밋 검토, 손으로 쓴 log 항목 무시, 동시 update 2개(한쪽 `held`), 프로젝트 테스트를 재실행하지 않는 평범한 update, 1시간 넘은 잠금에서 교체 없이 멈춤을 확인했다. 예산 안내(#18)는 문서 검토만 했다. 다른 Wiki는 0.7.0의 첫 update에서 trailer 없는 직전 실행 커밋을 한 번 검토한다.
- 공유 package의 self-update를 파일 잠금으로 한 번에 하나씩 실행한다(#17). 다른 self-update가 끝나지 않으면 `busy`를 반환하고, 진입점 `SKILL.md`가 지침을 읽기 전에 멈춘다.
- Wiki 실행은 자체 검사(preflight, lint, Git)만 항상 실행하고, 프로젝트 테스트·빌드·벤치마크는 기본적으로 다시 실행하지 않는다(#16). 작은 로컬 검사는 기록할 주장을 판정하는 데 필요하고, 기존 승인 범위 안이며, 몇 초 안에 부작용 없이 끝날 때만 허용한다. current의 Working은 근거(도구 관찰, 사용자 보고, `code read; not executed`)를 밝힌다.
- 비ASCII 언어는 같은 내용이어도 토큰 추정치가 더 크다는 점과, 예산은 크기 신호일 뿐이라는 점을 안내한다(#18). 초과하면 세부 내용을 정본 페이지로 옮기고, 중요한 기억을 지우거나 예산을 스스로 늘리지 않는다. 추정식과 기본 예산은 바꾸지 않았다.

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
