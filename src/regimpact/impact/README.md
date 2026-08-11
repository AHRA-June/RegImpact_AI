# impact — Before/After Impact Matrix

규제 변경이 대출 포트폴리오에 미치는 영향을 **룰엔진 실측**으로 산출한다.
브리프 코어 완성선(§18)의 중심 노드: `… → Before/After → Impact Matrix → …`.
`04_PLAN.md` Phase 1 Walking Skeleton의 "Impact Matrix(1~2행)"를 하드코딩이 아니라
엔진 실제 출력으로 구현한 것.

## 설계 — 정직한 counterfactual
같은 고객 프로필을 **두 정책 시점**에 동일 룰엔진으로 평가하고 그 '차이'만 낸다.
- `before` = 변경 전(as_of=2026-06-15): 지역 아직 非규제 → 종전 기준선. 경과규정 이벤트는
  '변경'의 산물이므로 before 뷰에선 제거(순수 기준선).
- `after`  = 변경 후(as_of=2026-07-02): 지역 규제 전환 + 경과규정 반영.

룰엔진이 이미 시점 해석을 하므로, 6·30 변경은 "같은 프로필을 두 날짜에 평가"로 표현된다.
**LOCKED §4 준수** — 새 규칙값을 만들지 않는다. before/after 모두 확정 명세의 엔진을 쓴다.

경과규정 대상 고객은 after에서도 종전규정(70%)을 유지 → before와 같음 → **UNCHANGED**.
즉 "경과규정 = 임팩트 없음"이 매트릭스에 정직하게 나타난다.

## 방향(ImpactDirection)
- `TIGHTENED` — LTV 하락, 또는 신규 대출거절(after 0%)
- `LOOSENED` — LTV 상승
- `UNCHANGED` — 변화 없음(경과규정 보호 포함)
- `STATUS_ONLY` — 수치 비교 불가하나 상태만 바뀜

**핵심 판정:** LTV 0%는 '완화된 결정'이 아니라 **대출 거절**이다. before가 검토불가/불명이어도
after 0%는 TIGHTENED로 읽는다.

## 고임팩트 (metrics_spec high-risk 후보 기반)
① LTV 30%p 이상 하락 · ② 신규 대출거절(after 0%, before 비거절) · ③ 자동판정→검토필요/판정불가 전환.

## 사용
```python
from regimpact.impact import analyze_portfolio, format_matrix
from regimpact.models import MortgageApplication
from datetime import date

apps = [MortgageApplication(region_code="GURI", evaluation_date=date(2026,7,2), house_count=0)]
matrix = analyze_portfolio(apps)
print(format_matrix(matrix))
print(matrix.n_high_impact, matrix.affected_rate)
```

## 실행
```bash
python -m pytest tests/test_impact.py
python examples/demo_impact_matrix.py
```
