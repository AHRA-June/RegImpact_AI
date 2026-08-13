"""Assurance 스코어카드 — 4 dimension 정량 지표 + 확정 임계값 판정.

핵심 진입점:
    build_scorecard(extraction, sources, gold, regression?) -> AssuranceScorecard
    format_scorecard_md(scorecard) -> str
    THRESHOLDS  (확정 임계값, Strict / Model Risk 보수)

4 dimension(metrics_spec.md):
    ① Source Grounding & Citation  ② Change & Exception Completeness
    ③ Temporal / Policy-Version Consistency  ④ Rule Regression & Conflict
종합 판정: 고위험(★) 지표 FAIL → 전체 FAIL, 그 외 FAIL/WARN → 전체 WARN.
"""
from .metrics import compute_metrics
from .scorecard import (
    AssuranceScorecard,
    DimensionResult,
    MetricResult,
    build_scorecard,
    format_scorecard_md,
)
from .thresholds import THRESHOLDS, MetricSpec, Status

__all__ = [
    "build_scorecard",
    "format_scorecard_md",
    "compute_metrics",
    "AssuranceScorecard",
    "DimensionResult",
    "MetricResult",
    "THRESHOLDS",
    "MetricSpec",
    "Status",
]
