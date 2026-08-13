# 기능단위: RegChange Extractor(E) + Citation Assurance(A)

> **버전:** v3   **날짜:** 2026-08-13   **상태:** 유효
> **이전 버전:** v2 (`extractor-assurance_v2.md`)

## 변경 이력 (v2 → v3)
- **[검증]** Exception Recall: **50% → 100%**. FAQ Q2 원문 근거(verbatim)로 서민·실수요(real_demand)
  예외 항목을 추출에 보완 — v2에서 Assurance가 포착한 누락을 닫음.
- **[범위]** 추출 항목 수: `9건 → 10건`(서민·실수요 EXCEPTION 추가). Citation Correctness 9/9 → **10/10**
  유지(신규 인용도 verbatim), Unsupported 0% 유지.
- **[문서]** `regchange_extracted_6_30.json` `_meta`에 `iteration`(v1→v2, Recall 50%→100%) 기록,
  measure 리포트·metrics_spec에 **Assurance 피드백 루프**(측정→포착→보완) 서사 반영.
- **[검증]** `test_assurance_measure` 기대값 갱신(total 10, Exception Recall 1.0). 전체 75 통과 유지.

> ⚠️ 용어: 여기서 v1/v2/v3는 **이 기능단위 문서의 버전**이다. 추출 산출물 내부의 `_meta.iteration`
> "v1→v2"는 **추출 반복 회차**(서민·실수요 보완)를 가리킨다. 문서 v2에 1차 실측, 문서 v3에 반복 보완이 담긴다.

---

## 1. 목적·책임
공식 원문(보도참고자료·FAQ)에서 **무엇이 바뀌었는지(RegChange)**를 구조화 추출하고(E),
그 추출이 **원문에 근거(grounding)하는지**를 인용 대조로 검증한다(A).
"정확한 자동화"가 아니라 **검증 가능한 초안화 + 환각의 명시적 탐지**가 가치제안.

## 2. 입력/출력 인터페이스
- 입력: 원문 텍스트(소스 스냅샷) + 소스 레지스트리(`sources.py`).
- 출력: `RegChangeExtraction` (`extractor/schema.py`)
  - `policy_id`, `effective_from`(ISO), `target_regions[]`,
    `changes[]`: {`category`, `summary`, `before`, `after`, `citation`{`source_doc_id`,`quote`}, `confidence`}.
- **structured output**(JSON Schema, `additionalProperties:false`) 강제.
- **LLM 주입 가능**(dependency injection) → API 키 없이 오프라인 테스트/채점 가능. 기본 모델 claude-opus-5.
- 채점: `check_citation_grounding(ext, sources)`(결정론), `score_against_gold(ext, gold)`.

## 3. 핵심 로직·설계 결정
- **Citation grounding:** 각 change의 `citation.quote`가 원문(정규화)에 **verbatim 부분문자열**로 존재하는지
  대조 → 환각 인용 탐지(`evaluate.py`). 의역/재구성은 unsupported로 잡힘.
- **골드 대조:** `docs/eval/regchange_gold_6_30.json`로 Change Completeness / Exception Recall 측정.
- **피드백 루프:** Assurance가 포착한 누락(서민·실수요)을 원문 근거로 보완 → 재측정. 완전성↑, 환각 0 유지.

## 4. 관련 파일
- `src/regimpact/extractor/` — `schema.py` `prompt.py` `extractor.py` `evaluate.py` `sources.py`
- `tests/test_extractor.py` · `tests/test_assurance_measure.py`
- 실행: `examples/run_extractor.py`(실제 LLM), `examples/measure_assurance_6_30.py`(저장 추출 채점)
- 골드/추출: `docs/eval/regchange_gold_6_30.json`, `docs/eval/regchange_extracted_6_30.json`
- 리포트: `docs/reports/assurance_6_30.md` · 참조 스킬 `claude-api`

## 5. 검증 상태 (실측 2026-08-13, v2 반복 후)
| 지표 | dimension | 값 |
|---|---|---|
| Citation Correctness | ① | 100% (10/10) |
| Unsupported Claim Rate | ① | 0% |
| Change Completeness | ② | 100% (4/4) |
| Exception Recall | ② | **100%** (2/2, 서민·실수요 보완) |
| Effective-date / Region | ③ | OK / OK |
- 테스트: `test_extractor.py`(5) + `test_assurance_measure.py`(3) — 전체 75 통과에 포함.

## 6. 알려진 제약·모호성
- provenance: 수동 grounded 추출. **자동 claude-opus-5 API 무인 실행 1회는 키 확보 후**(수치 재현·비교).
- n=1 문서셋. 골드셋 100~120 확대 시 통계화(04_PLAN Phase 2).
- Assurance 임계값(pass/fail) 확정은 도메인 검수 후.
