"""RegImpact AI — Validation Report (E2E 검증보고서 조립).

Source→Impact→Proposal→TestCases→Regression→Assurance→Human Review→Report 를
한 문서(Markdown)로 묶고, 승인 상태 + audit trail을 포함한다(브리프 §16~18).

핵심 진입점: build_validation_report(...) -> ValidationReport (.render_markdown()).
"""
from .validation_report import (
    ReportMeta,
    ValidationReport,
    build_validation_report,
)

__all__ = [
    "build_validation_report",
    "ValidationReport",
    "ReportMeta",
]
