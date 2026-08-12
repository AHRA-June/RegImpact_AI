"""RegImpact AI — deterministic 주담대 LTV 룰엔진.

핵심 진입점: regimpact.rule_engine.evaluate(MortgageApplication) -> LtvDecision
근거 명세: docs/05_RULE_SPEC.md (사람 확정 v1).
"""
from .models import (
    EvaluationStatus,
    LoanPurpose,
    LtvDecision,
    MortgageApplication,
    ReasonCode,
    RegionStatus,
    RegulatedType,
)
from .rule_engine import evaluate
from .impact import (
    CustomerSegment,
    ImpactMatrix,
    SegmentImpact,
    analyze_impact,
    format_report,
)

__all__ = [
    "evaluate",
    "MortgageApplication",
    "LtvDecision",
    "EvaluationStatus",
    "LoanPurpose",
    "ReasonCode",
    "RegionStatus",
    "RegulatedType",
    # Impact Matrix (E2E)
    "analyze_impact",
    "format_report",
    "ImpactMatrix",
    "SegmentImpact",
    "CustomerSegment",
]
