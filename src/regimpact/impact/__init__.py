"""RegImpact AI — Impact Matrix (규제 변경의 세그먼트별 영향 매트릭스).

deterministic 룰엔진을 시행 전/후(before/after) 두 시점에 차등 실행해
"지역 × 차주유형 → 기존 LTV / 변경 LTV / 경과규정 / reason_code" 매트릭스를 산출한다.
모든 LTV 값은 엔진 실제 출력(하드코딩 아님).

핵심 진입점: build_impact_matrix() -> ImpactMatrix
근거: docs/00_BRIEF.md §5~6(Impact Analyzer), docs/ui/stitch_review.md(정정 세그먼트 표).
"""
from .matrix import (
    AFTER_DATE,
    BEFORE_DATE,
    ImpactDirection,
    ImpactMatrix,
    ImpactRow,
    build_impact_matrix,
    format_report,
)
from .segments import (
    ANCHOR_SEGMENTS,
    DISCOVERY_SEGMENTS,
    SIX_THIRTY_SEGMENTS,
    Segment,
)

__all__ = [
    "build_impact_matrix",
    "format_report",
    "ImpactMatrix",
    "ImpactRow",
    "ImpactDirection",
    "Segment",
    "ANCHOR_SEGMENTS",
    "DISCOVERY_SEGMENTS",
    "SIX_THIRTY_SEGMENTS",
    "BEFORE_DATE",
    "AFTER_DATE",
]
