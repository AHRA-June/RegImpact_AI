"""RegChange Extractor — 공문 → 구조화 Before/After 추출 (LLM).

설계: LLM 호출(complete)을 주입 가능하게 해 API 키·비용 없이 오프라인 테스트 가능.
백엔드는 교체 가능:
  - gemini_completion()   — Google AI Studio(Gemini) REST. SDK 불필요(urllib), 기본 실행.
  - anthropic_completion() — Anthropic Claude SDK(structured output).
모델은 ADJUSTABLE.
"""
from __future__ import annotations

import json
import os
from typing import Callable, Optional

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


# --------------------------------------------------------------------------- #
# Gemini (Google AI Studio) 백엔드 — REST 직접 호출 (SDK 불필요)
# --------------------------------------------------------------------------- #

# 우리 JSON Schema(draft) → Gemini responseSchema(OpenAPI subset) 타입 매핑
_GEMINI_TYPE = {
    "object": "OBJECT",
    "array": "ARRAY",
    "string": "STRING",
    "number": "NUMBER",
    "integer": "INTEGER",
    "boolean": "BOOLEAN",
}


def to_gemini_schema(schema: dict) -> dict:
    """REGCHANGE_JSON_SCHEMA를 Gemini responseSchema 방언으로 변환.

    - type이 ["string","null"] 처럼 nullable이면 base 타입 + nullable:true.
    - additionalProperties는 Gemini가 미지원 → 제거.
    - enum/required/properties/items는 보존. type은 대문자.
    """
    t = schema.get("type")
    nullable = False
    if isinstance(t, list):
        non_null = [x for x in t if x != "null"]
        nullable = "null" in t
        t = non_null[0] if non_null else "string"

    out: dict = {}
    if t is not None:
        out["type"] = _GEMINI_TYPE.get(t, str(t).upper())
    if nullable:
        out["nullable"] = True
    if "enum" in schema:
        out["enum"] = list(schema["enum"])
    if t == "object":
        props = schema.get("properties", {})
        out["properties"] = {k: to_gemini_schema(v) for k, v in props.items()}
        if schema.get("required"):
            out["required"] = list(schema["required"])
            out["propertyOrdering"] = list(schema["required"])
    if t == "array" and "items" in schema:
        out["items"] = to_gemini_schema(schema["items"])
    return out


def _http_post_json(url: str, payload: dict, timeout: int = 120) -> dict:
    """urllib로 JSON POST. HTTPS_PROXY와 CA 번들(있으면)을 존중한다(프록시 샌드박스 호환)."""
    import ssl
    import urllib.error
    import urllib.request

    ca = os.environ.get("SSL_CERT_FILE") or os.environ.get("REQUESTS_CA_BUNDLE")
    ctx = ssl.create_default_context(cafile=ca) if ca else ssl.create_default_context()

    handlers: list = [urllib.request.HTTPSHandler(context=ctx)]
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    if proxy:
        handlers.append(urllib.request.ProxyHandler({"https": proxy, "http": proxy}))
    opener = urllib.request.build_opener(*handlers)

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with opener.open(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        raise RuntimeError(f"Gemini HTTP {e.code}: {body[:500]}") from None


def gemini_completion(
    model: str = "gemini-2.5-flash",
    max_tokens: int = 8192,
    api_key: Optional[str] = None,
    thinking_budget: int = 0,
) -> CompletionFn:
    """Google AI Studio(Gemini) 호출 함수를 만든다 (structured output, REST).

    인증: 인자 api_key 또는 환경변수 GEMINI_API_KEY / GOOGLE_API_KEY.
    thinking_budget=0 은 2.5 계열의 사고 토큰을 꺼서 structured 출력이 max_tokens에 잘리지
    않게 한다(추출 태스크엔 사고 불필요). 미지원 모델이면 이 필드를 무시하도록 예외 처리.
    """
    key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise RuntimeError(
            "GEMINI_API_KEY(또는 GOOGLE_API_KEY)가 없습니다. "
            "Google AI Studio(https://aistudio.google.com/apikey)에서 발급 후 설정하세요."
        )

    gemini_schema = to_gemini_schema(REGCHANGE_JSON_SCHEMA)
    base = "https://generativelanguage.googleapis.com/v1beta/models"

    def _complete(system: str, user: str) -> dict:
        gen_cfg: dict = {
            "responseMimeType": "application/json",
            "responseSchema": gemini_schema,
            "maxOutputTokens": max_tokens,
            "temperature": 0,
        }
        if thinking_budget is not None:
            gen_cfg["thinkingConfig"] = {"thinkingBudget": thinking_budget}

        payload = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": gen_cfg,
        }
        url = f"{base}/{model}:generateContent?key={key}"
        resp = _http_post_json(url, payload)

        candidates = resp.get("candidates") or []
        if not candidates:
            raise RuntimeError(f"Gemini 응답에 candidate 없음: {json.dumps(resp)[:400]}")
        cand = candidates[0]
        parts = (cand.get("content") or {}).get("parts") or []
        text = "".join(p.get("text", "") for p in parts).strip()
        if not text:
            fr = cand.get("finishReason")
            raise RuntimeError(f"Gemini 빈 응답(finishReason={fr}). max_tokens/thinking 확인.")
        return json.loads(text)

    return _complete


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
