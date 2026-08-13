```
================================================================
RegImpact — Rule Grid Stats (조합 격자, 넓은 입력공간)
================================================================
N = 3200   Pass Rate = 3200/3200 = 100.0%  (engine ⟷ independent spec oracle)

By category:
  SCOPE           128/128  100%
  BASELINE         70/70   100%
  EXCEPTION        42/42   100%
  BOUNDARY        112/112  100%
  GRANDFATHERING  2560/2560  100%
  CONFLICT        288/288  100%

By split (전량 측정 — 결정론 엔진, 튜닝 루프 없음 → 누수 위험 없음):
  CHALLENGE  912/912  100%
  DEV        1200/1200  100%
  LOCKED     1088/1088  100%

Coverage (판정 다양성):
  distinct status     = 4
  distinct rule_id    = 6
  distinct reason_code= 11

✓ 전 케이스 통과 — 엔진이 확정 명세(§H)와 전 입력공간에서 일치.
================================================================
```
