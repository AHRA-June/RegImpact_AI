"""RegChange Extractor + Assurance 테스트 (오프라인, API 불필요).

LLM 호출은 가짜 complete로 주입해 파싱·grounding·골드 채점 로직을 검증한다.
Citation grounding은 완전 deterministic이라 실제 원문으로 실측한다.
"""
import json
from pathlib import Path

from regimpact.extractor import (
    check_citation_grounding,
    extract_regchange,
    load_sources,
    score_against_gold,
    to_gemini_schema,
)
from regimpact.extractor.schema import REGCHANGE_JSON_SCHEMA

REPO = Path(__file__).resolve().parents[1]
GOLD = json.loads((REPO / "docs" / "eval" / "regchange_gold_6_30.json").read_text(encoding="utf-8"))


def _real_quote(text: str, start: int, length: int = 60) -> str:
    """원문에서 실제 substring을 잘라 grounded 인용으로 사용."""
    return text[start:start + length]


def _fake_extraction_dict(sources: dict) -> dict:
    fsc = sources["FSC_PRESS_20260630"]
    return {
        "policy_id": "FSC_20260630",
        "effective_from": "2026-07-01",
        "target_regions": ["GURI", "YONGIN_GIHEUNG", "HWASEONG_DONGTAN"],
        "changes": [
            {
                "category": "LTV", "summary": "규제지역 주담대 LTV 70% → 40%",
                "before": "70%", "after": "40%", "confidence": 0.95,
                "citation": {"source_doc_id": "FSC_PRESS_20260630", "quote": _real_quote(fsc, 200)},
            },
            {
                "category": "EFFECTIVE_DATE", "summary": "시행일 7.1 (7월 1일)",
                "before": None, "after": "2026-07-01", "confidence": 0.9,
                "citation": {"source_doc_id": "FSC_PRESS_20260630", "quote": _real_quote(fsc, 400)},
            },
            {
                "category": "REGION", "summary": "구리·용인기흥·화성동탄 규제지역(투기과열·조정대상) 지정",
                "before": None, "after": "REGULATED", "confidence": 0.9,
                "citation": {"source_doc_id": "FSC_PRESS_20260630", "quote": _real_quote(fsc, 600)},
            },
            {
                "category": "GRANDFATHERING", "summary": "6.30까지 접수/계약+계약금은 종전규정(경과규정)",
                "before": None, "after": "종전규정", "confidence": 0.85,
                "citation": {"source_doc_id": "FSC_PRESS_20260630", "quote": _real_quote(fsc, 800)},
            },
            {
                "category": "EXCEPTION", "summary": "생애최초·서민실수요는 완화 LTV",
                "before": None, "after": "생애최초 70% / 서민실수요 60%", "confidence": 0.8,
                "citation": {"source_doc_id": "FAQ_20260630",
                             "quote": _real_quote(sources["FAQ_20260630"], 300)},
            },
            {
                # 의도적 환각: 원문에 없는 인용 → grounding에서 unsupported로 잡혀야 함
                "category": "LTV", "summary": "지어낸 항목",
                "before": "60%", "after": "50%", "confidence": 0.4,
                "citation": {"source_doc_id": "FSC_PRESS_20260630",
                             "quote": "이 문장은 원문에 존재하지 않는 지어낸 인용입니다 XYZ123."},
            },
        ],
    }


def test_extract_parses_structured_output():
    sources = load_sources()
    assert sources, "원문 로드 실패 — docs/sources/raw 확인"
    ext = extract_regchange(sources, complete=lambda s, u: _fake_extraction_dict(sources))
    assert ext.policy_id == "FSC_20260630"
    assert ext.effective_from == "2026-07-01"
    assert "GURI" in ext.target_regions
    assert len(ext.changes) == 6
    assert ext.changes[0].category == "LTV"
    assert ext.changes[0].after == "40%"


def test_citation_grounding_catches_hallucination():
    sources = load_sources()
    ext = extract_regchange(sources, complete=lambda s, u: _fake_extraction_dict(sources))
    report = check_citation_grounding(ext, sources)
    assert report.total == 6
    assert report.grounded == 5           # 5개는 실제 원문 substring
    assert len(report.ungrounded) == 1    # 지어낸 1개
    assert report.ungrounded[0].summary == "지어낸 항목"
    assert abs(report.unsupported_claim_rate - (1 / 6)) < 1e-9


