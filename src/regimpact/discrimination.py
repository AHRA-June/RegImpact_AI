"""판별력(negative control) 측정 — 하니스가 '틀린 것'을 실제로 잡는가.

정상 데이터에서 100%가 나오는 것만으로는 검증 하니스에 이빨이 있는지 알 수 없다.
**항상 100%인 검증 시스템은 그 자체가 red flag다.** 이 모듈은 의도적으로 오류를 주입해
각 지표가 100%에서 떨어지는지를 실측한다. 지표가 오류에 둔감해지면 여기서 드러난다.

브리프 §12: "검증의 한계를 숨기지 않는 것이 오히려 신뢰성을 높인다."

주입하는 오류는 실제로 관측된 LLM 실패 양상을 본뜬다 — 환각 인용, 항목 누락,
시행일 오답, 지역 누락. 무작위 노이즈가 아니라 **그럴듯한 오답**이어야 판별력 측정이 된다.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from .extractor.schema import Citation, RegChangeExtraction, RegChangeItem


@dataclass
class Discrimination:
    """지표 하나의 판별력 — 정상값과 오염값의 간극."""
    metric: str
    clean: float
    corrupted: float
    lower_is_worse: bool = True

    @property
    def detected(self) -> bool:
        """오염이 지표를 실제로 떨어뜨렸는가."""
        return self.corrupted < self.clean if self.lower_is_worse else self.corrupted > self.clean

    @property
    def gap(self) -> float:
        return abs(self.clean - self.corrupted)

    def to_dict(self) -> dict:
        return {
            "metric": self.metric,
            "clean": self.clean,
            "corrupted": self.corrupted,
            "detected": self.detected,
            "gap": round(self.gap, 4),
        }


@dataclass
class DiscriminationReport:
    results: list[Discrimination]

    @property
    def all_detected(self) -> bool:
        return all(r.detected for r in self.results)

    @property
    def blind(self) -> list[Discrimination]:
        """오염을 감지하지 못한 지표 — 그 지표의 100%는 아무것도 증명하지 않는다."""
        return [r for r in self.results if not r.detected]

    def to_dict(self) -> dict:
        return {
            "all_detected": self.all_detected,
            "blind": [r.metric for r in self.blind],
            "results": [r.to_dict() for r in self.results],
        }


def corrupt_extraction(extraction: RegChangeExtraction) -> RegChangeExtraction:
    """추출에 현실적 LLM 오류를 주입한다.

    ① 인용 환각 — 원문에 없는 문장을 근거로 붙인다
    ② 항목 누락 — 예외·경과규정 항목을 떨어뜨린다
    ③ 시행일 오답 — 2주 뒤로 민다
    ④ 지역 누락 — 지정 지역 하나를 뺀다
    """
    kept: list[RegChangeItem] = []
    for item in extraction.changes:
        if item.category in ("EXCEPTION", "GRANDFATHERING"):
            continue                                    # ② 누락
        kept.append(item)

    if kept:
        first = kept[0]
        kept[0] = RegChangeItem(                        # ① 환각 인용
            category=first.category,
            summary=first.summary,
            before=first.before,
            after=first.after,
            citation=Citation(
                source_doc_id=first.citation.source_doc_id,
                quote="규제지역 LTV를 90%에서 20%로 인하한다",
            ),
            confidence=first.confidence,
        )

    regions = list(extraction.target_regions)[:-1] or []   # ④ 지역 누락

    return RegChangeExtraction(
        policy_id=extraction.policy_id,
        effective_from="2026-07-15",                       # ③ 시행일 오답
        target_regions=regions,
        changes=kept,
    )


def measure(
    clean_value: Callable[[], float],
    corrupted_value: Callable[[], float],
    *,
    metric: str,
) -> Discrimination:
    """지표 하나를 정상/오염 두 번 측정한다."""
    return Discrimination(metric=metric, clean=clean_value(), corrupted=corrupted_value())


def discriminate_extraction(
    extraction: RegChangeExtraction,
    sources: dict,
    gold: dict,
    *,
    corrupted: Optional[RegChangeExtraction] = None,
) -> DiscriminationReport:
    """Extractor Assurance 지표들의 판별력을 한 번에 잰다."""
    from .extractor import check_citation_grounding, score_against_gold

    bad = corrupted if corrupted is not None else corrupt_extraction(extraction)

    g_clean = check_citation_grounding(extraction, sources)
    g_bad = check_citation_grounding(bad, sources)
    s_clean = score_against_gold(extraction, gold)
    s_bad = score_against_gold(bad, gold)

    return DiscriminationReport([
        Discrimination("Citation Correctness",
                       g_clean.citation_correctness, g_bad.citation_correctness),
        Discrimination("Unsupported Claim Rate",
                       g_clean.unsupported_claim_rate, g_bad.unsupported_claim_rate,
                       lower_is_worse=False),
        Discrimination("Change Completeness",
                       s_clean.change_completeness, s_bad.change_completeness),
        Discrimination("Exception Recall",
                       s_clean.exception_recall, s_bad.exception_recall),
        Discrimination("Effective-date Correct",
                       float(s_clean.effective_date_correct), float(s_bad.effective_date_correct)),
        Discrimination("Regions Correct",
                       float(s_clean.regions_correct), float(s_bad.regions_correct)),
    ])


def discriminate_pipeline(
    extraction: RegChangeExtraction,
    sources: dict,
    gold: dict,
    *,
    rule_diff: Optional[list] = None,
) -> DiscriminationReport:
    """추출 지표 + 룰 회귀 + 변경안 일치검증까지 판별력을 한 번에 잰다.

    데모(`examples/demo_discrimination.py`)와 검증보고서가 같은 함수를 쓴다 —
    두 곳에서 따로 계산하면 보고서 수치와 데모 수치가 갈라진다.
    """
    from . import rule_engine
    from .proposal import build_proposal_from_extraction, check_proposal_consistency
    from .tc_generator import run_regression

    results = list(discriminate_extraction(extraction, sources, gold).results)

    clean_rate = run_regression().pass_rate
    for constant, mutated, label in (
        ("LTV_REGULATED_STANDARD", 0.50, "LTV 40%→50% 변조"),
        ("LTV_BASELINE", 0.65, "기준선 70%→65% 변조"),
    ):
        original = getattr(rule_engine, constant)
        setattr(rule_engine, constant, mutated)
        try:
            results.append(Discrimination(
                f"Rule Regression ({label})", clean_rate, run_regression().pass_rate))
        finally:
            setattr(rule_engine, constant, original)

    def _consistency_rate(ex) -> float:
        rep = check_proposal_consistency(
            build_proposal_from_extraction(ex), rule_diff=rule_diff)
        s = rep.summary()
        return s["passed"] / s["total"]

    results.append(Discrimination(
        "Proposal Consistency",
        _consistency_rate(extraction), _consistency_rate(corrupt_extraction(extraction)),
    ))
    return DiscriminationReport(results)
