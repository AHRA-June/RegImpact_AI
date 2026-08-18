"""Streamlit 검증 콘솔 스모크 테스트.

UI 코드가 엔진을 잘못 호출하면(필드 매핑 오류·라벨 오타 등) 테스트 없이는 배포 후에야 드러난다.
AppTest로 실제 스크립트를 실행해 핵심 시나리오의 화면 값이 엔진 판정과 일치하는지 확인한다.
streamlit 미설치 환경(코어 테스트만 돌릴 때)에서는 skip.
"""
from __future__ import annotations

import pytest

pytest.importorskip("streamlit", reason="streamlit 미설치 — UI 테스트 skip")

from pathlib import Path  # noqa: E402

from streamlit.testing.v1 import AppTest  # noqa: E402

APP = str(Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py")


def _run() -> AppTest:
    at = AppTest.from_file(APP, default_timeout=120).run()
    assert not at.exception, [str(e.value) for e in at.exception]
    return at


def _ltv(at: AppTest) -> str:
    return next(m.value for m in at.metric if m.label == "적용 LTV")


def _status(at: AppTest) -> str:
    return next(m.value for m in at.metric if m.label == "판정 상태")


def test_app_runs_and_renders_five_tabs():
    at = _run()
    assert at.title[0].value.startswith("⚖️")
    assert len(at.tabs) == 5


def test_policy_tab_shows_current_and_upcoming_versions():
    """정책 버전 탭이 Policy Version DB 를 읽어 현재/예정을 보여준다."""
    at = _run()
    labels = [m.label for m in at.metric]
    assert "현재 유효 정책" in labels
    assert "시행 예정" in labels
    current = next(m for m in at.metric if m.label == "현재 유효 정책")
    assert current.value == "FSC_20260630"      # 기준 시점 2026-07-02


def test_impact_tab_reports_e2e_headline():
    """E2E 탭이 파이프라인을 실제로 돌려 헤드라인 지표를 낸다."""
    at = _run()
    labels = [m.label for m in at.metric]
    assert "영향률 (경과규정 미해당 층)" in labels
    assert "자동판정 거부" in labels
    assert any("한도 변화" in lb for lb in labels)


def test_default_is_regulated_standard_40():
    """기본값(구리시·2026-07-02·무주택) = 규제지역 표준 40%."""
    at = _run()
    assert _ltv(at) == "40%"
    assert _status(at) == "판정 확정"


def test_first_home_buyer_exception_70():
    at = _run()
    cb = next(c for c in at.checkbox if c.label == "생애최초 구입 (P5)")
    cb.check().run()
    assert not at.exception
    assert _ltv(at) == "70%"


def test_policy_loan_routes_to_discovery():
    at = _run()
    cb = next(c for c in at.checkbox if c.label.startswith("정책대출"))
    cb.check().run()
    assert not at.exception
    assert _status(at) == "Discovery (수동)"
    assert _ltv(at) == "—"


def test_seoul_gangnam_shows_regulated_40_in_app():
    """UI에서 서울 강남구를 고르면 40%여야 한다(70%로 보이던 사고의 회귀선)."""
    at = _run()
    region = next(sb for sb in at.selectbox if sb.label.startswith("지역"))
    region.set_value("SEOUL_GANGNAM").run()
    assert not at.exception, [str(e.value) for e in at.exception]
    assert _ltv(at) == "40%"


def test_non_regulated_region_shows_baseline_70_in_app():
    at = _run()
    region = next(sb for sb in at.selectbox if sb.label.startswith("지역"))
    region.set_value("ULSAN_NAM").run()
    assert not at.exception
    assert _ltv(at) == "70%"


def test_non_capital_non_regulated_owner_shows_60_in_app():
    """Q9 확정 — 울산 남구 유주택 1 → 60% (예전엔 '사람 검토'였다)."""
    at = _run()
    next(sb for sb in at.selectbox if sb.label.startswith("지역")).set_value("ULSAN_NAM").run()
    at.select_slider[0].set_value(1).run()
    assert not at.exception, [str(e.value) for e in at.exception]
    assert _ltv(at) == "60%"


def test_capital_non_regulated_multi_home_shows_0_in_app():
    """Q10 확정 — 인천 연수구 다주택 → 비규제여도 0%."""
    at = _run()
    next(sb for sb in at.selectbox if sb.label.startswith("지역")).set_value("INCHEON_YEONSU").run()
    at.select_slider[0].set_value(2).run()
    assert not at.exception
    assert _ltv(at) == "0%"


def test_region_selectbox_offers_whole_country():
    at = _run()
    region = next(sb for sb in at.selectbox if sb.label.startswith("지역"))
    # AppTest 의 .options 는 format_func 가 적용된 표시 라벨을 준다.
    labels = region.options
    assert len(labels) > 200
    for label in ("서울특별시 강남구 · 투기과열", "서울특별시 노원구 · 투기과열",
                  "경기도 구리시 · 투기과열", "인천광역시 연수구 · 비규제",
                  "울산광역시 남구 · 비규제", "제주특별자치도 제주시 · 비규제"):
        assert label in labels


def test_regression_tab_reports_full_pass_rate():
    at = _run()
    rate = next(m.value for m in at.metric if m.label == "Rule-regression Pass Rate")
    assert rate == "100%"
