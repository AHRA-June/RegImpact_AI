"""판별력(negative control) 계산 — 검증보고서/데모가 공유하는 '오류 주입' 로직.

정상 데이터와 의도적으로 오염된 데이터의 Assurance 지표 차이를 계산해,
하니스가 오류에 반응(동적 범위)함을 정량화한다.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..extractor import check_citation_grounding, load_sources, score_against_gold
from ..extractor.schema import Citation, RegChangeExtraction, RegChangeItem
from ..impact import anchor_extraction, load_gold, run_e2e


def bad_extraction() -> RegChangeExtraction:
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
            # 누락: EFFECTIVE_DATE·GRANDFATHERING·생애최초/서민 EXCEPTION
        ],
    )


@dataclass
class ControlPair:
    metric: str
    good: float
    bad: float

    @property
    def detects(self) -> bool:
        return self.bad < self.good


def discrimination_pairs() -> list[ControlPair]:
    """정상 vs 오류 주입의 Assurance 지표 쌍을 계산한다(Extractor Assurance 축)."""
    sources = load_sources()
    gold = load_gold()
    good, bad = anchor_extraction(), bad_extraction()
    gg = check_citation_grounding(good, sources).citation_correctness
    bg = check_citation_grounding(bad, sources).citation_correctness
    gs, bs = score_against_gold(good, gold), score_against_gold(bad, gold)
    return [
        ControlPair("Citation Correctness", gg, bg),
        ControlPair("Change Completeness", gs.change_completeness, bs.change_completeness),
        ControlPair("Exception Recall", gs.exception_recall, bs.exception_recall),
        ControlPair("Effective-date OK", float(gs.effective_date_correct), float(bs.effective_date_correct)),
        ControlPair("Regions OK", float(gs.regions_correct), float(bs.regions_correct)),
    ]


def e2e_control() -> tuple[bool, bool]:
    """(정상 e2e_ok, 오류 e2e_ok). 오류가 False면 관통 실패를 잡은 것."""
    return run_e2e().e2e_ok, run_e2e(extraction=bad_extraction()).e2e_ok
