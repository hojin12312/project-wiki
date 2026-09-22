# Wiki Schema

<!--
이 파일은 이 저장소 Wiki의 운영 계약이다.
/wiki-update는 일반적인 프로젝트 작업 때문에 이 파일을 수정하지 않는다.
Wiki 정책 자체를 바꿀 때만, 사용자의 승인을 받아 수정한다.
-->

schema-version: {{SCHEMA_VERSION}}
wiki-language: {{WIKI_LANGUAGE}}

## 1. Purpose

이 Wiki는 미래의 에이전트 세션이 과거 대화 없이 프로젝트를 이해하도록 돕는 압축된 semantic memory다. 저장소에서 다시 알아내기 어렵거나 비용이 큰 지식만 보존한다. 채팅 기록의 요약본이 아니다.

## 2. Authority Hierarchy

충돌하면 위쪽이 우선한다.

1. Actual implementation
2. Tests and executable validation
3. Benchmark / experiment artifacts
4. Git history
5. 사람이 작성하거나 검토한 문서
6. Wiki, 그리고 이전 에이전트가 작성한 문서와 skill
7. Current conversation

- Wiki가 코드와 다르면 Wiki를 고친다. Wiki에 맞추려고 코드를 바꾸지 않는다.
- Runtime 사실(서비스 상태, 모델 파일, launchd·systemd 상태)에는 관측 날짜와 확인 방법을 함께 적고, 그 사실을 관측한 host의 current 파일에만 둔다.
- 목표와 요구사항은 사용자와 maintainer가 정한다. 현재 구현만 보고 목표를 추론하지 않는다.

## 3. Page Taxonomy

| 경로 | 용도 |
|---|---|
| `index.md` | Router. 모든 substantive page를 link와 한 줄 요약으로 나열한다 |
| `overview.md` | 안정적인 장기 context: 목적, non-goals, hard constraint, 상위 구조, 용어 |
| `current.md` 또는 `current/<host>.md` | 현재 상태 snapshot. 인계 문서가 아니다 |
| `log.md` | Update audit trail. Bootstrap에서 읽지 않는다 |
| `architecture/` | 구조와 rationale |
| `components/` | Subsystem의 책임, interface, invariant |
| `decisions/NNNN-<slug>.md` | ADR. 번호는 4자리로 증가시킨다 |
| `experiments/` | 이후 설계 판단에 영향을 준 실험 |
| `runbooks/` | 반복 수행하는 절차 |
| `archive/` | Superseded 기록. Bootstrap에서 읽지 않는다 |

필요 없는 category는 만들지 않는다. 새 category는 기존 category로 표현할 수 없을 때만 만들고, 이 표에 추가한다(정책 변경).

## 4. Page Format

- 파일 이름은 영어 kebab-case로 짓는다. `.gitignore` 패턴(예: `*token*`, `*secret*`)에 걸리는 이름을 쓰지 않는다.
- `index.md`, `log.md`, `SCHEMA.md`를 제외한 모든 페이지는 frontmatter를 가진다.

  ```yaml
  ---
  title: <제목>
  type: overview | current | architecture | component | decision | experiment | runbook
  status: <아래 vocabulary>
  updated: YYYY-MM-DD
  ---
  ```

- Status vocabulary:
  - overview, current, architecture, component, runbook: `current`, `partial`, `deprecated`, `archived`
  - decision: `proposed`, `accepted`, `rejected`, `superseded`
  - experiment: `planned`, `running`, `completed`, `inconclusive`
- `updated`는 내용이 실제로 바뀔 때만 갱신한다.
- 본문 template은 skill package의 `core/page-schema.md`를 따른다.
- 경로는 repository-root 기준으로 적는다. Line number는 적지 않는다. 필요하면 symbol 이름을 적는다.

## 5. Update Rules

- 새 페이지보다 기존 페이지 수정을 우선한다. 3~5개 bullet로 충분한 내용, 파일 하나에 대한 설명, 일회성 디버깅 기록은 새 페이지로 만들지 않는다.
- Minimum necessary edit를 한다. 관련 없는 문장이나 서식을 바꾸지 않는다.
- Current 파일은 append하지 않고 매번 다시 계산한다. 해결된 항목은 제거하거나 정본 페이지로 옮긴다.
- `overview.md`는 scope, hard constraint, 상위 구조, canonical reference, 주요 subsystem이 바뀔 때만 수정한다.
- `index.md`는 페이지를 추가·rename·archive하거나 요약이 의미 있게 바뀔 때 갱신한다.
- 페이지 사이의 모순은 저장소를 조사하여 정본을 고친다. 판단할 수 없으면 `Unresolved contradiction`으로 표시한다.
- 한 concept는 정본 페이지 하나에서만 설명하고, 다른 페이지는 link한다. 기존 문서가 정본이면 복사하지 않고 link한다.

