# Assurance Evaluation — 깊은 4 dimension 집계

각 노드가 낸 검증 신호를 metrics_spec의 **깊은 4 dimension**으로 집계하고,
임계(threshold) 대비 pass/fail·gate·사람 escalation 사유를 산출한다.

| Dim | 항목 | 입력 신호(출처) |
|---|---|---|
| **D1** | Source Grounding & Citation | `check_citation_grounding` (extractor) |
| **D2** | Change & Exception Completeness | `score_against_gold` (extractor) |
| **D3** | Temporal / Policy-Version Consistency | `check_proposal_consistency` (proposal) + 시행일(gold) |
| **D4** | Rule Regression & Conflict | `run_regression` + `check_proposal_fidelity` + coverage (tc_generator) |

## 사용

```python
from regimpact.assurance import evaluate_assurance

report = evaluate_assurance(
    grounding=..., gold=..., consistency=...,
    regression=..., fidelity=..., coverage=..., matrix=...,
)
report.gate            # AssuranceGate.PASS / REVIEW_REQUIRED
report.escalations     # 게이트를 막는 검증 실패(사람 검토 필수)
report.notes           # 참고(설계상 정직한 gap — 게이트 무관)
report.to_dict()
```

## Gate 로직

- **PASS**: 전 dimension 통과 AND `escalations` 없음 → 사람 승인 절차로.
- **REVIEW_REQUIRED**: 하나라도 실패/escalation → 사람 검토 필수.

**escalations vs notes 분리**: 환각 인용·골드 누락·회귀 실패 등 *AI 검증 실패*는
`escalations`(게이트 차단). 유주택 '기존 LTV' 명세 부재 같은 *설계상 정직한 gap*은
`notes`(게이트 무관, 보고서에 노출) — AI가 틀린 게 아니라 사람 확정 대기 항목이다.

## 임계값 (확정 2026-08-11)

`AssuranceThresholds`는 `docs/metrics_spec.md`의 **tier 체계**를 구현한다(차등):

| tier | 지표 | 값 |
|---|---|---|
| T0 안전핵심 | regression / fidelity / consistency | 하드(100% / all-passed) |
| T1 고위험 recall | exception_recall / effective_date / regions | Gate 95% |
| T2 완전성·grounding | change_completeness / citation_correctness | Gate 90% / 95% |

**핵심:** 개별 miss는 항상 `escalations`에 쌓여 gate를 `REVIEW_REQUIRED`로 만든다 →
Gate 수치와 무관하게 silent error가 불가능하다(안전은 escalation이 보장, 지표는 배포 판단선).
