# 이슈 기반 자율 개발 워크플로우 (설계)

> 이 문서는 **gifra와 무관한, 어떤 레포에든 붙일 수 있는 독립 도구**의 설계다.
> gifra 레포에 임시로 보관하고 있을 뿐이며, 구현 시에는 별도 레포로 분리한다.
> 목적: GitHub 이슈를 단일 진실의 원천(SSoT)으로 삼아, 열린 이슈를 자동으로
> 골라 개발 → 검증 → PR까지 돌리는 루프를 만든다.

---

## 1. 한 줄 요약

> **결정론적 스크립트 오케스트레이터**가 주기적으로 GitHub 이슈를 폴링해, 작업
> 가능한(actionable) 이슈 하나를 골라 worktree를 만들고, **교체 가능한 LLM CLI
> 에이전트**(opencode / claude / codex)로 개발과 검증을 돌린 뒤, 통과하면 PR을
> 연다. 사람 검증은 PR 머지 직전 단 한 번.

---

## 2. 핵심 원칙 (이게 깨지면 전부 깨진다)

1. **상태는 전부 GitHub에 산다.** 매 틱은 cold start다. 에이전트 머릿속에 "지금
   #5 작업 중" 같은 기억은 남지 않는다. "작업 중" 같은 모든 상태는 라벨/assignee로
   GitHub에 박는다. → 루프는 틱 간 stateless.
2. **AC(Acceptance Criteria)가 "완료"의 유일한 정의다.** 별도 게이트 설정 파일을
   두지 않는다. 검증에 필요한 구체적 체크(명령 포함)는 이슈의 AC가 직접 품는다.
   ⇒ **시스템의 신뢰도는 이슈/AC 작성 품질에 100% 묶인다.** 이게 이 설계의 가장 큰
   단일 의존점이다.
3. **AC는 에이전트가 확실히 판정 가능한 항목만.** 주관적·"사람이 봐야 아는" 항목은
   AC에 넣지 않는다. 사람 검증은 PR 머지 직전 한 번뿐.
4. **오케스트레이터는 LLM이 아니라 결정론적 스크립트다.** 폴링·선정·claim·worktree·
   PR은 전부 결정론적이라 코드로 짠다. LLM이면 "라벨 떼는 걸 잊는" 식의 불안정이
   생긴다. fuzzy한 부분(개발·검증)만 LLM CLI로 위임한다.
5. **외부로 나가는 행위(PR, push)는 오케스트레이터가, 사람 게이트를 두고 한다.**
   서브에이전트는 worktree 안에서만 일한다. auto-merge 하지 않는다.

---

## 3. 아키텍처: 3층

```
1) 컨벤션        대상 레포에 복붙: 이슈 템플릿 + 라벨 세트
   (이슈 템플릿 .github/ISSUE_TEMPLATE/feature.yml, 라벨 생성 스크립트)

2) 오케스트레이터  결정론 스크립트 (gh + git). 도구 레포에 있고, 대상 레포에 무관.
   workflow --repo owner/name --agent claude --interval 10m

3) 에이전트 어댑터  3개 CLI 명령 템플릿 + 결과파일 계약. 백엔드 무관.
   dev / verify 두 역할을 어떤 백엔드로든 돌릴 수 있게 추상화.
```

오케스트레이터에는 **레포 종속 코드가 0**이다. (원칙 2 덕분 — 게이트 파일이 없으니
레포마다 다를 게 없다.) 대상 레포는 컨벤션(이슈 템플릿 + 라벨)만 갖추면 된다.

---

## 4. 메인 루프 (한 틱 = 한 이슈)

오케스트레이터 한 번 실행 = 이슈 하나를 1→6까지 처리하고 종료.

1. **폴링 & 선정.** 대상 레포의 열린 이슈를 오래된→최신 순으로 스캔, 첫 번째
   actionable 이슈 하나를 고른다. (선정 규칙은 §5) 없으면 그냥 종료.
2. **claim.** 고른 이슈에 `in-progress` 라벨을 붙인다. (claim은 라벨로만 한다.)
3. **worktree 생성.** 오케스트레이터가 직접 `git worktree`를 만든다. 브랜치명
   `agent/issue-<n>-<slug>`.
4. **개발 (서브에이전트).** dev 에이전트를 띄워 worktree에서 개발. 입력은 이슈의
   목적/상세/AC. dev는 라운드마다 정상 커밋한다.
5. **검증 (서브에이전트) ↔ 4 반복.** verify 에이전트가 AC를 전부 검사.
   - 통과 → 6으로.
   - 실패 → 부족한 점을 dev에 넘겨 4로 복귀.
   - **최대 3라운드.** 초과하면 `needs-human` 붙이고 이슈에 막힌 이유 코멘트,
     worktree 정리, 종료.
