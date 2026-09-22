# Wiki Run Review Checklist

`/wiki-init`이나 `/wiki-update`가 끝난 뒤, 그 실행이 Wiki의 본래 목적에 맞게 동작했는지 검토할 때 쓴다. 검토는 실행한 세션이 아니라 사용자나 다른 에이전트가 한다. 실행한 에이전트는 자기 판단의 문제를 알아차리기 어렵기 때문이다.

근거로 삼는 자료:

- Wiki commit: `git show --stat HEAD`, `git show HEAD`
- `python3 <skill-dir>/core/scripts/wiki_lint.py <repo>`
- `wiki/log.md`의 마지막 entry
- 실행 보고와 그 안의 `Skill feedback`
- 필요하면 실행 세션의 기록(harness마다 위치가 다르다)

각 항목에 문제가 있으면 근거(파일, 줄, 명령 출력)와 함께 적는다.

## 1. 범위

- [ ] 현재 저장소만 조사했는가? 다른 저장소나 다른 머신(SSH 등)을 조사하지 않았는가?
- [ ] 다른 프로젝트나 머신 전체(fleet)를 설명하는 페이지를 만들지 않았는가? 다른 시스템은 이 저장소 코드가 직접 다루는 연결 지점만 언급했는가?
- [ ] Protected Paths와 독립 Git 저장소를 읽거나 수정하지 않았는가?
- [ ] Git 저장소의 하위 폴더에서 실행했다면, 대상 범위(저장소 전체)가 사용자의 의도와 맞았는가?

## 2. Git 안전

- [ ] Commit에 `wiki/`와 managed block을 넣은 instruction 파일만 들어갔는가?
- [ ] 사용자의 미커밋 작업(특히 `dirty_instruction_files`)이 commit에 섞이지 않았는가?
- [ ] 사용자가 미리 stage한 파일이 staged 상태로 남아 있는가?
- [ ] Push하지 않았는가? 금지 명령(`git add -A`, `reset --hard`, `stash` 등)을 쓰지 않았는가?

## 3. 사실 정확성

- [ ] Current의 상태가 실제 구현과 맞는가? TODO나 stub을 완료로 적지 않았는가?
- [ ] 실행하지 않은 테스트나 검증을 PASS로 적지 않았는가?
- [ ] 검증하지 않은 주장이 `Unknown`, `Not yet verified`, `Hypothesis`로 표시되어 있는가?
- [ ] Runtime 사실에 관측 날짜와 확인 방법이 붙어 있는가?
- [ ] 여러 host 저장소라면, 머신에 따라 달라지는 사실에 host 이름이 붙어 있는가? 다른 host의 current 파일은 바뀌지 않았는가?
- [ ] 목표와 non-goal을 구현에서 추론하지 않았는가?
- [ ] 비밀값을 옮기지 않았는가?

## 4. 압축과 구조

- [ ] Bootstrap(index, overview, current)이 예산 안에 있고, 이것만 읽어도 프로젝트가 무엇이고 지금 어디까지 왔는지 알 수 있는가?
- [ ] 페이지 수가 적절한가? File-per-page나 사소한 decision·experiment 페이지가 없는가?
- [ ] 기존 정본 문서를 복사하지 않고 link했는가? 같은 개념을 두 페이지에서 설명하지 않는가?
- [ ] `/wiki-update`라면 관련 없는 페이지를 바꾸지 않았는가? Current를 append하지 않고 다시 계산했는가?
- [ ] 대화 요약이나 작업 과정이 Wiki에 들어가지 않았는가?

## 5. 절차

- [ ] 시작할 때 self-update와 preflight를 실행했는가?
- [ ] `/wiki-init`이라면 파일을 만들기 전에 사용자 확인을 받았는가? 확인 요약에 host 구조, 페이지 목록, 충돌 정책, managed block 위치가 있었는가?
- [ ] Structural lint가 PASS인가? 남은 warning을 보고했는가?
- [ ] 보고에 `Skill feedback`이 있는가?

## 결과 처리

- Wiki 내용의 문제: 해당 저장소에서 바로 고치거나 다음 `/wiki-update`에서 반영한다.
- Skill의 문제: 사용자가 개선을 지시하면 `core/protocol.md` §10에 따라 skill package에 반영한다.
- 같은 검토를 여러 번 반복하게 되면, 이 checklist를 별도 skill로 만드는 것을 검토한다.
