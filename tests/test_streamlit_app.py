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


def test_app_runs_and_renders_three_tabs():
    at = _run()
    assert at.title[0].value.startswith("⚖️")
    assert len(at.tabs) == 3


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


def test_regression_tab_reports_full_pass_rate():
    at = _run()
    rate = next(m.value for m in at.metric if m.label == "Rule-regression Pass Rate")
    assert rate == "100%"
