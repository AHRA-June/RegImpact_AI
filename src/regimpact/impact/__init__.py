"""Impact Analyzer — 규제 변경을 §10 임팩트 매트릭스로 전개한다.

    build_portfolio()      -> 층화 합성 포트폴리오 (결정적)
    analyze_portfolio()    -> 시행 전/후 룰엔진 평가 → 고객 영향 집계
    build_impact_matrix()  -> 추출·엔진·회귀 실제 출력을 §10 행/열로 조립
    format_matrix_markdown() / format_matrix_text()
"""
from .builder import build_impact_matrix, derive_rule_diff
from .customer import (
    CustomerImpact,
    CustomerImpactReport,
    Segment,
    analyze_portfolio,
)
from .portfolio import (
    AFTER_DATE,
    BEFORE_DATE,
    CONTROL_REGION,
    DEFAULT_SEED,
    TARGET_REGIONS,
    PortfolioCustomer,
    build_portfolio,
    composition,
)
from .report import format_matrix_markdown, format_matrix_text
from .schema import (
    ApprovalStatus,
    Evidence,
    ImpactMatrix,
    ImpactRow,
    Owner,
    Phase,
    Priority,
)

__all__ = [
    "build_portfolio", "composition", "PortfolioCustomer",
    "TARGET_REGIONS", "CONTROL_REGION", "DEFAULT_SEED", "BEFORE_DATE", "AFTER_DATE",
    "analyze_portfolio", "CustomerImpactReport", "CustomerImpact", "Segment",
    "build_impact_matrix", "derive_rule_diff",
    "format_matrix_markdown", "format_matrix_text",
    "ImpactMatrix", "ImpactRow", "Evidence", "Phase", "Priority", "Owner", "ApprovalStatus",
]
