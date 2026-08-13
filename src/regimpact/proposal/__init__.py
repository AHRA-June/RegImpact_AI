"""Rule Change Proposal — 구조화 룰변경 제안(AI초안→사람확정).

핵심 진입점:
    build_proposal(matrix, extraction?) -> RuleChangeProposal
    record_decision(proposal, status, reviewer?, note?) -> RuleChangeProposal   ([7] Human Review)

LOCKED §4: 제안은 초안(approval=PENDING_REVIEW)으로 나오고, 값은 ImpactMatrix에서만 유도된다.
"""
from .builder import build_proposal, record_decision
from .schema import (
    ApprovalStatus,
    ReviewDecision,
    RuleChangeLine,
    RuleChangeProposal,
)

__all__ = [
    "build_proposal",
    "record_decision",
    "RuleChangeProposal",
    "RuleChangeLine",
    "ReviewDecision",
    "ApprovalStatus",
]
