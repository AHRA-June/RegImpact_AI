"""Rule Change Proposal 스키마 (구조화 룰변경 제안).

Walking Skeleton(docs/04_PLAN.md Phase 1)의 **[4] Rule Change Proposal 노드.**

LOCKED §4 "AI초안 → 사람확정": 이 제안은 **초안(DRAFT)**이며, 룰 로직을 자동 확정하지 않는다.
`approval` 필드가 사람 검토([7] Human Review) 결과를 담는 envelope 다. 기본값은 검토 대기.
제안 내용(before/after LTV, 근거)은 **엔진 실제 산출(ImpactMatrix)** 에서만 오므로 하드코딩이 없다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional


class ApprovalStatus(str, Enum):
    """사람 검토([7]) 결과. 기본은 PENDING_REVIEW(AI초안, 확정 대기)."""
    PENDING_REVIEW = "PENDING_REVIEW"      # AI초안 — 사람 확정 대기
    APPROVED = "APPROVED"                  # 사람 승인
    REJECTED = "REJECTED"                  # 사람 반려
    CHANGES_REQUESTED = "CHANGES_REQUESTED"  # 수정 요청


@dataclass(frozen=True)
class RuleChangeLine:
    """제안된 룰 변경 1행 (세그먼트 단위). 값은 ImpactMatrix에서 유도된 것."""
    segment_id: str
    segment_label: str
    rule_id: Optional[str]            # 시행 후 applicable_rule_id
    before_ltv: Optional[float]       # 시행 전 max_ltv (없으면 None=기준값 부재)
    after_ltv: Optional[float]        # 시행 후 max_ltv
    direction: str                    # ImpactDirection value
    delta_ltv: Optional[float]
    reason_codes: tuple[str, ...] = field(default_factory=tuple)
    source_policy_ids: tuple[str, ...] = field(default_factory=tuple)
    needs_review: bool = False        # 이 행이 사람 검토 필요(escalation)한지
    note: Optional[str] = None


@dataclass(frozen=True)
class ReviewDecision:
    """사람 검토([7]) 기록."""
    status: ApprovalStatus
    reviewer: Optional[str] = None
    reviewed_at: Optional[date] = None
    note: Optional[str] = None


@dataclass
class RuleChangeProposal:
    """구조화 룰변경 제안 (AI초안). 사람 확정 전까지 approval=PENDING_REVIEW."""
    proposal_id: str
    policy_id: Optional[str]
    effective_from: Optional[str]           # ISO date
    target_regions: list[str] = field(default_factory=list)
    lines: list[RuleChangeLine] = field(default_factory=list)
    approval: ReviewDecision = field(
        default_factory=lambda: ReviewDecision(status=ApprovalStatus.PENDING_REVIEW)
    )

    @property
    def review_required_lines(self) -> list[RuleChangeLine]:
        """자동 확정 불가(escalation)로 사람 판단이 필요한 행."""
        return [ln for ln in self.lines if ln.needs_review]

    def summary(self) -> dict[str, int]:
        """방향별 제안 행 수 요약(ImpactDirection value 기준)."""
        out: dict[str, int] = {}
        for ln in self.lines:
            out[ln.direction] = out.get(ln.direction, 0) + 1
        return out
