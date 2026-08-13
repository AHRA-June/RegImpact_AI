"""Impact Matrix 테스트.

검증 포인트:
    - 시행 전/후 temporal diff 가 세그먼트별로 올바른 방향(강화/동일/검토)을 낸다.
    - 예외(생애최초)는 규제 후에도 보호되어 UNCHANGED.
    - 명세에 기준값 없는 경우(非규제 유주택)는 델타를 억지로 만들지 않고 REVIEW 로 표면화.
    - Extractor(effective_from) → Impact Matrix E2E 연결이 시점을 올바로 유도.
    - Impact Matrix 는 룰엔진과 일치(자체 규칙값을 갖지 않음).
"""
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from regimpact import MortgageApplication, evaluate  # noqa: E402
from regimpact.extractor.schema import RegChangeExtraction  # noqa: E402
from regimpact.impact import (  # noqa: E402
    DEFAULT_REGION,
    SIX_THIRTY_SEGMENTS,
    ImpactDirection,
    Segment,
    analyze_from_extraction,
    analyze_impact,
    format_matrix,
)

BEFORE = date(2026, 6, 30)
AFTER = date(2026, 7, 2)


def _matrix():
    return analyze_impact(
        segments=SIX_THIRTY_SEGMENTS,
        region_code=DEFAULT_REGION,
        before_date=BEFORE,
        after_date=AFTER,
    )


def _row(matrix, segment_id):
    return next(r for r in matrix.rows if r.segment.segment_id == segment_id)


# --- 방향·델타 ---------------------------------------------------------------
def test_no_home_tightened_70_to_40():
    """무주택 일반: 非규제 70% → 규제 40% (강화 -30pp)."""
    r = _row(_matrix(), "SEG-01")
    assert r.direction == ImpactDirection.TIGHTENED
    assert r.before_ltv == pytest.approx(0.70)
    assert r.after_ltv == pytest.approx(0.40)
    assert r.delta_ltv == pytest.approx(-0.30)


def test_first_home_unchanged():
    """생애최초: 시행 전 70%(무주택 기준선) → 시행 후 70%(예외) = 동일. 예외 보호."""
    r = _row(_matrix(), "SEG-02")
    assert r.direction == ImpactDirection.UNCHANGED
    assert r.delta_ltv == pytest.approx(0.0)


def test_real_demand_tightened_70_to_60():
    r = _row(_matrix(), "SEG-03")
    assert r.direction == ImpactDirection.TIGHTENED
    assert r.after_ltv == pytest.approx(0.60)
    assert r.delta_ltv == pytest.approx(-0.10)


def test_disposal_one_home_tightened():
    """처분조건부 1주택 = 무주택 기준 → 70% → 40% 강화."""
    r = _row(_matrix(), "SEG-05")
    assert r.direction == ImpactDirection.TIGHTENED
    assert r.after_ltv == pytest.approx(0.40)


# --- 정직성: 기준값 부재 → REVIEW -------------------------------------------
def test_owner_segments_are_review_not_fake_delta():
    """非규제 유주택은 명세에 기준값 없음 → 델타를 만들지 않고 REVIEW."""
    m = _matrix()
    for seg_id in ("SEG-04", "SEG-06"):
        r = _row(m, seg_id)
        assert r.direction == ImpactDirection.REVIEW
        assert r.delta_ltv is None
        assert r.before_ltv is None       # before 가 escalation
        assert r.note is not None          # 사유 노출
        assert "OWNER_BASELINE_UNKNOWN" in r.note


def test_summary_counts():
    m = _matrix()
    s = m.summary()
    assert s[ImpactDirection.TIGHTENED.value] == 3   # 무주택·서민실수요·처분조건부
    assert s[ImpactDirection.UNCHANGED.value] == 1   # 생애최초
    assert s[ImpactDirection.REVIEW.value] == 2      # 비처분1주택·다주택
    assert s[ImpactDirection.LOOSENED.value] == 0


def test_review_required_accessor():
    m = _matrix()
    ids = {r.segment.segment_id for r in m.review_required}
    assert ids == {"SEG-04", "SEG-06"}


# --- 룰엔진 일치(자체 규칙값 미보유) ---------------------------------------
def test_matrix_matches_rule_engine():
    """Impact Matrix 의 before/after 는 룰엔진 직접 판정과 정확히 일치해야 한다."""
    m = _matrix()
    for r in m.rows:
        exp_before = evaluate(r.segment.build(DEFAULT_REGION, BEFORE))
        exp_after = evaluate(r.segment.build(DEFAULT_REGION, AFTER))
        assert r.before.status == exp_before.status
        assert r.before.max_ltv == exp_before.max_ltv
        assert r.after.status == exp_after.status
        assert r.after.max_ltv == exp_after.max_ltv


# --- 시점 경계: 효력일 ±1 --------------------------------------------------
def test_effective_date_boundary():
    """before=6.30(전일) 非규제, after=7.1(효력일) 규제 → 강화 확인."""
    m = analyze_impact(
        segments=[Segment("T", "무주택", dict(house_count=0))],
        region_code=DEFAULT_REGION,
        before_date=date(2026, 6, 30),
        after_date=date(2026, 7, 1),
    )
    r = m.rows[0]
    assert r.direction == ImpactDirection.TIGHTENED
    assert r.before_ltv == pytest.approx(0.70)
    assert r.after_ltv == pytest.approx(0.40)


def test_same_date_all_unchanged():
    """before==after 이면 모든 수치 세그먼트가 UNCHANGED(변경 없음)."""
    m = analyze_impact(
        segments=[Segment("T", "무주택", dict(house_count=0))],
        region_code=DEFAULT_REGION,
        before_date=AFTER,
        after_date=AFTER,
    )
    assert m.rows[0].direction == ImpactDirection.UNCHANGED
    assert m.rows[0].delta_ltv == pytest.approx(0.0)


# --- E2E: Extractor → Impact Matrix ----------------------------------------
def test_analyze_from_extraction_derives_dates():
    """effective_from 에서 before=전일, after=+2일 을 유도한다."""
    extraction = RegChangeExtraction(
        policy_id="FSC_20260630",
        effective_from="2026-07-01",
        target_regions=["구리"],
        changes=[],
    )
    m = analyze_from_extraction(
        extraction,
        segments=SIX_THIRTY_SEGMENTS,
        region_code=DEFAULT_REGION,
    )
    assert m.before_date == date(2026, 6, 30)
    assert m.after_date == date(2026, 7, 3)
    assert m.policy_id == "FSC_20260630"
    # 무주택 일반은 여전히 강화(70→40)로 나와야 함
    assert _row(m, "SEG-01").direction == ImpactDirection.TIGHTENED


def test_analyze_from_extraction_missing_effective_raises():
    extraction = RegChangeExtraction(policy_id="X", effective_from=None, changes=[])
    with pytest.raises(ValueError):
        analyze_from_extraction(extraction, SIX_THIRTY_SEGMENTS, DEFAULT_REGION)


def test_analyze_from_extraction_bad_date_raises():
    extraction = RegChangeExtraction(policy_id="X", effective_from="not-a-date", changes=[])
    with pytest.raises(ValueError):
        analyze_from_extraction(extraction, SIX_THIRTY_SEGMENTS, DEFAULT_REGION)


# --- 리포트 렌더 -------------------------------------------------------------
def test_format_matrix_renders():
    text = format_matrix(_matrix())
    assert "Impact Matrix" in text
    assert "무주택 일반" in text
    assert "-30pp" in text
    assert "검토 필요" in text
