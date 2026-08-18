# regimpact.extractor — RegChange Extractor (E) + Citation Assurance (A)

공문 원문 → **Before/After 변경사항 구조화 추출**(LLM) → **검증**(Assurance).
제품(E)과 신뢰(A)를 잇는 첫 컴포넌트.

## 설계 원칙
- **LLM 호출 주입(injectable):** `extract_regchange(sources, complete=...)`. 테스트는 가짜 `complete`,
  실행은 `resolve_completion(provider)`. → **API 키·비용 없이 오프라인 테스트 + 실제 실행** 가능.
- **무과금 provider 우선:** `cli`(Claude Code 구독 포함) / `gemini`(무료 티어) / `manual` / `replay`.
  유료 `anthropic`은 선택 경로. 상세는 `docs/06_LLM_PROVIDER.md`.
- **스키마 강제:** 유료 structured output이 없어도 JSON 정규화 + 스키마 검증 + 1회 교정 재시도
  (`backends.with_schema_retry`)로 형식을 보장한다.
- **경계 변환은 LLM에게 맡기지 않는다:** 한글 지역명 → 룰엔진 지역코드는 결정적 별칭 테이블
  (`postprocess.normalize_regions`). 프롬프트에 코드 어휘를 주면 정답 힌트가 되어 평가가 오염된다.
- **grounding 강제:** 프롬프트가 원문 verbatim 인용을 요구 → deterministic하게 검증.
- **LLM은 룰을 만들지 않는다:** 추출은 '초안'이며, `rule_engine`(사람 확정 정답지)이 별도 검증 기준.

## 구조
- `schema.py` — RegChangeExtraction / RegChangeItem / Citation + JSON Schema
- `prompt.py` — grounding·citation 강제 프롬프트
- `extractor.py` — `extract_regchange()` (LLM 주입 지점)
- `backends.py` — **provider 레이어**: `cli`/`gemini`/`manual`/`replay`/`anthropic` + 스키마 검증·교정 재시도
- `postprocess.py` — `normalize_regions()`: 지역명→코드 결정적 변환, 실패는 `unmapped`로 표면화
- `evaluate.py` — **Assurance 지표**
  - `check_citation_grounding()` — 인용이 원문에 실제 존재하는지(오프라인 실측) → Citation Correctness / Unsupported Claim Rate
  - `score_against_gold()` — 사람 확정 골드 대조 → Change Completeness / Exception Recall
- `sources.py` — `docs/sources/raw/*.txt` 로더

## 실행
```bash
python -m pytest -k "extractor or backends"     # 오프라인 로직 검증 (호출 0회)

# 실제 실행 — 유료 API 키 불필요 (Claude Code 구독 사용)
python examples/run_extractor.py --provider cli --model claude-sonnet-5

# 저장된 실측 재현 (LLM 호출 0회, 완전 결정적)
python examples/run_extractor.py --provider replay --run docs/eval/runs/run_cli_sonnet5_v2.json
```

실측 결과·확인된 결함: `docs/eval/EXTRACTOR_RUN_REPORT.md`

## Assurance 시연 포인트
테스트 `test_citation_grounding_catches_hallucination`은 **의도적으로 심은 환각 인용**을
grounding 검사가 잡아내는 것을 보여준다 — "LLM이 LLM을 채점"하지 않는, 원문 대조 기반 검증.
