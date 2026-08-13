"""Impact Analysis + E2E Pipeline — 6·30 1건을 Source→Report까지 관통.

핵심 진입점:
    run_e2e(extraction?) -> E2EReport      (전체 파이프라인 관통)
    format_e2e_report(report) -> str        (사람이 읽는 검증보고서)
    build_impact_matrix(regions?) -> [ImpactRow]
    build_proposal(extraction, matrix) -> RuleChangeProposal
    anchor_extraction() -> RegChangeExtraction   (원문 grounding된 오프라인 추출)

설계: Impact Matrix·Proposal의 LTV 값은 전부 deterministic 룰엔진에서 온다(LOCKED §4).
LLM 추출은 검증 대상(Assurance ① Citation grounding)으로만 흐른다.
"""
from .anchor import anchor_extraction
from .matrix import (
    AFTER_DATE,
    BEFORE_DATE,
    SIX_THIRTY_REGIONS,
    ImpactRow,
    build_impact_matrix,
)
from .personas import SIX_THIRTY_PERSONAS, Persona
from .pipeline import E2EReport, load_gold, run_e2e
from .proposal import (
    ApprovalStatus,
    ProposedRuleChange,
    Provenance,
    RuleChangeProposal,
    build_proposal,
)
from .report import format_e2e_report

__all__ = [
    "run_e2e",
    "E2EReport",
    "load_gold",
    "format_e2e_report",
    "build_impact_matrix",
    "ImpactRow",
    "BEFORE_DATE",
    "AFTER_DATE",
    "SIX_THIRTY_REGIONS",
    "Persona",
    "SIX_THIRTY_PERSONAS",
    "anchor_extraction",
    "build_proposal",
    "RuleChangeProposal",
    "ProposedRuleChange",
    "ApprovalStatus",
    "Provenance",
]