## 6. Evidence Rules

- 중요한 주장에는 근거 위치(구현 경로, 테스트, 결과물)를 적는다.
- 확실하지 않으면 `Unknown`, `Not yet verified`, `Hypothesis`, `Partially validated`로 표시한다.
- Experiment는 measurement와 interpretation을 분리하고, 측정한 host와 하드웨어를 적는다. 다른 host에서 검증하기 전에는 결과를 일반화하지 않는다.
- 결과물이 gitignored·untracked 경로에 있으면 핵심 수치, 실행 명령, source revision을 페이지에 직접 적는다. Untracked 경로를 evidence로 link하지 않는다.
- 비밀값(API key, token, password, private key, 인증 파일 내용)을 기록하지 않는다.

## 7. Context-loading Rules

새 작업을 시작할 때는 다음 순서로 읽는다.

1. `index.md`
2. `overview.md`
3. `current.md` (여러 host 저장소는 자기 host의 `current/<host>.md`만)
4. 이번 작업과 관련된 페이지만

모든 decision, experiment, runbook, `log.md` 전체, `archive/`는 읽지 않는다. 최근 이력이 필요하면 `tail -n 60 wiki/log.md`만 읽는다.

## 8. Anti-bloat Rules

1. Chat transcript와 세션 요약을 저장하지 않는다.
2. Git이 이미 설명하는 사소한 변경을 반복하지 않는다.
3. 새 페이지보다 기존 페이지 수정을 우선한다.
4. Current 파일은 append-only가 아니며, 해결된 항목은 제거한다.
5. 역사적 세부 사항은 archive나 decision history로 옮긴다.
6. File-per-page 구조를 만들지 않는다.
7. 긴 code block을 복사하지 않고 source path를 적는다.
8. 미래의 판단 비용을 줄이는 정보만 보존한다.

## 9. Budgets

Token 수는 추정치다. 초과하면 lint가 warning을 낸다.

<!-- wiki:budgets:start -->
current_tokens: 2000
bootstrap_tokens: 6000
<!-- wiki:budgets:end -->

## 10. Hosts

여러 머신에서 사용하는 저장소만 채운다. 비어 있으면 단일 host 저장소이며 `current.md`를 사용한다.

형식은 `<host-name>: <hostname -s 값>[, <다른 값>...]`이다.

<!-- wiki:hosts:start -->
{{HOSTS}}
<!-- wiki:hosts:end -->

- 에이전트는 자기 host의 current 파일만 읽고 수정한다. 다른 host의 current 파일은 byte 단위로도 바꾸지 않는다.
- 현재 hostname이 대응표에 없으면 어떤 current 파일에도 쓰지 않고 중단한 뒤 사용자에게 묻는다.

## 11. Protected Paths

Wiki 작업은 다음 경로를 조사하거나 수정하지 않는다. 한 줄에 경로 하나씩 적는다.

<!-- wiki:protected:start -->
{{PROTECTED_PATHS}}
<!-- wiki:protected:end -->

## 12. Lint Rules

- Structural lint: `python3 <skill-dir>/core/scripts/wiki_lint.py <repo-root>`. Structural error가 있으면 exit code 1이며, commit하기 전에 모두 해결한다.
- Semantic lint: `/wiki-update`가 수행한다(코드와의 모순, 오래된 상태, 중복, current 비대화 등).

## 13. Git Rules

- Wiki commit은 pathspec commit으로 한다: `git commit -m "docs(wiki): ..." -- wiki/ <수정한 instruction 파일>`.
- 금지: `git add -A`, `git commit -a`, `git reset --hard`, `git checkout -- .`, `git clean`, `git stash`, force push.
- Push는 사용자가 요청할 때만 한다.
- Commit message: `docs(wiki): initialize project memory`, `docs(wiki): update project memory after <topic>`.
- `log.md` entry는 다음 형식을 따른다. 모든 entry에는 `Source HEAD:` 줄이 있어야 한다.

  ```markdown
  ## [YYYY-MM-DD] update | <topic>

  Host: <host-name>              (여러 host 저장소만)
  Source HEAD: <sha>
  Wiki:
  - updated <page>
  Validation:
  - <실제로 실행한 검증과 결과>
  Open:
  - <남은 일>
  ```
