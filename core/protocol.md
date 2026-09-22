# Project Wiki Protocol

`wiki-init`과 `wiki-update`가 함께 따르는 절차다. Wiki의 정책(무엇을 어떻게 저장하는가)은 각 저장소의 `wiki/SCHEMA.md`가 정본이고, 이 파일은 그 정책을 실행하는 절차를 정한다.

아래에서 `<skill-dir>`은 지금 실행 중인 skill 디렉터리(`SKILL.md`가 있는 곳)를 뜻한다. 공유 자원은 항상 `<skill-dir>/core/...` 경로로 접근하고, `..`을 조합한 경로를 쓰지 않는다.

## 1. Skill 자동 최신화

작업을 시작할 때 가장 먼저 실행한다.

```bash
python3 <skill-dir>/core/scripts/wiki_state.py self-update
```

- 출력의 `status`가 `updated`이고 `changed`에 `SKILL.md`나 `core/` 파일이 있으면, 이미 읽은 내용이 바뀐 것이다. 해당 파일을 다시 읽고 새 내용을 따른다.
- `skipped`(미커밋 수정, 원격과 갈라짐, 네트워크 실패, 시간 초과)면 경고를 사용자에게 한 줄로 알리고 현재 버전으로 계속한다. Package 저장소를 reset·stash·force하지 않는다.

## 2. Preflight

```bash
python3 <skill-dir>/core/scripts/wiki_state.py preflight <repo-root>
```

JSON 결과를 다음처럼 해석한다.

| 필드 | 의미와 행동 |
|---|---|
| `blockers` | 비어 있지 않으면 중단하고 사용자에게 알린다 |
| `host` | `mode`가 `multi`이면 `current_path`만 읽고 수정한다. `error`가 있으면 중단하고 어느 host인지 묻는다 |
| `staged` | 사용자가 미리 stage한 파일이다. 건드리지 않으며, pathspec commit으로 commit에서 제외된다 |
| `dirty_source` | 미커밋 source 변경이다. §5의 규칙을 따른다 |
| `dirty_instruction_files` | 사용자의 미커밋 변경이 있는 instruction 파일이다. managed block은 넣되 commit에서 뺀다(§5, §6) |
| `untracked_entries` | Update와 무관하면 무시한다. 읽거나 수정하지 않는다 |
| `ignored_wiki_files` | Git이 무시하는 Wiki 파일이다. 이름을 바꾸거나 사용자에게 알린다. `.gitignore`는 수정하지 않는다 |
| `anchor`, `changed_source` | 마지막 Wiki update 이후의 source 변경 범위다 |
| `schema_version`, `package_version` | major.minor가 다르면 사용자에게 알리기만 한다. SCHEMA를 자동 갱신하지 않는다. Patch 차이는 무시한다 |
| `upstream` | `behind`가 0보다 크면(마지막 fetch 기준) 사용자에게 알린다 |

## 3. 저장소 조사 원칙

- 조사 범위는 현재 저장소뿐이다. 다른 저장소, 다른 머신(SSH 등 원격 접속), 저장소 밖의 사용자 데이터는 조사하지 않는다. 다른 host의 hostname처럼 이 머신에서 알 수 없는 정보는 사용자에게 묻는다.
- 프로젝트 Wiki는 저장소마다 독립적으로 운영한다. 머신 사이에 공유되는 것은 이 skill package뿐이다. 다른 프로젝트나 머신 전체(fleet)를 설명하는 페이지를 만들지 않고, 다른 시스템은 이 저장소의 코드와 스크립트가 직접 다루는 연결 지점만 필요한 만큼 언급한다.
- Authority 순서는 SCHEMA §2를 따른다. 저장소가 Wiki와 대화보다 우선한다.
- Tracked 파일은 `git ls-files`로 파악한다. `node_modules/`, `vendor/`, `dist/`, `build/`, cache, 생성물, 모델 가중치, binary, 벤치마크 출력은 읽지 않는다.
- SCHEMA의 Protected Paths와 project instruction이 보호 대상으로 지정한 경로(예: 독립 Git 저장소인 clone)는 조사하거나 수정하지 않는다.
- 큰 파일은 전체를 읽지 않고 구조, entry point, interface부터 읽는다.
- 비밀값을 Wiki로 옮기지 않는다. 저장소에서 비밀값을 발견하면 위치만 사용자에게 알린다.

## 4. 저장 판단 기준

저장 여부가 애매하면 다음 질문으로 판단한다.

