# jh-loops

이슈 기반 자율 개발 루프. GitHub 이슈를 단일 진실의 원천(SSoT)으로 삼아, 작업
가능한 이슈를 자동으로 골라 **개발 → 검증 → PR**까지 돌린다. 개발/검증은 교체
가능한 LLM CLI 에이전트(claude / codex / opencode)로 수행한다.

> 전체 설계와 결정 근거는 [`docs/design.md`](docs/design.md) 참고. 이 README는
> 코드 구조 안내만 담는다.

## 아키텍처 (3층)

1. **컨벤션** (`conventions/`) — 대상 레포에 설치하는 이슈 템플릿 + 라벨 세트.
2. **오케스트레이터** (`src/jh_loops/`) — 결정론 스크립트(폴링·선정·claim·worktree·
   PR). 대상 레포에 무관.
3. **에이전트 어댑터** (`src/jh_loops/agents/`) — 3개 CLI 명령 템플릿 +
   `verify-result.json` 계약. 백엔드 무관.

## 모듈 지도

| 파일 | 역할 | 설계 |
|---|---|---|
| `cli.py` | typer + rich CLI (`init` / `tick` / `run`) | §12.1 |
| `orchestrator.py` | 한 틱 = 한 이슈, 1→6 루프 | §4 |
| `selection.py` | actionable 이슈 선정 | §5 |
| `issues.py` | 이슈 모델 + Depends-on/AC 파싱 | §7 |
| `github.py` | `gh` 래퍼 (이슈·라벨·PR) | §3 |
| `worktree.py` | worktree 생성/정리 (브랜치까지 삭제) | §6, §11 |
| `verify.py` | `verify-result.json` 계약 | §8 |
| `labels.py` | 라벨 세트 + 라이프사이클 | §6 |
| `agents/` | 백엔드 어댑터 (claude/codex/opencode) | §8 |

## 상태

**스캐폴드 단계.** 구조와 시그니처는 설계대로 잡혀 있고, 핵심 로직은 `TODO` /
`NotImplementedError`로 비어 있다.

## Quickstart (예정)

```bash
# 대상 레포에 컨벤션(라벨 + 이슈 템플릿) 설치
jh-loops init owner/repo

# 한 틱만 (이슈 하나 처리)
jh-loops tick owner/repo --agent claude

# 루프 (single-flight는 cron + flock로 외부에서 보장)
jh-loops run owner/repo --agent claude --interval 10m
```
