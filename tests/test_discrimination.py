"""판별력(negative control) 테스트 — 하니스가 '틀린 것'을 실제로 잡는가.

정상 데이터의 100%만으로는 하니스에 이빨이 있는지 알 수 없다. 이 테스트는
**의도적으로 오류를 주입**하고 각 지표가 100%에서 떨어지는지 고정한다.
지표가 오류에 둔감(항상 100%)해지면 이 테스트가 실패로 알린다.
"""
from regimpact import rule_engine
from regimpact.extractor import (
    check_citation_grounding,
    load_sources,
    score_against_gold,
)
from regimpact.extractor.schema import Citation, RegChangeExtraction, RegChangeItem
from regimpact.goldset import (
    Split,
    check_goldset_grounding,
    load_goldset,
    score_scenario_items,
)
from regimpact.impact import anchor_extraction, load_gold, run_e2e


def _bad_extraction() -> RegChangeExtraction:
    """현실적 LLM 오류를 심은 추출: 환각 인용 + 항목 누락 + 시행일/지역 오류."""
    return RegChangeExtraction(
        policy_id="FSC_20260630",
        effective_from="2026-07-15",                 # 오답(정답 2026-07-01)
        target_regions=["GURI", "YONGIN_GIHEUNG"],    # 화성동탄 누락
        changes=[
            RegChangeItem(
                category="LTV",
                summary="규제지역 LTV 강화 (70% → 40%)",
                before="70%", after="40%",
                citation=Citation("FAQ_20260630", "규제지역 LTV를 90%에서 20%로 인하한다"),  # 환각
                confidence=0.9,
            ),
            RegChangeItem(
                category="REGION",
                summary="규제지역 추가 지정 (투기과열지구·조정대상지역)",
                after="규제지역",
                citation=Citation("FSC_PRESS_20260630",
                                  "동탄구, 기흥구, 구리시의 규제지역(투기과열지역, 조정대상지역) 지정에"),
                confidence=0.95,
            ),
            # 누락: EFFECTIVE_DATE 항목·GRANDFATHERING 항목·생애최초/서민 EXCEPTION 항목
        ],
    )


# ---------- Extractor Assurance: 오류에 지표가 반응 ----------
def test_bad_extraction_lowers_citation_grounding():
    sources = load_sources()
    good = check_citation_grounding(anchor_extraction(), sources).citation_correctness
    bad = check_citation_grounding(_bad_extraction(), sources).citation_correctness
    assert good == 1.0
    assert bad < 1.0                    # 환각 인용을 잡아야 한다


def test_bad_extraction_lowers_gold_metrics():
    gold = load_gold()
    good = score_against_gold(anchor_extraction(), gold)
    bad = score_against_gold(_bad_extraction(), gold)
    assert good.change_completeness == 1.0 and good.exception_recall == 1.0
    # 누락 항목 → completeness/recall 하락, 필드 오류 → date/region 실패
    assert bad.change_completeness < 1.0
    assert bad.exception_recall < 1.0
    assert bad.effective_date_correct is False
    assert bad.regions_correct is False


def test_e2e_flags_bad_extraction():
    assert run_e2e().e2e_ok is True
    assert run_e2e(extraction=_bad_extraction()).e2e_ok is False


# ---------- 골드셋: 변조 엔진 / 오염 인용에 반응 ----------
def test_goldset_scenario_catches_mutated_engine(monkeypatch):
    items = load_goldset(splits=[Split.DEV, Split.LOCKED, Split.CHALLENGE])
    assert score_scenario_items(items).accuracy == 1.0
    monkeypatch.setattr(rule_engine, "LTV_REGULATED_STANDARD", 0.50)   # 40%→50% 버그
    mutated = score_scenario_items(items)
    assert mutated.accuracy < 1.0                     # 골드가 오류를 잡아야 한다
    # 규제 무주택 일반(NORMAL) 계열이 실패로 잡혀야 함
    failed_cats = {r.item.category.value for r in mutated.failures}
    assert "NORMAL" in failed_cats


def test_goldset_grounding_catches_corrupted_quote():
    sources = load_sources()
    items = load_goldset(splits=[Split.DEV])
    assert check_goldset_grounding(items, sources).rate == 1.0
    hit = next(it for it in items if it.source_quote)
    hit.source_quote = "이 문장은 원문에 존재하지 않는다"
    assert check_goldset_grounding(items, sources).rate < 1.0
