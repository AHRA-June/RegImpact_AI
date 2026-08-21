import pathlib
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
)

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


def test_grounding_perfect_when_all_real():
    sources = load_sources()
    d = _fake_extraction_dict(sources)
    d["changes"] = [c for c in d["changes"] if c["summary"] != "지어낸 항목"]
    ext = extract_regchange(sources, complete=lambda s, u: d)
    report = check_citation_grounding(ext, sources)
    assert report.citation_correctness == 1.0
    assert report.unsupported_claim_rate == 0.0


# 채점 로직 자체를 보는 테스트는 **자체 골드**를 쓴다.
# 실제 골드(regchange_gold_6_30.json)는 커버리지를 넓히려고 계속 자라므로, 그것에 묶어 두면
# 골드를 확장할 때마다 스코어러 테스트가 깨진다 — 테스트가 골드 확장을 방해하게 된다.
MINI_GOLD = {
    "effective_from": "2026-07-01",
    "target_regions": ["GURI", "YONGIN_GIHEUNG", "HWASEONG_DONGTAN"],
    "required_changes": [
        {"id": "LTV_40", "keywords": ["40%"]},
        {"id": "GF", "keywords": ["경과", "종전규정"]},
    ],
    "exceptions": [{"name": "first_home_buyer", "keywords": ["생애최초"]}],
}


def test_score_against_gold():
    sources = load_sources()
    ext = extract_regchange(sources, complete=lambda s, u: _fake_extraction_dict(sources))
    g = score_against_gold(ext, MINI_GOLD)
    assert g.change_completeness == 1.0
    assert g.exception_recall == 1.0
    assert g.effective_date_correct is True
    assert g.regions_correct is True
    assert g.missed_changes == []


def test_score_matches_keywords_containing_spaces():
    """키워드와 원문 양쪽을 같은 기준으로 정규화하지 않으면 공백이 든 키워드가 영원히 안 맞는다."""
    sources = load_sources()
    ext = extract_regchange(sources, complete=lambda s, u: _fake_extraction_dict(sources))
    gold = {"required_changes": [{"id": "X", "keywords": ["7월 1일", "2026-07-01", "7.1"]}],
            "exceptions": [], "effective_from": "2026-07-01", "target_regions": []}
    assert score_against_gold(ext, gold).change_completeness == 1.0


def test_score_detects_missing_exception():
    sources = load_sources()
    d = _fake_extraction_dict(sources)
    # 예외 항목 제거 → exception_recall 하락해야 함
    d["changes"] = [c for c in d["changes"] if c["category"] != "EXCEPTION"]
    ext = extract_regchange(sources, complete=lambda s, u: d)
    g = score_against_gold(ext, MINI_GOLD)
    assert g.exception_recall == 0.0
    assert "first_home_buyer" in g.missed_exceptions


# ---------- 인용 대조 정규화 (2026-08-18 정정) ----------

def test_grounding_tolerates_pdf_line_breaks_inside_words():
    """PDF 추출본은 단어 중간에서도 줄을 바꾼다 — 그것 때문에 실제 인용이 환각으로 잡혔었다."""
    from regimpact.extractor import RegChangeExtraction, check_citation_grounding

    ext = RegChangeExtraction.from_dict({
        "policy_id": "P", "effective_from": "2026-07-01", "target_regions": [],
        "changes": [{
            "category": "LTV", "summary": "s", "before": None, "after": None,
            "citation": {"source_doc_id": "D1", "quote": "규제지역 내 3억원 초과 APT 취득"},
            "confidence": 0.9,
        }],
    })
    sources = {"D1": "전세대출 보유 차주의 규제\n지역 내 3억원 초과 APT 취득과"}
    assert check_citation_grounding(ext, sources).citation_correctness == 1.0


def test_grounding_still_catches_fabricated_wording():
    """공백을 무시해도 **다른 단어를 지어낸 인용**은 걸려야 한다 — 환각 탐지력을 잃지 않았는가."""
    from regimpact.extractor import RegChangeExtraction, check_citation_grounding

    ext = RegChangeExtraction.from_dict({
        "policy_id": "P", "effective_from": "2026-07-01", "target_regions": [],
        "changes": [{
            "category": "LTV", "summary": "s", "before": None, "after": None,
            "citation": {"source_doc_id": "D1", "quote": "규제지역 내 5억원 초과 APT 취득"},
            "confidence": 0.9,
        }],
    })
    sources = {"D1": "전세대출 보유 차주의 규제\n지역 내 3억원 초과 APT 취득과"}
    assert check_citation_grounding(ext, sources).unsupported_claim_rate == 1.0


