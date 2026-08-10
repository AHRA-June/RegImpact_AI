"""룰엔진 테스트 하네스 — docs/05_RULE_SPEC.md의 각 분기(P0~P7) + 경과규정 커버.

이 테스트는 '확정된 명세(v1)'가 코드에 정확히 구현됐는지 검증하는 회귀 fixture다.
brief §15의 TC 일부는 FAQ Q2 확정 이전 값(1주택=40%)이라, 확정 사실(유주택=0%)로 갱신해 검증한다.
"""
from datetime import date

import pytest

from regimpact import (
    EvaluationStatus,
    LoanPurpose,
    MortgageApplication,
    evaluate,
)

AFTER = date(2026, 7, 2)    # 시행 후, 경과규정 미해당
BEFORE = date(2026, 6, 15)  # 시행 전


def app(**kw) -> MortgageApplication:
    base = dict(region_code="GURI", evaluation_date=AFTER)
    base.update(kw)
    return MortgageApplication(**base)


# ---------- P0 / P0b: 스코프 ----------
def test_p0_out_of_scope_when_not_home_purchase():
    d = evaluate(app(loan_purpose=LoanPurpose.OTHER))
    assert d.status == EvaluationStatus.OUT_OF_SCOPE
    assert d.max_ltv is None
    assert "OUT_OF_SCOPE_PRODUCT" in d.reason_codes


def test_p0b_policy_loan_goes_to_discovery():
    d = evaluate(app(policy_mortgage_flag=True, first_home_buyer=True))
    assert d.status == EvaluationStatus.DISCOVERY
    assert "DISCOVERY_POLICY_LOAN" in d.reason_codes


# ---------- P2: 지역상태(시점) ----------
def test_p2_before_effective_date_is_baseline_70():
    # 시행 전(6.15) 구리는 아직 非규제 → 기준선 70%
    d = evaluate(app(evaluation_date=BEFORE, house_count=0))
    assert d.status == EvaluationStatus.DECIDED
    assert d.max_ltv == 0.70


def test_p2_unregistered_region_is_non_regulated():
    d = evaluate(app(region_code="SEOUL_GANGNAM", house_count=0))
    assert d.max_ltv == 0.70  # 미등록 지역 → 非규제 기준선


# ---------- P3 / P4: 소유 상태 ----------
def test_p3_multi_home_zero():
    d = evaluate(app(house_count=2))
    assert d.max_ltv == 0.0
    assert "LTV_MULTI_HOME_0" in d.reason_codes


def test_p4_owner_one_home_non_disposal_zero():
    # 비처분 1주택 = 유주택 → 0% (확정 사실; brief 초기 TC001의 40%를 교정)
    d = evaluate(app(house_count=1, disposal_condition_flag=False))
    assert d.max_ltv == 0.0
    assert "LTV_OWNER_0" in d.reason_codes


def test_disposal_condition_one_home_treated_as_no_home_40():
    # 처분조건부 1주택 = 무주택 기준 → 40%
    d = evaluate(app(house_count=1, disposal_condition_flag=True))
    assert d.max_ltv == 0.40
    assert d.applicable_rule_id == "REG_STD"


# ---------- P5 / P6 / P7: 무주택 기준 예외 계층 ----------
def test_p5_first_home_buyer_70():
    d = evaluate(app(house_count=0, first_home_buyer=True))
    assert d.max_ltv == 0.70
    assert "EXCEPTION_FIRST_HOME" in d.reason_codes


def test_p6_real_demand_60():
    d = evaluate(app(house_count=0, real_demand_flag=True))
    assert d.max_ltv == 0.60
    assert "EXCEPTION_REAL_DEMAND" in d.reason_codes


def test_p7_standard_no_home_40():
    d = evaluate(app(house_count=0))
    assert d.max_ltv == 0.40
    assert "LTV_REGULATED_40" in d.reason_codes


