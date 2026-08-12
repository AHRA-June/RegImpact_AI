"""Impact Matrix — 규제 변경의 before/after 차등 임팩트 (Walking Skeleton E2E).

진입점: analyze_impact(segments) -> ImpactMatrix. 룰엔진을 두 시점으로 돌려 차이를 집계.
새 규칙을 만들지 않고 deterministic 엔진 위에서만 동작한다(LOCKED §4).
"""
from .matrix import (
    AFTER_DATE,
    BEFORE_DATE,
    CustomerSegment,
    ImpactDirection,
    ImpactMatrix,
    SegmentImpact,
    analyze_impact,
    analyze_segment,
    format_report,
)
from .segments import SIX_THIRTY_SEGMENTS

__all__ = [
    "analyze_impact",
    "analyze_segment",
    "format_report",
    "ImpactMatrix",
    "SegmentImpact",
    "CustomerSegment",
    "ImpactDirection",
    "SIX_THIRTY_SEGMENTS",
    "BEFORE_DATE",
    "AFTER_DATE",
]
