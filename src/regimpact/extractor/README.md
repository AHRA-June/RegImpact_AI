# regimpact.extractor — RegChange Extractor (E) + Citation Assurance (A)

공문 원문 → **Before/After 변경사항 구조화 추출**(LLM) → **검증**(Assurance).
제품(E)과 신뢰(A)를 잇는 첫 컴포넌트.

## 설계 원칙
- **LLM 호출 주입(injectable):** `extract_regchange(sources, complete=...)`. 테스트는 가짜 `complete`,
  실행은 `anthropic_completion()`. → **API 키·비용 없이 오프라인 테스트** 가능.
- **structured output:** `output_config.format`(JSON Schema)로 스키마 강제 (`schema.py`).
- **grounding 강제:** 프롬프트가 원문 verbatim 인용을 요구 → deterministic하게 검증.
- **LLM은 룰을 만들지 않는다:** 추출은 '초안'이며, `rule_engine`(사람 확정 정답지)이 별도 검증 기준.

## 구조
- `schema.py` — RegChangeExtraction / RegChangeItem / Citation + JSON Schema
- `prompt.py` — grounding·citation 강제 프롬프트
- `extractor.py` — `extract_regchange()` + `anthropic_completion()`(claude-opus-5, ADJUSTABLE)
- `backends.py` — **무료/대체 백엔드** `ollama_completion()`(로컬·무료·키불필요), `openai_compatible_completion()`(무료 티어). stdlib만 사용, 구조화 출력 강제.
- `evaluate.py` — **Assurance 지표**
  - `check_citation_grounding()` — 인용이 원문에 실제 존재하는지(오프라인 실측) → Citation Correctness / Unsupported Claim Rate
  - `score_against_gold()` — 사람 확정 골드 대조 → Change Completeness / Exception Recall
- `sources.py` — `docs/sources/raw/*.txt` 로더

## 실행
```bash
python -m pytest -k "extractor or backends"   # 오프라인 로직 검증

# --e2e: 추출을 전체 파이프라인(Impact→Proposal→TC→Regression→Assurance→Report)에 관통
# --offline: canonical 추출로 배선만 확인(LLM 미호출)

# (A) 무료·로컬 — Ollama (키 불필요): `ollama pull qwen2.5` 후
REGIMPACT_EXTRACTOR_BACKEND=ollama REGIMPACT_EXTRACTOR_MODEL=qwen2.5 \
  python examples/run_extractor.py --e2e

# (B) 무료 티어 — OpenAI 호환 (Groq/OpenRouter/Gemini-호환 등, 무료 키)
REGIMPACT_EXTRACTOR_BACKEND=openai \
REGIMPACT_OPENAI_BASE_URL=https://api.groq.com/openai/v1 \
REGIMPACT_OPENAI_API_KEY=... REGIMPACT_EXTRACTOR_MODEL=llama-3.3-70b-versatile \
  python examples/run_extractor.py --e2e

# (C) Anthropic (유료)
ANTHROPIC_API_KEY=... REGIMPACT_EXTRACTOR_MODEL=claude-opus-5 \
  python examples/run_extractor.py --e2e
```

> 소형/로컬 모델은 한국어 규제 추출 품질이 낮을 수 있고, 그 경우 citation grounding·
> gold recall이 떨어진다 — Assurance가 그 실패를 실제로 잡아내 gate를 REVIEW_REQUIRED로
> 승격하는 것이 이 시스템의 요점이다(모델 무관하게 "검증 가능한 초안화").

## Assurance 시연 포인트
테스트 `test_citation_grounding_catches_hallucination`은 **의도적으로 심은 환각 인용**을
grounding 검사가 잡아내는 것을 보여준다 — "LLM이 LLM을 채점"하지 않는, 원문 대조 기반 검증.
