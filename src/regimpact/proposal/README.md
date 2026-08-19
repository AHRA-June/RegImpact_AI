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
from regimpact.impact.builder import derive_rule_diff
from regimpact.proposal import (
    build_proposal_from_extraction, check_proposal_consistency, apply_consistency_status,
)

proposal = build_proposal_from_extraction(extraction)   # extractor LLM 출력 → DRAFT
report = check_proposal_consistency(proposal, rule_diff=derive_rule_diff())
apply_consistency_status(proposal, report)              # 불일치 시 NEEDS_REVIEW 승격
```

데모: `python examples/demo_impact_e2e.py` (7단계)

손으로 쓴 추출 fixture는 두지 않는다. 오프라인 재현은 `--provider replay` 로 **실제 LLM
실행 기록**을 재생한다 — fixture를 직접 타이핑하면 변경안이 내 타이핑에 대해 검증된다.

## 구성

| 파일 | 역할 |
|---|---|
| `schema.py` | `RuleChangeProposal`·`RuleState`·`Grandfathering`·`ProposalSource`, `ChangeType`/`ProposalStatus`, JSON Schema |
| `builder.py` | `build_proposal_from_extraction` — 추출 카테고리별 → 변경안 필드 결정적 매핑, `parse_ltv` |
| `consistency.py` | `check_proposal_consistency` — 변경안 ↔ 엔진 상수/`derive_rule_diff()` 교차검증, `apply_consistency_status`, `newly_designated_regions` |

## 조립 매핑 (builder)

| 추출 카테고리 | → 변경안 필드 |
|---|---|
| `LTV` | `before/after.ltv_by_segment[세그먼트]`, `max_ltv` = STANDARD |
| `REGION` | `after.target_regions`, `region_status` 전환 |
| `EFFECTIVE_DATE` | `after.effective_from` |
| `EXCEPTION` | `exceptions[]` (생애최초→FIRST_HOME_BUYER, 서민실수요→REAL_DEMAND 등) |
| `GRANDFATHERING` | `grandfathering{cutoff_date, conditions}` |
| `SCOPE_LIMIT` | (Discovery — 변경안 코어 제외, 브리프 §5.2) |

각 매핑은 해당 추출 항목의 citation을 `sources[]`에 근거로 남긴다(필드→원문 추적).

### LTV는 스칼라 하나가 아니다

정책 하나가 세그먼트마다 다른 LTV를 정한다(무주택 40 / 생애최초 70 / 서민실수요 60 /
유주택·다주택 0 / 보금자리론 60). 항목을 돌며 `max_ltv` 를 덮어쓰면 **마지막 항목이 이긴다** —
6·30 추출에서는 마지막 LTV 항목이 보금자리론이라 규제지역 표준이 0.6으로 나왔다.

그래서 세그먼트별로 모으고, 한 세그먼트에 값이 갈리면 **최빈값을 쓰되 `conflicts[]` 에 남긴다**.
동률이면 고르지 않는다(임의 선택은 값 창작이다). `unmapped[]` 는 LTV로 분류됐지만 비율이
아닌 항목(한도 6억·전입의무·만기 30년)이다 — 엔진이 모델링하지 않는 별도 룰 차원이라
조용히 버리지 않고 사람에게 넘긴다.

`parse_ltv` 는 **맨숫자를 받지 않는다.** 이전 판의 fallback이 아무 정수나 100으로 나눠서
"최대한도 6억원"을 LTV 0.06, "최대 만기 30년"을 LTV 0.30으로 만들어냈다.

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
5. `target_regions` == 엔진 **신규지정 지역(델타)** — 그 시점 규제지역 **전체**가 아니다.
   두 개념은 레지스트리에 6·30 신규 3곳만 있던 시절 우연히 같았고, 기존 규제지역 40곳이
   들어오면서(R-01) 갈라졌다 — 스냅샷 40곳 vs 델타 3곳
6. `exceptions` ⊇ 엔진 예외경로(생애최초·서민실수요)
7. `conflicts` 비어 있음 — 세그먼트 값 충돌이 남아 있으면 사람이 봐야 한다
8. `unmapped` 비어 있음 — 엔진이 모르는 룰 차원이 있으면 사람이 배치해야 한다
9~10. (rule_diff 제공 시) 엔진에서 유도한 룰 diff 의 REG_STD 행과 before/after 대조

**방향이 중요하다.** 기준은 언제나 엔진 쪽이다. 변경안을 기준으로 삼으면 LLM 출력이
스스로를 검증하는 셈이 되어 검사가 무의미해진다.

`tests/test_proposal.py` 의 **mutation 테스트 7종**이 각 필드(LTV·기준선·시행일·컷오프·
지역 누락·지역 과다·예외 누락)를 손상시켜 consistency 가 반드시 잡아내는지 증명한다.
