"""Impact Matrix 테스트 — Before/After 관통(E2E)이 세그먼트별로 정확한지 검증.

이 테스트는 룰엔진 자체가 아니라 '두 시점 델타 계산 + 방향 분류 + Discovery 분리'가
정확한지를 회귀 fixture로 고정한다. LTV 값의 진실은 test_rule_engine.py가 담당한다.
"""
from datetime import date

from regimpact.impact import (
    AFTER_DATE,
    BEFORE_DATE,
    ImpactDirection,
    Segment,
    build_impact_matrix,
    format_matrix,
    render_impact_matrix_html,
)


def _rows_by_key(matrix):
    return {r.key: r for r in matrix.rows}


# ---------- 기본 관통 ----------
def test_matrix_builds_all_segments():
    m = build_impact_matrix()
    assert len(m.rows) == 9
    assert m.before_date == BEFORE_DATE == date(2026, 6, 30)
    assert m.after_date == AFTER_DATE == date(2026, 7, 2)


def test_no_home_standard_downgrades_70_to_40():
    r = _rows_by_key(build_impact_matrix())["NO_HOME_STANDARD"]
    assert r.before_ltv == 0.70
    assert r.after_ltv == 0.40
    assert r.direction == ImpactDirection.DOWNGRADE
    assert r.delta == -0.30
    assert "LTV_REGULATED_40" in r.reason_codes


def test_first_home_unchanged():
    r = _rows_by_key(build_impact_matrix())["FIRST_HOME"]
    assert r.before_ltv == 0.70 and r.after_ltv == 0.70
    assert r.direction == ImpactDirection.UNCHANGED
    assert r.delta == 0.0


def test_real_demand_downgrades_to_60():
    r = _rows_by_key(build_impact_matrix())["REAL_DEMAND"]
    assert r.after_ltv == 0.60
    assert r.direction == ImpactDirection.DOWNGRADE


# ---------- 정직성: 非규제 유주택 기준선 명세부재 ----------
def test_owner_before_undefined_after_new_restriction():
    """유주택 before 는 명세부재(검토) → after 0% 는 NEW_RESTRICTION (fabricate 금지)."""
    r = _rows_by_key(build_impact_matrix())["OWNER_1_NON_DISPOSAL"]
    assert r.before_ltv is None           # 명세부재 → 수치 없음
    assert r.after_ltv == 0.0
    assert r.direction == ImpactDirection.NEW_RESTRICTION
    assert r.delta is None                # 한쪽이 비수치면 델타 없음


def test_multi_home_new_restriction():
    r = _rows_by_key(build_impact_matrix())["MULTI_HOME"]
    assert r.before_ltv is None
    assert r.after_ltv == 0.0
    assert r.direction == ImpactDirection.NEW_RESTRICTION
    assert "LTV_MULTI_HOME_0" in r.reason_codes


def test_disposal_1home_treated_as_no_home():
    r = _rows_by_key(build_impact_matrix())["DISPOSAL_1_HOME"]
    assert r.before_ltv == 0.70 and r.after_ltv == 0.40
    assert r.direction == ImpactDirection.DOWNGRADE


# ---------- 경과규정 보호 + counterfactual ----------
def test_grandfathered_holds_70_with_counterfactual_40():
    r = _rows_by_key(build_impact_matrix())["GRANDFATHERED_CONTRACT"]
    assert r.grandfathering_applied is True
    assert r.after_ltv == 0.70                 # 종전규정 유지
    assert r.direction == ImpactDirection.UNCHANGED
    assert r.counterfactual_ltv == 0.40        # 보호 없었다면 하향됐을 값


# ---------- Discovery Scope 분리 ----------
def test_discovery_scope_separated():
    m = build_impact_matrix()
    disc_keys = {r.key for r in m.discovery_rows}
    assert disc_keys == {"POLICY_LOAN", "JEONSE_LOAN"}
    for r in m.discovery_rows:
        assert r.direction == ImpactDirection.DISCOVERY
        assert r.is_discovery
    # core_rows 와 discovery_rows 는 겹치지 않고 전체를 이룬다
    assert len(m.core_rows) + len(m.discovery_rows) == len(m.rows)
    assert len(m.core_rows) == 7


# ---------- 요약 지표 ----------
def test_summary_counts():
    s = build_impact_matrix().summary
    assert s["TOTAL"] == 9
    assert s["CORE"] == 7
    assert s["DOWNGRADE"] == 3          # NO_HOME, REAL_DEMAND, DISPOSAL
    assert s["NEW_RESTRICTION"] == 2    # OWNER, MULTI
    assert s["UNCHANGED"] == 2          # FIRST_HOME, GRANDFATHERED
    assert s["DISCOVERY"] == 2
    assert s["GRANDFATHERED"] == 1
    # 방향 카운트 합(Discovery 포함) == 전체
    direction_total = sum(s[d.value] for d in ImpactDirection)
    assert direction_total == s["TOTAL"]


# ---------- 커스텀 세그먼트 (재사용성) ----------
def test_custom_segment_upgrade_direction():
    """엔진값이 오르는 인위적 방향도 분류되는지(회귀 안전망)."""
    # 시점을 뒤집으면(before=시행후, after=시행전) 무주택 일반은 40→70 상향으로 관측된다.
    seg = Segment(
        key="NO_HOME_STANDARD",
        borrower_type="무주택 일반",
        region_code="GURI",
        profile=dict(house_count=0),
    )
    m = build_impact_matrix(
        segments=[seg], before_date=date(2026, 7, 2), after_date=date(2026, 6, 30)
    )
    r = m.rows[0]
    assert r.before_ltv == 0.40 and r.after_ltv == 0.70
    assert r.direction == ImpactDirection.UPGRADE


# ---------- format 스모크 ----------
def test_format_matrix_renders():
    out = format_matrix(build_impact_matrix())
    assert "Impact Matrix" in out
    assert "Discovery Scope" in out
    assert "요약:" in out


# ---------- HTML 렌더 (UI = 엔진 산출물) ----------
def test_html_render_is_engine_backed_not_hardcoded():
    h = render_impact_matrix_html(build_impact_matrix())
    # 자기완결 페이지
    assert h.startswith("<html") and h.rstrip().endswith("</html>")
    # 실제 엔진 값/근거코드가 표에 존재
    assert "LTV_REGULATED_40" in h
    assert "LTV_MULTI_HOME_0" in h
    assert "DISCOVERY_POLICY_LOAN" in h
    # 정직성 신호: 명세부재·종전유지(counterfactual) 노출
    assert "명세부재" in h
    assert "종전유지" in h
    # 엔진 산출 근거 스트립
    assert "rule_engine v1" in h
    # 과거 환각 값은 없어야 한다 (Stitch 목업의 "60% → 50%")
    assert "60% → 50%" not in h
    assert "50% 하향" not in h


def test_html_render_reflects_row_count():
    m = build_impact_matrix()
    h = render_impact_matrix_html(m)
    # 각 세그먼트의 차주유형이 화면에 렌더된다
    for r in m.rows:
        assert r.borrower_type in h
