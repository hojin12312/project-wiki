# project-wiki

저장소마다 `wiki/`를 두고, 에이전트 세션이 바뀌어도 프로젝트 지식이 이어지게 하는 skill package다. 사용자가 실행하는 명령은 두 개다.

| Skill | 역할 |
|---|---|
| `wiki-init` | 저장소를 조사해 Wiki를 처음 구축한다 |
| `wiki-update` | 작업 단위가 끝난 뒤 Wiki를 저장소 상태와 대조해 증분 갱신한다. 구조 유지보수(index 분할, archive, rename, 모순 해소)도 담당한다 |

> **상태: 실험 단계.** macOS 2대와 Linux 1대, Claude Code·Pi·Devin·Codex에서 설치와 skill 인식을 확인했고, `/wiki-init`은 실제 저장소 두 곳에서 실행해 검토했다. `/wiki-update`는 아직 실사용 검증 전이다.

설계 의도와 판단 근거는 [`docs/design.md`](docs/design.md)에 있다. 구현과 다르면 이 README와 `core/`가 우선한다.

## 호출 방법

| Harness | 호출 |
|---|---|
| Claude Code | `/wiki-init`, `/wiki-update` |
| Pi | `/skill:wiki-init`, `/skill:wiki-update` |
| Devin CLI | `/wiki-init`, `/wiki-update` |
| Codex | `$wiki-init`, `$wiki-update` (또는 `/skills`) |

두 skill 모두 사용자가 명시적으로 호출할 때만 실행된다. 에이전트가 스스로 호출하지 않도록 Claude Code·Pi는 `disable-model-invocation`, Devin은 `triggers: [user]`, Codex는 `agents/openai.yaml`로 막아 두었다.

## 설치

자기 환경에 맞춰 고쳐 쓸 계획이면 **먼저 fork한 뒤 자신의 fork를 clone한다.** Skill은 실행할 때마다 `origin`에서 최신 버전을 받고, 개선 사항을 `origin`에 push한다(`core/protocol.md` §1, §10). 이 저장소를 그대로 clone하면 push 권한이 없어 개선 반영이 실패하고, 로컬 수정이 있는 동안은 자동 최신화도 건너뛴다.

```sh
# <you>는 자신의 GitHub 계정
git clone https://github.com/<you>/project-wiki.git ~/Projects/tools/project-wiki
sh ~/Projects/tools/project-wiki/install.sh
```

이 저장소의 이후 변경을 받으려면 upstream을 등록하고 원할 때 병합한다.

```sh
git -C ~/Projects/tools/project-wiki remote add upstream https://github.com/hojin12312/project-wiki.git
git -C ~/Projects/tools/project-wiki fetch upstream
git -C ~/Projects/tools/project-wiki merge upstream/main
```

고쳐 쓰지 않고 그대로 쓸 거라면 이 저장소를 바로 clone해도 된다. 여러 머신에서 쓰면 머신마다 clone하고 `install.sh`를 실행한다.

### 요구 사항

- Git, Python 3.8 이상(표준 라이브러리만 사용)
- macOS 또는 Linux
- 지원 harness: Claude Code, Pi, Devin CLI, Codex. 다른 harness는 `SKILL.md`를 읽을 수 있으면 대체로 동작하지만 확인하지 않았다.

### 자기 환경에 맞출 때 볼 곳

- Skill 문서와 SCHEMA template은 한국어로 쓰여 있다. 각 저장소의 Wiki 언어는 그 저장소의 규칙을 따른다(`wiki-language`).
- 정책(페이지 종류, status 값, 예산, host 구조): `core/SCHEMA.template.md`. 바꾸면 `core/SCHEMA_VERSION`을 올린다.
- 절차(Git 안전, instruction 파일 배치, 보고 형식): `core/protocol.md`
- 설치 위치: `install.sh`의 `targets()`

`install.sh`는 그 머신에 있는 harness에 맞춰 symlink를 만든다.

- `~/.claude/skills/wiki-*` → Claude Code
- `~/.agents/skills/wiki-*` → Pi, Devin CLI, Codex가 함께 읽는다

기존 파일이나 다른 곳을 가리키는 link는 덮어쓰지 않는다. `sh install.sh status`로 상태를 보고, `sh install.sh uninstall`로 이 package를 가리키는 link만 제거한다.

## 갱신과 개선

- `wiki-init`과 `wiki-update`는 실행할 때마다 먼저 이 저장소를 `git pull --ff-only`로 최신화한다. 미커밋 수정이 있거나 원격과 갈라져 있으면 갱신을 건너뛰고 경고한다.
- 사용 중에 skill 개선을 지시하면, 에이전트가 이 저장소에서 수정하고 테스트한 뒤 commit과 push까지 한다. 절차는 `core/protocol.md` §10에 있다.
- Symlink로 연결되어 있으므로, 이 저장소의 파일을 고치면 그 머신의 모든 harness에 바로 반영된다.
- 실행 보고에는 `Skill feedback` 절(모호했던 지침, 건너뛴 단계)이 들어간다. 실행 결과를 검토할 때는 `core/review-checklist.md`를 쓴다.
- 문제나 개선 제안은 Issue로 남긴다(template 2종). 동료의 수정은 fork에서 PR로 받는다.
- 버전마다 git tag(`v0.4.0` 등)와 GitHub Release를 만든다. 변경 내역은 [`CHANGELOG.md`](CHANGELOG.md)에 있다. 자동 최신화는 release가 아니라 `main`의 최신 commit을 따르므로, 특정 버전에 고정하려면 fork에서 해당 tag를 기준으로 쓴다.
- 버전은 두 가지다. `VERSION`은 skill package 버전이고, `core/SCHEMA_VERSION`은 SCHEMA 정책 버전이다. 기존 Wiki와는 SCHEMA 정책 버전만 비교한다.

## 구조

```text
project-wiki/
├── VERSION                  # skill package 버전
├── LICENSE                  # MIT
├── CHANGELOG.md
├── docs/design.md           # 초기 설계 명세
├── install.sh
├── core/
│   ├── protocol.md          # 두 skill이 공유하는 절차
│   ├── page-schema.md       # 페이지 template
│   ├── SCHEMA.template.md   # 저장소에 설치되는 wiki/SCHEMA.md 원본
│   ├── SCHEMA_VERSION       # SCHEMA 정책 버전
│   ├── review-checklist.md  # 실행 결과 검토 점검표
│   └── scripts/
│       ├── wiki_state.py    # self-update, preflight, host, anchor
│       └── wiki_lint.py     # structural lint
├── wiki-init/
│   ├── SKILL.md
│   ├── agents/openai.yaml   # Codex: 암묵적 호출 금지
│   └── core -> ../core
├── wiki-update/             # wiki-init과 같은 구성
└── tests/
```

## 개발

```sh
python3 -m unittest discover -s tests
python3 core/scripts/wiki_lint.py <repo>
python3 core/scripts/wiki_state.py preflight <repo>
```

Python 3.8 이상의 표준 라이브러리와 Git만 사용한다. macOS와 Linux에서 모두 동작해야 한다.

## 라이선스

MIT. [`LICENSE`](LICENSE)를 참고한다.
