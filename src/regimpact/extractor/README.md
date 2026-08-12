# regimpact.extractor — RegChange Extractor (E) + Citation Assurance (A)

공문 원문 → **Before/After 변경사항 구조화 추출**(LLM) → **검증**(Assurance).
제품(E)과 신뢰(A)를 잇는 첫 컴포넌트.

## 설계 원칙
- **LLM 호출 주입(injectable):** `extract_regchange(sources, complete=...)`. 테스트는 가짜 `complete`,
  실행은 `gemini_completion()`(기본) 또는 `anthropic_completion()`. → **API 키·비용 없이 오프라인 테스트** 가능.
- **백엔드 교체 가능:** Gemini(Google AI Studio)·Anthropic 모두 **SDK 없이 urllib REST**로 동작(추가 의존성 0).
  둘 다 structured output(Gemini responseSchema / Anthropic output_config.format)로 스키마 강제.
- **structured output:** Gemini `responseSchema` / Anthropic `output_config.format`(JSON Schema, `schema.py`).
- **grounding 강제:** 프롬프트가 원문 verbatim 인용을 요구 → deterministic하게 검증.
- **LLM은 룰을 만들지 않는다:** 추출은 '초안'이며, `rule_engine`(사람 확정 정답지)이 별도 검증 기준.

## 구조
- `schema.py` — RegChangeExtraction / RegChangeItem / Citation + JSON Schema
- `prompt.py` — grounding·citation 강제 프롬프트
- `extractor.py` — `extract_regchange()` + `gemini_completion()`(gemini-2.5-flash, REST) /
  `anthropic_completion()`(claude-opus-5, REST) + `to_gemini_schema()`(JSON Schema→Gemini 방언 변환)
- `evaluate.py` — **Assurance 지표**
  - `check_citation_grounding()` — 인용이 원문에 실제 존재하는지(오프라인 실측) → Citation Correctness / Unsupported Claim Rate
  - `score_against_gold()` — 사람 확정 골드 대조 → Change Completeness / Exception Recall
- `sources.py` — `docs/sources/raw/*.txt` 로더

## 실행
```bash
python -m pytest -k extractor          # 오프라인 로직 검증(7개)

# 기본: Gemini (SDK 불필요). https://aistudio.google.com/apikey 에서 발급
export GEMINI_API_KEY=...
python examples/run_extractor.py        # 공문 → 추출 → Assurance 채점

# 또는 Anthropic 백엔드 (역시 SDK 불필요, REST). https://console.anthropic.com 에서 발급
export ANTHROPIC_API_KEY=...
REGIMPACT_LLM=anthropic python examples/run_extractor.py
```
백엔드/모델 강제: `REGIMPACT_LLM=gemini|anthropic`, `REGIMPACT_MODEL=...`(예: claude-opus-5).
두 백엔드 모두 `output_config.format`/`responseSchema`로 structured output을 강제하며 의존성 0.

## Assurance 시연 포인트
테스트 `test_citation_grounding_catches_hallucination`은 **의도적으로 심은 환각 인용**을
grounding 검사가 잡아내는 것을 보여준다 — "LLM이 LLM을 채점"하지 않는, 원문 대조 기반 검증.