6. **PR.** 오케스트레이터가 push + PR 작성. `in-progress` → `in-review`로 교체.
   (PR 세부는 §10)

dev/verify는 **둘 다 매 라운드 풀 서브에이전트**로 띄운다 (가벼운 버전 안 씀).
verify의 독립성("작성자가 자기 숙제 채점" 방지)을 유지하기 위함.

---

## 5. 이슈 선정 알고리즘

매 사이클, 오래된→최신 순으로 스캔해서 **첫 번째로 아래를 전부 만족하는 이슈 하나**:

- open이고
- `agent` 라벨이 있고 (opt-in — 사람이 "봇이 해도 됨" 표시한 것만 건드린다)
- `in-progress` / `in-review` 가 아니고 (이미 진행/PR 중 아님)
- `needs-spec` / `needs-human` 이 아니고 (고정 스킵)
- `Depends-on`에 적힌 이슈가 **전부 closed**이고
- `Acceptance Criteria` 섹션이 있다

예시: 이슈 1~10 중 1~4가 의존성 미충족이라 스킵, 5를 수행. 다음 사이클엔 1~4를
다시 확인(자동 재계산)하고 5는 `in-progress`라 스킵 → 6을 수행.

### 재확인되는 스킵 vs 고정되는 스킵 — 중요

- **의존성 막힘** (`Depends-on` 미충족): 라벨 안 붙인다. 매 사이클 다시 계산되므로,
  막은 이슈가 닫히면 자동으로 풀린다.
- **needs-spec / needs-human**: 봇이 붙이는 **고정 라벨**. 사람이 이슈를 고치고
  라벨을 떼기 전까지 매 사이클 스킵된다.

### 데드락 아님

`Depends-on`이 영영 안 닫혀도 그 이슈만 매 사이클 스킵될 뿐, 루프는 다음 actionable로
넘어간다.

### single-flight 전제

claim을 라벨로만 하므로 **동시에 루프 인스턴스가 하나만** 돌아야 한다(레이스 방지).
cron이라면 `flock`으로 직전 틱이 안 끝났으면 다음 틱을 스킵.

---

## 6. 라벨 세트 & 라이프사이클

| 라벨 | 누가/언제 | 의미 |
|---|---|---|
| `agent` | 사람이 붙임 | 자동화 대상(opt-in). 이게 없으면 봇은 손대지 않음 |
| `in-progress` | 봇, 작업 시작 시 | claim. 진행 중 |
| `in-review` | 봇, PR 열면서 (`in-progress` 제거) | PR 대기 중 |
| `needs-spec` | 봇 | `Depends-on`/`AC` 파싱 불가 또는 AC 없음 — 고정, 사람이 풀어야 함 |
| `needs-human` | 봇 또는 사람 | 본질적으로 사람이 직접 해야 하는 이슈. 3라운드 실패 에스컬레이션 포함 — 고정 |
| (closed) | PR 머지 (`Closes #n`) | 완료 |

전이: `agent` → `in-progress` → `in-review` → (머지 시 close).
예외: 검증 실패(3라운드) → `needs-human`. 스펙 불량 → `needs-spec`.

### 비정상 종료 클린업 (필수)

틱이 claim 후 PR 전에 죽으면(dev 죽음, push 실패 등):

1. `in-progress` 라벨 제거
2. `git worktree remove`로 worktree 정리
3. 작업 브랜치(`agent/issue-<n>-*`)도 삭제 — 완전히 깨끗하게

이렇게 해야 이슈가 영구히 묶이지 않는다. 다음 틱이 같은 이슈를 처음부터 재시도한다.

---

## 7. 이슈 본문 템플릿

`.github/ISSUE_TEMPLATE/feature.yml`로 대상 레포에 복붙. AGENTS.md(이슈를 쓰는/읽는
에이전트용)에도 이 컨벤션을 명시한다.

```markdown
## 목적 (Why)            ← 필수
As <역할>, I want <무엇>, so that <왜>.

## 상세 (What / Context)  ← 선택
배경, 범위, 비범위, 참고 링크, 제약사항.

## Depends-on            ← 없으면 의존성 없음
- #12
- #15

## Acceptance Criteria   ← 없으면 needs-spec
- [ ] 사용자가 X 하면 Y가 보인다
- [ ] `npm test` 통과
```

### 섹션 규칙

