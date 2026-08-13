"""LLM 제공자 어댑터 테스트 (오프라인).

라이브 호출 없이 검증: ①JSON 견고 파싱(펜스·잡텍스트) ②주입식 완성 함수로 추출 관통
③env 기반 구성(무료 프리셋) ④anthropic 없이 동작(외부 SDK 불필요).
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from regimpact.extractor import (  # noqa: E402
    FREE_PROVIDERS,
    completion_from_env,
    extract_json_object,
    extract_regchange,
    openai_compatible_completion,
)


# --- JSON 견고 파싱 ---
def test_parse_plain_json():
    assert extract_json_object('{"a": 1}') == {"a": 1}


def test_parse_code_fence():
    text = "여기 결과:\n```json\n{\"policy_id\": \"X\", \"changes\": []}\n```\n끝"
    assert extract_json_object(text)["policy_id"] == "X"


def test_parse_surrounding_text():
    text = 'Sure! {"k": [1,2]} 도움이 됐길.'
    assert extract_json_object(text) == {"k": [1, 2]}


def test_parse_empty_raises():
    with pytest.raises(ValueError):
        extract_json_object("설명만 있고 JSON 없음")


# --- 주입식: 어떤 제공자든 (system,user)->dict 이면 추출 관통 ---
def test_extract_with_injected_completion():
    """OpenAI 호환 응답을 흉내낸 fake completion으로 추출이 동작해야 한다."""
    def fake_complete(system: str, user: str) -> dict:
        return {
            "policy_id": "FSC_20260630",
            "effective_from": "2026-07-01",
            "target_regions": ["GURI"],
            "changes": [{
                "category": "LTV", "summary": "70→40",
                "before": "70%", "after": "40%",
                "citation": {"source_doc_id": "FAQ_20260630", "quote": "LTV(70→40%)"},
                "confidence": 0.9,
            }],
        }
    ext = extract_regchange({"FAQ_20260630": "..."}, complete=fake_complete)
    assert ext.policy_id == "FSC_20260630"
    assert ext.changes[0].after == "40%"


# --- 어댑터 구성 (라이브 호출 없이 함수 생성만) ---
def test_openai_compatible_builds_callable():
    fn = openai_compatible_completion("http://localhost:11434/v1", "llama3.1")
    assert callable(fn)


def test_free_providers_registry():
    assert set(FREE_PROVIDERS) == {"ollama", "groq", "openrouter", "gemini"}
    # ollama는 로컬·무료·키 불필요
    assert FREE_PROVIDERS["ollama"]["key_env"] is None


# --- env 기반 구성 ---
def test_completion_from_env_none_when_unset(monkeypatch):
    for k in ("REGIMPACT_LLM_PROVIDER", "REGIMPACT_LLM_BASE_URL", "REGIMPACT_LLM_MODEL"):
        monkeypatch.delenv(k, raising=False)
    assert completion_from_env() is None


def test_completion_from_env_preset(monkeypatch):
    monkeypatch.setenv("REGIMPACT_LLM_PROVIDER", "ollama")
    monkeypatch.delenv("REGIMPACT_LLM_BASE_URL", raising=False)
    monkeypatch.delenv("REGIMPACT_LLM_MODEL", raising=False)
    fn = completion_from_env()
    assert callable(fn)   # ollama 프리셋으로 구성됨(키 불필요)


def test_completion_from_env_direct(monkeypatch):
    monkeypatch.delenv("REGIMPACT_LLM_PROVIDER", raising=False)
    monkeypatch.setenv("REGIMPACT_LLM_BASE_URL", "https://api.groq.com/openai/v1")
    monkeypatch.setenv("REGIMPACT_LLM_MODEL", "llama-3.3-70b-versatile")
    assert callable(completion_from_env())
