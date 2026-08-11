"""RegImpact AI — Assurance Evaluation (깊은 4 dimension 집계).

각 노드의 검증 신호(citation grounding, gold 대조, proposal consistency,
rule regression, proposal fidelity, coverage)를 metrics_spec의 4 dimension으로
집계하고, 임계 대비 pass/fail·gate·사람 escalation 사유를 산출한다.

핵심 진입점: evaluate_assurance(...) -> AssuranceReport
"""
from .evaluate import (
    DEFAULT_THRESHOLDS,
    AssuranceGate,
    AssuranceReport,
    AssuranceThresholds,
    DimensionResult,
    evaluate_assurance,
)

__all__ = [
    "evaluate_assurance",
    "AssuranceReport",
    "AssuranceGate",
    "AssuranceThresholds",
    "DEFAULT_THRESHOLDS",
    "DimensionResult",
]
