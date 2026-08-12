# TC Generator + Rule-Regression

룰엔진(`regimpact.rule_engine`)이 **확정 명세**(`docs/05_RULE_SPEC.md §H`)를 정확히 구현했는지
**차등 검증(differential testing)** 하는 회귀 하네스.

## 왜 이렇게 만들었나 (설계 근거)

엔진이 스스로 만든 출력을 '기대값'으로 쓰면 회귀는 tautology(항상 통과)가 되어 무의미하다.
Model Risk / 모델검증 관점의 정석은 **독립적으로 유도한 기준(challenger model)** 과 대조하는 것이다.

```
                  ┌─────────────────────┐
   MortgageApp ──▶│ rule_engine.evaluate│──▶ LtvDecision  (검증 대상)
        │         └─────────────────────┘        │
        │                                        ▼
        │         ┌─────────────────────┐    ┌──────────┐
        └────────▶│ oracle.expected_... │──▶ │ 비교/채점 │──▶ Pass Rate
                  └─────────────────────┘    └──────────┘
                   (명세에서 독립 유도)
```

- **오라클(`oracle.py`)** 은 `rule_engine`·`regions`·`grandfathering` 을 **import 하지 않는다.**
  지역상태·경과규정·판정 우선순위를 명세에서 독립 코드 경로로 재구현한다.
  → `regions.py` / `grandfathering.py` / `rule_engine.py` 어느 구현의 오차든 disagreement로 드러난다.
- **생성기(`generator.py`)** 는 '입력을 어떻게 훑을지'만 책임진다(정답은 오라클이 준다 = 관심사 분리).
- **회귀(`regression.py`)** 는 엔진 출력과 오라클 기대값을 status / max_ltv / rule_id /
  grandfathering / reason_codes 기준으로 비교하고, 카테고리별 Pass Rate를 낸다.

## 카테고리 (metrics_spec.md §3와 정렬)

| 카테고리 | 대상 |
|---|---|
| `SCOPE` | P0/P0b 스코프·정책대출(Discovery) |
| `BASELINE` | 非규제/시행 전/미등록 지역 기준선 |
| `EXCEPTION` | 무주택 예외 계층(생애최초·서민실수요·처분조건부) |
| `BOUNDARY` | 경계값(효력일·경과규정 컷오프 ±1일, house_count 0/1/2) |
| `GRANDFATHERING` | G1/G2/G3 경과규정 |
| `CONFLICT` | 동시 충족·우선순위 충돌·escalation |

## 사용법

```python
from regimpact.tc_generator import generate_all, run_regression, format_report

report = run_regression(generate_all())
print(format_report(report))
print(report.pass_rate)                         # Rule-regression Pass Rate
print(report.pass_rate_by_category())           # {카테고리: (통과, 전체, 비율)}
```

데모: `python examples/demo_tc_regression.py`

## 골드셋 확대 — 층화 합성 포트폴리오 (`portfolio.py`)

seed 30건을 넘어 입력 차원을 **체계적으로 층화 스윕**해 178건을 결정적으로 생성한다. 분모를 키워
metrics_spec §3 지표의 신뢰를 확보하고, LOCKED §0-5의 **DEV/LOCKED/CHALLENGE 3분할**을 코드로 실현.

```python
from regimpact.tc_generator import generate_portfolio, run_regression, cases_in_split

cases = generate_portfolio()              # 178건, 각 케이스에 category + split
report = run_regression(cases)            # 엔진 ⟷ 오라클 (현재 178/178 100%)
print(report.pass_rate_by_split())        # {DEV/LOCKED/CHALLENGE: (통과,전체,비율)}
dev_only = cases_in_split(cases, "DEV")   # 개발 중 DEV만 열람(LOCKED §0-5)
```

- 기대값은 여전히 **오라클**에서만 온다 → 대량에서도 tautology 아님.
- 분할은 **결정적**(hashlib) + CHALLENGE 하드 카테고리 가중. `docs/eval/goldset_manifest.json`에 freeze.
- 데모/freeze: `python examples/demo_portfolio.py`. 상세: `docs/eval/goldset_portfolio.md`.

## fixture에 이빨이 있는가? (mutation test)

`tests/test_tc_generator.py` 는 엔진에 의도적 버그를 심어(LTV 상수 변조, 경과규정 무력화)
회귀가 실제로 실패를 잡아내는지 검증한다. 이는 이 fixture가 tautology가 아니라
**실제 회귀 방어력**을 가진다는 증거다.

## 알려진 명세 모호성

- **CFL-04 (유주택 + 생애최초):** `§E` 주석은 "논리상 불가 → 데이터 충돌 시 NEEDS_HUMAN_REVIEW",
  `§H` 의사코드(엔진 구현 기준)는 P4 short-circuit으로 0%. 현재 **권위 기준은 §H**(0%)를 채택하고,
  케이스에 `spec_note`로 표면화한다. 향후 정책 결정은 `docs/03_OPEN_QUESTIONS.md` 참조.
