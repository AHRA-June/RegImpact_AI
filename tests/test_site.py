"""정적 사이트 — 배포되는 것이 실제로 온전한지 고정한다.

배포는 되돌리기 어렵다. 깨진 링크·빈 페이지·외부 의존이 올라가면 링크를 받은 사람이
먼저 발견한다. 여기서 먼저 잡는다.
"""
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    out = tmp_path_factory.mktemp("site")
    subprocess.run(
        [sys.executable, str(REPO / "tools" / "build_site.py"), "--out", str(out)],
        cwd=REPO, check=True, capture_output=True,
    )
    return {p.name: p.read_text(encoding="utf-8") for p in out.glob("*.html")} | {
        "_dir": out
    }


EXPECTED = {
    "index.html", "regchange.html", "impact_matrix.html", "rule.html",
    "assurance.html", "portfolio.html",
    "validation_report.html", "model_system_card.html", "ai_risk_register.html",
}


def test_all_expected_pages_are_built(site):
    assert EXPECTED <= set(site) - {"_dir"}


def test_nojekyll_is_present(site):
    """없으면 GitHub Pages 가 Jekyll 로 처리하며 밑줄로 시작하는 파일을 버린다."""
    assert (site["_dir"] / ".nojekyll").exists()


# ---------- 링크가 살아 있는가 ----------
def test_every_internal_link_resolves(site):
    pages = {k: v for k, v in site.items() if k != "_dir"}
    missing = []
    for name, html in pages.items():
        for href in re.findall(r'href="([^"#?]+\.html)[^"]*"', html):
            if href not in pages:
                missing.append(f"{name} → {href}")
    assert not missing, f"깨진 링크: {missing}"


def test_landing_links_to_every_screen_and_doc(site):
    index = site["index.html"]
    for target in EXPECTED - {"index.html"}:
        assert f'href="{target}"' in index, f"랜딩에 {target} 링크가 없다"


def test_docs_link_back_home(site):
    for name in ("validation_report.html", "model_system_card.html",
                 "ai_risk_register.html"):
        assert 'href="index.html"' in site[name], f"{name} 에 홈 링크가 없다"


# ---------- 외부 의존이 없는가 ----------
def test_no_external_scripts_or_stylesheets(site):
    """CDN 이 죽으면 화면이 통째로 무너진다 — PR #4 에서 겪은 문제다."""
    bad = []
    for name, html in site.items():
        if name == "_dir":
            continue
        for m in re.findall(r'<(?:script|link)[^>]*(?:src|href)="(https?://[^"]+)"', html):
            if "fonts.googleapis.com" in m or "fonts.gstatic.com" in m:
                continue          # 웹폰트는 실패해도 fallback 스택으로 읽힌다
            bad.append(f"{name}: {m}")
    assert not bad, f"외부 의존: {bad}"


def test_no_page_is_suspiciously_small(site):
    for name, html in site.items():
        if name == "_dir":
            continue
        assert len(html) > 5_000, f"{name} 이 너무 작다 ({len(html)}바이트) — 렌더 실패 의심"


# ---------- 내용이 실제 산출인가 ----------
def test_landing_numbers_come_from_the_pipeline(site):
    from regimpact.report import collect
    ev = collect(generated_at="x")
    index = site["index.html"]
    assert f"{ev.grounding.citation_correctness:.0%}" in index
    assert f"{len(ev.extraction.changes)}건" in index
    assert f"{ev.impact.impact_coverage:.1%}" in index


def test_landing_does_not_overclaim(site):
    """미통과 항목이 있는데 '완전 자동'을 내세우면 안 된다."""
    index = site["index.html"]
    assert "100%가 아닌 것이 이 프로젝트의 요점" in index


def test_report_page_has_toc_and_tables(site):
    html = site["validation_report.html"]
    assert html.count("<table>") >= 15, "표가 렌더되지 않았다"
    assert 'class="toc-2"' in html, "목차가 비었다"


def test_markdown_is_fully_converted(site):
    """마크다운 잔재가 화면에 그대로 나오면 렌더러가 문법을 놓친 것이다."""
    for name in ("validation_report.html", "ai_risk_register.html"):
        body = re.sub(r"<style>.*?</style>", "", site[name], flags=re.S)
        body = re.sub(r"<[^>]+>", "", body)
        assert "|---" not in body, f"{name}: 표 구분선이 남았다"
        assert not re.search(r"^\s*## ", body, re.M), f"{name}: 제목이 남았다"


def test_screens_carry_no_mockup_ltv_values(site):
    """랜딩·화면에 엔진이 모르는 LTV 값이 새어 들어가지 않았는지 재확인."""
    from regimpact import rule_engine
    allowed = {f"{v:.0%}" for v in (
        rule_engine.LTV_BASELINE, rule_engine.LTV_REGULATED_STANDARD,
        rule_engine.LTV_FIRST_HOME, rule_engine.LTV_REAL_DEMAND,
        rule_engine.LTV_OWNER, rule_engine.LTV_MULTI)}
    found = set(re.findall(r"LTV (\d{1,3}%)", site["rule.html"]))
    assert found <= allowed, f"엔진에 없는 LTV: {found - allowed}"
