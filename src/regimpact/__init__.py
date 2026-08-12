"""RegImpact AI — deterministic 주담대 LTV 룰엔진.

핵심 진입점: regimpact.rule_engine.evaluate(MortgageApplication) -> LtvDecision
근거 명세: docs/05_RULE_SPEC.md (사람 확정 v1).
"""
from .models import (
    EvaluationStatus,
    LoanPurpose,
    LtvDecision,
    MortgageApplication,
    ReasonCode,
    RegionStatus,
    RegulatedType,
)
from .rule_engine import evaluate
from .regions import (
    KNOWN_REGION_CODES,
    normalize_regions,
    resolve_region_code,
    resolve_region_status,
)
from .impact import (
    CustomerSegment,
    ImpactMatrix,
    PolicyImpact,
    SegmentImpact,
    analyze_impact,
    format_report,
    impact_from_extraction,
)
from .report import render_report
from .rule_proposal import (
    Disposition,
    RuleChangeProposal,
    RuleDelta,
    build_proposal,
    format_proposal,
)
from .livefire import (
    EvidenceManifest,
    render_evidence_record,
    run_livefire,
)
from .rule_catalog import (
    DEFAULT_CATALOG,
    CatalogImpact,
    InternalRule,
    RuleImpact,
    format_catalog,
    map_catalog_impact,
)

__all__ = [
    "evaluate",
    "MortgageApplication",
    "LtvDecision",
    "EvaluationStatus",
    "LoanPurpose",
    "ReasonCode",
    "RegionStatus",
    "RegulatedType",
    # 지역 정규화
    "resolve_region_code",
    "resolve_region_status",
    "normalize_regions",
    "KNOWN_REGION_CODES",
    # Impact Matrix (E2E)
    "analyze_impact",
    "format_report",
    "impact_from_extraction",
    "PolicyImpact",
    "ImpactMatrix",
    "SegmentImpact",
    "CustomerSegment",
    # HTML 리포트(UI)
    "render_report",
    # Rule Change Proposal
    "build_proposal",
    "format_proposal",
    "RuleChangeProposal",
    "RuleDelta",
    "Disposition",
    # 라이브파이어 (증거 패키지)
    "run_livefire",
    "render_evidence_record",
    "EvidenceManifest",
    # 내규 영향도 맵
    "map_catalog_impact",
    "format_catalog",
    "CatalogImpact",
    "InternalRule",
    "RuleImpact",
    "DEFAULT_CATALOG",
]
