"""정적 사이트 — 배포되는 것이 실제로 온전한지 고정한다.

배포는 되돌리기 어렵다. 깨진 링크·빈 페이지·외부 의존이 올라가면 링크를 받은 사람이
먼저 발견한다. 여기서 먼저 잡는다.
"""
import os
import re
import shutil
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
    "assurance.html", "portfolio.html", "sources.html",
    "validation_report.html", "validation_summary.html",
    "model_system_card.html", "ai_risk_register.html",
    "graph.html", "search.html",
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


def test_every_page_has_the_same_global_nav(site):
    """홈 버튼이 없고 메뉴가 화면마다 다르다는 리뷰(2026-08-19)를 고정한다.

    랜딩(=홈)을 제외한 모든 페이지는 같은 사이드바를 쓴다 — 홈 링크와
    전 화면·전 문서 링크가 어느 페이지에서든 보여야 한다.
    """
    from regimpact.ui.theme import NAV
    for name, html in site.items():
        if name in ("_dir", "index.html"):
            continue
        for href, label, _ in NAV:
            assert f'href="{href}"' in html, f"{name} 의 메뉴에 {href} 가 없다"
        assert 'href="index.html"' in html, f"{name} 에 홈 버튼이 없다"


def test_sources_page_hashes_come_from_real_files(site):
    """문서 등록 화면의 스냅샷 해시는 손으로 적은 값이 아니라 실제 파일에서 계산된다."""
    import hashlib
    html = site["sources.html"]
    originals = REPO / "docs" / "sources" / "original"
    files = list(originals.iterdir())
    assert files, "원본 스냅샷 파일이 없다"
    for f in files:
        digest = hashlib.sha256(f.read_bytes()).hexdigest()
        assert digest in html, f"{f.name} 의 실제 SHA-256 이 화면에 없다"


def test_summary_numbers_come_from_the_pipeline(site):
    """1페이지 요약도 본문 보고서와 같은 규칙 — 수치는 전부 evidence 에서."""
    from regimpact.report import collect
    # 사이트 빌드와 같은 조건으로 — node 가 있으면 JS 포팅 대조가 측정돼 통과 수가 달라진다
    agreement = 1.0 if shutil.which("node") else None
    ev = collect(generated_at="x", js_port_agreement=agreement)
    html = site["validation_summary.html"]
    s = ev.scorecard.summary()
    assert f"{s['passed']}/{s['total']}" in html
    assert f"{len(ev.impact.reduced):,}건" in html
    assert f"{ev.impact.impact_coverage:.1%}" in html
    assert f"{ev.regression.total}케이스" in html


def test_summary_shows_gaps_not_only_scores(site):
    """요약이 좋은 것만 추리면 요약이 곧 과장이다 — 한계가 점수와 함께 실려야 한다."""
    html = site["validation_summary.html"]
    assert "부족한 것" in html
    assert "미개봉" in html                      # LOCKED/CHALLENGE 미평가
    assert "독립 벤치마크가 아니다" in html       # 골드셋 한계
    assert "미측정" in html                      # 측정 불가 지표를 통과로 치지 않는다


def test_graph_page_carries_provenance(site):
    """그래프 화면의 관계마다 출처가 실려 있어야 한다 — 없으면 LLM 그래프와 구분이 안 된다."""
    html = site["graph.html"]
    for prov in ("정책 버전 DB", "룰엔진 상수 diff", "고객 영향 실측", "독립 명세 오라클"):
        assert prov in html, f"그래프에 출처 '{prov}' 가 없다"


def test_search_page_shows_measured_recall_and_misses(site):
    """검색 화면은 recall 실측과 **못 찾은 인용**을 함께 싣는다 — 좋은 숫자만 실으면 과장."""
    from regimpact.extractor.sources import load_sources
    from regimpact.retrieval import BM25Index, chunk_sources, citation_recall
    src = load_sources()
    rep = citation_recall(BM25Index(chunk_sources(src)), src)
    html = site["search.html"]
    for k in rep.ks:
        assert f"recall@{k}" in html
    assert f"{rep.recall(5):.0%}" in html
    assert f"못 찾은 인용 {len(rep.misses_at_max_k)}건" in html
    for m in rep.misses_at_max_k:
        assert m.item_id in html, f"미적중 {m.item_id} 이 화면에 없다"


