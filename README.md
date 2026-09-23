# project-wiki

project-wiki는 저장소마다 `wiki/` 폴더를 두고, AI 코딩 에이전트의 세션이 바뀌어도 프로젝트 지식이 이어지도록 돕는 skill package입니다. 사용자가 실행하는 명령은 다음 두 가지입니다.

| Skill | 역할 |
|---|---|
| `wiki-init` | 저장소를 조사해서 Wiki를 처음 만듭니다. |
| `wiki-update` | 작업 단위가 끝난 뒤, Wiki를 저장소의 실제 상태와 대조해서 필요한 부분만 갱신합니다. index 분할, archive 이동, 페이지 이름 변경, 모순 해소 같은 구조 유지보수도 이 명령이 담당합니다. |

> **상태: 실험 단계입니다.** macOS 머신 2대와 Linux 머신 1대에서, Claude Code·Pi·Devin·Codex·OpenCode가 skill을 인식하는 것까지 확인했습니다. `/wiki-init`은 실제 저장소 여러 곳에서 실행한 결과를 검토했고, `/wiki-update`는 실제 저장소에서 한 번 실행해 검토했습니다.

설계 의도와 판단 근거는 [`docs/design.md`](docs/design.md)에 정리되어 있습니다. 이 문서와 구현이 서로 다르면, 이 README와 `core/` 폴더의 내용이 우선합니다.

## 호출 방법

아래 표에서 harness는 skill을 실행하는 에이전트 도구를 뜻합니다.

| Harness | 호출 방법 |
|---|---|
| Claude Code | `/wiki-init`, `/wiki-update` |
| Pi | `/skill:wiki-init`, `/skill:wiki-update` |
| Devin CLI | `/wiki-init`, `/wiki-update` |
| Codex | `$wiki-init`, `$wiki-update` (또는 `/skills`에서 선택) |
| OpenCode | 자연어 호출(예: "wiki-init 실행해줘") — `skill` tool이 로드 |

두 skill은 사용자가 직접 호출할 때만 실행됩니다. 에이전트가 스스로 판단해서 호출하는 일을 막기 위해, 도구마다 다음 설정을 넣어 두었습니다.

- Claude Code와 Pi: `SKILL.md`의 `disable-model-invocation`
- Devin: `SKILL.md`의 `triggers: [user]`
- Codex: `agents/openai.yaml`의 암묵적 호출 금지 설정
- OpenCode: 해당 frontmatter 플래그를 지원하지 않으므로, `SKILL.md` description의 "Run only when the user explicitly invokes" 문구에 의존합니다

## 설치

자기 환경에 맞춰 고쳐 쓸 계획이라면, **먼저 이 저장소를 fork하고 자신의 fork를 clone하십시오.** fork는 GitHub에서 저장소를 자기 계정으로 복제하는 기능입니다.

fork가 필요한 이유는 다음과 같습니다. skill은 실행할 때마다 `origin` 원격 저장소에서 최신 버전을 받아 오고, 사용자가 개선을 지시하면 수정 내용을 `origin`에 push합니다(`core/protocol.md` §1, §12). 이 저장소를 fork하지 않고 그대로 clone하면, push 권한이 없어서 개선 사항을 반영할 수 없습니다. 또한 로컬에서 수정한 내용이 남아 있는 동안에는 자동 최신화가 매번 건너뛰어집니다.

```sh
# <you>에는 자신의 GitHub 계정을 넣습니다.
git clone https://github.com/<you>/project-wiki.git ~/Projects/tools/project-wiki
sh ~/Projects/tools/project-wiki/install.sh
```

이후에 이 원본 저장소(upstream)의 변경 사항을 받고 싶다면, upstream을 원격 저장소로 등록한 뒤 원하는 시점에 병합합니다.

```sh
git -C ~/Projects/tools/project-wiki remote add upstream https://github.com/hojin12312/project-wiki.git
git -C ~/Projects/tools/project-wiki fetch upstream
git -C ~/Projects/tools/project-wiki merge upstream/main
```

고쳐 쓰지 않고 그대로 사용할 계획이라면, 이 저장소를 바로 clone해도 됩니다. 여러 머신에서 사용한다면 머신마다 clone하고 `install.sh`를 실행합니다.

### 요구 사항

- Git과 Python 3.8 이상이 필요합니다. Python은 표준 라이브러리만 사용합니다.
- macOS와 Linux를 지원합니다.
- 확인한 harness는 Claude Code, Pi, Devin CLI, Codex, OpenCode입니다. 다른 harness도 `SKILL.md`를 읽을 수 있다면 대체로 동작하겠지만, 확인하지는 않았습니다.

### 설치 스크립트가 하는 일

`install.sh`는 그 머신에 설치된 harness를 확인하고, 각 harness가 skill을 찾는 폴더에 symlink를 만듭니다. symlink는 다른 위치의 파일이나 폴더를 가리키는 연결 파일입니다.

- `~/.claude/skills/wiki-*`: Claude Code가 읽습니다.
- `~/.agents/skills/wiki-*`: Pi, Devin CLI, Codex가 함께 읽습니다.
- `~/.config/opencode/skills/wiki-*`: OpenCode가 읽습니다.

같은 이름의 파일이 이미 있거나, 같은 이름의 link가 다른 곳을 가리키고 있으면 덮어쓰지 않고 멈춥니다. `sh install.sh status`로 연결 상태를 확인할 수 있고, `sh install.sh uninstall`을 실행하면 이 package를 가리키는 link만 제거합니다.

### 자기 환경에 맞출 때 수정할 곳

