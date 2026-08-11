# Impact Matrix — 규제 변경의 세그먼트별 영향 매트릭스

deterministic 룰엔진을 **시행 전(before)·후(after) 두 시점에 차등 실행**해,
`지역 × 차주유형 → 기존 LTV / 변경 LTV / 경과규정 / reason_code` 매트릭스를 산출한다.

> **모든 LTV 값은 엔진 실제 출력이다(하드코딩 아님).**
> UI/Stitch 목업의 하드코딩값을 이 출력으로 교체하는 것이 목표.

## 축(axis) 정의

| 축 | 시점 | 이벤트 처리 | 의미 |
|---|---|---|---|
| **before(기존)** | 2026-06-30 | 경과규정/타이밍 이벤트 **제거** | 구(舊)규제 기준선 |
| **after(변경)** | 2026-07-02 | 모든 속성/이벤트 **반영** | 신(新)규제 적용값 |

- `before`에서 경과규정 이벤트를 제거하는 이유: 경과규정은 신규 규제가 존재할 때만
  의미가 있으므로, 규제 시행 전 세계에 `grandfathering_applied=True`가 찍히는 오해를 막는다.
- `after`는 경과규정을 반영해 "종전규정 유지(70%)"가 실제 판정으로 드러나게 한다.

## 정직성(honest escalation)

유주택·다주택의 **기존 LTV**는 명세(`05_RULE_SPEC.md`)에 비규제 수도권 기준선이 없어
엔진이 `NEEDS_HUMAN_REVIEW`(기준부재)를 반환한다. 이를 임의로 70%로 채우지 않고
`검토필요(기준부재)`로 그대로 노출한다 → `direction = BASELINE_GAP`.
(Stitch 목업의 "70%→0%"는 조작값이었고, 엔진 실측은 "기준부재→0%"다. 브리프 §5, LOCKED §4.)

## 사용

```python
from regimpact.impact import build_impact_matrix, format_report

matrix = build_impact_matrix()          # 기본 = 6·30 SIX_THIRTY_SEGMENTS
print(format_report(matrix))            # 표 리포트
payload = matrix.to_dict()              # UI 연동용 JSON (summary + rows)
```

데모: `python examples/demo_impact_matrix.py`

## 구성

| 파일 | 역할 |
|---|---|
| `segments.py` | `Segment` 정의 + 6·30 앵커 세그먼트(Core 7 / Discovery 2) |
| `matrix.py` | `ImpactRow`·`ImpactMatrix`·`ImpactDirection`, `build_impact_matrix`·`format_report`·`to_dict` |

## 방향(direction) 분류

| 값 | 의미 |
|---|---|
| `TIGHTENED` | 하향(규제강화): after < before |
| `EASED` | 상향(완화): after > before |
| `UNCHANGED` | 동일(예외·경과규정 유지 포함) |
| `BASELINE_GAP` | before 기준부재(검토필요) → 델타 계산 불가 |
| `NON_CORE` | Discovery / Out-of-scope (자동판정 제외) |

## 고영향(high_impact) 플래그

`metrics_spec.md`의 high-risk 정의와 정렬: LTV가 0%로 떨어지거나(대출불가),
15%p 이상 하향, 또는 기준부재인 행을 `★`로 표시.

## E2E 위치

이 모듈은 브리프 §18 "코어 완성" 파이프라인의 **Impact Matrix** 노드다.
Source Snapshot → Policy Version → Before/After → **Impact Matrix** →
Rule Change Proposal → Test Cases → Rule Regression → Assurance → Report.
