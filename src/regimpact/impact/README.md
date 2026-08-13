# impact — Impact Matrix (시행 전/후 영향)

Walking Skeleton(`docs/04_PLAN.md` Phase 1)의 **Before/After → Impact Matrix 노드.**

## 핵심 아이디어
규제 변경의 '임팩트' = **같은 고객 프로필을 시행 전/후 두 시점으로 판정**한 차이.
룰엔진(`rule_engine.evaluate`)이 지역 규제상태를 `evaluation_date`로 시점 해석하므로,
동일 프로필을 `before_date`/`after_date`로 두 번 돌리면 Before/After가 자연히 나온다.
→ **temporal diff.** 규칙값을 자체 보유하지 않아 **LOCKED §4**(규칙은 확정 명세→엔진에서만) 준수.

## 정직성 원칙 (브리프 §12)
한쪽 시점이라도 판정이 `DECIDED`가 아니면(escalation/discovery/scope) 델타를 억지로
만들지 않고 `REVIEW`로 표면화한다. 예: 非규제 수도권 유주택은 명세에 기준값이 없어
시행 전이 `NEEDS_HUMAN_REVIEW` → 임팩트도 `REVIEW(검토필요)` + 사유(note) 노출.

## 구조
- `matrix.py` — `Segment` / `ImpactRow` / `ImpactMatrix` / `analyze_impact` / `analyze_from_extraction`
- `segments.py` — 6·30 표준 세그먼트 6종(`SIX_THIRTY_SEGMENTS`)
- `report.py` — `format_matrix` (텍스트 렌더, UI 연동 기준 출력)

## 사용
```python
from datetime import date
from regimpact.impact import SIX_THIRTY_SEGMENTS, analyze_impact, format_matrix

m = analyze_impact(SIX_THIRTY_SEGMENTS, "GURI",
                   before_date=date(2026, 6, 30), after_date=date(2026, 7, 2))
print(format_matrix(m))
```

## E2E 연결 (Extractor → Impact Matrix)
```python
from regimpact.impact import analyze_from_extraction, SIX_THIRTY_SEGMENTS
# extraction: RegChangeExtraction (effective_from="2026-07-01")
m = analyze_from_extraction(extraction, SIX_THIRTY_SEGMENTS, region_code="GURI")
# before = 효력일 전일, after = 효력일 + 2일 로 자동 유도
```

## 6·30 산출 요약 (GURI, 시행 전 6.30 → 후 7.2)
| 세그먼트 | before | after | Δ | 방향 |
|---|---|---|---|---|
| 무주택 일반 | 70% | 40% | -30pp | ▼ 강화 |
| 생애최초 | 70% | 70% | 0pp | = 동일(예외 보호) |
| 서민·실수요 | 70% | 60% | -10pp | ▼ 강화 |
| 비처분 1주택 | (기준값 부재) | 0% | - | ⚠ 검토 |
| 처분조건부 1주택 | 70% | 40% | -30pp | ▼ 강화 |
| 다주택 | (기준값 부재) | 0% | - | ⚠ 검토 |