- **목적**: 필수. 유저 스토리(As X, I want Y, so that Z)로 시작.
- **상세**: 선택.
- **Depends-on**: 없으면 의존성 없음(정상). 적힌 `#n`이 전부 closed여야 actionable.
- **Acceptance Criteria**: 없으면 `needs-spec`. **에이전트가 확실히 판정 가능한
  항목만.** 검증 명령(예: `` `npm test` 통과 ``)을 여기에 직접 적는다 — 별도 게이트
  파일이 없으므로 AC에 없으면 verify가 객관적으로 돌릴 게 없다.

dev 에이전트는 **목적·상세로 맥락**을 잡고 **AC를 계약**으로 삼는다.

---

## 8. dev / verify 에이전트 계약 (백엔드 무관)

### 어댑터 = 백엔드별 명령 템플릿

각 CLI의 헤드리스(비대화) 모드로 호출. (정확한 플래그는 구현 시점에 확인해서 핀)

```
claude:   claude -p "<prompt>" --permission-mode acceptEdits
codex:    codex exec "<prompt>"          # --full-auto 류
opencode: opencode run "<prompt>"
```

공통 시그니처: `run(cwd=<worktree>, prompt=<role별 프롬프트>) → 완료까지 실행`.

### 출력 파싱 문제 → 결과 파일 계약으로 해결

세 CLI의 출력 포맷이 다 다르다. **각 CLI 출력에 의존하지 않는다.** 대신:

- **dev**: "이 worktree에서 작업하고 커밋하라"만 시킨다. 결과는 **git 상태**로 확인
  (커밋 여부, diff). 백엔드별 특수 파싱 없음.
- **verify**: "AC 각 항목을 검사하고 worktree 루트에 `verify-result.json`을 쓰라"고
  시킨다. 오케스트레이터는 **이 파일만** 읽는다.

`verify-result.json` 포맷:

```json
{
  "pass": true,
  "items": [
    { "ac": "사용자가 X 하면 Y가 보인다", "pass": true, "evidence": "..." },
    { "ac": "`npm test` 통과", "pass": true, "evidence": "42 passing" }
  ]
}
```

dev가 "어떻게 빌드/실행하나"는 레포 자체(README, package.json 등)에서 알아낸다.
게이트 파일이 없으므로 레포 종속 설정이 없다.

---

## 9. dev↔verify 내부 루프

- 최대 **3라운드**.
- verify 실패 시, `verify-result.json`의 실패 항목(무엇이 왜 부족한지)을 다음
  라운드 dev 입력으로 투입.
- 3라운드 초과 → `needs-human` + 이슈 코멘트(막힌 이유) + worktree 정리 + 종료.
- verify의 판정은 100% 객관(원칙 3). 루프 안에 사람 게이트는 없다.

---

## 10. 브랜치 / 커밋 / PR 컨벤션

- **브랜치**: `agent/issue-<n>-<slug>`
- **커밋**: dev가 라운드마다 정상 커밋. verify는 커밋된 상태에서 검사. 히스토리
  유지 (머지는 사람이 squash로).
- **PR**:
  - title: `<type>: <이슈 제목> (#<n>)`
  - body: 요약 + AC 체크 결과(verify 결과로 체크박스 채워 증거로 남김) + `Closes #<n>`
  - **auto-merge 안 함.** 사람 검증/머지가 유일한 휴먼 게이트.
- 머지 시 `Closes #n`으로 이슈가 닫히면, 그 이슈에 걸려 있던 downstream이 다음
  사이클에 자동으로 actionable해진다 — 의존성 DAG를 틱이 거듭되며 자연스럽게 타고
  내려간다.

---

## 11. idempotency / 재개

- claim(`in-progress`) 후 PR 전에 죽으면 클린업이 라벨 제거 + worktree + 브랜치
  삭제(§6). 부분 작업은 버린다.
- 다음 틱이 같은 이슈를 **처음부터** 재시도(재사용 없음). 매 시도가 깨끗한 상태에서
  시작하므로 재개 로직이 단순하다.

---

## 12. 실행 / 호스팅

- **시작(개발/디버깅)**: 로컬에서 `/loop`이나 cron으로 스크립트를 돌리며 한 이슈가
  1→6까지 매끄럽게 도는지 눈으로 확인.
- **무인 운영**: 전용 러너(또는 항상 켜진 머신)에서 **cron + flock**. 3개 CLI 설치 +
  각 API 키만 있으면 됨. 가장 단순.
- **승격**: GitHub Actions `on: schedule` (gh 토큰·체크아웃 자동) 또는 셀프호스티드
  러너. 단 LLM CLI 설치·키 시크릿·실행시간 제한 고려.
- 매 틱이 cold라는 점이 오히려 원칙 1(상태는 GitHub)을 강제해줘서 좋다.

---

## 13. 미결 사항

1. 각 CLI 헤드리스 모드의 **정확한 플래그**(권한/샌드박스/완료 신호)는 구현 시 확인.