# ---------- 문서별 추출 + 문서 간 병합 (D-02 대책) ----------

def _item(cat, summary, doc, quote="q", before=None, after=None):
    from regimpact.extractor.schema import Citation, RegChangeItem
    return RegChangeItem(category=cat, summary=summary, citation=Citation(doc, quote),
                         before=before, after=after, confidence=0.9)


def test_per_document_extraction_calls_once_per_document():
    """문서별 추출은 문서 수만큼 호출하고, 각 호출에는 그 문서만 들어간다."""
    from regimpact.extractor import extract_per_document

    seen = []

    def fake(system, user):
        doc = next(d for d in ("A", "B") if f"<doc id={d}>" in user)
        seen.append(doc)
        assert f"<doc id={'B' if doc == 'A' else 'A'}>" not in user
        return {"policy_id": "P", "effective_from": "2026-07-01", "target_regions": [doc],
                "changes": [{"category": "LTV", "summary": f"{doc} 변경", "before": None,
                             "after": None, "citation": {"source_doc_id": doc, "quote": "q"},
                             "confidence": 0.9}]}

    ext, rep = extract_per_document({"A": "본문A", "B": "본문B"}, complete=fake)
    assert seen == ["A", "B"]
    assert rep.per_document == {"A": 1, "B": 1}
    assert len(ext.changes) == 2 and set(ext.target_regions) == {"A", "B"}


def test_per_document_cache_avoids_repeat_calls(tmp_path):
    """무과금 경로에서 한 번의 실행이 수 분이라, 완료된 문서를 다시 부르지 않아야 한다."""
    from regimpact.extractor import extract_per_document

    calls = []

    def fake(system, user):
        calls.append(1)
        return {"policy_id": "P", "effective_from": None, "target_regions": [],
                "changes": [{"category": "LTV", "summary": "s", "before": None, "after": None,
                             "citation": {"source_doc_id": "A", "quote": "q"}, "confidence": 0.9}]}

    for _ in range(2):
        extract_per_document({"A": "본문"}, complete=fake, cache_dir=tmp_path)
    assert len(calls) == 1


def test_cross_document_merge_combines_the_same_fact_and_keeps_both_citations():
    from regimpact.extractor import merge_cross_document

    items = [
        _item("LTV", "규제지역 내 주담대 취급시 LTV 70%에서 40%로 강화", "FSC",
              before="70%", after="40%"),
        _item("LTV", "규제지역 내 주담대 취급시 LTV 규제비율 70%→40% 강화", "FAQ",
              before="70%", after="40%"),
    ]
    # 병합 '동작'을 보는 테스트이므로 임계값을 명시한다. 기본값(0.5)은 일부러 보수적이라
    # 이 정도 표현 차이는 합치지 않는다 — 그 보수성은 아래 테스트가 따로 고정한다.
    merged, removed = merge_cross_document(items, threshold=0.4)
    assert removed == 1 and len(merged) == 1
    # 대표는 더 긴 요약(FAQ), 나머지는 corroboration으로 남는다 — 어느 쪽도 버려지지 않는다
    docs = {merged[0].citation.source_doc_id} | {
        c.source_doc_id for c in merged[0].corroborations
    }
    assert docs == {"FSC", "FAQ"}


def test_default_threshold_is_conservative():
    """기본값은 '합칠 수 있는 것'보다 '합치면 안 되는 것'을 우선한다 — 누락이 중복보다 위험하다."""
    from regimpact.extractor import merge_cross_document

    items = [
        _item("LTV", "규제지역 내 주담대 취급시 LTV 70%에서 40%로 강화", "FSC",
              before="70%", after="40%"),
        _item("LTV", "규제지역 내 주담대 취급시 LTV 규제비율 70%→40% 강화", "FAQ",
              before="70%", after="40%"),
    ]
    assert merge_cross_document(items)[1] == 0


