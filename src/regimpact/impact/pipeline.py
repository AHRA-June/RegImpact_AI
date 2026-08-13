"""E2E Pipeline — 6·30 1건을 Source부터 Report까지 관통시킨다.

04_PLAN "코어 완성의 정의"(LOCKED):
    Source Snapshot → (Policy Version) → Before/After → Impact Matrix
    → Rule Change Proposal → Test Cases → Deterministic Rule Regression
    → Assurance Evaluation → (Human Review) → Validation Report

이 모듈은 그 배관을 실제로 연결한다(Walking Skeleton). 각 노드는 이미 구현된
컴포넌트를 호출한다:
    - Source        : extractor.sources.load_sources
    - Before/After  : impact.anchor.anchor_extraction (또는 주입된 실제 LLM 추출)
    - Impact Matrix : impact.matrix.build_impact_matrix (룰엔진 2시점)
    - Proposal      : impact.proposal.build_proposal
    - Test/Regression: tc_generator.run_regression (독립 오라클 차등검증)
    - Assurance     : extractor.evaluate.check_citation_grounding + score_against_gold

extraction 인자를 주면 실제 LLM 추출 결과로 동일 파이프라인을 돌릴 수 있다
(오프라인 기본값은 원문 grounding된 앵커).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ..extractor.evaluate import (
    GoldReport,
    GroundingReport,
    check_citation_grounding,
    score_against_gold,
)
from ..extractor.schema import RegChangeExtraction
from ..extractor.sources import load_sources
from ..tc_generator import RegressionReport, run_regression
from .anchor import anchor_extraction
from .matrix import ImpactRow, build_impact_matrix
from .proposal import RuleChangeProposal, build_proposal

_GOLD_PATH = Path(__file__).resolve().parents[3] / "docs" / "eval" / "regchange_gold_6_30.json"


def load_gold(path: str | Path | None = None) -> dict:
    """RegChange 골드 정답지를 로드한다(Assurance ②③ 채점용)."""
    p = Path(path) if path else _GOLD_PATH
    return json.loads(p.read_text(encoding="utf-8"))


@dataclass
class E2EReport:
    """6·30 E2E 관통 산출물 — 각 단계 결과 + Assurance 지표를 한 곳에."""
    scenario: str
    sources_loaded: list[str]
    extraction: RegChangeExtraction
    impact_matrix: list[ImpactRow]
    proposal: RuleChangeProposal
    regression: RegressionReport
    grounding: GroundingReport
    gold: GoldReport

    # --- 편의 지표 (metrics_spec 정렬) ---
    @property
    def regression_pass_rate(self) -> float:
        return self.regression.pass_rate

    @property
    def citation_correctness(self) -> float:
        return self.grounding.citation_correctness

    @property
    def unsupported_claim_rate(self) -> float:
        return self.grounding.unsupported_claim_rate

    @property
    def high_impact_rows(self) -> list[ImpactRow]:
        return [r for r in self.impact_matrix if r.high_impact]

    @property
    def escalated_rows(self) -> list[ImpactRow]:
        return [r for r in self.impact_matrix if r.escalated]

    @property
    def e2e_ok(self) -> bool:
        """스모크 판정: 파이프라인이 의미있게 관통했는가.

        - 추출 변경 항목 ≥ 1
        - Impact Matrix 행 ≥ 1
        - 회귀 100% 통과 (엔진이 확정 명세와 일치)
        - 모든 citation이 원문에 grounding (환각 인용 0)
        """
        return (
            len(self.extraction.changes) > 0
            and len(self.impact_matrix) > 0
            and self.regression.pass_rate == 1.0
            and self.grounding.unsupported_claim_rate == 0.0
        )

    def to_dict(self) -> dict:
        return {
            "scenario": self.scenario,
            "sources_loaded": self.sources_loaded,
            "extraction": {
                "policy_id": self.extraction.policy_id,
                "effective_from": self.extraction.effective_from,
                "target_regions": self.extraction.target_regions,
                "num_changes": len(self.extraction.changes),
            },
            "impact_matrix": [
                {
                    "persona_id": r.persona_id,
                    "segment": r.segment_label,
                    "region": r.region_code,
                    "before_status": r.before.status.value,
                    "after_status": r.after.status.value,
                    "before_ltv": r.before_ltv,
                    "after_ltv": r.after_ltv,
                    "delta_ltv": r.delta_ltv,
                    "escalated": r.escalated,
                    "high_impact": r.high_impact,
                }
                for r in self.impact_matrix
            ],
            "proposal": self.proposal.to_dict(),
            "assurance": {
                "regression_pass_rate": self.regression_pass_rate,
                "regression_by_category": self.regression.pass_rate_by_category(),
                "citation_correctness": self.citation_correctness,
                "unsupported_claim_rate": self.unsupported_claim_rate,
                "change_completeness": self.gold.change_completeness,
                "exception_recall": self.gold.exception_recall,
                "effective_date_correct": self.gold.effective_date_correct,
                "regions_correct": self.gold.regions_correct,
            },
            "e2e_ok": self.e2e_ok,
        }


def run_e2e(
    extraction: Optional[RegChangeExtraction] = None,
    sources: Optional[dict[str, str]] = None,
    gold: Optional[dict] = None,
    scenario: str = "6·30 규제지역 추가지정",
) -> E2EReport:
    """6·30 시나리오를 E2E로 관통시켜 검증보고서를 만든다.

    extraction=None 이면 원문 grounding된 앵커 추출을 사용(오프라인).
    실제 LLM 추출 결과를 주입하면 동일 파이프라인으로 그 출력을 검증한다.
    """
    sources = sources if sources is not None else load_sources()
    extraction = extraction if extraction is not None else anchor_extraction()
    gold = gold if gold is not None else load_gold()

    # 지역 목록은 추출의 target_regions에서 온다(없으면 matrix 기본값).
    regions = extraction.target_regions or None
    impact_matrix = build_impact_matrix(regions=regions)

    proposal = build_proposal(extraction, impact_matrix)
    regression = run_regression()
    grounding = check_citation_grounding(extraction, sources)
    gold_report = score_against_gold(extraction, gold)

    return E2EReport(
        scenario=scenario,
        sources_loaded=sorted(sources.keys()),
        extraction=extraction,
        impact_matrix=impact_matrix,
        proposal=proposal,
        regression=regression,
        grounding=grounding,
        gold=gold_report,
    )
