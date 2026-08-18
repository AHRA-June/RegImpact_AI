"""UI grounding 테스트 — 화면에 찍힌 값이 실제 엔진 출력에서 왔는지 검증한다.

배경: Stitch 1차 목업(2026-08-10)은 디자인은 좋았으나 도메인 데이터를 환각했다
(지역을 세종·부산·강남·분당으로, LTV 60%→50%, 경과규정 부등호 반대). 사람 리뷰로 겨우 잡았다.
이제 UI가 코드에서 생성되므로 **그 사고를 테스트로 고정한다** — Citation grounding이
LLM 인용을 원문에 대조하듯, 여기서는 UI 표시값을 엔진 출력에 대조한다.
"""
import json
import re
from pathlib import Path

import pytest

from regimpact import rule_engine
from regimpact.extractor.evaluate import check_citation_grounding, score_against_gold
from regimpact.extractor.schema import RegChangeExtraction
from regimpact.grandfathering import CUTOFF
from regimpact.impact import analyze_portfolio, build_impact_matrix, build_portfolio
from regimpact.impact.portfolio import CONTROL_REGION, TARGET_REGIONS
from regimpact.tc_generator import run_regression
from regimpact.ui import NAV, TAILWIND_CONFIG, render_site, write_site

REPO = Path(__file__).resolve().parent.parent
RUN = REPO / "docs" / "eval" / "runs" / "run_cli_sonnet5_v2.json"
GOLD = REPO / "docs" / "eval" / "regchange_gold_6_30.json"
STITCH_EXPORT = REPO / "docs" / "ui" / "stitch_export" / "_1" / "code.html"

# 2026-08-10 Stitch 환각 사고에서 실제로 나왔던 지역명 — 다시 나타나면 실패
HALLUCINATED_REGIONS = ("세종", "부산", "해운대", "강남", "서초", "분당", "SEJONG", "BUSAN")


@pytest.fixture(scope="module")
def site():
    """저장된 실제 실행 기록으로 5개 화면을 렌더한다 (LLM 호출 0회)."""
    payload = json.loads(RUN.read_text(encoding="utf-8"))
    extraction = RegChangeExtraction.from_dict(payload["extraction"])
    sources = {
        doc: (REPO / "docs" / "sources" / "raw" / f).read_text(encoding="utf-8")
        for doc, f in (
            ("FSC_PRESS_20260630", "fsc_press_20260630.txt"),
            ("MOLIT_PRESS_20260630", "molit_press_20260630.txt"),
            ("FAQ_20260630", "faq_20260630.txt"),
        )
    }
    grounding = check_citation_grounding(extraction, sources)
    scored = score_against_gold(extraction, json.loads(GOLD.read_text(encoding="utf-8")))
    impact = analyze_portfolio(build_portfolio(size=600, seed=101), seed=101)
    regression = run_regression()
    matrix = build_impact_matrix(extraction, impact, grounding=grounding, regression=regression)
    pages = render_site(
        extraction=extraction, grounding=grounding, scored=scored,
        impact=impact, matrix=matrix, regression=regression,
    )
    return {
        "pages": pages, "extraction": extraction, "impact": impact,
        "matrix": matrix, "regression": regression, "grounding": grounding,
    }


def _all_html(site) -> str:
    return "\n".join(site["pages"].values())


# ------------------------------------------------------- ★ UI grounding (환각 회귀)

def test_no_hallucinated_region_names_anywhere(site):
    """Stitch가 지어냈던 지역명이 어느 화면에도 나오면 안 된다."""
    html = _all_html(site)
    found = [r for r in HALLUCINATED_REGIONS if r in html]
    assert not found, f"환각 지역명이 UI에 다시 나타났다: {found}"


def test_only_engine_known_region_codes_are_displayed(site):
    """화면에 뜨는 지역코드는 추출 결과 또는 포트폴리오 실제 지역이어야 한다."""
    allowed = set(site["extraction"].target_regions) | set(TARGET_REGIONS) | {CONTROL_REGION}
    shown = set(re.findall(r"\b[A-Z]{4,}(?:_[A-Z]+)*\b", _all_html(site)))
    # reason_code·상태 라벨 등 지역이 아닌 대문자 토큰은 제외
    region_like = {t for t in shown if t in allowed or t.endswith(("SI", "GU"))}
    assert region_like <= allowed, f"근거 없는 지역코드: {region_like - allowed}"


def test_wrong_ltv_transition_from_stitch_incident_is_absent(site):
    """Stitch가 찍었던 '60% → 50%'는 존재하지 않는 값이다."""
    html = _all_html(site)
    for bad in ("60% → 50%", "60%→50%", "60% -> 50%"):
        assert bad not in html


