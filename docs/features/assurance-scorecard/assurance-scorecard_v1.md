# 기능단위: Assurance Scorecard (4 dimension + 확정 임계값)

> **버전:** v1   **날짜:** 2026-08-13   **상태:** 유효
> **이전 버전:** 없음 — 최초 작성

## 변경 이력 (→ v1)
- 최초 작성 (신규). 이전 버전 없음. (구현: `src/regimpact/assurance/`.)

---

## 1. 목적·책임
Assurance **4 dimension을 완성**하고, **확정 임계값(Strict)**으로 PASS/WARN/FAIL을 판정·집계한다.
기존 지표(citation·gold·regression)에 누락됐던 **3지표를 추가**해 12지표를 완비하고, 차원별·전체
종합 판정(고위험 FAIL → 전체 FAIL)을 낸다. 브리프 §13 Assurance의 정량 급소.

## 2. 입력/출력 인터페이스
- `build_scorecard(extraction, sources, gold, regression?) -> AssuranceScorecard`
- `format_scorecard_md(scorecard) -> str`
- `AssuranceScorecard`: `dimensions[]`, `overall`(Status), `failed[]`, `summary()`, `dimension_summary()`.
- `THRESHOLDS: dict[str, MetricSpec]` — 확정 임계값 단일 진실. `MetricSpec.evaluate(value) -> Status`.
- `compute_metrics(extraction, sources, gold, regression?) -> dict[key, float]` — 원시 지표.

## 3. 핵심 로직·설계 결정
- **누락 3지표 추가:**
  - ① **Source Contradiction Rate** — 인용은 grounded지만 주장한 LTV %값이 원문에 없는 비율(값 날조 프록시).
  - ② **Grandfathering Recall** — 골드 경과규정 항목 포착 비율(고위험, Change Completeness와 분리 노출).
  - ③ **Policy-version Consistency** — 효력일 경계 시점 질의에서 엔진이 시점정합 버전을 반환하는 비율.
    독립 오라클(expected_outcome)로 검증 → 룰엔진 시점 해석의 일관성.
- **확정 임계값(Strict, 사용자 확정 2026-08-13):** `thresholds.py`가 단일 진실. exact(=100%) 지표는
  WARN 밴드 없이 100% 아니면 FAIL. lower-is-better(Unsupported/Contradiction)는 반대 방향.
- **종합 판정:** 고위험(★) 지표 FAIL → 전체 FAIL, 그 외 FAIL/WARN → 전체 WARN, else PASS.
- **결정론·오프라인:** 모든 지표가 결정론 코드로 산출(API 불필요).

## 4. 관련 파일
- `src/regimpact/assurance/` — `thresholds.py`(임계값) `metrics.py`(원시 지표) `scorecard.py`(판정·렌더)
- `tests/test_assurance_scorecard.py` · `examples/assurance_scorecard.py`
- 산출물: `docs/reports/assurance_scorecard.md` · 임계 근거: `docs/metrics_spec.md §0-C`
- 연동: `validation` [8] 보고서 [6] 섹션(`dimension_summary()`), E2E 데모.

## 5. 검증 상태 (6·30, 2026-08-13)
- **12/12 지표 PASS → 종합 PASS.** ①100/0/0 ②100/100/100 ③100/100/100 ④100/100/100.
- 가드레일: 서민·실수요 누락 시 Exception Recall FAIL → 전체 FAIL(테스트 고정). 값 날조 시 Contradiction 포착.
- 테스트: `test_assurance_scorecard.py`(14) — 구성·실측·새 지표·임계 판정·종합 규칙·가드레일·렌더.

## 6. 알려진 제약·모호성
- n=1 문서셋(6·30). 오라클은 challenger(제3자 벤치마크 아님) → 100%는 "엔진=명세" 일치.
- Source Contradiction은 %값 존재 여부 프록시(NLI 아님) — 의미적 모순은 미탐지 가능.
- escalation 계열은 [ROADMAP](5번째 dimension 승격 여부는 03_OPEN_QUESTIONS Q2 잔여).
- provenance: 추출은 세션 수동 grounded(자동 claude-opus-5 API 무인 실행은 키 확보 후).
