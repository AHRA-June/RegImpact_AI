"""Impact Matrix 테스트 — 6·30 앵커 세그먼트의 엔진 실제 출력 검증.

이 테스트는 매트릭스가 룰엔진 출력을 정확히 반영하는지(하드코딩 아님),
그리고 정직한 escalation(유주택 기준부재)을 은폐하지 않는지 확인한다.
"""
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from regimpact.impact import (  # noqa: E402
    ANCHOR_SEGMENTS,
    DISCOVERY_SEGMENTS,
    ImpactDirection,
    SIX_THIRTY_SEGMENTS,
    build_impact_matrix,
    format_report,
)
from regimpact.impact.matrix import AFTER_DATE, BEFORE_DATE  # noqa: E402


@pytest.fixture(scope="module")
def matrix():
    return build_impact_matrix()


def _row(matrix, segment_id):
    return next(r for r in matrix.rows if r.segment.segment_id == segment_id)


# ── 앵커 세그먼트 기대값 (stitch_review.md 정정표 + 엔진 실제 출력) ──
# (segment_id, ltv_before, ltv_after, direction, reason_code, grandfathering)
ANCHOR_EXPECTATIONS = [
    ("SEG_STD_YONGIN", 0.70, 0.40, ImpactDirection.TIGHTENED, "LTV_REGULATED_40", False),
    ("SEG_FIRSTHOME_HWASEONG", 0.70, 0.70, ImpactDirection.UNCHANGED, "EXCEPTION_FIRST_HOME", False),
    ("SEG_REALDEMAND_GURI", 0.70, 0.60, ImpactDirection.TIGHTENED, "EXCEPTION_REAL_DEMAND", False),
    ("SEG_DISPOSAL_GURI", 0.70, 0.40, ImpactDirection.TIGHTENED, "LTV_REGULATED_40", False),
    ("SEG_GRANDFATHERED_HWASEONG", 0.70, 0.70, ImpactDirection.UNCHANGED,
     "GRANDFATHERED_ACCEPTED_OR_CONTRACT", True),
]


@pytest.mark.parametrize("sid,before,after,direction,reason,gf", ANCHOR_EXPECTATIONS)
def test_anchor_segment_values(matrix, sid, before, after, direction, reason, gf):
    r = _row(matrix, sid)
    assert r.ltv_before == before
    assert r.ltv_after == after
    assert r.direction == direction
    assert reason in r.reason_codes
    assert r.grandfathering is gf


# ── 정직한 escalation: 유주택/다주택의 '기존 LTV'는 기준부재(임의 70% 금지) ──
@pytest.mark.parametrize("sid,after_ltv,reason", [
    ("SEG_MULTI_GURI", 0.0, "LTV_MULTI_HOME_0"),
    ("SEG_OWNER_YONGIN", 0.0, "LTV_OWNER_0"),
])
def test_owner_baseline_gap_is_honest(matrix, sid, after_ltv, reason):
    r = _row(matrix, sid)
    # before는 기준부재 → 수치 없음(임의 채움 금지)
    assert r.ltv_before is None
    assert "검토" in r.before_display
    # after는 규제로 0% 확정
    assert r.ltv_after == after_ltv
    assert reason in r.reason_codes
    assert r.direction == ImpactDirection.BASELINE_GAP
    assert r.high_impact is True


# ── before 평가는 경과규정 이벤트를 제거한다(before에 grandfathering 오적용 금지) ──
def test_before_strips_grandfathering(matrix):
    r = _row(matrix, "SEG_GRANDFATHERED_HWASEONG")
    assert r.before.grandfathering_applied is False   # before는 경과규정 미적용
    assert r.after.grandfathering_applied is True      # after만 경과규정으로 70% 유지
    assert r.ltv_before == r.ltv_after == 0.70          # 값 자체는 동일(종전유지)
    assert r.changed is False


# ── Discovery/Out-of-scope 는 코어 자동판정에서 분리 ──
def test_discovery_rows_are_non_core(matrix):
    disc = matrix.discovery_rows
    assert len(disc) == len(DISCOVERY_SEGMENTS) == 2
    for r in disc:
        assert r.is_core is False
        assert r.direction == ImpactDirection.NON_CORE
        assert r.ltv_before is None and r.ltv_after is None


def test_core_rows_partition(matrix):
    assert len(matrix.core_rows) == len(ANCHOR_SEGMENTS)
    assert len(matrix.rows) == len(SIX_THIRTY_SEGMENTS)
    assert len(matrix.core_rows) + len(matrix.discovery_rows) == len(matrix.rows)


# ── summary 집계 정합성 ──
def test_summary_counts(matrix):
    s = matrix.summary()
    assert s["total_segments"] == 9
    assert s["core_segments"] == 7
    assert s["discovery_segments"] == 2
    assert s["tightened"] == 3       # 무주택·서민실수요·처분조건부
    assert s["unchanged"] == 2       # 생애최초·경과규정
    assert s["baseline_gap"] == 2    # 다주택·유주택
    assert s["grandfathered"] == 1
    assert s["changed"] == s["tightened"] + s["baseline_gap"]  # 5


# ── 방향 파생 로직 단위 검증 ──
def test_delta_pp(matrix):
    assert _row(matrix, "SEG_STD_YONGIN").delta_pp == pytest.approx(-30.0)
    assert _row(matrix, "SEG_REALDEMAND_GURI").delta_pp == pytest.approx(-10.0)
    assert _row(matrix, "SEG_FIRSTHOME_HWASEONG").delta_pp == pytest.approx(0.0)
    assert _row(matrix, "SEG_MULTI_GURI").delta_pp is None  # 기준부재


# ── 시점 파라미터 정합성 ──
def test_dates(matrix):
    assert matrix.before_date == BEFORE_DATE == date(2026, 6, 30)
    assert matrix.after_date == AFTER_DATE == date(2026, 7, 2)


# ── 결정성(determinism): 같은 입력 → 같은 출력 ──
def test_deterministic():
    a = build_impact_matrix().to_dict()
    b = build_impact_matrix().to_dict()
    assert a == b


# ── to_dict 직렬화 계약 ──
def test_to_dict_contract(matrix):
    d = matrix.to_dict()
    assert set(d.keys()) == {"summary", "rows"}
    assert len(d["rows"]) == 9
    row = d["rows"][0]
    for key in (
        "segment_id", "region_label", "borrower_type", "ltv_before", "ltv_after",
        "before_display", "after_display", "delta_pp", "direction", "direction_label",
        "changed", "grandfathering", "review_required", "is_core", "high_impact",
        "applicable_rule_id", "reason_codes", "source_policy_ids", "note",
    ):
        assert key in row


def test_format_report_smoke(matrix):
    out = format_report(matrix)
    assert "Impact Matrix" in out
    assert "다주택" in out
    assert "LTV_REGULATED_40" in out
