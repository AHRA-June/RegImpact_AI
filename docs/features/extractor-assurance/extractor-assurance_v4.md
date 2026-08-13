# 기능단위: RegChange Extractor(E) + Citation Assurance(A)

> **버전:** v4   **날짜:** 2026-08-13   **상태:** 유효
> **이전 버전:** v3 (`extractor-assurance_v3.md`)

## 변경 이력 (v3 → v4)
- **[범위]** **무료 LLM 제공자 지원**: `providers.py` — OpenAI 호환 범용 어댑터
  (`openai_compatible_completion`) + env 구성(`completion_from_env`) + 무료 프리셋(`FREE_PROVIDERS`:
  Ollama 로컬/Groq/OpenRouter/Gemini). **anthropic(유료)·외부 SDK 불필요** — 표준 라이브러리 urllib만.
- **[범위]** 견고 JSON 파서 `extract_json_object`(코드펜스·잡텍스트 대응).
- **[문서]** `run_extractor.py`를 제공자-불문으로 재작성(무료 옵션 안내·env 기반 선택).
- **[검증]** 어댑터 오프라인 테스트 10건(파싱·주입 관통·env 구성). 전체 120 통과.
- **[근거]** Extractor는 완성 함수 주입식(injection) 설계라 제공자 교체가 자연스럽다(LOCKED §0 ADJUSTABLE).

---

## 1. 목적·책임
공식 원문에서 **무엇이 바뀌었는지(RegChange)**를 구조화 추출(E)하고, 원문 근거(grounding)를 검증(A)한다.
"정확한 자동화"가 아니라 **검증 가능한 초안화 + 환각의 명시적 탐지**가 가치제안.

## 2. 입력/출력 인터페이스
- 입력: 원문 텍스트 + 소스 레지스트리(`sources.py`).
- 출력: `RegChangeExtraction`(policy_id·effective_from·target_regions·changes[category·summary·before·after·citation·confidence]).
- **완성 함수 주입:** `extract_regchange(sources, complete=CompletionFn)` — `(system,user)->dict` 이면 무엇이든 가능.
- **제공자 어댑터:**
  - `openai_compatible_completion(base_url, model, api_key_env?)` — Ollama/Groq/OpenRouter/Gemini(호환) 공용.
  - `completion_from_env()` — `REGIMPACT_LLM_PROVIDER`(프리셋) 또는 `REGIMPACT_LLM_BASE_URL/MODEL` 로 구성.
  - `anthropic_completion(model)` — 선택(유료).
- 채점: `check_citation_grounding`, `score_against_gold`.

## 3. 핵심 로직·설계 결정
- **제공자 독립(주입식):** 확률론 컴포넌트를 특정 벤더에 묶지 않는다. 무료(로컬 Ollama 포함)로도 실측 가능.
- **의존성 최소화:** 어댑터는 표준 라이브러리 urllib만. structured output은 response_format+프롬프트로 유도,
  `extract_json_object`로 견고 파싱(미지원 제공자도 대응).
- **Citation grounding(결정론):** 인용 verbatim 대조로 환각 탐지. 골드 대조로 완전성·재현율.

## 4. 관련 파일
- `src/regimpact/extractor/` — `schema.py` `prompt.py` `extractor.py` `evaluate.py` `sources.py` **`providers.py`**
- `tests/test_extractor.py` · `tests/test_assurance_measure.py` · **`tests/test_providers.py`**
- 실행: `examples/run_extractor.py`(무료 옵션 포함), `examples/measure_assurance_6_30.py`(저장 추출 채점)
- 골드/추출: `docs/eval/regchange_gold_6_30.json`, `regchange_extracted_6_30.json`

## 5. 검증 상태 (실측 2026-08-13)
- Assurance: Citation 100%(10/10)·Unsupported 0%·Change Completeness 100%·Exception Recall 100%·시점/지역 OK.
- 어댑터: 오프라인 10건(JSON 파싱·주입 관통·env 구성). 전체 120 통과.

## 6. 알려진 제약·모호성
- **무료 제공자 실행은 사용자 환경에서**(로컬 Ollama = 키 불필요·완전 무료; Groq/OpenRouter/Gemini = 무료 키).
  현 검증 환경은 키·egress 정책상 라이브 호출 미수행 — provenance는 세션 수동 grounded 추출 유지.
- 무료 모델(소형 Llama 등)은 대형 모델 대비 추출 완전성이 낮을 수 있음 → Assurance 지표로 그 차이가 드러남
  (본 시스템의 목적: 어떤 모델을 쓰든 **검증 가능**하게).
- n=1 문서셋. 오라클은 challenger(제3자 벤치마크 아님).
