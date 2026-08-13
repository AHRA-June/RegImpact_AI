"""LLM 제공자 어댑터 — anthropic(유료) 없이도 추출을 돌릴 수 있게 한다.

Extractor는 완성 함수(CompletionFn: (system, user) -> dict)를 주입받도록 설계됐다(injection).
따라서 **어떤 제공자든** 이 시그니처만 맞추면 꽂을 수 있다. 이 모듈은 **OpenAI 호환** 엔드포인트를
쓰는 범용 어댑터를 제공한다 → 무료 옵션 전부를 base_url·model·키 환경변수만으로 커버:

    - Ollama (로컬, 완전 무료·가입 불필요):  base_url=http://localhost:11434/v1, 키 불필요
    - Groq (무료 티어):                      base_url=https://api.groq.com/openai/v1
    - OpenRouter (무료 모델 `:free`):        base_url=https://openrouter.ai/api/v1
    - Google Gemini (무료 티어, OpenAI 호환): base_url=https://generativelanguage.googleapis.com/v1beta/openai

의존성: **표준 라이브러리 urllib만** 사용(외부 SDK 불필요). structured output은 response_format
json_object + 프롬프트(스키마)로 유도하고, 응답 텍스트에서 JSON 오브젝트를 견고하게 파싱한다.
"""
from __future__ import annotations

import json
import os
import re
from typing import Callable, Optional

CompletionFn = Callable[[str, str], dict]

# 무료로 시작할 수 있는 제공자 프리셋 (모델은 예시 — 가용 모델로 교체 가능)
FREE_PROVIDERS: dict[str, dict] = {
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "model": "llama3.1",
        "key_env": None,            # 로컬, 인증 불필요
        "note": "로컬 실행, 완전 무료·가입 불필요. `ollama pull llama3.1` 후 사용.",
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "model": "llama-3.3-70b-versatile",
        "key_env": "GROQ_API_KEY",
        "note": "무료 티어. https://console.groq.com 에서 키 발급.",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "model": "meta-llama/llama-3.3-70b-instruct:free",
        "key_env": "OPENROUTER_API_KEY",
        "note": "무료 모델(`:free`). https://openrouter.ai 에서 키 발급.",
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "model": "gemini-2.0-flash",
        "key_env": "GEMINI_API_KEY",
        "note": "무료 티어. https://aistudio.google.com 에서 키 발급.",
    },
}

_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def extract_json_object(text: str) -> dict:
    """LLM 응답 텍스트에서 JSON 오브젝트를 견고하게 추출한다.

    코드펜스(```json ... ```)나 앞뒤 잡텍스트가 섞여도 첫 완결 오브젝트를 파싱.
    """
    if text is None:
        raise ValueError("빈 응답")
    # 1) 코드펜스 우선
    m = _FENCE.search(text)
    candidate = m.group(1).strip() if m else text.strip()
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass
    # 2) 첫 '{' ~ 마지막 '}' 구간
    start = candidate.find("{")
    end = candidate.rfind("}")
    if start != -1 and end != -1 and end > start:
        return json.loads(candidate[start:end + 1])
    raise ValueError(f"응답에서 JSON 오브젝트를 찾지 못함: {text[:120]!r}")


def openai_compatible_completion(
    base_url: str,
    model: str,
    *,
    api_key: Optional[str] = None,
    api_key_env: Optional[str] = None,
    max_tokens: int = 16000,
    temperature: float = 0.0,
    timeout: int = 180,
) -> CompletionFn:
    """OpenAI 호환 `/chat/completions` 엔드포인트용 완성 함수를 만든다(표준 라이브러리만).

    무료 제공자(Ollama/Groq/OpenRouter/Gemini-호환)를 base_url·model·키만 바꿔 사용.
    키는 api_key 직접 전달 또는 api_key_env(환경변수명)로 로드. 로컬(Ollama)은 키 없이 동작.
    """
    import urllib.request  # 지연 import

    key = api_key or (os.environ.get(api_key_env) if api_key_env else None)
    url = base_url.rstrip("/") + "/chat/completions"

    def _complete(system: str, user: str) -> dict:
        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            # 지원하는 제공자는 JSON 강제; 미지원이어도 프롬프트가 JSON을 유도.
            "response_format": {"type": "json_object"},
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        if key:
            req.add_header("Authorization", f"Bearer {key}")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        text = body["choices"][0]["message"]["content"]
        return extract_json_object(text)

    return _complete


def completion_from_env() -> Optional[CompletionFn]:
    """환경변수로 완성 함수를 구성한다(무료 제공자 선택). 미설정이면 None.

    사용:
        REGIMPACT_LLM_PROVIDER=ollama|groq|openrouter|gemini   (프리셋 사용)
        # 또는 직접 지정:
        REGIMPACT_LLM_BASE_URL=... REGIMPACT_LLM_MODEL=... [REGIMPACT_LLM_KEY_ENV=...]
        REGIMPACT_LLM_MODEL 로 프리셋 기본 모델을 덮어쓸 수 있음.
    """
    base_url = os.environ.get("REGIMPACT_LLM_BASE_URL")
    model = os.environ.get("REGIMPACT_LLM_MODEL")
    key_env = os.environ.get("REGIMPACT_LLM_KEY_ENV")

    provider = (os.environ.get("REGIMPACT_LLM_PROVIDER") or "").lower()
    if provider in FREE_PROVIDERS:
        preset = FREE_PROVIDERS[provider]
        base_url = base_url or preset["base_url"]
        model = model or preset["model"]
        key_env = key_env or preset["key_env"]

    if not (base_url and model):
        return None
    return openai_compatible_completion(base_url, model, api_key_env=key_env)
