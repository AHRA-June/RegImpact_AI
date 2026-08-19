"""RegImpact AI — Rule Change Proposal (구조화 정책 변경안).

거버넌스(LOCKED, docs/00_BRIEF.md §9): LLM은 룰엔진 코드를 직접 수정하지 않는다.
LLM은 인용 근거가 붙은 사실만 추출하고(RegChange Extractor), 이 모듈이 그 추출을
구조화 변경안으로 deterministic하게 조립한다(status=DRAFT). 변경안은 사람 승인 후에야
deterministic rule registry(룰엔진)에 반영된다.

파이프라인: RegChange Extractor → **Rule Change Proposal** → (사람 승인) → Rule Engine.
Assurance: 변경안이 엔진 실제 동작(Impact Matrix)과 일치하는지 consistency 교차검증.
"""
from .builder import build_proposal_from_extraction, parse_ltv
from .consistency import (
    ConsistencyCheck,
    ConsistencyReport,
    apply_consistency_status,
    check_proposal_consistency,
    newly_designated_regions,
)
from .schema import (
    ChangeType,
    Grandfathering,
    ProposalSource,
    ProposalStatus,
    RuleChangeProposal,
    RuleState,
)

__all__ = [
    "build_proposal_from_extraction",
    "parse_ltv",
    "check_proposal_consistency",
    "apply_consistency_status",
    "ConsistencyReport",
    "ConsistencyCheck",
    "newly_designated_regions",
    "RuleChangeProposal",
    "RuleState",
    "Grandfathering",
    "ProposalSource",
    "ChangeType",
    "ProposalStatus",
]
