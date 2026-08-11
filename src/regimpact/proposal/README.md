# Rule Change Proposal — 구조화 정책 변경안

브리프 §9의 거버넌스 원칙 구현: **LLM은 룰엔진 코드를 직접 수정하지 않는다.**
LLM은 인용 근거가 붙은 사실만 추출하고, 이 모듈이 그 추출을 구조화 변경안으로
**deterministic하게 조립**한다. 변경안은 항상 `status=DRAFT`로 생성되며, 사람 승인
후에야 deterministic rule registry(룰엔진)에 반영된다.

```
RegChange Extractor (LLM, 인용 필수)
  → Rule Change Proposal (deterministic 조립, DRAFT)      ← 이 모듈
  → Consistency 검증 (vs 엔진 실측)
  → Human Review / Approve
  → Deterministic Rule Registry (룰엔진)
```

## 사용

```python
from regimpact.impact import build_impact_matrix
from regimpact.proposal import (
    six_thirty_extraction, build_proposal_from_extraction,
    check_proposal_consistency, apply_consistency_status,
)

extraction = six_thirty_extraction()               # 실제로는 extractor LLM 출력
proposal = build_proposal_from_extraction(extraction)   # DRAFT + 필드별 인용
report = check_proposal_consistency(proposal, matrix=build_impact_matrix())
apply_consistency_status(proposal, report)         # 불일치 시 NEEDS_REVIEW 승격
```

데모: `python examples/demo_rule_proposal.py`

## 구성

| 파일 | 역할 |
|---|---|
| `schema.py` | `RuleChangeProposal`·`RuleState`·`Grandfathering`·`ProposalSource`, `ChangeType`/`ProposalStatus`, JSON Schema |
| `builder.py` | `build_proposal_from_extraction` — 추출 카테고리별 → 변경안 필드 결정적 매핑, `parse_ltv` |
| `consistency.py` | `check_proposal_consistency` — 변경안 ↔ 엔진 상수/Impact Matrix 교차검증, `apply_consistency_status` |
| `samples.py` | `six_thirty_extraction` — 오프라인 E2E용 canonical 추출(사람 확정 AI초안 대리) |

## 조립 매핑 (builder)

| 추출 카테고리 | → 변경안 필드 |
|---|---|
| `LTV` | `before.max_ltv` / `after.max_ltv` |
| `REGION` | `after.target_regions`, `region_status` 전환 |
| `EFFECTIVE_DATE` | `after.effective_from` |
| `EXCEPTION` | `exceptions[]` (생애최초→FIRST_HOME_BUYER, 서민실수요→REAL_DEMAND 등) |
| `GRANDFATHERING` | `grandfathering{cutoff_date, conditions}` |
| `SCOPE_LIMIT` | (Discovery — 변경안 코어 제외, 브리프 §5.2) |

각 매핑은 해당 추출 항목의 citation을 `sources[]`에 근거로 남긴다(필드→원문 추적).

## Consistency 검증 (Assurance 연결)

변경안(LLM 산출)이 사람이 확정한 deterministic 엔진(=승인된 rule registry)의 실제
동작과 일치하는지 교차검증한다. 불일치 = LLM 추출 오류 또는 엔진 드리프트 →
`NEEDS_REVIEW`. metrics_spec의 *Rule Regression & Conflict* / *Policy-version Consistency*
dimension과 정렬.

검증 항목:
1. `before.max_ltv` == 엔진 기준선(70%)
2. `after.max_ltv` == 엔진 규제표준(40%)
3. `effective_from` == 엔진 시행일(2026-07-01)
4. `grandfathering.cutoff` == 엔진 CUTOFF(2026-06-30)
5. `target_regions` == 엔진 규제지역 집합
6. `exceptions` ⊇ 엔진 예외경로(생애최초·서민실수요)
7. (matrix 제공 시) Impact Matrix 실측 LTV와 제안값 대조 3건

`tests/test_proposal.py`의 **mutation 테스트**가 각 필드를 손상시켜 consistency가
반드시 잡아내는지(자동 승인 없음) 증명한다.
