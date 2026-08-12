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
from .connect import PolicyImpact, impact_from_extraction
from .population import (
    ARCHETYPE_SHARE,
    REGION_MIX,
    enumerate_weighted_profiles,
    sample_portfolio,
    weight_model_note,
)
from .segments import (
    DEFAULT_ARCHETYPES,
    SIX_THIRTY_SEGMENTS,
    SegmentArchetype,
    segments_for_region,
)

__all__ = [
    "analyze_impact",
    "analyze_segment",
    "format_report",
    "impact_from_extraction",
    "PolicyImpact",
    "ImpactMatrix",
    "SegmentImpact",
    "CustomerSegment",
    "ImpactDirection",
    "SegmentArchetype",
    "segments_for_region",
    "DEFAULT_ARCHETYPES",
    "SIX_THIRTY_SEGMENTS",
    "BEFORE_DATE",
    "AFTER_DATE",
    # 가중 합성 모집단
    "enumerate_weighted_profiles",
    "sample_portfolio",
    "weight_model_note",
    "ARCHETYPE_SHARE",
    "REGION_MIX",
]
