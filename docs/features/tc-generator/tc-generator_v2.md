# 기능단위: TC Generator + Rule-Regression (독립 명세 오라클)

> **버전:** v2   **날짜:** 2026-08-13   **상태:** 유효
> **이전 버전:** v1 (`tc-generator_v1.md`)

## 변경 이력 (v1 → v2)
- **[범위]** 평가셋 확대: seed **30건 → 층화 합성 포트폴리오 106건**(`generate_portfolio()`).
  정답은 독립 오라클이 유도(차등검증) → 손라벨 없이 확장. 카테고리 6종 층화 커버.
- **[범위]** **split(DEV/LOCKED/CHALLENGE) 부여 + 전량 측정.** `GeneratedCase.split` 필드 추가,
  `RegressionReport.pass_rate_by_split()`, `format_portfolio_stats()`. CHALLENGE 35(적대적 가중).
- **[검증]** 포트폴리오 Pass Rate **106/106 100%**(engine ⟷ oracle), split별 100%,
  커버리지 status 4/rule_id 6/reason_code 11. 산출물 `docs/reports/rule_portfolio_stats.md`.
- **[검증]** mutation test를 포트폴리오에도 적용(LTV 상수·유주택 규칙 변조 시 실패 포착). 테스트 +11(총 86).
- **[문서]** `examples/demo_portfolio.py`, metrics_spec §3 seed/포트폴리오 비교·split 정당성 반영.

---

## 1. 목적·책임
룰엔진이 확정 명세(§H)를 정확히 구현했는지 **차등 검증(differential testing)**한다.
엔진 출력을 기대값으로 쓰면 회귀가 tautology가 되므로, **명세에서 독립 유도한 오라클(challenger)**과
대조한다(Model Risk 정석). Assurance 깊은 4 dimension 중 ④(Rule Regression & Conflict) 담당.

## 2. 입력/출력 인터페이스
- `generate_all() -> list[GeneratedCase]` — seed 30건(경계·예외·충돌).
- `generate_portfolio() -> list[GeneratedCase]` — 층화 합성 106건(split 부여).
- `expected_outcome(app) -> ExpectedOutcome` — 명세 독립 유도 기대값(rule_engine 미import).
- `run_regression(cases?) -> RegressionReport` — 엔진 ⟷ 오라클 비교.
  - `.pass_rate_by_category()`, `.pass_rate_by_split()`.
- `coverage(cases) -> dict` — 판정 다양성(distinct status/rule_id/reason_code).
- `format_report(report)` / `format_portfolio_stats(report)` -> str.

## 3. 핵심 로직·설계 결정
- **구조적 독립성:** 오라클(`oracle.py`)은 `rule_engine`·`regions`·`grandfathering`를 **import하지 않고**
  독립 재구현 → 어느 구현 오차든 disagreement로 드러남.
- **층화 생성(`portfolio.py`):** 입력 차원(지역·시점·house_count·예외·경과규정·스코프)을 중첩 루프로
  체계 훑기. 난수 없이 결정론(재현 가능). case_id 안정·유일.
- **split 전량 측정:** 룰엔진은 결정론(성능 튜닝 루프 없음) → LOCKED/CHALLENGE를 열어도 누수 위험 없음
  (04_PLAN §0-5 정합). LLM 추출용 골드셋 봉인 원칙과 별개. split은 라벨·리포트로 표기.
- **권위 기준:** §H. §E 충돌(유주택+생애최초)은 ConflictCase로 표면화(Q8).

## 4. 관련 파일
- `src/regimpact/tc_generator/` — `oracle.py` `generator.py` `portfolio.py` `regression.py`
- `tests/test_tc_generator.py`(seed) · `tests/test_portfolio.py`(포트폴리오)
- `examples/demo_tc_regression.py` · `examples/demo_portfolio.py`
- 리포트: `docs/reports/rule_portfolio_stats.md` · 설명: `docs/explainer/tc_regression_explainer.html`

## 5. 검증 상태
- seed: 30/30 100%(Boundary 8/8, Conflict 5/5).
- **포트폴리오: 106/106 100%** — split DEV 36/LOCKED 35/CHALLENGE 35(각 100%),
  커버리지 status 4·rule_id 6·reason_code 11. mutation 방어력 확인(seed·포트폴리오).
- 테스트: `test_tc_generator.py`(11) + `test_portfolio.py`(11) — 전체 86 통과에 포함.

## 6. 알려진 제약·모호성
- n=106은 검정력이 아니라 **실패모드 층화 커버리지 + 넓은 입력공간 명세 일치**가 목표.
- 오라클은 challenger(제3자 벤치마크 아님). 100%는 "엔진=명세"를 뜻하며, 명세 자체의 정합성은 별도.
- **후속:** 수천 건 확대(선택), CFL/Q8 도메인 확정 시 오라클·회귀 함께 갱신.
