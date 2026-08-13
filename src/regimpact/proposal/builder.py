"""Rule Change Proposal 조립 — Extractor + Impact Matrix → 구조화 초안.

파이프라인 연결: RegChangeExtraction(정책 메타·시점) + ImpactMatrix(세그먼트 영향) →
RuleChangeProposal(초안). 제안 값은 ImpactMatrix에서만 유도 → 하드코딩 없음(엔진과 일치).
LOCKED §4: 초안은 approval=PENDING_REVIEW 로 나오고, record_decision 으로 사람이 확정한다.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from ..impact.matrix import ImpactDirection, ImpactMatrix
from .schema import (
    ApprovalStatus,
    ReviewDecision,
    RuleChangeLine,
    RuleChangeProposal,
)


def _line_from_row(row) -> RuleChangeLine:
    needs_review = row.direction == ImpactDirection.REVIEW
    # 근거 reason_code / 출처: 시행 후 우선, 없으면 시행 전(escalation 사유).
    reasons = tuple(row.after.reason_codes or row.before.reason_codes)
    sources = tuple(row.after.source_policy_ids or row.before.source_policy_ids)
    return RuleChangeLine(
        segment_id=row.segment.segment_id,
        segment_label=row.segment.label,
        rule_id=row.after.applicable_rule_id,
        before_ltv=row.before_ltv,
        after_ltv=row.after_ltv,
        direction=row.direction.value,
        delta_ltv=row.delta_ltv,
        reason_codes=reasons,
        source_policy_ids=sources,
        needs_review=needs_review,
        note=row.note,
    )


def build_proposal(
    matrix: ImpactMatrix,
    extraction=None,
    proposal_id: Optional[str] = None,
) -> RuleChangeProposal:
    """ImpactMatrix(+선택적 extraction 메타)에서 룰변경 제안 초안을 만든다.

    Args:
        matrix: analyze_impact/analyze_from_extraction 결과.
        extraction: RegChangeExtraction (정책 메타 보강용, 선택).
        proposal_id: 제안 식별자(미지정 시 정책·지역으로 유도).
    """
    policy_id = matrix.policy_id or getattr(extraction, "policy_id", None)
    effective_from = getattr(extraction, "effective_from", None)
    regions = list(getattr(extraction, "target_regions", None) or [matrix.region_code])

    if proposal_id is None:
        base = policy_id or "PROPOSAL"
        proposal_id = f"{base}::{matrix.region_code}"

    lines = [_line_from_row(r) for r in matrix.rows]

    return RuleChangeProposal(
        proposal_id=proposal_id,
        policy_id=policy_id,
        effective_from=effective_from,
        target_regions=regions,
        lines=lines,
        approval=ReviewDecision(status=ApprovalStatus.PENDING_REVIEW),
    )


def record_decision(
    proposal: RuleChangeProposal,
    status: ApprovalStatus,
    reviewer: Optional[str] = None,
    note: Optional[str] = None,
    reviewed_at: Optional[date] = None,
) -> RuleChangeProposal:
    """[7] Human Review — 사람 검토 결과를 제안에 기록한다(approval envelope 갱신).

    제안 본문(lines)은 그대로 두고 approval 만 바꾼다. 새 객체를 반환(원본 불변).
    """
    return RuleChangeProposal(
        proposal_id=proposal.proposal_id,
        policy_id=proposal.policy_id,
        effective_from=proposal.effective_from,
        target_regions=list(proposal.target_regions),
        lines=list(proposal.lines),
        approval=ReviewDecision(
            status=status, reviewer=reviewer, reviewed_at=reviewed_at, note=note
        ),
    )