def test_grounding_ignores_pdf_linewrap_whitespace():
    """원문이 문장 중간에서 줄바꿈돼도(PDF/HWP 추출 아티팩트) 정확한 인용은 grounded.

    실측에서 발견: '...전일(6.30일)\n까지...' 원문을 모델이 '(6.30일)까지'로 정확히 인용하면,
    공백정규화만으로는 오탐(환각)이 났다. 공백 무관 비교(_squish)로 방어.
    """
    sources = {"DOC": "규제지역 효력 발생일 전일(6.30일)\n까지 접수 완료 시 종전규정 적용"}
    d = {
        "policy_id": "P", "effective_from": None, "target_regions": [],
        "changes": [{
            "category": "GRANDFATHERING", "summary": "경과규정",
            "before": None, "after": "종전규정", "confidence": 0.9,
            # 원문엔 '(6.30일) 까지'(줄바꿈)지만 모델은 붙여서 정확히 인용
            "citation": {"source_doc_id": "DOC", "quote": "전일(6.30일)까지 접수 완료"},
        }],
    }
    ext = extract_regchange(sources, complete=lambda s, u: d)
    report = check_citation_grounding(ext, sources)
    assert report.grounded == 1
    assert report.ungrounded == []


def test_grounding_perfect_when_all_real():
    sources = load_sources()
    d = _fake_extraction_dict(sources)
    d["changes"] = [c for c in d["changes"] if c["summary"] != "지어낸 항목"]
    ext = extract_regchange(sources, complete=lambda s, u: d)
    report = check_citation_grounding(ext, sources)
    assert report.citation_correctness == 1.0
    assert report.unsupported_claim_rate == 0.0


def test_score_against_gold():
    sources = load_sources()
    ext = extract_regchange(sources, complete=lambda s, u: _fake_extraction_dict(sources))
    g = score_against_gold(ext, GOLD)
    # 필수 변경 4개(LTV/시행일/경과규정/지역) 모두 포착
    assert g.change_completeness == 1.0
    # 예외 2개(생애최초·서민실수요) 포착
    assert g.exception_recall == 1.0
    assert g.effective_date_correct is True
    assert g.regions_correct is True
    assert g.missed_changes == []


def test_score_detects_missing_exception():
    sources = load_sources()
    d = _fake_extraction_dict(sources)
    # 예외 항목 제거 → exception_recall 하락해야 함
    d["changes"] = [c for c in d["changes"] if c["category"] != "EXCEPTION"]
    ext = extract_regchange(sources, complete=lambda s, u: d)
    g = score_against_gold(ext, GOLD)
    assert g.exception_recall == 0.0
    assert "first_home_buyer" in g.missed_exceptions


# ---------- Gemini 스키마 변환기 (오프라인) ----------
def test_to_gemini_schema_maps_types_and_nullable():
    gs = to_gemini_schema(REGCHANGE_JSON_SCHEMA)
    assert gs["type"] == "OBJECT"
    # nullable 합성: ["string","null"] → STRING + nullable:true
    eff = gs["properties"]["effective_from"]
    assert eff["type"] == "STRING" and eff["nullable"] is True
    # 배열 items 재귀
    assert gs["properties"]["target_regions"]["items"]["type"] == "STRING"
    # required 보존 + propertyOrdering 부여
    assert set(gs["required"]) == {"policy_id", "effective_from", "target_regions", "changes"}


def test_to_gemini_schema_preserves_enum_and_drops_additionalprops():
    gs = to_gemini_schema(REGCHANGE_JSON_SCHEMA)
    item = gs["properties"]["changes"]["items"]
    assert "additionalProperties" not in item          # Gemini 미지원 → 제거
    assert item["properties"]["category"]["enum"][0] == "LTV"
    # 중첩 object(citation)도 변환
    assert item["properties"]["citation"]["type"] == "OBJECT"
