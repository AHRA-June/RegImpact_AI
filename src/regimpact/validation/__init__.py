"""Validation Report — 파이프라인 산출을 검증보고서로 조립(stub).

핵심 진입점:
    build_report(scenario_title, extraction?, matrix?, proposal?, regression?, assurance?)
        -> ValidationReport
    format_report_md(report) -> str

Walking Skeleton [8] Validation Report 노드. 각 노드 실제 산출을 묶어 관통을 보이고,
present/missing·사람검토 필요 건수를 정직하게 노출한다.
"""
from .report import ValidationReport, build_report, format_report_md

__all__ = [
    "ValidationReport",
    "build_report",
    "format_report_md",
]
