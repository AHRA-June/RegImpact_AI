"""RegImpact AI — Impact Matrix (규제 변경 영향분석 E2E).

룰엔진(deterministic)을 Before/After 두 시점으로 관통시켜, 세그먼트별로
'기존 LTV → 변경 LTV / 방향 / 경과규정 / 근거코드'를 산출한다. 이것이 제품의
핵심 출력(RegChange / Impact Analysis)이며, UI는 이 구조를 그대로 렌더한다.

근거: docs/00_BRIEF.md §6([Impact Analyzer]), docs/04_PLAN.md Phase 1(Walking Skeleton).
LOCKED §4: LTV 값·판정 로직은 rule_engine(사람 확정 명세)에서만 온다. 이 모듈은
그 엔진을 두 시점에 실행해 '차이'를 계산할 뿐, 규칙을 새로 만들지 않는다.
"""
from .matrix import (
    BEFORE_DATE,
    AFTER_DATE,
    ImpactDirection,
    ImpactMatrix,
    ImpactRow,
    build_impact_matrix,
    classify_direction,
    format_matrix,
)
from .portfolio import (
    Applicant,
    PortfolioImpact,
    analyze_portfolio,
    build_synthetic_portfolio,
)
from .segments import SIX_THIRTY_SEGMENTS, Segment

__all__ = [
    "build_impact_matrix",
    "format_matrix",
    "classify_direction",
    "ImpactMatrix",
    "ImpactRow",
    "ImpactDirection",
    "Segment",
    "SIX_THIRTY_SEGMENTS",
    "BEFORE_DATE",
    "AFTER_DATE",
    # 포트폴리오(합성) 집계
    "analyze_portfolio",
    "build_synthetic_portfolio",
    "PortfolioImpact",
    "Applicant",
]