def test_search_js_port_matches_python(site):
    """검색 JS 포팅본 ↔ Python 대조 — 룰엔진 포팅 대조와 같은 통제."""
    if shutil.which("node") is None:
        pytest.skip("node 없음 — CI 에서는 반드시 돈다")
    r = subprocess.run(
        ["node", str(REPO / "tools" / "verify_search_port.mjs"),
         str(site["_dir"] / "search_fixtures.json")],
        cwd=REPO, capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr or r.stdout


def test_search_page_does_not_pretend_to_be_full_rag(site):
    """생성(LLM)은 정적 페이지에서 실행되지 않는다 — 실행하는 척 금지."""
    html = site["search.html"]
    assert "검색 절반" in html
    assert "run_retrieval_eval" in html


def test_sources_page_does_not_pretend_to_extract(site):
    """정적 페이지가 추출(LLM)·확정(사람)을 실행하는 척하면 그게 곧 환각이다."""
    html = site["sources.html"]
    assert "run_extractor" in html, "다음 단계 CLI 안내가 없다"
    assert "LOCKED" in html, "사람 확정(LOCKED §4) 안내가 없다"


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


# ---------- JS 포팅본 대조 ----------
def test_js_port_matches_python_engine(site):
    """화면에 두 번째 룰 구현을 두는 것 자체가 위험이다 — 그 위험을 대조로 상쇄한다.

    이 테스트가 없으면 JS 가 조용히 갈라져도 아무도 모르고, 화면만 거짓말을 한다.
    """
    if shutil.which("node") is None:
        pytest.skip("node 없음 — CI 에서는 반드시 돈다")
    r = subprocess.run(
        ["node", str(REPO / "tools" / "verify_js_port.mjs"),
         str(site["_dir"] / "fixtures.json")],
        cwd=REPO, capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr or r.stdout


def test_playground_is_built_and_linked(site):
    assert "playground.html" in site
    assert 'href="playground.html"' in site["index.html"]


def test_playground_has_no_hardcoded_ltv(site):
    """규칙 값은 픽스처에서 읽어야 한다 — JS 에 적으면 엔진이 바뀌어도 화면이 안 따라온다."""
    engine = (REPO / "src" / "regimpact" / "ui" / "static" / "engine.js").read_text(
        encoding="utf-8")
    code = re.sub(r"/\*[\s\S]*?\*/", "", engine)
    code = re.sub(r"//.*$", "", code, flags=re.M)
    assert not re.findall(r"(?<![\w.])0\.\d+", code), "engine.js 에 LTV 리터럴이 있다"


def test_playground_shows_the_rule_trace(site):
    """값만 보여주면 검증 시스템의 화면이 아니다 — 어디서 멈췄는지가 있어야 한다."""
    html = site["playground.html"]
    for rule_id in ("P0c", "P0d", "P1", "P7"):
        assert rule_id in html


# ---------- README 의 문서 지도가 실재하는가 ----------
def test_readme_paths_exist():
    """문서 지도에 없는 파일을 적어두면 처음 오는 사람이 거기서 막힌다."""
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    missing = [
        p for p in re.findall(r"`((?:docs|src|tests|tools|examples)/[^`]*)`", readme)
        if not (REPO / p).exists()
    ]
    assert not missing, f"README 가 가리키는 경로가 없다: {sorted(set(missing))}"


def test_readme_commands_exist():
    """실행 예시가 없는 파일을 가리키면 첫 2분에서 실패한다."""
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    scripts = re.findall(r"python ((?:examples|tools)/[\w_]+\.py)", readme)
    assert scripts, "실행 예시를 찾지 못했다 — 테스트가 무력화됐는지 확인"
    missing = [s for s in scripts if not (REPO / s).exists()]
    assert not missing, f"README 실행 예시의 스크립트가 없다: {missing}"


def test_readme_site_links_match_built_pages(site):
    """랜딩에서 링크한 페이지를 README 도 가리킨다 — 배포 후 404 가 나면 안 된다."""
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    linked = set(re.findall(r"github\.io/RegImpact_AI/([\w_]+\.html)", readme))
    assert linked, "README 에 사이트 링크가 없다"
    missing = linked - set(site) - {"_dir"}
    assert not missing, f"README 가 가리키는 페이지가 빌드되지 않는다: {missing}"


def test_playground_shows_verdict_before_form_on_mobile(site):
    """모바일에서 결과가 폼 아래면 입력을 바꿔도 화면 밖이라 안 보인다.

    실제 모바일 뷰포트로 확인하다 발견했다 — 세로 배치에서 순서를 안 바꾸면
    "즉시 바뀐다"는 것 자체가 전달되지 않는다.
    """
    html = site["playground.html"]
    assert 'class="result"' in html, "결과 영역에 순서 제어용 클래스가 없다"
    assert ".cols > .result{order:-1}" in html, "모바일에서 결과를 위로 올리는 규칙이 없다"
    assert "min-width:940px" in html and ".cols > .result{order:0}" in html, \
        "데스크톱에서 원래 좌우 배치로 되돌리는 규칙이 없다"


# ---------- 모바일 ----------
def _find_chromium() -> Path | None:
    """샌드박스는 /opt/pw-browsers 에, CI 는 ~/.cache/ms-playwright 에 둔다."""
    for root in (Path("/opt/pw-browsers"), Path.home() / ".cache" / "ms-playwright"):
        if not root.exists():
            continue
        for exe in sorted(root.glob("chromium*/chrome-linux/chrome")):
            return exe
    return None


CHROMIUM = _find_chromium()
MOBILE_WIDTH = 390


@pytest.fixture(scope="module")
def mobile_scroll(site):
    """390px 에서 페이지별 실제 가로 스크롤량. 브라우저는 한 번만 띄운다.

    `scrollWidth` 비교만으로는 부족하다 — 스크롤 컨테이너 안의 넓은 표는 정상이고
    페이지 자체가 밀리는 것만 문제다. 그래서 실제로 스크롤을 시도해 본다.
    """
    if not os.environ.get("REGIMPACT_BROWSER_TESTS"):
        pytest.skip(
            "브라우저 검사는 이 샌드박스에서 페이지당 ~10초라 기본 스위트에서 제외한다. "
            "CI 가 REGIMPACT_BROWSER_TESTS=1 로 돌린다.")
    pytest.importorskip("playwright")
    if CHROMIUM is None:
        pytest.skip("chromium 없음")
    from playwright.sync_api import sync_playwright

    out = {}
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=str(CHROMIUM))
        pg = b.new_page(viewport={"width": MOBILE_WIDTH, "height": 844})
        for name in sorted(EXPECTED):
            pg.goto(f"file://{site['_dir']}/{name}")
            pg.wait_for_timeout(150)
            pg.evaluate("window.scrollTo(900, 0)")
            out[name] = pg.evaluate("window.scrollX")
            pg.evaluate("window.scrollTo(0, 0)")
        b.close()
    return out


def test_no_horizontal_scroll_on_mobile(mobile_scroll):
    """폰에서 실제로 가로로 밀리는지 브라우저로 확인한다 (CI 전용).

    아래 정적 검사들은 규칙이 **존재하는지**만 본다. 규칙이 있어도 다른 곳에서 넘칠 수
    있으므로 실제 확인이 필요하고, 그건 CI 에서 돈다.

    폰에서 가로로 밀리면 글자 배치가 무너진 것으로 보인다.

    Stitch 목업이 데스크톱 전용(사이드바 fixed w-72 + 본문 pl-72)이라 390px 에서
    본문이 102px 로 찌그러져 있었다. 데스크톱만 확인하면 이걸 못 잡는다.
    """
    bad = {k: v for k, v in mobile_scroll.items() if v}
    assert not bad, f"390px 에서 가로로 밀리는 페이지: {bad}"


def test_mobile_css_is_present_in_every_page(site):
    """미디어 쿼리가 통째로 빠지면 반응형이 조용히 되돌아간다."""
    for name, html in site.items():
        if name == "_dir":
            continue
        assert "@media" in html, f"{name}: 반응형 규칙이 없다"


@pytest.mark.parametrize("rule,why", [
    (".pl-72{padding-left:0}", "사이드바 288px 가 본문을 102px 로 찌그러뜨린다"),
    ("aside.fixed{position:static", "사이드바가 fixed 로 남으면 본문 위를 덮는다"),
    ("main .grid-cols-4,main .grid-cols-3{grid-template-columns:repeat(2",
     "4열 그리드가 안 접혀 칸이 78px 이 되고 글자가 칸 밖으로 나간다"),
    ("main .shrink-0{flex-shrink:1", "고정폭 열이 안 줄어 페이지를 밀어낸다"),
    ("main table{display:block", "넓은 표가 페이지를 밀어낸다"),
])
def test_mobile_rules_that_actually_fixed_something(site, rule, why):
    """각 규칙은 실제로 관측된 깨짐 하나씩에 대응한다. 지우면 그게 되돌아온다."""
    assert rule in site["regchange.html"], why


def test_long_code_paths_wrap_in_documents(site):
    """파일 경로 같은 긴 인라인 코드는 끊을 곳이 없어 문단을 밀어낸다."""
    assert ".doc-body code{overflow-wrap:anywhere}" in site["ai_risk_register.html"]