> 다음 달의 새 에이전트가 이 정보를 몰라서 시간이나 compute를 낭비하거나, 잘못된 설계 판단을 할 가능성이 있는가?

그렇다면 저장한다. 아니라면 Git history와 source에 맡긴다. 저장할 가치가 큰 정보는 architecture rationale, invariant, hard constraint, 코드에서 드러나지 않는 동작, subsystem 사이의 interface, A 대신 B를 고른 이유, 기각한 접근과 그 이유, 검증된 실험 결론, 알려진 blocker, 반복 절차, 현재 구현 성숙도다.

## 5. Git 안전 절차

- 사용하지 않는 명령: `git add -A`, `git commit -a`, `git reset --hard`, `git checkout -- .`, `git clean`, `git stash`, force push, destructive rebase.
- 미커밋 source 변경(`dirty_source`)이 있을 때:
  - 이번 작업에서 에이전트가 직접 바꾼 파일이고 범위가 명확하면, 사용자에게 먼저 commit할지 묻는다.
  - 그렇지 않으면 커밋된 상태만 Wiki에 반영하고, 미커밋 변경은 Wiki에 사실로 기록하지 않는다.
- Commit 순서:

  ```bash
  git diff --cached --name-only                                  # staged 확인 (preflight와 같음)
  git add wiki/ <수정한 instruction 파일>
  git ls-files --others --ignored --exclude-standard -- wiki/    # 출력이 없어야 한다
  git commit -m "docs(wiki): <message>" -- wiki/ <수정한 instruction 파일>
  ```

  Pathspec commit은 지정한 경로만 기록하므로, 사용자가 미리 stage한 다른 파일은 staged 상태로 남는다.
- Pathspec commit은 지정한 파일의 **변경 전체**를 기록한다. 따라서 preflight의 `dirty_instruction_files`에 있는 파일(사용자가 작업 중인 instruction 파일)은 commit 경로에 넣지 않는다. 그 파일에 넣은 managed block은 미커밋 상태로 두고, 보고에 "`<파일>`의 managed block은 사용자의 미커밋 변경과 섞여 commit하지 않았다"고 적는다.
- Push는 사용자가 요청할 때만 한다.
- 작업 도중 HEAD가 바뀌었으면(다른 에이전트의 commit 등) 오래된 가정으로 commit하지 않는다. Preflight를 다시 실행한다.

## 6. Instruction 파일과 managed block

Harness마다 project instruction 파일을 읽는 방식이 다르다.

- Claude Code: `CLAUDE.md`만 읽는다.
- Codex: `AGENTS.md`를 읽는다. `CLAUDE.md`는 설정(`project_doc_fallback_filenames`)에 등록한 경우에만, `AGENTS.md`가 없는 디렉터리에서 읽는다.
- Pi: 디렉터리마다 `AGENTS.override.md` → `AGENTS.md` → `CLAUDE.md` 순서로 처음 발견한 파일 하나만 읽는다.
- Devin: `AGENTS.md`와 `CLAUDE.md`를 모두 읽는다.

배치 규칙:

1. 두 파일이 모두 있으면 두 파일에 같은 block을 둔다. 예외는 `CLAUDE.md`가 `@AGENTS.md` 같은 import 문법으로 `AGENTS.md`를 실제로 불러오는 경우뿐이며, 이때는 `AGENTS.md`에만 둔다. 문장으로 다른 파일을 가리키는 것은 import가 아니다.
2. `CLAUDE.md`만 있으면 `CLAUDE.md`에만 둔다. `AGENTS.md`를 새로 만들지 않는다. 새로 만들면 Pi가 `CLAUDE.md`를 더 이상 읽지 않는다. Codex를 쓴다면 사용자에게 `project_doc_fallback_filenames` 설정을 안내한다.
3. `AGENTS.md`만 있으면 `AGENTS.md`에 두고, Claude Code를 쓴다면 `CLAUDE.md`를 만들지 사용자에게 묻는다.
4. 둘 다 없으면 어느 파일을 만들지 사용자에게 묻는다.
5. 파일 전체를 덮어쓰지 않는다. `<!-- project-wiki:start -->`와 `<!-- project-wiki:end -->` 사이만 관리하고, 이미 있으면 그 사이만 갱신한다.
6. 넣을 파일이 preflight의 `dirty_instruction_files`에 있으면, 6단계 확인 요약에 "이 파일에는 미커밋 변경이 있어 block을 commit하지 않는다"고 미리 알린다(§5).
7. Instruction 파일에 Wiki와 충돌하는 정책(예: "인계 문서를 만들지 않는다", "상태는 commit message로만 남긴다")이 있으면, 사용자에게 확인한 뒤 Wiki를 예외로 두도록 해당 문구만 고친다.

