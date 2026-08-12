# impact — Impact Matrix (before/after 차등 임팩트)

규제 변경 1건이 대표 고객 세그먼트에 미치는 영향을 **시행 전/후 차등**으로 표로 낸다.
`04_PLAN.md` Phase 1(Walking Skeleton)의 "6·30 1건 E2E 관통" 산출물.

## 핵심 원칙 (LOCKED §4)

이 모듈은 **새로운 규칙을 만들지 않는다.** deterministic 룰엔진(`regimpact.evaluate`)을
같은 세그먼트에 대해 **두 시점**으로 돌린 뒤 그 차이를 정리할 뿐이다.
6·30 건은 지역 규제상태가 2026-07-01부터 바뀌므로(`regions.py`), 같은 세그먼트를
`before=2026-06-30`, `after=2026-07-02` 로 평가하면 정책 효과가 그대로 드러난다.

- 임팩트는 엔진의 **시점 해석**에서 나온다 → `test_no_impact_when_both_dates_pre_effective`
  가 두 날짜를 모두 시행 전으로 두면 임팩트가 사라짐을 확인(differential 이 tautology 아님).
- 각 행은 before/after의 status·reason_codes·source_policy_ids 를 보존한다(감사 추적).

## 사용

```python
from regimpact import analyze_impact, format_report
from regimpact.impact import SIX_THIRTY_SEGMENTS

matrix = analyze_impact(SIX_THIRTY_SEGMENTS, policy_id="6_30_2026")
print(format_report(matrix))
```

데모: `python examples/demo_impact_matrix.py`

## 출력 모델

- `ImpactDirection` — `TIGHTENED`(강화·LTV↓) / `LOOSENED`(완화·LTV↑) /
  `UNCHANGED`(예외·경과규정 보호 또는 동일) / `NEEDS_REVIEW`(한 시점 자동판정 불가 →
  수치 delta 산출 불가).
- `SegmentImpact` — before/after 판정, `ltv_delta`(둘 다 DECIDED일 때만),
  `escalation_required`(after가 검토/Discovery), `high_impact`(대폭 delta 또는 실질 전이).
- `ImpactMatrix` — 집계: `count_by_direction()`, `weighted_mean_delta()`(수치비교 가능 행만,
  제외분은 리포트에 명시), `escalation_count`, `high_impact_count`.

## 정직성 표기

- **비규제 유주택 기준선은 명세 여백**이라 시행 전 판정이 `NEEDS_HUMAN_REVIEW`.
  임팩트는 이를 숨기지 않고 `NEEDS_REVIEW` 방향 + 중대영향으로 표면화한다.
- `weight`(포트폴리오 비중)는 **예시값**이며 실측 아님. 집계는 참고용.
- 가중평균은 수치비교 가능 행만 분모에 넣고, 제외된 행 수를 리포트에 명시(조용한 누락 금지).

## 다음 심화(Phase 2)

- 세그먼트 → 층화 합성 포트폴리오(2,000~5,000)로 확대, 비중 실측/시나리오화.
- 고객영향 행(브리프 §요구)·구조화 Rule Change Proposal 연동.
- UI(Stitch) 하드코딩값을 이 매트릭스 실제 출력으로 교체.
