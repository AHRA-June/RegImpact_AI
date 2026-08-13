# 기능단위: TC Generator + Rule-Regression (독립 명세 오라클)

> **버전:** v1   **날짜:** 2026-08-13   **상태:** 유효
> **이전 버전:** 없음 — 최초 작성

## 변경 이력 (→ v1)
- 최초 작성 (신규). 이전 버전 없음. (구현 자체는 2026-08-10 커밋 `9b950a0`.)

---

## 1. 목적·책임
룰엔진이 확정 명세(§H)를 정확히 구현했는지 **차등 검증(differential testing)**한다.
엔진 출력을 기대값으로 쓰면 회귀가 tautology가 되므로, **명세에서 독립 유도한 오라클(challenger)**과
대조한다(Model Risk 정석). Assurance 깊은 4 dimension 중 ④(Rule Regression & Conflict) 담당.

## 2. 입력/출력 인터페이스
- `generate_all() -> list[GeneratedCase]` — 경계·예외·충돌 케이스 체계 생성.
- `expected_outcome(app) -> ExpectedOutcome` — 명세 독립 유도 기대값(rule_engine 미import).
- `run_regression(cases?) -> RegressionReport` — 엔진 ⟷ 오라클 비교, Pass Rate 산출.
- `format_report(report) -> str`.

## 3. 핵심 로직·설계 결정
- **구조적 독립성:** 오라클(`oracle.py`)은 `rule_engine`·`regions`·`grandfathering`를 **import하지 않고**
  지역·경과·판정을 독립 코드 경로로 재구현 → 어느 구현 오차든 disagreement로 드러남.
- **관심사 분리:** 생성기는 '입력을 어떻게 훑을지', 오라클은 '정답이 무엇인지'를 책임.
- **카테고리:** SCOPE/BASELINE/EXCEPTION/BOUNDARY/GRANDFATHERING/CONFLICT.
- **mutation test:** 엔진에 버그를 심으면 회귀가 실패로 잡는지 확인(fixture 방어력 증명).
- **권위 기준:** §H(엔진 구현 기준). §E 충돌(유주택+생애최초)은 ConflictCase로 표면화(Q8).

## 4. 관련 파일
- `src/regimpact/tc_generator/` — `oracle.py` `generator.py` `regression.py`
- `tests/test_tc_generator.py` · `examples/demo_tc_regression.py`
- 설명 자료: `docs/explainer/tc_regression_explainer.html`

## 5. 검증 상태
- `tests/test_tc_generator.py` — 11건(전체 58 통과에 포함).
- 현재 30 케이스 Pass Rate 100%(Boundary 8/8, Conflict 5/5). mutation test 2건 방어력 확인.

## 6. 알려진 제약·모호성
- 케이스 수 = 6·30 소규모 seed. **후속:** 층화 합성 포트폴리오 2,000~5,000 확대(04_PLAN Phase 2).
- CFL-04(Q8) 도메인 확정 시 오라클·회귀 함께 갱신 필요.
