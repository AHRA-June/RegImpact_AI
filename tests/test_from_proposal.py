"""Proposal → Test Cases 연결 테스트 — 커버리지·추적성·fidelity·회귀.

거버넌스 계약: 변경안의 모든 주장이 테스트로 커버되고, 엔진 실제 동작이 변경안
주장과 일치(fidelity)하며, 변경안이 틀리면 fidelity가 이를 잡는다.
"""
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from regimpact.proposal import (  # noqa: E402
    build_proposal_from_extraction,
    six_thirty_extraction,
)
from regimpact.tc_generator import (  # noqa: E402
    check_proposal_fidelity,
    generate_cases_for_proposal,
    run_regression,
)


@pytest.fixture()
def proposal():
    return build_proposal_from_extraction(six_thirty_extraction())


@pytest.fixture()
def suite(proposal):
    return generate_cases_for_proposal(proposal)


# ── 생성·커버리지 ──
def test_claims_present(suite):
    ids = {c.claim_id for c in suite.claims}
    assert ids == {
        "REGION_DESIGNATION", "LTV_STANDARD", "EFFECTIVE_BOUNDARY",
        "EXC_FIRST_HOME", "EXC_REAL_DEMAND", "GF_ON_CUTOFF", "GF_AFTER_CUTOFF",
    }


def test_full_coverage(suite):
    cov = suite.coverage()
    assert cov["covered"] is True
    assert cov["uncovered"] == []
    assert cov["covered_claims"] == cov["total_claims"] == 7
    # 대상지역 3개 → REGION_DESIGNATION 케이스 3건
    assert cov["per_claim"]["REGION_DESIGNATION"] == 3


def test_case_count(suite):
    # 3(region) + 1(std) + 1(eff) + 2(exc) + 2(gf) = 9
    assert len(suite.generated_cases()) == 9


# ── 추적성: 모든 케이스가 유효한 주장에 매핑 ──
def test_traceability(suite):
    claim_ids = {c.claim_id for c in suite.claims}
    for t in suite.traced:
        assert t.claim_id in claim_ids
        assert t.case.case_id.startswith("PROP-")


def test_case_ids_unique(suite):
    ids = [t.case.case_id for t in suite.traced]
    assert len(ids) == len(set(ids))


# ── 시점이 proposal 값에서 유도되는가(하드코딩 아님) ──
def test_effective_boundary_uses_proposal_date(suite):
    eff_cases = suite.cases_for("EFFECTIVE_BOUNDARY")
    assert len(eff_cases) == 1
    assert eff_cases[0].app.evaluation_date == date(2026, 6, 30)  # 시행일 7/1의 전일


# ── Fidelity: canonical 은 전부 통과 ──
def test_fidelity_all_pass(suite, proposal):
    rep = check_proposal_fidelity(suite, proposal)
    assert rep.all_passed, [r.detail for r in rep.failures]
    assert rep.summary()["total"] == 9


# ── 회귀(engine ⟷ oracle): 생성 케이스 100% ──
def test_regression_passes(suite):
    report = run_regression(suite.generated_cases())
    assert report.pass_rate == 1.0
    assert report.total == 9


# ── Fidelity가 잘못된 변경안을 잡는다 ──
def test_fidelity_catches_wrong_ltv(proposal):
    proposal.after.max_ltv = 0.50            # 엔진 실제는 0.40 → 불일치
    suite = generate_cases_for_proposal(proposal)
    rep = check_proposal_fidelity(suite, proposal)
    assert not rep.all_passed
    failed_claims = {r.claim_id for r in rep.failures}
    assert "LTV_STANDARD" in failed_claims
    assert "REGION_DESIGNATION" in failed_claims


def test_fidelity_catches_wrong_baseline(proposal):
    # 구규제 기준선을 잘못 주장하면(엔진 실제 70%) 시행 전일 경계 케이스가 잡는다.
    proposal.before.max_ltv = 0.60           # 엔진 실제는 70% → 불일치
    suite = generate_cases_for_proposal(proposal)
    rep = check_proposal_fidelity(suite, proposal)
    assert not rep.all_passed
    assert "EFFECTIVE_BOUNDARY" in {r.claim_id for r in rep.failures}


def test_fidelity_complements_consistency(proposal):
    # 실행 기반 fidelity는 엔진의 REG_EFFECTIVE(7/1)가 proposal과 독립이라
    # 시행일 오류를 직접 잡지 못한다 → 이는 proposal.consistency(상수 대조)의 몫.
    # 여기서는 시행일을 바꿔도 fidelity가 여전히 통과함을 문서화한다(역할 분담).
    from regimpact.proposal import check_proposal_consistency
    proposal.after.effective_from = "2026-06-30"
    suite = generate_cases_for_proposal(proposal)
    assert check_proposal_fidelity(suite, proposal).all_passed          # 실행 기반은 못 잡음
    assert not check_proposal_consistency(proposal).all_passed          # 상수 대조가 잡음


# ── 경계: 빈 대상지역·시행일 누락은 명시적 오류 ──
def test_empty_regions_raises(proposal):
    proposal.after.target_regions = []
    with pytest.raises(ValueError):
        generate_cases_for_proposal(proposal)


def test_missing_effective_raises(proposal):
    proposal.after.effective_from = None
    with pytest.raises(ValueError):
        generate_cases_for_proposal(proposal)


# ── 예외가 없는 변경안은 예외 주장도 없다(불필요 케이스 미생성) ──
def test_no_exceptions_no_exception_claims(proposal):
    proposal.exceptions = []
    suite = generate_cases_for_proposal(proposal)
    ids = {c.claim_id for c in suite.claims}
    assert "EXC_FIRST_HOME" not in ids
    assert "EXC_REAL_DEMAND" not in ids
