"""무료/대체 LLM 백엔드 어댑터 — Anthropic 없이 extractor를 돌리기 위한 주입 함수.

extractor.extract_regchange(sources, complete=…) 의 `complete(system, user) -> dict`
계약에 맞는 함수를 만든다. 의존성 최소화를 위해 표준 라이브러리(urllib)만 사용한다.

지원 백엔드:
  - Ollama            : 로컬·완전 무료·키 불필요 (http://localhost:11434)
  - OpenAI 호환 엔드포인트: Groq/OpenRouter/Gemini(OpenAI 호환)/vLLM/LM Studio 등 (무료 티어 키)

구조화 출력:
  - OpenAI 호환은 response_format=json_schema, Ollama는 format=<schema> 로 JSON을 강제한다.
  - 모델/엔드포인트가 스키마 강제를 지원하지 않아도 프롬프트가 JSON을 요구하므로, 코드 펜스·
    잡텍스트를 제거하고 첫 JSON 객체를 파싱해 방어한다.

주의: 소형/로컬 모델은 한국어 규제 추출 품질이 낮을 수 있다 — 그 경우 citation grounding·
gold recall이 떨어지고, 그것을 Assurance가 실패로 잡아낸다(정직한 실측).
"""
from __future__ import annotations

import json
import re
import urllib.request
from typing import Callable, Optional

from .schema import REGCHANGE_JSON_SCHEMA

# complete(system, user) -> dict, 그리고 테스트용 주입 transport(url, body, headers) -> str
CompletionFn = Callable[[str, str], dict]
Transport = Callable[[str, dict, dict], str]


def _urllib_post(url: str, payload: dict, headers: dict) -> str:
    """POST JSON, 응답 본문 텍스트를 반환(stdlib). 프록시 환경변수 자동 반영."""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    for k, v in headers.items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=180) as resp:  # noqa: S310 (신뢰 endpoint)
        return resp.read().decode("utf-8")


def _extract_json_object(text: str) -> dict:
    """모델 응답 문자열에서 JSON 객체를 뽑아 파싱한다(코드펜스·잡텍스트 방어)."""
    s = text.strip()
    # ```json ... ``` 펜스 제거
    fence = re.search(r"```(?:json)?\s*(.+?)\s*```", s, re.DOTALL)
    if fence:
        s = fence.group(1).strip()
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        # 첫 '{' ~ 마지막 '}' 구간 재시도
        start, end = s.find("{"), s.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(s[start:end + 1])
        raise


_JSON_INSTRUCTION = (
    "\n\n반드시 아래 JSON 스키마를 만족하는 **JSON 객체 하나만** 출력하라. "
    "설명·코드펜스·머리말 금지.\n" + json.dumps(REGCHANGE_JSON_SCHEMA, ensure_ascii=False)
)


def openai_compatible_completion(
    *,
    base_url: str,
    model: str,
    api_key: Optional[str] = None,
    max_tokens: int = 16000,
    temperature: float = 0.0,
    _transport: Transport = _urllib_post,
) -> CompletionFn:
    """OpenAI 호환 /chat/completions 엔드포인트용 complete 함수.

    base_url 예: 'https://api.groq.com/openai/v1', 'http://localhost:1234/v1'.
    구조화 출력은 response_format=json_schema 로 요청하되, 미지원 서버 대비 방어 파싱한다.
    """
    url = base_url.rstrip("/") + "/chat/completions"

    def _complete(system: str, user: str) -> dict:
        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system + _JSON_INSTRUCTION},
                {"role": "user", "content": user},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "regchange", "schema": REGCHANGE_JSON_SCHEMA},
            },
        }
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        raw = _transport(url, payload, headers)
        body = json.loads(raw)
        content = body["choices"][0]["message"]["content"]
        return _extract_json_object(content)

    return _complete


def ollama_completion(
    *,
    model: str = "qwen2.5",
    host: str = "http://localhost:11434",
    max_tokens: int = 16000,
    _transport: Transport = _urllib_post,
) -> CompletionFn:
    """Ollama /api/chat 용 complete 함수 (로컬·무료·키 불필요).

    구조화 출력은 Ollama의 format=<json schema> 로 강제한다. 사전에 `ollama pull <model>` 필요.
    """
    url = host.rstrip("/") + "/api/chat"

    def _complete(system: str, user: str) -> dict:
        payload = {
            "model": model,
            "stream": False,
            "format": REGCHANGE_JSON_SCHEMA,   # Ollama structured output
            "options": {"temperature": 0.0, "num_predict": max_tokens},
            "messages": [
                {"role": "system", "content": system + _JSON_INSTRUCTION},
                {"role": "user", "content": user},
            ],
        }
        raw = _transport(url, payload, {})
        body = json.loads(raw)
        content = body["message"]["content"]
        return _extract_json_object(content)

    return _complete
