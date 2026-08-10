"""RegChange Extractor — 공문 → 구조화 Before/After 추출 (LLM).

설계: LLM 호출(complete)을 주입 가능하게 해 API 키·비용 없이 오프라인 테스트 가능.
실제 실행은 anthropic SDK(structured output). 기본 모델 claude-opus-5(ADJUSTABLE).
"""
from __future__ import annotations

import json
from typing import Callable

from .prompt import SYSTEM_PROMPT, build_user_prompt
from .schema import REGCHANGE_JSON_SCHEMA, RegChangeExtraction

# complete(system_prompt, user_prompt) -> 파싱된 dict (REGCHANGE_JSON_SCHEMA 준수)
CompletionFn = Callable[[str, str], dict]


def extract_regchange(sources: dict[str, str], *, complete: CompletionFn) -> RegChangeExtraction:
    """공문 원문(dict[doc_id, text])에서 RegChange를 추출한다.

    complete는 (system, user) -> dict를 반환하는 주입된 LLM 함수.
    테스트에서는 가짜 complete를, 실행에서는 anthropic_completion()을 넘긴다.
    """
    user = build_user_prompt(sources)
    raw = complete(SYSTEM_PROMPT, user)
    return RegChangeExtraction.from_dict(raw)


def anthropic_completion(model: str = "claude-opus-5", max_tokens: int = 16000) -> CompletionFn:
    """실제 Anthropic Claude 호출 함수를 만든다 (structured output).

    ANTHROPIC_API_KEY(또는 `ant auth login` 프로필)로 인증. import는 지연(테스트는 불필요).
    모델은 ADJUSTABLE — 비용/성능에 따라 claude-sonnet-5 등으로 교체 가능.
    """
    import anthropic  # 지연 import: 오프라인 테스트에는 SDK가 필요 없음

    client = anthropic.Anthropic()

    def _complete(system: str, user: str) -> dict:
        resp = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
            output_config={
                "format": {"type": "json_schema", "schema": REGCHANGE_JSON_SCHEMA}
            },
        )
        # output_config.format 보장: 첫 text 블록이 유효 JSON
        text = next(b.text for b in resp.content if b.type == "text")
        return json.loads(text)

    return _complete
