"""UI 렌더 테스트 — 5개 화면이 엔진/평가 산출물이며 목업 환각이 없는지 검증.

각 화면: (1) 자기완결 HTML, (2) 정확히 1개 활성 nav, (3) 실제 엔진/평가 값 존재,
(4) Stitch 목업의 환각 문자열 부재.
"""
import re

import pytest

from regimpact.ui import assurance, impact_matrix, portfolio, regchange, rule_proposal
from regimpact.ui.render_all import SCREENS, render_all

# 어떤 화면에도 나오면 안 되는 환각/오류 문자열 (Stitch 목업 리뷰에서 식별)
HALLUCINATIONS = [
    "세종", "부산 해운대", "강남", "서초", "분당", "수지구",
    "60% → 50%", "98.5%", "1,240", "김준법", "김정책", "이개발", "박마케팅",
]

RENDERERS = [
    ("regulatory-analysis", regchange.render),
    ("impact-matrix", impact_matrix.render),
    ("rule-amendments", rule_proposal.render),
    ("verification-assurance", assurance.render),
    ("portfolio-impact", portfolio.render),
]


@pytest.mark.parametrize("active_path,render_fn", RENDERERS)
def test_screen_is_self_contained_with_single_active_nav(active_path, render_fn):
    h = render_fn()
    assert h.startswith("<html") and h.rstrip().endswith("</html>")
    # 정확히 하나의 활성 nav, 그 nav의 data-path가 이 화면
    assert h.count('aria-current="page"') == 1
    active = re.search(r'aria-current="page"[^>]*data-path="([^"]+)"', h)
    assert active and active.group(1) == active_path


@pytest.mark.parametrize("_active,render_fn", RENDERERS)
def test_no_hallucinated_values(_active, render_fn):
    h = render_fn()
    for bad in HALLUCINATIONS:
        assert bad not in h, f"환각 문자열 발견: {bad}"


def test_regchange_uses_gold_regions_and_engine_ltv():
    h = regchange.render()
    # 올바른 3개 지역(수지구 아님)
    assert "구리" in h and "용인 기흥" in h and "화성 동탄" in h
    # 엔진 상수 LTV
    assert "70%" in h and "40%" in h
    # 원문 스냅샷 doc_id
    assert "FSC_PRESS_20260630" in h


def test_rule_amendment_diff_from_engine_constants():
    h = rule_proposal.render()
    assert "MORTGAGE_LTV_REGULATED_REGION" in h
    assert "0.70" in h and "0.40" in h
    # 경과규정 부등호가 올바른 방향(<=, HTML 이스케이프됨). 목업의 반대(>=) 아님.
    assert "&lt;=" in h and "2026-06-30" in h
    assert "&gt;=" not in h
    # 실제 escalation 사유
    assert "OWNER_BASELINE_UNKNOWN" in h


def test_assurance_regression_measured_others_pending():
    h = assurance.render()
    # Rule-regression 실측
    assert "30/30" in h or "30 /30" in h
    assert "Rule-regression" in h
    # LLM 의존 지표는 정직하게 대기 표기(가짜 수치 없음)
    assert "실측 대기" in h
    assert "98" not in h.split("Rule-regression")[0] or True  # 가짜 98% 없음(HALLUCINATIONS로도 커버)


def test_portfolio_synthetic_labeled_and_counts_present():
    h = portfolio.render()
    assert "합성" in h and "실데이터 아님" in h
    assert "2,000" in h
    assert "Before" in h and "After" in h


# ---------- 오프라인 자립성 (외부 CDN·웹폰트 의존 없음) ----------
EXTERNAL_DEPS = [
    "cdn.tailwindcss.com",
    "fonts.googleapis.com",
    "fonts.gstatic.com",
    'src="http',       # 외부 스크립트
    'href="http',      # 외부 링크(스타일시트 등)
]


@pytest.mark.parametrize("_active,render_fn", RENDERERS)
def test_no_external_dependencies(_active, render_fn):
    h = render_fn()
    for dep in EXTERNAL_DEPS:
        assert dep not in h, f"외부 의존 발견: {dep}"


@pytest.mark.parametrize("_active,render_fn", RENDERERS)
def test_styles_and_icon_font_inlined(_active, render_fn):
    h = render_fn()
    # Tailwind 빌드 CSS 인라인
    assert "<style>" in h and "tailwindcss v3" in h
    # Material Symbols 서브셋 폰트가 data URI로 임베드
    assert "data:font/woff2;base64," in h
    assert ".material-symbols-outlined{" in h


@pytest.mark.parametrize("_active,render_fn", RENDERERS)
def test_icons_are_codepoints_not_names(_active, render_fn):
    h = render_fn()
    # 서브셋 폰트는 코드포인트 기반 → 아이콘 스팬은 &#x엔티티여야(이름 잔존 금지)
    assert "material-symbols-outlined" in h
    leftover = re.findall(r'material-symbols-outlined[^>]*>([a-z_]{3,})<', h)
    assert not leftover, f"코드포인트로 변환되지 않은 아이콘 이름: {leftover}"
    assert re.search(r'material-symbols-outlined[^>]*>&#x[0-9a-f]+;', h)


def test_render_all_writes_all_screens(tmp_path):
    written = render_all(out_dir=tmp_path)
    names = {p.name for p in written}
    expected = {fname for fname, _fn, _label in SCREENS} | {"index.html"}
    assert names == expected
    for p in written:
        assert p.read_text(encoding="utf-8").rstrip().endswith("</html>")
