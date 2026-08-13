"""Impact Matrix — 규제 변경의 시행 전/후 영향을 세그먼트별로 산출.

핵심 진입점:
    analyze_impact(segments, region_code, before_date, after_date) -> ImpactMatrix
    analyze_from_extraction(extraction, segments, region_code)      -> ImpactMatrix  (E2E)
    format_matrix(matrix)                                           -> str
    SIX_THIRTY_SEGMENTS                                             (6·30 표준 세그먼트)

설계: 룰엔진(rule_engine.evaluate)을 시행 전/후 두 시점으로 차등 실행(temporal diff)한다.
규칙값을 자체 보유하지 않으므로 LOCKED §4(규칙은 확정 명세→엔진에서만)를 위반하지 않는다.
"""
from .matrix import (
    ImpactDirection,
    ImpactMatrix,
    ImpactRow,
    Segment,
    analyze_from_extraction,
    analyze_impact,
)
from .report import format_matrix
from .segments import DEFAULT_REGION, SIX_THIRTY_REGIONS, SIX_THIRTY_SEGMENTS

__all__ = [
    "Segment",
    "ImpactRow",
    "ImpactMatrix",
    "ImpactDirection",
    "analyze_impact",
    "analyze_from_extraction",
    "format_matrix",
    "SIX_THIRTY_SEGMENTS",
    "SIX_THIRTY_REGIONS",
    "DEFAULT_REGION",
]