def test_merge_never_touches_items_from_the_same_document():
    """한 문서 안에서 모델이 나눈 항목은 나눈 이유가 있다고 본다."""
    from regimpact.extractor import merge_cross_document

    items = [
        _item("EXCEPTION", "생애최초는 60% 유지(좌동)", "FAQ", after="60%"),
        _item("EXCEPTION", "서민·실수요자는 60% 유지(좌동)", "FAQ", after="60%"),
    ]
    merged, removed = merge_cross_document(items, threshold=0.1)
    assert removed == 0 and len(merged) == 2


def test_merge_keeps_different_entities_apart_across_documents():
    """개체어가 다르면 문장 구조가 같아도 다른 사실이다 — 지문(fingerprint)이 막는다."""
    from regimpact.extractor import merge_cross_document

    items = [
        _item("EXCEPTION", "서민·실수요자 요건: 연소득 9천만원 이하", "FSC"),
        _item("EXCEPTION", "생애최초 요건: 연소득 7천만원 이하", "FAQ"),
    ]
    merged, removed = merge_cross_document(items, threshold=0.1)
    assert removed == 0 and len(merged) == 2


def test_merge_prefers_the_fuller_summary():
    """축약된 서술이 완전한 열거를 덮어쓰면 D-02가 병합 단계에서 되살아난다."""
    from regimpact.extractor import merge_cross_document

    short = _item("EXCEPTION", "생애최초·정책모기지 등 완화 적용", "FSC")
    full = _item("EXCEPTION", "생애최초·정책모기지 등 완화 적용 대상 상세 서술", "FAQ")
    merged, _ = merge_cross_document([short, full], threshold=0.5)
    assert merged[0].summary == full.summary


def test_merge_report_surfaces_effective_date_conflicts():
    """문서마다 시행일이 다르면 조용히 하나를 고르지 않고 드러낸다."""
    from regimpact.extractor import extract_per_document

    def fake(system, user):
        doc = next(d for d in ("A", "B") if f"<doc id={d}>" in user)
        return {"policy_id": "P", "effective_from": "2026-07-01" if doc == "A" else "2026-07-05",
                "target_regions": [], "changes": []}

    _, rep = extract_per_document({"A": "x", "B": "y"}, complete=fake)
    assert rep.effective_from_conflict
    assert any("effective_from" in c for c in rep.conflicts)


# ---------- 값 전이 채점 (골드 v3) ----------

def test_transition_matching_checks_before_and_after_fields():
    """'70%가 어딘가 있다'와 '70%에서 40%로 바뀌었다'는 다른 주장이다."""
    sources = load_sources()
    d = _fake_extraction_dict(sources)
    ext = extract_regchange(sources, complete=lambda s, u: d)
    gold = {"required_changes": [{"id": "T", "keywords": [],
                                  "transition": {"before": "70%", "after": "40%"}}],
            "exceptions": [], "effective_from": "2026-07-01", "target_regions": []}
    assert score_against_gold(ext, gold).change_completeness == 1.0


def test_transition_matching_rejects_a_wrong_after_value():
    sources = load_sources()
    ext = extract_regchange(sources, complete=lambda s, u: _fake_extraction_dict(sources))
    gold = {"required_changes": [{"id": "T", "keywords": [],
                                  "transition": {"before": "70%", "after": "35%"}}],
            "exceptions": [], "effective_from": "2026-07-01", "target_regions": []}
    assert score_against_gold(ext, gold).missed_changes == ["T"]


def test_transition_matching_is_not_satisfied_by_the_value_appearing_in_prose():
    """요약문에 70%·40%가 흩어져 있어도 before/after가 아니면 전이가 아니다."""
    from regimpact.extractor.schema import RegChangeExtraction

    ext = RegChangeExtraction.from_dict({
        "policy_id": "P", "effective_from": "2026-07-01", "target_regions": [],
        "changes": [{"category": "LTV", "summary": "70%와 40%가 언급된 문장",
                     "before": None, "after": None,
                     "citation": {"source_doc_id": "D", "quote": "q"}, "confidence": 0.9}],
    })
    gold = {"required_changes": [{"id": "T", "keywords": [],
                                  "transition": {"before": "70%", "after": "40%"}}],
            "exceptions": [], "effective_from": "2026-07-01", "target_regions": []}
    assert score_against_gold(ext, gold).change_completeness == 0.0


