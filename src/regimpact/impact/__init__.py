"""Impact Analyzer — 규제 변경의 Before/After 임팩트 매트릭스.

핵심 진입점:
    analyze_row(app)          -> ImpactRow       (고객 1건 before/after 임팩트)
    analyze_portfolio(apps)   -> ImpactMatrix     (포트폴리오 세그먼트 매트릭스)
    format_matrix(matrix)     -> str              (사람이 읽는 요약)

설계: 같은 프로필을 두 정책 시점(before/after)에 동일 룰엔진으로 평가해 '차이'만 낸다.
LOCKED §4 — 새로운 규칙값을 만들지 않는다. 경과규정 보호는 UNCHANGED로 정직하게 표기된다.
"""
from .analyzer import (
    DEFAULT_AFTER_DATE,
    DEFAULT_BEFORE_DATE,
    HIGH_IMPACT_LTV_DROP,
    ImpactDirection,
    ImpactMatrix,
    ImpactRow,
    Segment,
    SegmentImpact,
    analyze_portfolio,
    analyze_row,
    format_matrix,
    segment_of,
)

__all__ = [
    "analyze_row",
    "analyze_portfolio",
    "format_matrix",
    "segment_of",
    "ImpactRow",
    "ImpactMatrix",
    "ImpactDirection",
    "Segment",
    "SegmentImpact",
    "DEFAULT_BEFORE_DATE",
    "DEFAULT_AFTER_DATE",
    "HIGH_IMPACT_LTV_DROP",
]
