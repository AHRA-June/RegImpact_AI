# 기능단위: TC Generator + Rule-Regression (독립 명세 오라클)

> **버전:** v3   **날짜:** 2026-08-13   **상태:** 유효
> **이전 버전:** v2 (`tc-generator_v2.md`)

## 변경 이력 (v2 → v3)
- **[범위]** 대규모 **조합 격자(`generate_grid()`) 3,200건** 추가 — 결정론적 cartesian(지역·시점·
  house_count·처분·생애최초·서민실수요·경과규정 6-way + 스코프 격자). 정답은 오라클 유도(손라벨 없음).
- **[검증]** 격자 Pass Rate **3,200/3,200 100%**(engine ⟷ oracle), split 전량 측정 각 100%,
  커버리지 status 4·reason_code 11. 생성+회귀 ≈0.05s. `docs/reports/rule_grid_stats.md`.
- **[검증]** mutation test 격자 적용(경과규정 무력화 시 GRANDFATHERING 실패 포착). 테스트 +6(총 92).
- **[문서]** `format_portfolio_stats(title=...)` 옵션, `demo_portfolio.py`가 큐레이션 106 + 격자 3,200 동시 산출.
- **[제약]** 격자는 경과규정(temporal) 축을 의도적으로 넓게 샘플링 → GRANDFATHERING 비중이 큼
  (최고위험 차원 과표집). 카테고리 균형 뷰는 큐레이션 106건이 담당(상호 보완).

---

## 1. 목적·책임
룰엔진이 확정 명세(§H)를 정확히 구현했는지 **차등 검증(differential testing)**한다.
엔진 출력을 기대값으로 쓰면 회귀가 tautology가 되므로, **명세에서 독립 유도한 오라클(challenger)**과
대조한다(Model Risk 정석). Assurance 깊은 4 dimension 중 ④(Rule Regression & Conflict) 담당.

## 2. 입력/출력 인터페이스
- `generate_all() -> list[GeneratedCase]` — seed 30건(경계·예외·충돌, 사람이 읽는 case_id).
- `generate_portfolio() -> list[GeneratedCase]` — 큐레이션 층화 106건(카테고리 균형, split 부여).
- `generate_grid() -> list[GeneratedCase]` — 조합 격자 3,200건(넓은 입력공간, split 부여).
- `expected_outcome(app) -> ExpectedOutcome` — 명세 독립 유도 기대값(rule_engine 미import).
- `run_regression(cases?) -> RegressionReport` — `.pass_rate_by_category()` / `.pass_rate_by_split()`.
- `coverage(cases)`, `format_portfolio_stats(report, title?)`.

## 3. 핵심 로직·설계 결정
- **구조적 독립성:** 오라클은 `rule_engine`·`regions`·`grandfathering` 미import → 어느 오차든 disagreement.
- **3계층 평가셋:** seed 30(가독성) / 큐레이션 106(카테고리 균형) / 격자 3,200(스케일·넓은 입력공간).
  모두 오라클이 라벨 → 손라벨 없이 확장.
- **결정론:** 난수 없이 cartesian/중첩 루프 + 안정 case_id → 재현 가능.
- **split 전량 측정:** 룰엔진은 결정론(튜닝 루프 없음) → LOCKED/CHALLENGE 열어도 누수 위험 없음
  (04_PLAN §0-5). LLM 골드셋 봉인과 별개.

## 4. 관련 파일
- `src/regimpact/tc_generator/` — `oracle.py` `generator.py` `portfolio.py`(포트폴리오+격자) `regression.py`
- `tests/test_tc_generator.py`(seed) · `tests/test_portfolio.py`(포트폴리오+격자)
- `examples/demo_tc_regression.py` · `examples/demo_portfolio.py`
- 리포트: `docs/reports/rule_portfolio_stats.md`, `docs/reports/rule_grid_stats.md`

## 5. 검증 상태
- seed 30/30 · 큐레이션 106/106 · **격자 3,200/3,200** — 전부 100%(engine ⟷ oracle).
- split·커버리지(status 4·rule_id 6·reason_code 11) 산출. mutation 방어력 확인(3계층).
- 테스트: `test_tc_generator.py`(11) + `test_portfolio.py`(17) — 전체 92 통과에 포함.

## 6. 알려진 제약·모호성
- 오라클은 challenger(제3자 벤치마크 아님). 100%는 "엔진=명세"를 뜻하며 명세 자체 정합성은 별도.
- 격자는 GRANDFATHERING 과표집(temporal 6-way 축). 카테고리 균형은 큐레이션 106이 보완.
- **후속:** 더 큰 격자(선택), CFL/Q8 도메인 확정 시 오라클·회귀 함께 갱신.
