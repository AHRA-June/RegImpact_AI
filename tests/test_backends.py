"""LLM 백엔드 레이어 테스트 — 전부 오프라인(네트워크·API 키·CLI 호출 없음).

무과금 경로의 핵심은 "structured output이 없는 백엔드도 스키마를 지키게 만드는" 것이므로
JSON 정규화·스키마 검증·교정 재시도를 집중적으로 검증한다.
"""
import json

import pytest

from regimpact.extractor import (
    LLMBackendError,
    available_providers,
    coerce_json,
    normalize_regions,
    replay_completion,
    resolve_completion,
    validate_regchange,
)
from regimpact.extractor.backends import with_schema_retry
from regimpact.extractor.schema import RegChangeExtraction
from regimpact.regions import normalize_region_name


def _valid_payload(**over):
    d = {
        "policy_id": "FSC_20260630",
        "effective_from": "2026-07-01",
        "target_regions": ["구리시"],
        "changes": [
            {
                "category": "LTV",
                "summary": "규제지역 LTV 강화",
                "before": "70%",
                "after": "40%",
                "citation": {"source_doc_id": "FSC_PRESS_20260630", "quote": "LTV 강화"},
                "confidence": 0.9,
            }
        ],
    }
    d.update(over)
    return d


# ------------------------------------------------------------------ coerce_json

def test_coerce_json_plain():
    assert coerce_json('{"a": 1}') == {"a": 1}


def test_coerce_json_strips_code_fence():
    assert coerce_json('```json\n{"a": 1}\n```') == {"a": 1}


def test_coerce_json_tolerates_preamble():
    assert coerce_json('다음과 같습니다:\n{"a": 1}\n감사합니다.') == {"a": 1}


def test_coerce_json_rejects_non_object():
    with pytest.raises(LLMBackendError):
        coerce_json("[1, 2, 3]")


def test_coerce_json_rejects_empty_and_garbage():
    for bad in ("", "   ", "JSON이 없습니다"):
        with pytest.raises(LLMBackendError):
            coerce_json(bad)


# ------------------------------------------------------------- validate_regchange

def test_validate_accepts_valid_payload():
    assert validate_regchange(_valid_payload()) == []


def test_validate_flags_missing_required_key():
    d = _valid_payload()
    del d["target_regions"]
    assert any("target_regions" in e for e in validate_regchange(d))


def test_validate_flags_unknown_category():
    d = _valid_payload()
    d["changes"][0]["category"] = "MADE_UP"
    assert any("category" in e for e in validate_regchange(d))


def test_validate_flags_incomplete_citation():
    d = _valid_payload()
    d["changes"][0]["citation"] = {"source_doc_id": "X"}   # quote 누락
    assert any("citation" in e for e in validate_regchange(d))


def test_validate_flags_confidence_out_of_range():
    d = _valid_payload()
    d["changes"][0]["confidence"] = 1.7
    assert any("confidence" in e for e in validate_regchange(d))


# ------------------------------------------------------------- with_schema_retry

def test_retry_repairs_malformed_first_response():
    """1차 응답이 코드펜스+스키마 위반이면 교정 요청 후 2차 응답을 채택한다."""
    calls = []

    def fake(system, user):
        calls.append(user)
        if len(calls) == 1:
            bad = _valid_payload()
            bad["changes"][0]["category"] = "WRONG"
            return "```json\n" + json.dumps(bad) + "\n```"
        return json.dumps(_valid_payload())

    out = with_schema_retry(fake)("sys", "user")
    assert out["changes"][0]["category"] == "LTV"
    assert len(calls) == 2
    assert "형식 위반" in calls[1]           # 교정 사유가 전달됨
    assert "LTV" not in calls[1].split("[직전 응답")[1]   # 정답은 알려주지 않음


def test_retry_raises_after_exhausting_attempts():
    with pytest.raises(LLMBackendError, match="스키마 검증 실패"):
        with_schema_retry(lambda s, u: "not json")("sys", "user")


