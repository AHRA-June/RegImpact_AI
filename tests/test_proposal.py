"""Rule Change Proposal 테스트.

검증: ①제안 값이 ImpactMatrix에서만 유도(하드코딩 없음, 엔진 일치) ②AI초안=PENDING_REVIEW
③escalation 세그먼트 needs_review 표시 ④record_decision([7] Human Review) 승인 반영·원본 불변.
"""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from regimpact.impact import (  # noqa: E402
    DEFAULT_REGION,
    SIX_THIRTY_SEGMENTS,
    analyze_impact,
)
from regimpact.proposal import (  # noqa: E402
    ApprovalStatus,
    build_proposal,
    record_decision,
)

BEFORE = date(2026, 6, 30)
AFTER = date(2026, 7, 2)


def _matrix():
    return analyze_impact(SIX_THIRTY_SEGMENTS, DEFAULT_REGION, BEFORE, AFTER,
                          policy_id="FSC_20260630")


def _line(proposal, seg_id):
    return next(ln for ln in proposal.lines if ln.segment_id == seg_id)


def test_proposal_default_pending_review():
    """AI초안은 사람 확정 전(PENDING_REVIEW)."""
    p = build_proposal(_matrix())
    assert p.approval.status == ApprovalStatus.PENDING_REVIEW
    assert p.approval.reviewer is None


def test_proposal_lines_match_matrix():
    """제안 행 수·값이 매트릭스와 일치(자체 값 미보유)."""
    m = _matrix()
    p = build_proposal(m)
    assert len(p.lines) == len(m.rows)
    ln = _line(p, "SEG-01")   # 무주택 일반
    assert ln.before_ltv == 0.70
    assert ln.after_ltv == 0.40
    assert ln.rule_id == "REG_STD"
    assert "LTV_REGULATED_40" in ln.reason_codes


def test_proposal_review_flags_escalation():
    """非규제 유주택(기준값 부재) 세그먼트는 needs_review=True."""
    p = build_proposal(_matrix())
    review_ids = {ln.segment_id for ln in p.review_required_lines}
    assert review_ids == {"SEG-04", "SEG-06"}
    assert _line(p, "SEG-04").before_ltv is None


def test_proposal_id_derivation():
    p = build_proposal(_matrix())
    assert p.proposal_id == "FSC_20260630::GURI"
    assert p.policy_id == "FSC_20260630"


def test_proposal_summary():
    s = build_proposal(_matrix()).summary()
    assert s["TIGHTENED"] == 3
    assert s["UNCHANGED"] == 1
    assert s["REVIEW"] == 2


def test_record_decision_approves_without_mutating_original():
    """[7] Human Review: 승인 기록은 새 객체, 원본은 불변."""
    p0 = build_proposal(_matrix())
    p1 = record_decision(p0, ApprovalStatus.APPROVED, reviewer="심사역", note="확인",
                         reviewed_at=date(2026, 7, 1))
    assert p1.approval.status == ApprovalStatus.APPROVED
    assert p1.approval.reviewer == "심사역"
    assert p1.approval.reviewed_at == date(2026, 7, 1)
    # 원본 불변
    assert p0.approval.status == ApprovalStatus.PENDING_REVIEW
    # 본문(lines)은 그대로
    assert len(p1.lines) == len(p0.lines)


def test_record_decision_reject():
    p = record_decision(build_proposal(_matrix()), ApprovalStatus.REJECTED,
                        reviewer="심사역", note="근거 부족")
    assert p.approval.status == ApprovalStatus.REJECTED