- 에이전트가 읽는 문서(`SKILL.md`와 `core/`의 문서)는 영어로 쓰여 있습니다. 사람이 읽는 문서(이 README, CHANGELOG, Issue·PR template, 설계 명세)는 한국어로 쓰여 있습니다.
- 각 저장소에 만들어지는 Wiki의 언어는 그 저장소의 규칙을 따릅니다(SCHEMA의 `wiki-language`). skill 문서가 영어여도, 한국어 저장소의 Wiki는 한국어로 작성됩니다.
- 페이지 종류, status 값, 크기 예산, host 구조 같은 정책은 `core/SCHEMA.template.md`에서 정합니다. 정책을 바꿨다면 `core/SCHEMA_VERSION`도 올립니다.
- Git 안전 절차, instruction 파일에 안내를 넣는 방법, 보고 형식 같은 공통 규칙은 `core/protocol.md`에서 정하고, 명령별 단계는 `core/init.md`와 `core/update.md`에서 정합니다. `SKILL.md`는 진입점일 뿐이므로 절차를 넣지 않습니다. harness가 `SKILL.md`를 업데이트 전에 읽어 두어도 실제 절차는 업데이트 뒤 디스크에서 읽히게 하기 위해서입니다.
- 설치 위치는 `install.sh`의 `targets()` 함수에서 정합니다.

## 갱신과 개선

- `wiki-init`과 `wiki-update`는 실행할 때마다 먼저 이 저장소를 `git pull --ff-only`로 최신 상태로 맞춥니다. 로컬에 커밋하지 않은 수정이 있거나 원격 저장소와 이력이 갈라져 있으면, 갱신을 건너뛰고 경고만 표시합니다.
- 사용 중에 skill의 개선을 지시하면, 에이전트가 이 저장소에서 파일을 수정하고 테스트한 뒤 commit과 push까지 진행합니다. 자세한 절차는 `core/protocol.md` §12에 있습니다.
- skill이 symlink로 연결되어 있으므로, 이 저장소의 파일을 수정하면 그 머신의 모든 harness에 즉시 반영됩니다.
- 실행 보고의 마지막에는 `Skill feedback` 절이 들어갑니다. 이 절에는 지침이 모호해서 추측한 부분이나 건너뛴 단계가 적힙니다. 실행 결과를 검토할 때는 `core/review-checklist.md`를 사용합니다.
- 문제나 개선 제안은 Issue로 남겨 주십시오. Issue template은 "Skill feedback / 개선 제안"과 "버그" 두 가지입니다. 다른 사람의 수정은 fork에서 보낸 PR로 받습니다.
- 버전마다 git tag(`v0.4.0` 등)와 GitHub Release를 만들고, 변경 내역은 [`CHANGELOG.md`](CHANGELOG.md)에 기록합니다. 자동 최신화는 release가 아니라 `main` 브랜치의 최신 commit을 따릅니다. 따라서 특정 버전에 고정해서 쓰고 싶다면, 자신의 fork에서 해당 tag를 기준으로 사용하십시오.
- 버전은 두 종류입니다. `VERSION`은 skill package의 버전이고, `core/SCHEMA_VERSION`은 SCHEMA 정책의 버전입니다. 이미 만들어진 Wiki와 비교할 때는 SCHEMA 정책 버전의 major.minor만 사용합니다.
- 설치된 Wiki의 SCHEMA가 template보다 오래되었다면, `/wiki-update`가 정상 갱신을 끝낸 뒤 `core/schema-migrations.md`를 바탕으로 빠진 항목만 최소 패치로 제안합니다. 사용자가 승인해야 적용되고, 언어·Hosts·Protected Paths·예산 같은 로컬 설정은 바뀌지 않습니다. 보류하면 이후 실행은 다시 묻지 않습니다.
- 같은 checkout에서 Wiki 명령을 두 개 동시에 실행하면 뒤의 실행이 잠금 때문에 멈추고, 잠금을 가진 명령과 시작 시각을 알립니다. 잠금은 오래되어도 자동으로 교체되지 않습니다. 이전 실행이 비정상 종료된 것이 확실할 때만, 안내된 명령 `python3 core/scripts/wiki_state.py unlock <repo> --force --id <id>`로 그 잠금만 지웁니다.
- 여러 harness가 동시에 시작해도 package의 self-update는 한 번에 하나씩 실행됩니다. 다른 self-update가 끝나지 않으면 `busy`로 멈추고, 교체 중인 지침을 읽지 않습니다.

## 구조

```text
project-wiki/
├── VERSION                  # skill package 버전
├── LICENSE                  # MIT
├── CHANGELOG.md
├── docs/design.md           # 초기 설계 명세
├── install.sh
├── core/
│   ├── protocol.md          # 두 skill이 공유하는 규칙
│   ├── init.md              # /wiki-init 절차
│   ├── update.md            # /wiki-update 절차
│   ├── schema-migrations.md # SCHEMA 정책 버전별 변경 요약(승인 기반 이전용)
│   ├── page-schema.md       # 페이지 template
│   ├── SCHEMA.template.md   # 저장소에 설치되는 wiki/SCHEMA.md 원본
│   ├── SCHEMA_VERSION       # SCHEMA 정책 버전
│   ├── review-checklist.md  # 실행 결과 검토 점검표
│   └── scripts/
│       ├── wiki_state.py    # self-update, preflight, host, anchor, lock/unlock
│       └── wiki_lint.py     # structural lint
├── wiki-init/
│   ├── SKILL.md             # 진입점: self-update 후 core 절차를 읽게 한다
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

스크립트는 Python 3.8 이상의 표준 라이브러리와 Git만 사용하며, macOS와 Linux에서 모두 동작해야 합니다.

## 라이선스

이 저장소는 MIT 라이선스를 따릅니다. 자세한 내용은 [`LICENSE`](LICENSE)를 참고하십시오.
