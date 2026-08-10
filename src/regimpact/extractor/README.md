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
- `evaluate.py` — **Assurance 지표**
  - `check_citation_grounding()` — 인용이 원문에 실제 존재하는지(오프라인 실측) → Citation Correctness / Unsupported Claim Rate
  - `score_against_gold()` — 사람 확정 골드 대조 → Change Completeness / Exception Recall
- `sources.py` — `docs/sources/raw/*.txt` 로더

## 실행
```bash
python -m pytest -k extractor          # 오프라인 로직 검증(5개)
pip install ".[llm]"                    # 실제 실행용 SDK
export ANTHROPIC_API_KEY=...            # 또는: ant auth login
python examples/run_extractor.py        # 공문 → 추출 → Assurance 채점
```

## Assurance 시연 포인트
테스트 `test_citation_grounding_catches_hallucination`은 **의도적으로 심은 환각 인용**을
grounding 검사가 잡아내는 것을 보여준다 — "LLM이 LLM을 채점"하지 않는, 원문 대조 기반 검증.
