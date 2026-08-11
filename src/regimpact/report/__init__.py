"""Report node — 6·30 1건을 끝까지 관통시키는 E2E 파이프라인 + Validation Report(stub).

핵심 진입점:
    run_e2e(complete=None) -> ValidationReport   (전 노드 배선·관통. complete 없으면 오프라인 stub)
    render_markdown(report) -> str               (사람이 읽는 검증보고서 Markdown)

브리프 §18 코어라인의 마지막 노드. 각 실제 노드(rule_engine·impact·tc_generator·extractor)를
배선하고, LLM 추출만 주입 가능한 stub로 두어 API 키 없이 E2E가 관통되게 한다.
"""
from .pipeline import (
    ReviewItem,
    SourceSnapshot,
    ValidationReport,
    default_6_30_portfolio,
    offline_stub_extraction,
    run_e2e,
)
from .proposal import LtvRuleLine, RuleChangeProposal, build_proposal
from .render import render_markdown

__all__ = [
    "run_e2e",
    "render_markdown",
    "ValidationReport",
    "SourceSnapshot",
    "ReviewItem",
    "default_6_30_portfolio",
    "offline_stub_extraction",
    "RuleChangeProposal",
    "LtvRuleLine",
    "build_proposal",
]
