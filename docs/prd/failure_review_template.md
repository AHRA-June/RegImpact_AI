# Failure Review Template

> Assurance 지표가 임계를 위반하거나 케이스가 실패했을 때 **1건씩 구조화 기록**하는 양식.
> 목적: 실패를 error taxonomy(PRD §5.4)로 분류하고, 근본원인·조치를 추적해 재발을 막는다.
> "실패를 조용히 덮지 않는다"는 Assurance 원칙의 운영 도구.

## 필드

| 필드 | 설명 |
|---|---|
| `id` | 실패 기록 ID (예: FR-2026-08-12-001) |
| `date` | 발견일 |
| `case_id` | 대상 케이스/추출 항목 ID (골드 case_id, claim_id, PF-… 등) |
| `dimension` | ① Grounding / ②③ Change·Temporal / ④ Rule·Test / Escalation |
| `metric` | 위반한 지표 (예: Exception Recall) |
| `threshold` | 확정 임계 (예: ≥95% + 핵심예외 0누락) |
| `expected` | 기대값(오라클/골드/명세) |
| `actual` | 실제 관측값 |
| `error_class` | E1~E9 (PRD §5.4 error taxonomy) |
| `high_risk` | Y/N (metrics_spec high-risk 정의 4종 해당 여부) |
| `root_cause` | 근본원인 (모델 오류 / 프롬프트 / 채점기 정규화 / 명세 모호성 / 엔진 버그 / 데이터) |
| `disposition` | 조치: `fix-prompt` / `fix-engine` / `fix-scorer` / `spec-clarify` / `escalate-user` / `accept-out-of-scope` |
| `citation` | 근거 (원문 doc/quote, 또는 명세 위치 §) |
| `status` | open / fixed / accepted |

## 예시 (2026-08-12 실측에서 나온 2건)

```yaml
- id: FR-2026-08-12-001
  case_id: extractor_run_6_30 (Citation Grounding)
  dimension: "① Grounding"
  metric: Citation Correctness
  threshold: "≥ 95%"
  expected: "정확 인용 grounded"
  actual: "67% (2건 오탐)"
  error_class: E4
  high_risk: N
  root_cause: "채점기 정규화 — 원문 PDF 문장중간 줄바꿈을 공백정규화가 공백으로 바꿔 정확한 인용을 오탐"
  disposition: fix-scorer
  citation: "docs/eval/extractor_run_6_30.md 발견 1; evaluate._squish 보정"
  status: fixed        # 공백무관 비교로 67%→100%

- id: FR-2026-08-12-002
  case_id: extractor EXCEPTION (서민·실수요)
  dimension: "②③ Change·Temporal"
  metric: Exception Recall
  threshold: "≥ 95% + 핵심예외 0누락(하드게이트)"
  expected: "생애최초·서민실수요·정책모기지 개별 포착"
  actual: "50% (서민·실수요 누락)"
  error_class: E2
  high_risk: Y
  root_cause: "프롬프트 — 예외를 한 항목으로 뭉뚱그려 서민·실수요 키워드 탈락"
  disposition: fix-prompt
  citation: "docs/eval/extractor_run_6_30.md 발견 2; prompt.py 규칙6"
  status: fixed        # 예외 개별 분리 프롬프트로 50%→100%
```

> 두 실패 모두 **탐지 → 근본원인 분류 → 조치 → 재측정**으로 닫혔고, 회귀 방지 테스트가 걸려 있다
> (`test_grounding_ignores_pdf_linewrap_whitespace`, 예외 recall 재측정). 이 양식이 그 과정을 표준화한다.
