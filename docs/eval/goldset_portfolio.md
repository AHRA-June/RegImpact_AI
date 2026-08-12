# 골드셋 확대 — 층화 합성 포트폴리오 (Rule-Regression)

> **목적:** metrics_spec §3(Rule/Test) 지표의 **분모를 키워** "정책 n=1, 소규모 seed(30건)" 한계를
> 완화하고, LOCKED §0-5의 **DEV / LOCKED TEST / CHALLENGE 3분할**을 코드로 실현한다.
> 생성: `src/regimpact/tc_generator/portfolio.py` · freeze: `docs/eval/goldset_manifest.json` ·
> 실행: `python examples/demo_portfolio.py`.

- **작성일:** 2026-08-12
- **규모:** **178건**(seed 30 + 층화 148, 결정적 생성) — 필요 시 층 확장으로 수천까지 스케일 가능.
- **정답 출처:** 각 케이스의 기대값은 `oracle.expected_outcome`(엔진 미import, 명세 §H 독립 재구현)이
  채운다. 포트폴리오를 키워도 회귀가 tautology가 되지 않음(차등 검증 유지).

---

## 왜 이렇게 만들었나 (Model Risk 관점)

1. **분모 확대 = 신뢰 확보.** seed 30건에서 100%는 표현력이 약하다. 178건(그중 CHALLENGE 67)에서
   엔진이 독립 오라클과 **100% 일치**하면, 알고리즘 §H 구현의 정확성 주장에 훨씬 큰 무게가 실린다.
2. **tautology 방지.** 기대값을 엔진이 아니라 **독립 명세 오라클**에서 유도한다(regions/grandfathering/
   rule_engine 미import). 대량 케이스에서도 disagreement가 곧 실제 버그다.
3. **3분할 규율.** LOCKED §0-5("평가셋을 개발보다 먼저, DEV/LOCKED/CHALLENGE 분리")를 결정적 해시
   분할로 구현. `cases_in_split(cases, "DEV")`로 "개발 중 DEV만 열람"을 코드로 강제 가능.
4. **CHALLENGE 가중.** 브리프 §11 철학대로 EXCEPTION/GRANDFATHERING/BOUNDARY/CONFLICT(하드
   카테고리)를 CHALLENGE에 더 배분(45% vs SCOPE/BASELINE 15%).

---

## 층 구성 (stratified)

| 층 | 조건 | 건수 | 주 카테고리 |
|---|---|---:|---|
| A. 규제 코어 | gf=none, scen=REG, 소유×예외 | 20 | EXCEPTION / CONFLICT |
| B. 기준선 | gf=none, scen∈{NONREG,UNREG} | 40 | BASELINE / CONFLICT |
| C. 경계 | gf=none, scen∈{EFFDAY,PREEFF} | 40 | BOUNDARY / CONFLICT |
| D. 경과규정 전용 | gf≠none, exc=plain, scen∈{REG,PREEFF} | 50 | GRANDFATHERING |
| E. 경과규정×예외 교차 | gf∈{g1in,g2,g3}×소유×예외 | 18 | GRANDFATHERING |
| F. 스코프 | 정책대출 / 비주택구입 × 소유 | 10 | SCOPE |

> 경과규정을 **전용 층에 가둔** 이유: 전체 예외 그리드와 교차시키면 GRANDFATHERING이 폭증
> (초안에서 500/610)해 카테고리 균형이 깨진다.

**입력 차원(층):** 시나리오 5(REG/NONREG/UNREG/EFFDAY/PREEFF) · 소유 5(hc0/hc1/hc1disp/hc2/hc3) ·
예외 4(plain/fh/rd/fhrd) · 경과규정 6(none/g1in/g1out/g2/g2ndp/g3).

---

## 현재 결과 (2026-08-12)

```
Rule-regression Pass Rate: 178/178 = 100.0%
  DEV        52/52  100%      SCOPE           10/10  100%
  LOCKED     59/59  100%      BASELINE        18/18  100%
  CHALLENGE  67/67  100%      EXCEPTION        9/9   100%
                              BOUNDARY        40/40  100%
                              GRANDFATHERING  68/68  100%
                              CONFLICT        33/33  100%
```

**mutation 민감도:** 엔진 상수(규제 표준 40%)를 오염시키면 포트폴리오 회귀가 max_ltv 불일치로
실패를 잡아낸다(`test_portfolio_catches_engine_mutation`) → 큰 골드셋이 '이빨'을 가짐을 증명.

---

## 한계 · 다음

- 여전히 **정책 1건(6·30)** 기반 합성. 실제 벤치마크가 아니라 명세 준수 회귀다(정직한 표기).
- RegChange 추출(§1 dimension) 골드는 실제 공문이 1건뿐이라 이 방식으로 확대 불가 — 별도 공문 확보 필요.
- 확장: 층별 상한을 늘려 수천 건으로(계획 Phase 2의 2,000~5,000), 지역·시점 버전 다양화, 비중 실측화.
