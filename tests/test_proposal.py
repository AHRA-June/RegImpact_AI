"""Rule Change Proposal 테스트 — 조립 정확성 + 엔진 일치 검증(+mutation 방어).

거버넌스 계약: 변경안은 항상 DRAFT로 생성되고, 엔진과 불일치하면 consistency가
이를 잡아 NEEDS_REVIEW로 승격한다(자동 승인 없음).
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from regimpact.impact import build_impact_matrix  # noqa: E402
from regimpact.proposal import (  # noqa: E402
    ChangeType,
    ProposalStatus,
    apply_consistency_status,
    build_proposal_from_extraction,
    check_proposal_consistency,
    parse_ltv,
    six_thirty_extraction,
)


@pytest.fixture(scope="module")
def proposal():
    return build_proposal_from_extraction(six_thirty_extraction())


@pytest.fixture(scope="module")
def matrix():
    return build_impact_matrix()


# ── parse_ltv ──
@pytest.mark.parametrize("s,expected", [
    ("70%", 0.70), ("40%", 0.40), ("60%", 0.60),
    ("0.70", 0.70), ("0.4", 0.40), ("70", 0.70), ("100%", 1.0),
    (None, None), ("", None), ("종전규정", None),
])
def test_parse_ltv(s, expected):
    assert parse_ltv(s) == expected


# ── builder: 추출 → 변경안 필드 매핑 ──
def test_proposal_core_fields(proposal):
    assert proposal.rule_id == "MORTGAGE_LTV_REGULATED_REGION"
    assert proposal.change_type == ChangeType.MODIFY
    assert proposal.status == ProposalStatus.DRAFT       # 항상 초안으로 생성
    assert proposal.before.max_ltv == 0.70
    assert proposal.before.region_status == "NON_REGULATED"
    assert proposal.after.max_ltv == 0.40
    assert proposal.after.region_status == "REGULATED"
    assert proposal.after.effective_from == "2026-07-01"
    assert set(proposal.after.target_regions) == {"GURI", "YONGIN_GIHEUNG", "HWASEONG_DONGTAN"}


def test_proposal_exceptions(proposal):
    assert "FIRST_HOME_BUYER" in proposal.exceptions
    assert "REAL_DEMAND" in proposal.exceptions


def test_proposal_grandfathering(proposal):
    gf = proposal.grandfathering
    assert gf is not None
    assert gf.cutoff_date == "2026-06-30"
    assert "APPLICATION_ACCEPTED" in gf.conditions
    assert "CONTRACT_SIGNED_AND_DOWNPAYMENT_PROVEN" in gf.conditions


def test_proposal_sources_provenance(proposal):
    # 모든 핵심 필드가 인용 근거를 가진다 (citation grounding 연결)
    fields = {s.field_name for s in proposal.sources}
    assert {"after.max_ltv", "after.target_regions", "after.effective_from",
            "exceptions", "grandfathering"} <= fields
    for s in proposal.sources:
        assert s.evidence_span and s.source_doc_id


# ── consistency: canonical 은 전부 통과 ──
def test_consistency_all_pass(proposal, matrix):
    report = check_proposal_consistency(proposal, matrix=matrix)
    assert report.all_passed, [c.to_dict() for c in report.failed]
    assert report.summary()["failed"] == 0
    # 통과 시 DRAFT 유지 (자동 승인 아님)
    apply_consistency_status(proposal, report)
    assert proposal.status == ProposalStatus.DRAFT


def test_consistency_runs_without_matrix(proposal):
    report = check_proposal_consistency(proposal)   # matrix 없이 엔진 상수만
    assert report.all_passed
    assert report.summary()["total"] == 6           # matrix 대조 3건 제외


# ── mutation: 변경안을 손상시키면 consistency가 잡아 NEEDS_REVIEW 승격 ──
@pytest.mark.parametrize("mutate", [
    lambda p: setattr(p.after, "max_ltv", 0.50),                 # 잘못된 LTV
    lambda p: setattr(p.after, "effective_from", "2026-08-01"),  # 잘못된 시행일
    lambda p: setattr(p.after, "target_regions", ["SEJONG"]),    # 환각 지역
    lambda p: setattr(p.grandfathering, "cutoff_date", "2026-06-29"),  # 잘못된 컷오프
    lambda p: setattr(p, "exceptions", []),                      # 예외 누락
])
def test_consistency_catches_mutation(matrix, mutate):
    p = build_proposal_from_extraction(six_thirty_extraction())
    mutate(p)
    report = check_proposal_consistency(p, matrix=matrix)
    assert not report.all_passed
    apply_consistency_status(p, report)
    assert p.status == ProposalStatus.NEEDS_REVIEW


# ── to_dict 직렬화 계약 ──
def test_to_dict_contract(proposal):
    d = proposal.to_dict()
    for key in ("rule_id", "change_type", "status", "summary", "before", "after",
                "exceptions", "grandfathering", "sources"):
        assert key in d
    assert d["before"]["max_ltv"] == 0.70
    assert d["after"]["max_ltv"] == 0.40
    assert isinstance(d["sources"], list) and d["sources"]


# ── 결정성 ──
def test_deterministic():
    a = build_proposal_from_extraction(six_thirty_extraction()).to_dict()
    b = build_proposal_from_extraction(six_thirty_extraction()).to_dict()
    assert a == b
