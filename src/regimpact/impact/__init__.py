"""Impact Analyzer — 임팩트 매트릭스 · 고객영향 · Rule Proposal · E2E 파이프라인.

진입점:
    build_portfolio()          -> 층화 합성 포트폴리오 (커버리지 격자)
    analyze_customer_impact()  -> Before/After 판정 차이 집계
    build_impact_matrix()      -> 업무 임팩트 매트릭스 (Phase 포함, LOCKED §7)
    run_e2e()                  -> 브리프 §18 전 단계 관통
    render_report()            -> 검증보고서(마크다운)
"""
from .customer_impact import (
    CustomerImpactReport,
    RowImpact,
    SegmentImpact,
    StratumImpact,
    analyze_customer_impact,
)
from .matrix import (
    Automation,
    ImpactMatrix,
    MatrixRow,
    Owner,
    Phase,
    Priority,
    Provenance,
    build_impact_matrix,
)
from .pipeline import E2EResult, RuleChangeProposal, Stage, StageStatus, run_e2e
from .portfolio import BORROWER_PROFILES, EVENT_PROFILES, REGION_GROUPS, PortfolioRow, build_portfolio
from .report import render_matrix, render_report

__all__ = [
    "build_portfolio", "PortfolioRow", "REGION_GROUPS", "BORROWER_PROFILES", "EVENT_PROFILES",
    "analyze_customer_impact", "CustomerImpactReport", "RowImpact", "SegmentImpact", "StratumImpact",
    "build_impact_matrix", "ImpactMatrix", "MatrixRow", "Phase", "Priority", "Owner",
    "Automation", "Provenance",
    "run_e2e", "E2EResult", "Stage", "StageStatus", "RuleChangeProposal",
    "render_report", "render_matrix",
]