def test_schema_retry_injects_json_only_instruction():
    seen = {}

    def fake(system, user):
        seen["system"] = system
        return json.dumps(_valid_payload())

    with_schema_retry(fake)("원래 시스템 프롬프트", "user")
    assert "원래 시스템 프롬프트" in seen["system"]
    assert "JSON 객체 하나만" in seen["system"]


# -------------------------------------------------------------------- providers

def test_available_providers_lists_all_names():
    avail = available_providers()
    assert set(avail) == {"cli", "gemini", "manual", "replay", "anthropic"}
    assert avail["manual"] and avail["replay"]      # 항상 무과금으로 가능


def test_resolve_rejects_unknown_provider():
    with pytest.raises(LLMBackendError, match="알 수 없는 provider"):
        resolve_completion("gpt5")


def test_manual_provider_writes_prompt_and_guides(tmp_path):
    """수동 모드: 응답 파일이 없으면 프롬프트를 남기고 안내와 함께 중단한다."""
    complete = resolve_completion("manual", workdir=tmp_path)
    with pytest.raises(LLMBackendError, match="수동 모드"):
        complete("sys", "user")
    assert (tmp_path / "prompt.txt").exists()
    assert "user" in (tmp_path / "prompt.txt").read_text(encoding="utf-8")

    (tmp_path / "response.json").write_text(json.dumps(_valid_payload()), encoding="utf-8")
    assert complete("sys", "user")["policy_id"] == "FSC_20260630"


def test_replay_provider_is_deterministic(tmp_path):
    """저장된 실행 기록을 LLM 호출 없이 그대로 재생한다(CI·재현용)."""
    run = tmp_path / "run.json"
    run.write_text(json.dumps({"provider": "cli", "extraction": _valid_payload()}),
                   encoding="utf-8")
    complete = replay_completion(run)
    assert complete("sys", "user") == complete("sys", "다른 프롬프트")


def test_replay_rejects_saved_result_violating_schema(tmp_path):
    bad = _valid_payload()
    bad["changes"][0]["category"] = "WRONG"
    run = tmp_path / "run.json"
    run.write_text(json.dumps({"extraction": bad}), encoding="utf-8")
    with pytest.raises(LLMBackendError, match="스키마 위반"):
        replay_completion(run)("sys", "user")


# ------------------------------------------------------ 지역 코드 정규화(경계 변환)

@pytest.mark.parametrize("name,code", [
    ("구리시", "GURI"),
    ("용인시 기흥구", "YONGIN_GIHEUNG"),
    ("화성시 동탄구", "HWASEONG_DONGTAN"),
    ("경기도 화성시 동탄구 일원", "HWASEONG_DONGTAN"),
    ("GURI", "GURI"),
    ("세종시", "SEJONG"),
])
def test_normalize_region_name(name, code):
    assert normalize_region_name(name) == code


def test_normalize_region_name_returns_none_when_unknown():
    assert normalize_region_name("부산 해운대구") is None
    assert normalize_region_name("") is None


def test_normalize_regions_maps_and_flags_unknown():
    """미확인 지역은 조용히 버리지 않고 unmapped로 표면화한다(누락 은폐 방지)."""
    ext = RegChangeExtraction.from_dict(
        _valid_payload(target_regions=["구리시", "화성시 동탄구", "부산 해운대구"])
    )
    rep = normalize_regions(ext)
    assert rep.normalized.target_regions == ["GURI", "HWASEONG_DONGTAN", "부산 해운대구"]
    assert rep.unmapped == ["부산 해운대구"]
    assert rep.coverage == pytest.approx(2 / 3)


def test_normalize_regions_is_idempotent():
    ext = RegChangeExtraction.from_dict(_valid_payload(target_regions=["구리시"]))
    once = normalize_regions(ext).normalized
    assert normalize_regions(once).normalized.target_regions == ["GURI"]
