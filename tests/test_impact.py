"""Impact Analyzer 테스트 — Before/After 임팩트가 룰엔진 판정과 정합하는지 검증.

원칙: 임팩트는 룰엔진 출력의 '차이'여야 한다(독립적으로 규칙값을 만들지 않음).
각 테스트는 알려진 6·30 판정(rule_engine 테스트와 동일 사실)과 대조한다.
"""
from __future__ import annotations

from datetime import date

import pytest

from regimpact.impact import (
    ImpactDirection,
    analyze_portfolio,
    analyze_row,
    format_matrix,
    segment_of,
)
from regimpact.impact.analyzer import DEFAULT_AFTER_DATE, DEFAULT_BEFORE_DATE
from regimpact.models import EvaluationStatus, LoanPurpose, MortgageApplication

_REG = "GURI"           # 6·30 신규 규제지역
_NONREG = "SEOUL_GANGNAM"
_AFTER = date(2026, 7, 2)


def _a(**kw) -> MortgageApplication:
    base = dict(region_code=_REG, evaluation_date=_AFTER)
    base.update(kw)
    return MortgageApplication(**base)


# --- 개별 행 방향 -----------------------------------------------------------
def test_no_home_general_tightened_70_to_40():
    r = analyze_row(_a(house_count=0))
    assert r.before.max_ltv == 0.70
    assert r.after.max_ltv == 0.40
    assert r.direction == ImpactDirection.TIGHTENED
    assert r.ltv_delta == pytest.approx(-0.30)
    assert r.high_impact is True   # 30%p 하락


def test_first_home_unchanged_70():
    r = analyze_row(_a(house_count=0, first_home_buyer=True))
    assert r.before.max_ltv == 0.70 and r.after.max_ltv == 0.70
    assert r.direction == ImpactDirection.UNCHANGED
    assert r.changed is False and r.high_impact is False


def test_real_demand_tightened_70_to_60_not_high():
    r = analyze_row(_a(house_count=0, real_demand_flag=True))
    assert r.after.max_ltv == 0.60
    assert r.direction == ImpactDirection.TIGHTENED
    assert r.ltv_delta == pytest.approx(-0.10)
    assert r.high_impact is False   # 10%p 하락 < 임계


def test_multi_home_denial_is_tightened_and_high_impact():
    """다주택: before 비규제 owner=검토불가 → after 0%(거절). 강화·고임팩트."""
    r = analyze_row(_a(house_count=2))
    assert r.after.max_ltv == 0.0
    assert r.after.status == EvaluationStatus.DECIDED
    assert r.direction == ImpactDirection.TIGHTENED   # 0% 거절은 완화가 아니다
    assert r.high_impact is True


def test_owner_1home_denial_tightened():
    r = analyze_row(_a(house_count=1))
    assert r.after.max_ltv == 0.0
    assert r.direction == ImpactDirection.TIGHTENED
    assert r.high_impact is True


def test_disposal_1home_tightened_to_40():
    r = analyze_row(_a(house_count=1, disposal_condition_flag=True))
    assert r.after.max_ltv == 0.40
    assert r.direction == ImpactDirection.TIGHTENED


# --- 경과규정: 임팩트 없음이 정직하게 드러나야 함 ---------------------------
def test_grandfathered_g1_unchanged():
    r = analyze_row(_a(house_count=0, application_accepted_at=date(2026, 6, 30)))
    assert r.after.grandfathering_applied is True
    assert r.grandfathered is True
    assert r.after.max_ltv == 0.70
    assert r.direction == ImpactDirection.UNCHANGED   # 경과규정 = 임팩트 없음
    assert r.high_impact is False


def test_grandfathered_g2_unchanged():
    r = analyze_row(_a(
        house_count=0,
        contract_signed_at=date(2026, 6, 29),
        downpayment_paid_at=date(2026, 6, 29),
    ))
    assert r.grandfathered is True
    assert r.direction == ImpactDirection.UNCHANGED


