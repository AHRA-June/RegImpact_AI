# CHANGELOG — TC Generator + Rule-Regression

> 최신이 위. 각 항목은 해당 버전 파일(`tc-generator_vN.md`)의 변경 요약이다.

## v3 (2026-08-13)
- **조합 격자 `generate_grid()` 3,200건 추가** — 결정론 cartesian, 오라클 라벨. Pass Rate 3,200/3,200
  100%, split 전량 측정 각 100%. mutation(경과규정 무력화) 격자 포착. 테스트 +6(총 92).
- `format_portfolio_stats(title=...)`, demo_portfolio가 큐레이션 106 + 격자 3,200 동시 산출.
  `docs/reports/rule_grid_stats.md`. 격자는 temporal 축 과표집(균형은 106이 보완).
- 이전(v2) 대비 상세: `tc-generator_v3.md` 상단 "변경 이력" 참고.

## v2 (2026-08-13)
- **평가셋 확대: seed 30 → 층화 합성 포트폴리오 106건.** split(DEV 36/LOCKED 35/CHALLENGE 35)
  부여·전량 측정, Pass Rate 106/106 100%, 커버리지 status 4/rule_id 6/reason_code 11.
- `portfolio.py`·`pass_rate_by_split()`·`format_portfolio_stats()`·`coverage()` 추가,
  `GeneratedCase.split` 필드. mutation test 포트폴리오 적용. 테스트 +11(총 86).
- `examples/demo_portfolio.py`, `docs/reports/rule_portfolio_stats.md`.
- 이전(v1) 대비 상세: `tc-generator_v2.md` 상단 "변경 이력" 참고.

## v1 (2026-08-13)
- 최초 작성 (신규). 기능단위 문서화 시작.
- 대상 구현: 독립 명세 오라클 차등검증(구조적 독립), 6 카테고리 30 케이스 Pass Rate 100%,
  mutation test 방어력. 테스트 11건.
- 이전 버전 없음.