Block 내용(Wiki 언어가 한국어인 경우):

```markdown
<!-- project-wiki:start -->
## Project Wiki

이 저장소는 `wiki/`를 프로젝트의 장기 기억으로 사용한다.

큰 작업을 시작하기 전에:
1. `wiki/index.md`와 `wiki/overview.md`를 읽는다.
2. `wiki/current.md`를 읽는다.
3. index에서 이번 작업과 관련된 페이지만 골라 읽는다.
4. 중요한 주장은 실제 코드와 대조한다. 저장소가 Wiki보다 우선한다.

current 파일은 인계 문서가 아니라 `/wiki-update`가 저장소와 대조해 다시 계산하는 상태 snapshot이다. 작업 진행 기록은 commit message에 남긴다.
의미 있는 작업 단위를 마치면 사용자에게 `/wiki-update` 실행을 제안한다.
<!-- project-wiki:end -->
```

여러 host 저장소는 2번을 다음으로 바꾼다: "`hostname -s`와 `wiki/SCHEMA.md`의 Hosts 대응표로 자기 host를 확인하고, `wiki/current/<host>.md`만 읽는다." Wiki 언어가 영어면 같은 내용을 영어로 쓴다.

## 7. Lint

```bash
python3 <skill-dir>/core/scripts/wiki_lint.py <repo-root>
```

- `ERROR`가 있으면 exit code 1이다. Commit하기 전에 모두 해결한다.
- `WARN`은 판단해서 처리한다. 고치지 않은 warning은 보고에 포함한다.
- Script는 semantic 판단을 하지 않는다. 코드와의 모순, 오래된 상태, 중복은 에이전트가 판단한다.

## 8. 실패와 불확실성

- 테스트 실패, 결론 없는 벤치마크, 해소되지 않은 모순, 읽을 수 없는 파일, 안전하지 않은 Git 상태가 있으면 성공을 가장하지 않는다.
- Wiki에는 실제 상태를 적는다(예: `Partially implemented. Validation currently fails at ...`). PASS하지 않은 것을 PASS로 기록하지 않는다.
- 저장소에 자체 commit 정책이 있으면 그 정책을 우선한다.

## 9. 사용자 보고

짧게 보고한다. 세션 전체를 다시 설명하지 않는다.

```text
Project Wiki updated.

Source changes reviewed: <anchor>..<head>
Wiki:
- updated components/<page>.md
- updated current.md
Validation:
- structural lint: PASS
- stale claims corrected: <n>
- unresolved items: <n>
Commit: docs(wiki): <message>
```

## 10. Skill 자체 개선

사용 중에 사용자가 wiki skill의 개선을 지시하면, 에이전트는 개선 사항을 skill package 저장소에 반영하고 공유한다. 이 지시는 package 저장소에 대한 commit과 push를 허락한 것으로 본다.

1. Package 위치를 확인한다: `python3 <skill-dir>/core/scripts/wiki_state.py self-update`의 `package_dir`. Symlink가 가리키는 실제 저장소에서 수정한다.
2. 수정 전에 `git -C <package_dir> pull --ff-only`로 최신 상태를 받는다.
3. 지시받은 범위만 수정한다. `SKILL.md`는 150줄 이하로 유지한다.
4. 테스트를 실행한다: `python3 -m unittest discover -s <package_dir>/tests`.
5. `VERSION`을 올린다. 기능 변경이 없는 수정(문구 명확화, 오타, 버그 수정)은 patch, `core/SCHEMA.template.md` 정책의 호환되는 추가나 기능 추가는 minor, 호환되지 않는 변경은 major다. SCHEMA의 `schema-version`과의 비교는 major.minor만 하므로 patch는 기존 Wiki에 경고를 만들지 않는다. 이미 Wiki가 있는 저장소의 SCHEMA는 자동으로 바꾸지 않는다.
6. 수정한 파일만 지정해서 commit하고 push한다: `git -C <package_dir> commit -m "<type>: <요약>" -- <files>` → `git -C <package_dir> push`.
7. Push가 거절되면 `git -C <package_dir> pull --rebase`로 자신의 commit만 다시 올린 뒤 push한다. 충돌이 나면 멈추고 사용자에게 알린다.
8. 다른 머신은 다음 `/wiki-init` 또는 `/wiki-update` 실행 때 자동으로 최신화된다.