def test_ltv_values_match_engine_constants(site):
    """Rule 화면의 LTV는 엔진 상수(=사람 확정 명세)와 일치해야 한다."""
    rule_html = site["pages"]["rule.html"]
    assert f"{rule_engine.LTV_BASELINE:.0%}" in rule_html
    assert f"{rule_engine.LTV_REGULATED_STANDARD:.0%}" in rule_html
    assert f"{rule_engine.LTV_REAL_DEMAND:.0%}" in rule_html
    assert f"{rule_engine.LTV_BASELINE:.2f}" in rule_html      # 코드 블록


def test_rule_page_has_no_ltv_value_outside_engine_constants(site):
    """Rule 화면 코드 블록의 모든 LTV 값은 엔진 상수 집합 안에 있어야 한다.

    `test_ltv_values_match_engine_constants`는 "엔진 값이 화면에 있는가"만 본다. 그것만으로는
    화면 어딘가에 하드코딩된 **여분의** 값이 남아 있어도 통과한다(변이 테스트로 확인함).
    이 테스트는 반대 방향 — 화면에 엔진이 모르는 값이 있으면 실패한다.
    """
    allowed = {
        f"{v:.2f}" for v in (
            rule_engine.LTV_BASELINE, rule_engine.LTV_REGULATED_STANDARD,
            rule_engine.LTV_FIRST_HOME, rule_engine.LTV_REAL_DEMAND,
            rule_engine.LTV_OWNER, rule_engine.LTV_MULTI,
        )
    }
    found = set(re.findall(r"return (0\.\d{2})", site["pages"]["rule.html"]))
    assert found, "코드 블록에서 LTV 값을 찾지 못했다 — 테스트가 무력화됐는지 확인"
    assert found <= allowed, f"엔진 상수에 없는 값이 UI에 하드코딩됨: {found - allowed}"


def test_grandfathering_inequality_direction_is_correct(site):
    """Stitch는 부등호를 반대로 찍었다(>=). 컷오프는 '까지'이므로 <= 여야 한다."""
    rule_html = site["pages"]["rule.html"]
    assert f"&lt;= GRANDFATHERING_CUTOFF" in rule_html or "&lt;=" in rule_html
    assert f'&gt;= &quot;{CUTOFF.isoformat()}&quot;' not in rule_html
    assert CUTOFF.isoformat() in rule_html


# ------------------------------------------------------------- 수치가 실제 출력인가

def test_portfolio_numbers_come_from_the_report(site):
    html, impact = site["pages"]["portfolio.html"], site["impact"]
    assert f"{len(impact.reduced):,}건" in html
    assert f"{impact.undecidable_count:,}건" in html
    assert f"{impact.impact_unknown_count:,}건" in html
    assert f"{impact.grandfathered_count:,}건" in html
    assert f"seed={impact.seed}" in html


def test_portfolio_page_separates_decision_from_impact_coverage(site):
    """유주택 고객을 '처리 불가'로 묶어 보이게 하지 않는다 — 두 커버리지를 따로 보여준다."""
    html, impact = site["pages"]["portfolio.html"], site["impact"]
    assert f"{impact.decision_coverage:.1%}" in html
    assert f"{impact.impact_coverage:.1%}" in html
    assert "심사 판정" in html and "영향 측정" in html


def test_regression_numbers_come_from_the_report(site):
    html, reg = site["pages"]["assurance.html"], site["regression"]
    assert f"{reg.pass_rate:.0%}" in html
    assert f"{reg.total}케이스" in html
    for cat, (passed, total, _) in reg.pass_rate_by_category().items():
        assert f"{passed}/{total}" in html


def test_extraction_count_and_effective_date_come_from_extraction(site):
    html, ext = site["pages"]["regchange.html"], site["extraction"]
    assert f"{len(ext.changes)}건" in html
    assert ext.effective_from in html
    for region in ext.target_regions:
        assert region in html


def test_every_extracted_change_is_rendered(site):
    """추출된 항목을 화면에서 조용히 누락시키지 않는다."""
    html = site["pages"]["regchange.html"]
    import html as _h
    for c in site["extraction"].changes:
        assert _h.escape(c.summary, quote=True) in html


def test_matrix_page_shows_every_row_and_all_phases(site):
    html, matrix = site["pages"]["impact_matrix.html"], site["matrix"]
    import html as _h
    for row in matrix.rows:
        assert _h.escape(row.area, quote=True) in html
    for phase in {r.phase for r in matrix.rows}:
        assert _h.escape(phase.value, quote=True) in html


def test_human_review_reasons_are_all_surfaced(site):
    """자동/사람 경계가 화면에서 사라지면 이 UI의 의미가 없다."""
    html, matrix = site["pages"]["impact_matrix.html"], site["matrix"]
    import html as _h
    assert matrix.human_review_rows
    for row in matrix.human_review_rows:
        assert _h.escape(row.human_review_reason, quote=True) in html


def test_undefined_thresholds_are_shown_as_tbd_not_invented(site):
    """metrics_spec의 임계값이 미확정이면 화면도 TBD로 정직하게 표시한다."""
    assert "TBD" in site["pages"]["assurance.html"]


