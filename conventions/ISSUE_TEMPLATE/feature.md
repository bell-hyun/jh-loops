---
name: Feature (agent-workable)
about: 자율 에이전트가 집어갈 수 있는 작업. `agent` 라벨로 opt-in 됩니다.
labels: ["agent"]
---

<!--
설계 §7. 파서는 아래 `## Depends-on` / `## Acceptance Criteria` 섹션을 읽습니다.
헤딩 텍스트를 바꾸지 마세요.
-->

## 목적 (Why)
<!-- 필수. 유저 스토리로 시작 -->
As <역할>, I want <무엇>, so that <왜>.

## 상세 (What / Context)
<!-- 선택 -->
배경, 범위, 비범위, 참고 링크, 제약사항.

## Depends-on
<!-- 없으면 비워두세요. 적힌 이슈가 전부 close돼야 작업이 시작됩니다. -->
-

## Acceptance Criteria
<!--
없으면 needs-spec 처리됩니다.
에이전트가 확실히 판정 가능한 항목만. 검증 명령을 직접 적으세요.
주관적("UI가 깔끔하다") 항목 금지 — 사람 검증은 PR 머지 직전 한 번뿐입니다.
-->
- [ ] 사용자가 X 하면 Y가 보인다
- [ ] `npm test` 통과