def test_missed_change_label_survives_an_entry_without_keywords():
    """전이 전용 entry는 keywords가 비어도 되는데, 라벨 계산이 그걸 못 견디면 채점이 죽는다."""
    from regimpact.extractor.schema import RegChangeExtraction

    ext = RegChangeExtraction.from_dict({
        "policy_id": "P", "effective_from": "2026-07-01", "target_regions": [], "changes": [],
    })
    gold = {"required_changes": [{"id": "T", "keywords": [],
                                  "transition": {"before": "70%", "after": "40%"}}],
            "exceptions": [], "effective_from": "2026-07-01", "target_regions": []}
    assert score_against_gold(ext, gold).missed_changes == ["T"]

# ---------- 규제 이벤트 (파이프라인의 입력 단위) ----------
def test_default_event_documents_are_frozen():
    """기본 이벤트(6·30)의 문서 3건은 고정이다.

    기존 실측·골드가 전부 이 셋에 묶여 있다. 여기에 문서를 더하면 인용 정확성·완전성
    수치의 **의미가 조용히 바뀐다** — 새 대책은 EVENTS 에 별도 항목으로 넣어야 한다.
    """
    from regimpact.extractor.sources import DEFAULT_EVENT, SOURCE_FILES, get_event

    assert DEFAULT_EVENT == "20260630"
    assert set(SOURCE_FILES) == {
        "FSC_PRESS_20260630", "MOLIT_PRESS_20260630", "FAQ_20260630"}
    assert set(get_event().files) == set(SOURCE_FILES)


def test_every_event_document_exists_in_the_registry():
    """이벤트가 가리키는 문서는 전부 코퍼스 레지스트리에 있어야 한다."""
    from regimpact.extractor.sources import CORPUS_FILES, EVENTS

    for ev in EVENTS.values():
        missing = [d for d in ev.doc_ids if d not in CORPUS_FILES]
        assert not missing, f"{ev.event_id}: 레지스트리에 없는 문서 {missing}"
        assert ev.doc_ids, f"{ev.event_id}: 문서가 비었다"


def test_event_dates_agree_with_corpus_event_metadata():
    """이벤트 발표일과 문서 시점 메타데이터가 갈라지면 시점 필터가 조용히 틀린다."""
    from regimpact.extractor.sources import CORPUS_EVENTS, EVENTS

    for ev in EVENTS.values():
        for doc in ev.doc_ids:
            published, _label = CORPUS_EVENTS[doc]
            assert published == ev.published_at, (
                f"{ev.event_id}/{doc}: 이벤트 {ev.published_at} vs 문서 {published}")


def test_unknown_event_fails_loudly():
    """이름을 틀리면 조용히 기본값으로 떨어지지 않고 즉시 실패한다."""
    import pytest as _pytest

    from regimpact.extractor.sources import get_event

    with _pytest.raises(KeyError):
        get_event("20990101")


def test_event_without_gold_is_marked_as_such():
    """골드가 없는 이벤트는 그렇다고 표시돼야 한다 — 정답 없이 점수를 내지 않기 위해서다."""
    from regimpact.extractor.sources import EVENTS

    with_gold = [e for e in EVENTS.values() if e.gold]
    assert with_gold, "골드를 가진 이벤트가 하나도 없다"
    for ev in EVENTS.values():
        if ev.gold is None:
            continue
        assert (pathlib.Path(__file__).resolve().parents[1] / ev.gold).exists(), \
            f"{ev.event_id}: 골드 파일이 없다 — {ev.gold}"


def test_loading_an_event_returns_only_its_documents():
    from regimpact.extractor.sources import EVENTS, load_sources

    for eid, ev in EVENTS.items():
        loaded = load_sources(event=eid)
        assert set(loaded) == set(ev.doc_ids), f"{eid}: 로드된 문서가 이벤트와 다르다"
        assert all(loaded.values()), f"{eid}: 빈 원문이 있다"
