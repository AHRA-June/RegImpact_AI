"""Impact Matrix 테스트 — 6·30 before/after 차등 임팩트 (E2E Walking Skeleton).

검증 축:
  1. 계약: analyze_impact 이 세그먼트별 before/after 판정을 담은 행을 낸다.
  2. 6·30 앵커 단언: 각 대표 세그먼트의 방향·delta·상태전이가 명세(룰엔진)와 일치.
  3. 집계 정합성: 방향 카운트 합=행수, 가중평균은 수치비교 가능 행만, 조용한 누락 없음.
  4. 시점 무의존성 회귀: before/after 날짜를 시행 전으로 몰면 임팩트가 사라진다(엔진의
     시점 해석이 실제로 임팩트를 만든다는 증거 — tautology 방지).
"""
from datetime import date

from regimpact import EvaluationStatus, analyze_impact, format_report
from regimpact.impact import (
    AFTER_DATE,
    BEFORE_DATE,
    CustomerSegment,
    ImpactDirection,
    SIX_THIRTY_SEGMENTS,
    analyze_segment,
)


def _matrix():
    return analyze_impact(SIX_THIRTY_SEGMENTS, policy_id="6_30_2026")


def _row(matrix, label):
    for r in matrix.rows:
        if r.label == label:
            return r
    raise AssertionError(f"세그먼트 없음: {label}")


# ---------- 계약 ----------
def test_matrix_has_row_per_segment():
    m = _matrix()
    assert len(m.rows) == len(SIX_THIRTY_SEGMENTS)
    assert m.policy_id == "6_30_2026"
    assert m.before_date == BEFORE_DATE
    assert m.after_date == AFTER_DATE


def test_each_row_preserves_before_and_after_decisions():
    """감사 가능성: 모든 행이 before/after 판정과 reason_codes 를 보존."""
    m = _matrix()
    for r in m.rows:
        assert r.before is not None and r.after is not None
        assert isinstance(r.after.reason_codes, list)


# ---------- 6·30 앵커 단언 ----------
def test_baseline_no_house_tightened_70_to_40():
    r = _row(_matrix(), "무주택 일반")
    assert r.before.max_ltv == 0.70
    assert r.after.max_ltv == 0.40
    assert r.direction == ImpactDirection.TIGHTENED
    assert r.ltv_delta == -0.30
    assert r.high_impact is True
    assert r.escalation_required is False


def test_first_home_exception_unchanged():
    r = _row(_matrix(), "생애최초")
    assert r.before.max_ltv == 0.70 and r.after.max_ltv == 0.70
    assert r.direction == ImpactDirection.UNCHANGED
    assert r.ltv_delta == 0.0
    assert r.high_impact is False


def test_real_demand_tightened_70_to_60():
    r = _row(_matrix(), "서민·실수요")
    assert r.after.max_ltv == 0.60
    assert r.direction == ImpactDirection.TIGHTENED
    assert r.ltv_delta == -0.10
    assert r.high_impact is False  # 10pp < 30pp 임계


def test_disposal_conditional_treated_as_no_house():
    r = _row(_matrix(), "처분조건부 1주택")
    assert r.before.max_ltv == 0.70 and r.after.max_ltv == 0.40
    assert r.direction == ImpactDirection.TIGHTENED
    assert r.high_impact is True


def test_owner_before_baseline_gap_is_needs_review():
    """비규제 유주택 기준선은 명세 여백 → before 자동판정 불가, after 0%."""
    r = _row(_matrix(), "비처분 1주택(유주택)")
    assert r.before.status == EvaluationStatus.NEEDS_HUMAN_REVIEW
    assert r.after.status == EvaluationStatus.DECIDED and r.after.max_ltv == 0.0
    assert r.direction == ImpactDirection.NEEDS_REVIEW
    assert r.ltv_delta is None
    assert r.high_impact is True


def test_multi_home_after_zero():
    r = _row(_matrix(), "다주택")
    assert r.after.max_ltv == 0.0
    assert r.direction == ImpactDirection.NEEDS_REVIEW
    assert r.high_impact is True


def test_grandfathering_shields_from_change():
    r = _row(_matrix(), "경과규정(계약+계약금)")
    assert r.before.max_ltv == 0.70 and r.after.max_ltv == 0.70
    assert r.after.grandfathering_applied is True
    assert r.direction == ImpactDirection.UNCHANGED


def test_policy_loan_routes_to_discovery_both_sides():
    """정책대출은 코어 밖 Discovery — 전/후 동일 라우팅, 변화 없음(중대영향 아님)."""
    r = _row(_matrix(), "정책대출(디딤돌)")
    assert r.before.status == EvaluationStatus.DISCOVERY
    assert r.after.status == EvaluationStatus.DISCOVERY
    assert r.direction == ImpactDirection.UNCHANGED
    assert r.ltv_delta is None
    assert r.high_impact is False
    # 단, after가 자동판정(DECIDED)이 아니므로 운영상 사람검토 필요로 집계된다.
    assert r.escalation_required is True


# ---------- 집계 정합성 ----------
def test_direction_counts_sum_to_rows():
    m = _matrix()
    counts = m.count_by_direction()
    assert sum(counts.values()) == len(m.rows)


def test_weighted_mean_uses_only_comparable_rows():
    m = _matrix()
    # 수치비교 가능 행 수 < 전체 → 누락이 명시적으로 드러나야 함
    assert m.comparable_count < len(m.rows)
    assert m.weighted_mean_delta() is not None
    # 모든 비교가능 delta 는 <= 0 (이번 정책은 강화/유지뿐)
    assert m.weighted_mean_delta() <= 0


def test_report_flags_non_comparable_rows():
    report = format_report(_matrix())
    assert "수치비교 불가" in report
    assert "Impact Matrix" in report


# ---------- 시점 무의존성 회귀 (tautology 방지) ----------
def test_no_impact_when_both_dates_pre_effective():
    """before/after 를 모두 시행 전으로 두면 지역이 안 바뀌어 임팩트가 사라진다.

    임팩트가 엔진의 '시점 해석'에서 실제로 나온다는 증거. 만약 이 테스트가
    임팩트를 계속 잡아낸다면 differential 이 날짜와 무관하게 상수를 비교하는 셈.
    """
    seg = CustomerSegment(label="무주택 일반", attrs=dict(region_code="GURI", house_count=0))
    imp = analyze_segment(seg, before_date=date(2026, 6, 28), after_date=date(2026, 6, 30))
    assert imp.direction == ImpactDirection.UNCHANGED
    assert imp.ltv_delta == 0.0
