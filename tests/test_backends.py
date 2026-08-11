"""무료 백엔드 어댑터 테스트 — 요청 조립·응답 파싱을 네트워크 없이 검증.

주입된 fake transport로 실제 HTTP 없이, 어댑터가 (1) 스키마를 요청에 실어 보내고
(2) OpenAI/Ollama 응답 형태에서 JSON을 정확히 뽑아 RegChangeExtraction으로 만드는지 본다.
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from regimpact.extractor import (  # noqa: E402
    extract_regchange,
    ollama_completion,
    openai_compatible_completion,
)
from regimpact.extractor.backends import _extract_json_object  # noqa: E402
from regimpact.extractor.schema import REGCHANGE_JSON_SCHEMA  # noqa: E402

_EXTRACTION_JSON = {
    "policy_id": "FSC_20260630",
    "effective_from": "2026-07-01",
    "target_regions": ["GURI"],
    "changes": [
        {"category": "LTV", "summary": "70→40", "before": "70%", "after": "40%",
         "citation": {"source_doc_id": "FSC_PRESS_20260630", "quote": "LTV 강화"},
         "confidence": 0.9},
    ],
}


def _openai_body(content: str) -> str:
    return json.dumps({"choices": [{"message": {"content": content}}]})


def _ollama_body(content: str) -> str:
    return json.dumps({"message": {"content": content}})


# ── 응답 파서: 펜스/잡텍스트 방어 ──
@pytest.mark.parametrize("raw", [
    '{"a": 1}',
    '```json\n{"a": 1}\n```',
    '```\n{"a": 1}\n```',
    '설명입니다.\n{"a": 1}\n끝.',
])
def test_extract_json_object(raw):
    assert _extract_json_object(raw) == {"a": 1}


# ── OpenAI 호환: 요청에 스키마 실림 + 응답 파싱 ──
def test_openai_compatible_builds_request_and_parses():
    captured = {}

    def fake_transport(url, payload, headers):
        captured["url"] = url
        captured["payload"] = payload
        captured["headers"] = headers
        return _openai_body(json.dumps(_EXTRACTION_JSON, ensure_ascii=False))

    complete = openai_compatible_completion(
        base_url="https://example/v1", model="free-model", api_key="k",
        _transport=fake_transport,
    )
    ext = extract_regchange({"FSC_PRESS_20260630": "..."}, complete=complete)

    assert captured["url"].endswith("/chat/completions")
    assert captured["headers"]["Authorization"] == "Bearer k"
    # 구조화 출력 스키마가 요청에 포함
    assert captured["payload"]["response_format"]["json_schema"]["schema"] == REGCHANGE_JSON_SCHEMA
    # 시스템 메시지에 스키마 지시가 붙는다
    assert "JSON" in captured["payload"]["messages"][0]["content"]
    # 응답이 RegChangeExtraction으로 파싱
    assert ext.policy_id == "FSC_20260630"
    assert ext.target_regions == ["GURI"]
    assert ext.changes[0].category == "LTV"


def test_openai_handles_fenced_content():
    def fake_transport(url, payload, headers):
        fenced = "```json\n" + json.dumps(_EXTRACTION_JSON, ensure_ascii=False) + "\n```"
        return _openai_body(fenced)

    complete = openai_compatible_completion(
        base_url="https://example/v1", model="m", _transport=fake_transport)
    ext = extract_regchange({"d": "x"}, complete=complete)
    assert ext.changes[0].after == "40%"


def test_openai_without_api_key_sends_no_auth_header():
    captured = {}

    def fake_transport(url, payload, headers):
        captured["headers"] = headers
        return _openai_body(json.dumps(_EXTRACTION_JSON))

    complete = openai_compatible_completion(
        base_url="https://example/v1", model="m", _transport=fake_transport)
    extract_regchange({"d": "x"}, complete=complete)
    assert "Authorization" not in captured["headers"]


# ── Ollama: format=schema + 응답 파싱 ──
def test_ollama_builds_request_and_parses():
    captured = {}

    def fake_transport(url, payload, headers):
        captured["url"] = url
        captured["payload"] = payload
        return _ollama_body(json.dumps(_EXTRACTION_JSON, ensure_ascii=False))

    complete = ollama_completion(model="qwen2.5", host="http://localhost:11434",
                                 _transport=fake_transport)
    ext = extract_regchange({"FSC_PRESS_20260630": "..."}, complete=complete)

    assert captured["url"].endswith("/api/chat")
    assert captured["payload"]["format"] == REGCHANGE_JSON_SCHEMA  # 구조화 출력
    assert captured["payload"]["stream"] is False
    assert ext.policy_id == "FSC_20260630"
