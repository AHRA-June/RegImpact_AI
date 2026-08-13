# 기능단위: RegChange Extractor(E) + Citation Assurance(A)

> **버전:** v2   **날짜:** 2026-08-13   **상태:** 유효
> **이전 버전:** v1 (`extractor-assurance_v1.md`)

## 변경 이력 (v1 → v2)
- **[검증]** 첫 Assurance 실측 확보: `미실측` → **실측치 확보**. 6·30 원문 3건 grounded 추출을
  결정론 채점 하네스로 측정 — Citation Correctness `TBD` → **100%(9/9)**, Unsupported → **0%**,
  Change Completeness → **100%(4/4)**, Exception Recall → **50%(서민·실수요 누락)**, 시점·지역 → **OK**.
- **[범위]** 산출물 추가: `docs/eval/regchange_extracted_6_30.json`(추출 결과, provenance 명시),
  `examples/measure_assurance_6_30.py` → `docs/reports/assurance_6_30.md`.
- **[범위]** [6] Assurance가 E2E 검증보고서에 실측 수치로 연결(`examples/demo_e2e.py`).
- **[검증]** 실측 회귀 고정 테스트 `tests/test_assurance_measure.py`(3건) 추가 → 전체 75 통과.
- **[문서]** `metrics_spec.md`에 "첫 실측 결과(2026-08-13)" 블록 반영.
- **[제약]** provenance: Claude Code 세션 수동 grounded 추출(자동 claude-opus-5 API 무인 실행은 키 확보 후).

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
- **의존성 최소화:** Pydantic 대신 dataclass + JSON Schema dict.

## 4. 관련 파일
- `src/regimpact/extractor/` — `schema.py` `prompt.py` `extractor.py` `evaluate.py` `sources.py`
- `tests/test_extractor.py` · `tests/test_assurance_measure.py`
- 실행: `examples/run_extractor.py`(실제 LLM), `examples/measure_assurance_6_30.py`(저장 추출 채점)
- 골드/추출: `docs/eval/regchange_gold_6_30.json`, `docs/eval/regchange_extracted_6_30.json`
- 리포트: `docs/reports/assurance_6_30.md` · 참조 스킬 `claude-api`

## 5. 검증 상태 (첫 실측 2026-08-13)
| 지표 | dimension | 값 |
|---|---|---|
| Citation Correctness | ① | 100% (9/9) |
| Unsupported Claim Rate | ① | 0% |
| Change Completeness | ② | 100% (4/4) |
| Exception Recall | ② | **50%** (서민·실수요 누락) |
| Effective-date / Region | ③ | OK / OK |
- 테스트: `test_extractor.py`(5) + `test_assurance_measure.py`(3) — 전체 75 통과에 포함.

## 6. 알려진 제약·모호성
- **Exception Recall 50%:** 보수적 추출이 서민·실수요 예외를 미표면화 → 다음 반복 보완 대상(원문 FAQ에 존재).
- provenance: 수동 grounded 추출. **자동 claude-opus-5 API 무인 실행 1회는 키 확보 후**(수치 재현·비교).
- n=1 문서셋. 골드셋 100~120 확대 시 통계화(04_PLAN Phase 2).
- Assurance 임계값(pass/fail) 확정은 도메인 검수 후.
