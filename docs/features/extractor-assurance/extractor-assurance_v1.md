# 기능단위: RegChange Extractor(E) + Citation Assurance(A)

> **버전:** v1   **날짜:** 2026-08-13   **상태:** 유효
> **이전 버전:** 없음 — 최초 작성

## 변경 이력 (→ v1)
- 최초 작성 (신규). 이전 버전 없음. (구현 자체는 2026-08-10 커밋 `6235b42`.)

---

## 1. 목적·책임
공식 원문(보도참고자료·FAQ)에서 **무엇이 바뀌었는지(RegChange)**를 구조화 추출하고(E),
그 추출이 **원문에 근거(grounding)하는지**를 인용 대조로 검증한다(A).
"정확한 자동화"가 아니라 **검증 가능한 초안화 + 환각의 명시적 탐지**가 가치제안.

## 2. 입력/출력 인터페이스
- 입력: 원문 텍스트(소스 스냅샷) + 소스 레지스트리(`sources.py`).
- 출력: `RegChangeExtraction` (`extractor/schema.py`)
  - `policy_id`, `effective_from`(ISO), `target_regions[]`,
    `changes[]`: {`category`(LTV/EXCEPTION/GRANDFATHERING/EFFECTIVE_DATE/REGION/SCOPE_LIMIT),
    `summary`, `before`, `after`, `citation`{`source_doc_id`,`quote`}, `confidence`}.
- **structured output**(JSON Schema, `additionalProperties:false`) 강제.
- **LLM 주입 가능**(dependency injection) → API 키 없이 오프라인 테스트 가능. 기본 모델 claude-opus-5.

## 3. 핵심 로직·설계 결정
- **Citation grounding:** 각 change의 `citation.quote`가 실제 원문에 존재하는지 대조 →
  환각 인용(Unsupported/Contradiction) 탐지 실측(`evaluate.py`).
- **골드 대조:** `docs/eval/regchange_gold_6_30.json`로 Change Completeness / Exception Recall 측정.
- **의존성 최소화:** Pydantic 대신 dataclass + JSON Schema dict.

## 4. 관련 파일
- `src/regimpact/extractor/` — `schema.py` `prompt.py` `extractor.py` `evaluate.py` `sources.py`
- `tests/test_extractor.py` · `examples/run_extractor.py`(API 키 필요)
- 골드: `docs/eval/regchange_gold_6_30.json` · 소스: `docs/sources/`
- 참조 스킬: `claude-api`

## 5. 검증 상태
- `tests/test_extractor.py` — 5건(오프라인, 전체 58 통과에 포함).
- **미실측:** 실제 LLM 1회 실행(run_extractor.py)로 Assurance 수치 확보는 NEXT(첫 실측 지표).

## 6. 알려진 제약·모호성
- Assurance 임계값(metrics_spec) TBD — 도메인 검수 후 확정.
- target_regions(한글 원문) → 엔진 지역코드 매핑은 현재 수동/외부(Impact Matrix 연동 시 region_code 명시).
- 깊은 4 dimension 중 ①Source Grounding ②Change/Exception Completeness 담당(`metrics_spec.md`).
