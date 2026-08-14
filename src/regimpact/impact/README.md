# Impact Matrix (규제 변경 영향분석 E2E)

룰엔진(`regimpact.rule_engine`, deterministic)을 **시행 전/후 두 시점**에 관통시켜,
세그먼트별로 **기존 LTV → 변경 LTV / 방향 / 경과규정 / 근거코드**를 산출한다.
이것이 제품의 핵심 출력(**RegChange / Impact Analysis**)이며, UI 임팩트 매트릭스 화면의
하드코딩 값은 이 모듈의 실제 엔진 출력으로 대체된다.

## 왜 이렇게 만들었나 (설계 근거)

**규칙을 새로 만들지 않는다.** 동일한 차주 프로파일을 두 `evaluation_date`(Before/After)에
넣어 `evaluate()`를 두 번 호출하고, 두 판정의 **델타**를 구조화할 뿐이다. 지역의 규제상태(시점
버전 `regions.py`)와 경과규정(`grandfathering.py`)은 엔진이 날짜로 스스로 해석한다.

```
                Before=2026-06-30              After=2026-07-02
  Segment ──┬──▶ evaluate(app@before) ─┐   ┌─ evaluate(app@after) ──┬──▶ ImpactRow
            │                          ▼   ▼                        │   (기존→변경/방향/GF)
            └──────────────  델타 · 방향 분류 · Discovery 분리  ─────┘
```

- **`segments.py`** — 6·30 대표 차주 세그먼트('지역 × 차주유형'). 지역·시점은 빌더가 채운다.
- **`matrix.py`** — `build_impact_matrix()` 가 Before/After 두 판정 → `ImpactRow`/`ImpactMatrix`.

## 정직성 원칙 (LOCKED §4 · 브리프 §5.2)

이 모듈의 차별점은 **없는 값을 지어내지 않는다**는 것이다.

| 상황 | 처리 |
|---|---|
| 非규제 유주택/다주택 기준선이 원문에 없음 | before=`검토`(수치 없음) → after=0% = **`NEW_RESTRICTION`** (70→0 fabricate 금지) |
| 정책대출 · 비주택구입목적(전세 등) | 자동판정 제외 → **Discovery Scope**로 분리(`discovery_rows`) |
| 경과규정 충족 | 종전규정 유지(`UNCHANGED`) + **counterfactual**(보호 없었다면 적용됐을 LTV)을 함께 표기 |

즉, 넓게 발견(Discovery)하되 자동판정은 신뢰 가능한 좁은 범위(Core)에서만 한다.

## 사용법

```python
from regimpact.impact import build_impact_matrix, format_matrix

matrix = build_impact_matrix()          # 기본 = 6·30 시나리오 SIX_THIRTY_SEGMENTS
print(format_matrix(matrix))            # 사람이 읽는 표(리포트 stub)

matrix.core_rows                        # 자동판정 대상 행
matrix.discovery_rows                   # 수동 정책검토 행
matrix.summary                          # {DOWNGRADE, NEW_RESTRICTION, ..., TOTAL, CORE, GRANDFATHERED}
for r in matrix.core_rows:
    r.before_ltv, r.after_ltv, r.delta, r.direction, r.grandfathering_applied, r.counterfactual_ltv
```

데모: `python examples/demo_impact_matrix.py`

## 출력 모델

- `ImpactRow` — 한 세그먼트의 `before`/`after` `LtvDecision`, `direction`(`ImpactDirection`),
  `grandfathering_applied`, `counterfactual_ltv`, `reason_codes`, `delta`.
- `ImpactMatrix` — `rows` + `core_rows`/`discovery_rows` 분리 + `summary` 방향별 카운트.
- `ImpactDirection` — `DOWNGRADE` / `UPGRADE` / `UNCHANGED` / `NEW_RESTRICTION` / `REVIEW` / `DISCOVERY`.

## 테스트

`tests/test_impact.py` — 세그먼트별 before/after 값, 방향 분류, 명세부재 정직처리,
경과규정 counterfactual, Discovery 분리, 요약 카운트. 룰엔진 LTV 값의 진실은
`tests/test_rule_engine.py`가 담당(관심사 분리).