def test_missed_exception_is_escalated_not_hidden(site):
    """골드 대비 놓친 예외가 있으면 Assurance 화면 escalation에 떠야 한다."""
    html = site["pages"]["assurance.html"]
    assert "Escalation" in html
    assert "real_demand" in html          # 현재 실측에서 놓친 예외


# ----------------------------------------------------------------- 디자인·안전성

def test_tailwind_config_matches_stitch_export_verbatim():
    """디자인 토큰이 Stitch 산출물에서 표류하지 않았는지 확인."""
    stitch = STITCH_EXPORT.read_text(encoding="utf-8")
    cfg = re.search(
        r'<script id="tailwind-config">tailwind\.config=(\{.*?\})</script>', stitch, re.DOTALL
    ).group(1)
    assert TAILWIND_CONFIG == cfg


def test_every_page_links_to_every_other_page(site):
    for name, html in site["pages"].items():
        for href, label, _ in NAV:
            assert f'href="{href}"' in html, f"{name}에 {href} 링크 없음"
            assert label in html


def test_pages_are_self_contained_offline(site):
    """네트워크 없이 열어도 디자인이 유지돼야 한다.

    Stitch export는 `cdn.tailwindcss.com`의 런타임 JIT에 의존해서, 오프라인에서는 스타일이
    통째로 사라진다(스크립트 미로딩 = 클래스 미정의). 생성 화면은 같은 토큰에서 만든 정적 CSS를
    인라인하므로 외부 요청이 웹폰트 하나뿐이고, 그마저 실패해도 시스템 폰트로 읽힌다.
    """
    html = _all_html(site)
    assert "cdn.tailwindcss.com" not in html, "런타임 CDN 의존이 다시 들어왔다"
    assert "<script src=" not in html, "외부 스크립트 의존"
    hosts = set(re.findall(r"https://([a-z0-9.\-]+)/", html))
    assert hosts <= {"fonts.googleapis.com"}, f"예상 밖 외부 호스트: {hosts}"
    assert "<style>" in html


def test_every_class_used_has_a_css_rule(site):
    """마크업에 쓴 클래스가 CSS에 없으면 그 부분만 조용히 무스타일이 된다."""
    from regimpact.ui.theme import CSS

    used = set()
    for html in site["pages"].values():
        for group in re.findall(r'class="([^"]*)"', html):
            used.update(group.split())
    defined = {d.replace("\\", "") for d in re.findall(r"\.((?:[\w\-]|\\.)+)", CSS)}
    missing = {c for c in used if c not in defined and not c.startswith("phase-")}
    assert not missing, f"CSS 규칙이 없는 클래스: {sorted(missing)}"


def test_css_is_generated_from_stitch_tokens():
    """CSS 색·타이포가 Stitch 토큰에서 실제로 나왔는지 (정규식이 조용히 깨지면 무채색이 된다)."""
    from regimpact.ui.theme import CSS, _COLORS, _FONT_SIZES

    assert len(_COLORS) > 30 and len(_FONT_SIZES) >= 6
    assert _COLORS["primary"] == "#022448"          # Institutional Navy (DESIGN.md)
    for name, hexv in _COLORS.items():
        assert f".bg-{name}{{background-color:{hexv}}}" in CSS


def test_extracted_text_is_html_escaped(site):
    """추출 텍스트는 원문에서 오므로 이스케이프 없이 넣으면 안 된다."""
    from regimpact.ui.pages import regchange_page

    ext = RegChangeExtraction.from_dict({
        "policy_id": "P", "effective_from": "2026-07-01", "target_regions": ["GURI"],
        "changes": [{
            "category": "LTV", "summary": "<script>alert(1)</script>",
            "before": None, "after": None,
            "citation": {"source_doc_id": "D1", "quote": "<img onerror=x>"},
            "confidence": 0.9,
        }],
    })
    g = check_citation_grounding(ext, {"D1": "<img onerror=x>"})
    s = score_against_gold(ext, {"required_changes": [], "exceptions": []})
    html = regchange_page(ext, g, s)
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html


def test_pages_are_wellformed_documents(site):
    for name, html in site["pages"].items():
        assert html.startswith("<!DOCTYPE html>"), name
        assert html.rstrip().endswith("</html>"), name
        assert html.count("<body") == 1 and html.count("</body>") == 1, name


def test_rendering_is_deterministic(site):
    """같은 입력 → 같은 HTML. 스크린샷·리뷰 diff가 의미를 가지려면 필수."""
    again = render_site(
        extraction=site["extraction"], grounding=site["grounding"],
        scored=score_against_gold(site["extraction"],
                                  json.loads(GOLD.read_text(encoding="utf-8"))),
        impact=site["impact"], matrix=site["matrix"], regression=site["regression"],
    )
    assert again == site["pages"]


def test_write_site_emits_all_pages_and_index(site, tmp_path):
    written = write_site(site["pages"], tmp_path)
    names = {p.name for p in written}
    assert names == set(site["pages"]) | {"index.html"}
    assert "regchange.html" in (tmp_path / "index.html").read_text(encoding="utf-8")