def test_before_view_strips_grandfathering_events():
    """before 세계는 순수 종전 기준선이어야 한다(경과규정 이벤트 무시)."""
    r = analyze_row(_a(house_count=0, application_accepted_at=date(2026, 6, 30)))
    # before는 경과규정 근거 없이 평가 → grandfathering_applied False
    assert r.before.grandfathering_applied is False
    assert r.before.max_ltv == 0.70


# --- 스코프/할인 없는 상태 --------------------------------------------------
def test_non_regulated_unchanged():
    r = analyze_row(_a(region_code=_NONREG, house_count=0))
    assert r.direction == ImpactDirection.UNCHANGED
    assert r.changed is False


def test_out_of_scope_unchanged():
    r = analyze_row(_a(house_count=0, loan_purpose=LoanPurpose.OTHER))
    assert r.before.status == EvaluationStatus.OUT_OF_SCOPE
    assert r.after.status == EvaluationStatus.OUT_OF_SCOPE
    assert r.direction == ImpactDirection.UNCHANGED


def test_policy_loan_discovery_unchanged():
    r = analyze_row(_a(house_count=0, policy_mortgage_flag=True))
    assert r.after.status == EvaluationStatus.DISCOVERY
    assert r.direction == ImpactDirection.UNCHANGED


# --- 포트폴리오 집계 --------------------------------------------------------
def _portfolio() -> list[MortgageApplication]:
    return [
        _a(house_count=0),                                  # 강화 고임팩트
        _a(house_count=0),                                  # 강화 고임팩트
        _a(house_count=0, first_home_buyer=True),           # 변화없음
        _a(house_count=0, real_demand_flag=True),           # 강화(비고임팩트)
        _a(house_count=2),                                  # 거절 고임팩트
        _a(house_count=0, application_accepted_at=date(2026, 6, 30)),  # 경과규정
        _a(region_code=_NONREG, house_count=0),             # 비규제 변화없음
    ]


def test_portfolio_aggregate_counts():
    m = analyze_portfolio(_portfolio())
    assert m.n == 7
    # 변경영향: 무주택2 + 실수요1 + 다주택1 = 4
    assert m.n_changed == 4
    assert m.n_tightened == 4
    assert m.n_grandfathered == 1
    # 고임팩트: 무주택2(30%p) + 다주택1(거절) = 3
    assert m.n_high_impact == 3
    assert m.affected_rate == pytest.approx(4 / 7)


def test_portfolio_segments_sorted_by_severity():
    m = analyze_portfolio(_portfolio())
    segs = m.segments
    assert len(segs) >= 1
    # 정렬 키: (고임팩트, 강화, n) 내림차순 → 첫 세그먼트가 가장 심각
    keys = [(s.n_high_impact, s.n_tightened, s.n) for s in segs]
    assert keys == sorted(keys, reverse=True)
    # NO_HOME·GENERAL 세그먼트가 고임팩트 2로 최상위
    top = segs[0]
    assert top.segment.housing == "NO_HOME"
    assert top.n_high_impact == 2


def test_segment_labels_distinguish_transition():
    reg = segment_of(analyze_row(_a(house_count=0)))
    nonreg = segment_of(analyze_row(_a(region_code=_NONREG, house_count=0)))
    assert reg.region_transition == "NEWLY_REGULATED"
    assert nonreg.region_transition == "NON_REGULATED"


def test_avg_ltv_before_after_delta():
    m = analyze_portfolio([_a(house_count=0), _a(house_count=0)])
    seg = m.segments[0]
    assert seg.avg_ltv_before == pytest.approx(0.70)
    assert seg.avg_ltv_after == pytest.approx(0.40)
    assert seg.avg_ltv_delta == pytest.approx(-0.30)


def test_format_matrix_smoke():
    out = format_matrix(analyze_portfolio(_portfolio()))
    assert "Impact Matrix" in out
    assert "NEWLY_REGULATED" in out
    assert "고임팩트" in out


def test_default_dates_match_scenario():
    assert DEFAULT_BEFORE_DATE < date(2026, 7, 1) <= DEFAULT_AFTER_DATE