## 12.1 기술 스택 (확정)

- **언어: Python.** (근거 비교는 부록 참고)
- pretty CLI: `rich` (테이블·진행·패널·스타일 로그). CLI 인자/`--help`는 `typer`.
  나중에 라이브 대시보드가 필요하면 `textual`.
- shell-out: `subprocess` (필요 시 `asyncio`로 에이전트 출력 스트리밍).
- 배포: `uv` / `pipx`.

---

## 14. 결정 로그 (논의 합의 요약)

- 상태는 전부 GitHub에 (stateless 틱). **수용**
- `Depends-on` / `Acceptance Criteria`를 이슈 본문 섹션으로. AGENTS.md에도 명시.
  스펙 불량은 `needs-spec`. **수용**
- claim은 라벨로만. 선정은 오래된→최신, 틱당 1개, 스킵분은 재확인. **수용**
- dev↔verify 최대 3라운드. **수용**
- worktree 수명 주인은 오케스트레이터. **수용**
- PR은 `Closes #n` + 검증 증거, auto-merge 안 함. **수용**
- 재확인 스킵(의존성) vs 고정 스킵(needs-spec/human) 구분. **수용**
- single-flight 전제. **수용**
- opt-in `agent` 라벨만 처리. **수용**
- 이슈 템플릿에 목적(필수)·상세(선택) 추가. **수용**
- AC는 100% 에이전트 판정 가능 항목만. needs-human은 본질적으로 사람이 해야 하는
  이슈(3라운드 실패 포함). 사람 검증은 PR 머지 직전 한 번. **수용**
- AC가 SSoT. 게이트 설정 파일 없음. dev는 빌드법을 레포에서 알아냄. **수용**
- 브랜치/커밋/PR 컨벤션 (§10). **수용**
- dev·verify 둘 다 매번 풀 서브에이전트. **수용**
- 오케스트레이터 = 결정론 스크립트(LLM 아님). **수용**
- 클린업 시 라벨 + worktree + **브랜치까지 삭제**(완전 초기화), 재시도는 처음부터.
  **수용**
- 범용화: 별도 도구 레포 + 복붙 컨벤션. 오케스트레이터는 레포 무관. **수용**
- 3개 백엔드(opencode/claude/codex)를 어댑터(명령 템플릿 + 결과 파일 계약)로 지원.
  **수용**
- 구현 언어 = **Python** (rich/typer, 필요 시 textual). **수용** (근거: 부록)

---

## 부록: 언어 비교 (왜 Python)

도구의 실제 작업은 ① `gh`/`git`/에이전트 CLI shell-out, ② JSON 파싱
(`verify-result.json`, gh 출력), ③ 라벨 상태머신 글루 로직, ④ pretty 상태 출력,
⑤ cron 루프. 이 기준으로 비교했다.

| 기준 | Python (rich/typer) | Node/TS (execa/listr2) | Go (charm) | Rust | Bash (+gum) |
|---|---|---|---|---|---|
| pretty CLI | ★★★ rich 최소코드 최고룩 | ★★★ listr2 라운드에 딱 | ★★★ 가장 예쁨·코드↑ | ★★ 노력 최대 | ★★ gum 깔끔 |
| shell-out | ★★ subprocess 무난 | ★★★ execa 최강 | ★★ 장황 | ★★ 장황 | ★★★ 네이티브 |
| JSON+타입 | ★★ 네이티브, 타입X | ★★★ TS 타입이 계약 버그 차단 | ★★ struct | ★★ serde | ★ jq 지옥 |
| 배포/설치 | ★★ uv/pipx | ★★ npm | ★★★ 단일바이너리 | ★★★ 단일바이너리 | ★★★ gum 1개 |
| cold start | ★★ ~100ms | ★★ ~100ms | ★★★ 즉시 | ★★★ 즉시 | ★★★ 즉시 |
| 에이전트 유지보수 | ★★★ LLM 최강 | ★★★ LLM 최강 | ★★ 데이터↓ | ★ 반복비용↑ | ★ 로직 취약 |
| 글루 개발속도 | ★★★ | ★★★ | ★★ | ★ 과함 | ★★ |

- **Node/TS와 Python이 사실상 동률**. 객관적으론 Node가 근소 우위(execa·TS 타입 계약·
  러너에 이미 Node 존재). Go/Rust의 단일 바이너리 장점은 러너에 런타임이 이미 있어
  무효, 글루 도구엔 과함. Bash는 JSON·상태머신에서 무너짐.
- **최종 선택은 Python** — 유지보수자(사람)가 Python이 더 편하고, rich로 pretty가
  최소 노력이며, 필요 시 textual 대시보드를 거의 공짜로 얻기 때문.
