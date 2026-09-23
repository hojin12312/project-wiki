## 변경 내용

<!-- 무엇을 왜 바꿨는지 2~5줄로 적습니다. 관련 Issue가 있으면 `Fixes #<번호>`를 적습니다. -->

## 확인

- [ ] `python3 -m unittest discover -s tests` 통과
- [ ] `SKILL.md`는 진입점으로만 두고, 절차는 `core/`에 둠
- [ ] `VERSION`을 규칙대로 올림(기능 변경 없음 = patch, 기능 추가 = minor)
- [ ] SCHEMA template을 바꿨다면 `core/SCHEMA_VERSION`을 올리고 `core/schema-migrations.md`에 변경 요약을 추가함
- [ ] `CHANGELOG.md`에 새 버전 절을 추가함
- [ ] 머신 이름, 내부 프로젝트 이름, 경로, 비밀값이 들어 있지 않음