def test_first_home_beats_real_demand():
    # 우선순위: 생애최초(P5) > 서민실수요(P6)
    d = evaluate(app(house_count=0, first_home_buyer=True, real_demand_flag=True))
    assert d.max_ltv == 0.70


# ---------- P1: 경과규정 (최우선) ----------
def test_g1_accepted_before_cutoff_grandfathered_70():
    d = evaluate(app(house_count=0, application_accepted_at=date(2026, 6, 30)))
    assert d.grandfathering_applied is True
    assert d.max_ltv == 0.70
    assert "GRANDFATHERED_ACCEPTED_OR_CONTRACT" in d.reason_codes


def test_g1_accepted_after_cutoff_not_grandfathered():
    d = evaluate(app(house_count=0, application_accepted_at=date(2026, 7, 1)))
    assert d.grandfathering_applied is False
    assert d.max_ltv == 0.40  # 신규 규제


def test_g2_contract_plus_downpayment_grandfathered():
    d = evaluate(app(
        house_count=0,
        contract_signed_at=date(2026, 6, 29),
        downpayment_paid_at=date(2026, 6, 29),
        application_accepted_at=date(2026, 7, 1),  # 접수는 이후지만 계약+계약금으로 종전
    ))
    assert d.grandfathering_applied is True
    assert d.max_ltv == 0.70


def test_g2_contract_without_downpayment_not_grandfathered():
    d = evaluate(app(house_count=0, contract_signed_at=date(2026, 6, 29)))
    assert d.grandfathering_applied is False
    assert d.max_ltv == 0.40


def test_g3_land_permit_grandfathered():
    d = evaluate(app(
        house_count=0,
        land_permit_target=True,
        land_permit_applied_at=date(2026, 6, 30),
        contract_signed_at=date(2026, 7, 10),  # 이후 계약이어도 종전
    ))
    assert d.grandfathering_applied is True
    assert "GRANDFATHERED_LAND_PERMIT" in d.reason_codes


def test_grandfathering_beats_new_regulation_priority():
    # 경과규정(P1) > 규제지역 일반(P7): 접수 6.30, 무주택 → 40%가 아니라 70%
    d = evaluate(app(house_count=0, application_accepted_at=date(2026, 6, 29)))
    assert d.max_ltv == 0.70


# ---------- 엣지: 유주택 grandfathered → escalation ----------
def test_grandfathered_owner_needs_human_review():
    d = evaluate(app(
        house_count=2,
        application_accepted_at=date(2026, 6, 20),
    ))
    assert d.status == EvaluationStatus.NEEDS_HUMAN_REVIEW
    assert "OWNER_BASELINE_UNKNOWN" in d.reason_codes


# ---------- brief §15 앵커 케이스 (확정 사실로 갱신) ----------
def test_anchor_tc002_first_home_regulated_70():
    # TC002: 구리, 생애최초 Y, 접수 7.2 → 생애최초 예외 70%
    d = evaluate(app(house_count=0, first_home_buyer=True,
                     application_accepted_at=date(2026, 7, 2)))
    assert d.max_ltv == 0.70
    assert d.grandfathering_applied is False


def test_anchor_tc003_grandfathering_review():
    # TC003: 구리, 계약 6.29 + 계약금 Y, 접수 7.1 → 경과규정 종전규정
    d = evaluate(app(house_count=0,
                     contract_signed_at=date(2026, 6, 29),
                     downpayment_paid_at=date(2026, 6, 29),
                     application_accepted_at=date(2026, 7, 1)))
    assert d.grandfathering_applied is True
    assert d.max_ltv == 0.70


# ---------- 출력 계약: reason_code·source 항상 존재 ----------
@pytest.mark.parametrize("kw", [
    dict(house_count=0),
    dict(house_count=2),
    dict(house_count=0, first_home_buyer=True),
])
def test_decided_always_has_reason_and_source(kw):
    d = evaluate(app(**kw))
    assert d.reason_codes, "판정에는 최소 1개 reason_code가 있어야 한다"
    assert d.source_policy_ids, "판정에는 근거 정책이 있어야 한다"
