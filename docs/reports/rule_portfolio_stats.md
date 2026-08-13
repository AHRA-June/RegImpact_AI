```
================================================================
RegImpact — Rule Portfolio Stats (층화 합성 평가셋)
================================================================
N = 106   Pass Rate = 106/106 = 100.0%  (engine ⟷ independent spec oracle)

By category:
  SCOPE            18/18   100%
  BASELINE         25/25   100%
  EXCEPTION        21/21   100%
  BOUNDARY         19/19   100%
  GRANDFATHERING   13/13   100%
  CONFLICT         10/10   100%

By split (전량 측정 — 결정론 엔진, 튜닝 루프 없음 → 누수 위험 없음):
  CHALLENGE   35/35   100%
  DEV         36/36   100%
  LOCKED      35/35   100%

Coverage (판정 다양성):
  distinct status     = 4
  distinct rule_id    = 6
  distinct reason_code= 11

✓ 전 케이스 통과 — 엔진이 확정 명세(§H)와 전 입력공간에서 일치.
================================================================
```
