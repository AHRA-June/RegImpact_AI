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

## 임계값 (DRAFT)

`AssuranceThresholds`는 metrics_spec 상태=스켈레톤에 맞춰 **DRAFT**다(사용자 확정 대기).
high-risk dimension(예외·경과·시행일)은 엄격(1.0)하게 둔다. 확정 시 이 값만 교체.
