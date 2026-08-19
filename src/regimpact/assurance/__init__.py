"""Assurance 스코어카드 — 실측을 임계와 대조해 판정한다 (브리프 §13 4 DEEP dimension).

지표를 나열하는 것과 통과 여부를 **판정하는 것**은 다르다. 판정이 없으면 숫자를 본 사람이
각자 기준으로 해석하게 되고, 그러면 검증 산출물이 아니다.

    from regimpact.assurance import score
    from regimpact.report import collect
    sc = score(collect(), js_port_agreement=1.0)
    sc.verdict            # PASS / FAIL / NOT_MEASURED
    sc.failures           # 임계 미달 지표
    sc.unmeasured         # 측정하지 못한 지표 — **통과가 아니다**
"""
from .scorecard import DimensionResult, MetricResult, Scorecard, Verdict, score
from .thresholds import BY_METRIC, THRESHOLDS, Dimension, Direction, Threshold

__all__ = [
    "score", "Scorecard", "DimensionResult", "MetricResult", "Verdict",
    "THRESHOLDS", "BY_METRIC", "Threshold", "Dimension", "Direction",
]
