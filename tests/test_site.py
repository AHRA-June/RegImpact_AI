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
    "graph.html", "search.html", "demo.html", "signal.html",
    "service.html",
}

# 사이드바 셸 밖의 독립 화면 — 랜딩(그 자체가 안내판), 시연 모드(녹화 화면을 메뉴가
# 오염하면 안 된다), 내 한도 시그널(고객용 웹뷰 — B2B 사이드바가 어울리지 않는다),
# 서비스 설명서(제출 문서 그대로의 조판을 셸이 덮어쓰면 안 된다).
# 홈으로 돌아가는 링크는 전부 본문에 있다.
STANDALONE = {"index.html", "demo.html", "signal.html", "service.html"}


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
        if name == "_dir" or name in STANDALONE:
            continue
        for href, label, _ in NAV:
            assert f'href="{href}"' in html, f"{name} 의 메뉴에 {href} 가 없다"
        assert 'href="index.html"' in html, f"{name} 에 홈 버튼이 없다"


def test_standalone_pages_still_link_home(site):
    """무대·웹뷰 페이지는 사이드바가 없지만, 나가는 길은 있어야 한다."""
    for name in STANDALONE - {"index.html"}:
        assert 'href="index.html"' in site[name], f"{name} 에 홈 링크가 없다"


def test_service_page_is_the_repo_document_not_a_copy(site):
    """설명서를 사이트가 따로 베껴 두면 저장소 문서와 갈라진다 — 감싸기만 하는지 확인한다."""
    from regimpact.ui.servicedoc import DOC, SITE_ROOT, _localize
    html = site["service.html"]
    # 사이트 안에서는 자기 자신을 가리키는 절대 URL 만 상대 링크로 바뀐다 — 그 외는 그대로.
    doc = _localize(DOC.read_text(encoding="utf-8"))
    # 문서 본문(스타일 블록 뒤)이 통째로 들어가 있어야 한다.
    body = doc.partition("</style>")[2]
    for chunk in body.split("\n\n"):
        chunk = chunk.strip()
        if len(chunk) > 200 and "</header>" not in chunk and "<footer>" not in chunk:
            assert chunk in html, f"설명서 본문 일부가 사이트 페이지에 없다: {chunk[:60]}"
    assert SITE_ROOT not in html, "사이트 안에서 자기 자신을 절대 URL 로 가리킨다"


def test_service_page_carries_its_sources(site):
    """외부에서 가져온 주장은 링크로 확인 가능해야 한다 — 출처 절이 살아 있는지 고정한다."""
    html = site["service.html"]
    assert 'id="src"' in html and "출처" in html
    for sid in [f"[S{i}]" for i in range(1, 13)]:
        assert sid in html, f"출처 표시 {sid} 가 없다"
    for host in ("toss.im", "fnnews.com", "fsc.go.kr", "edaily.co.kr"):
        assert host in html, f"출처 링크 {host} 가 없다"
    assert "통계적으로 표집한 사용자 조사가 아니라" in html, "조사 한계 고지가 없다"
    # 고객 화면과 나란히 열어 두고 보는 페이지다 — 탭 제목이 같으면 구분이 안 된다.
    assert "<title>내 한도 시그널 — 서비스 설명서</title>" in html
    assert site["signal.html"].count("<title>내 한도 시그널 — 서비스 설명서</title>") == 0


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


def test_every_page_explains_itself_to_non_experts(site):
    """모든 페이지 상단에 '이 페이지는?' 설명이 있다 (2026-08-19 사용자 리뷰 —
    비전공자가 무엇을 보는 화면인지 알 수 없었다). 랜딩은 그 자체가 안내판이라 제외."""
    for name, html in site.items():
        if name in ("_dir", "index.html"):
            continue
        assert "pg-explain" in html and "이 페이지는?" in html, f"{name}: 페이지 설명 없음"
        assert "무엇으로 만들었나요?" in html, f"{name}: 재료 설명 없음"


def test_graph_page_carries_provenance(site):
    """그래프 화면의 관계마다 출처가 실려 있어야 한다 — 없으면 LLM 그래프와 구분이 안 된다."""
    html = site["graph.html"]
    for prov in ("정책 버전 DB", "룰엔진 상수 diff", "고객 영향 실측", "독립 명세 오라클"):
        assert prov in html, f"그래프에 출처 '{prov}' 가 없다"


def test_search_page_shows_measured_recall_and_misses(site):
    """검색 화면은 recall 실측과 **못 찾은 인용**을 함께 싣는다 — 좋은 숫자만 실으면 과장.

    코퍼스 확장(과거 정책 원문) 이후에는 전체 코퍼스와 시점 필터 두 수치가 모두 실려야 한다 —
    떨어진 수치(전체)를 숨기고 회복된 수치(필터)만 싣는 것도 과장이다."""
    from regimpact.extractor.sources import SOURCE_FILES, load_corpus
    from regimpact.retrieval import BM25Index, chunk_sources, citation_recall
    corpus = load_corpus()
    idx = BM25Index(chunk_sources(corpus))
    r_full = citation_recall(idx, corpus)
    r_filtered = citation_recall(idx, corpus, doc_ids=set(SOURCE_FILES))
    html = site["search.html"]
    for k in r_full.ks:
        assert f"recall@{k}" in html
    assert f"{r_full.recall(5):.0%}" in html, "전체 코퍼스 수치(떨어진 쪽)가 없다"
    assert f"{r_filtered.recall(5):.0%}" in html, "시점 필터 수치가 없다"
    assert f"못 찾은 인용 {len(r_filtered.misses_at_max_k)}건" in html
    for m in r_filtered.misses_at_max_k:
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


# ---------- 시연 모드 (신한퓨처스랩 데모) ----------
def test_demo_numbers_come_from_the_pipeline(site):
    """시연이라고 숫자를 꾸미면 이 제품의 존재 이유가 무너진다 — 전부 evidence 에서."""
    from regimpact.report import collect
    agreement = 1.0 if shutil.which("node") else None
    ev = collect(generated_at="x", js_port_agreement=agreement)
    html = site["demo.html"]
    s = ev.scorecard.summary()
    assert f"{s['passed']}/{s['total']}" in html                       # 스코어카드
    assert f"{len(ev.impact.reduced):,}건" in html                     # 한도 감소
    assert f"{ev.grounding.grounded}/{ev.grounding.total}" in html     # 인용 대조
    assert f"{ev.regression.passed}/{ev.regression.total}" in html     # 오라클 회귀
    assert ev.this_policy.published_at.isoformat() in html             # 발표일
    assert str(ev.extraction.effective_from) in html                   # 시행일


def test_demo_runs_the_verified_engine_not_a_mock(site):
    """라이브 판정은 플레이그라운드와 같은 검증된 엔진 포팅본이어야 한다 — 시연용 별도 로직 금지."""
    html = site["demo.html"]
    assert "evaluate(FX" in html          # 판정은 엔진 호출
    assert "GRANDFATHERING_CUTOFF" in html  # 규칙 값은 픽스처 상수에서
    # 시연 장면의 판정 결과(70%/40% 등)를 HTML 에 미리 박아두지 않는다 — 엔진이 그린다
    assert 'id="verdict"></div>' in html


def test_demo_admits_limits_even_in_a_pitch(site):
    """피치라고 좋은 숫자만 추리면 그 화면이 곧 과장이다 — 한계도 무대에 올린다."""
    html = site["demo.html"]
    assert "미측정" in html                       # 스코어카드 미측정을 숨기지 않는다
    assert "실 고객데이터 미사용" in html          # 합성 포트폴리오임을 명시
    assert "사람 검토" in html                    # 모르는 것은 검토로 넘긴다는 원칙


def test_demo_has_recording_and_live_controls(site):
    """녹화(자동 재생·전체화면)와 라이브 시연(수동 넘김·장면 선택) 둘 다 돼야 한다."""
    html = site["demo.html"]
    for token in ("자동 재생", "전체화면", 'data-dur="', "data-scene", "ArrowRight"):
        assert token in html


# ---------- 내 한도 시그널 (고객용 — Tomorrow Challenge 제안 화면) ----------
def test_signal_runs_verified_ports_not_mocks(site):
    """고객 화면도 본편과 같은 엔진·검색 포팅본이어야 한다 — 데모용 별도 로직 금지."""
    html = site["signal.html"]
    assert "evaluate(FX" in html            # 판정: 룰엔진 포팅본
    assert "estimateAffordability(" in html  # 한도 계산: 대조된 포팅본
    assert "buildIndex(" in html            # Q&A: BM25 포팅본
    assert "GRANDFATHERING_CUTOFF" in html  # 규칙 값·날짜는 픽스처 상수에서
    # 판정 결과(LTV·한도)는 HTML에 미리 박지 않는다 — 엔진이 그린다
    assert '<div class="vc" id="vc-before"></div>' in html


def test_signal_quotes_are_verbatim_from_the_corpus(site):
    """'근거 조문과 함께'가 이 제안의 약속이다 — 인용은 전부 원문에 실재해야 한다."""
    import re as _re
    from regimpact.extractor.sources import load_corpus
    from regimpact.report import collect
    from regimpact.ui.signal import _rule_quotes

    ev = collect(generated_at="x")
    norm = {k: _re.sub(r"\s+", " ", v).strip() for k, v in load_corpus().items()}
    html = site["signal.html"]
    quotes = _rule_quotes(ev.extraction)
    assert {"REG_STD", "REG_FIRSTHOME", "REG_REALDEMAND", "MULTI_0", "_GF"} <= set(quotes)
    for key, q in quotes.items():
        assert q["quote"] in norm[q["doc"]], f"{key}: 인용이 원문에 없다"
        assert q["quote"] in html, f"{key}: 인용이 화면에 실리지 않았다"


def test_signal_shows_what_calculators_cannot(site):
    """차별점이 말이 아니라 화면이어야 한다 — 두 사람 비교(경과규정)와 계산기 대비표."""
    html = site["signal.html"]
    assert "같은 날 계약한 두 사람" in html          # 원탭 비교 (모바일에서도 보임)
    assert '<div class="pc" id="duo-a"></div>' in html  # 값은 엔진이 그린다 (하드코딩 금지)
    assert "일반 대출한도 계산기와 뭐가 다른가요?" in html  # 피치 패널 비교표
    assert "오늘의 <b>상태</b>" in html and "사건" in html  # 상태 vs 사건 프레임


def test_signal_qa_answers_in_plain_language_backed_by_full_source(site):
    """원문 발췌만 주면 일반인은 벽을 만난다(2026-08-19 사용자 리뷰) — 쉬운 요약이 먼저,
    그 아래 원문 발췌, 누르면 공문 전체(해당 문장 강조)가 열려야 한다. 요약은 LLM 생성이
    아니라 **미리 작성해 사람이 검수하는 안내문**이고, 인용·규칙 값은 전부 검증된 재료에서 온다."""
    import json as _json
    import re as _re

    from regimpact.extractor.sources import load_corpus
    from regimpact.report import collect
    from regimpact.ui.signal import _rule_quotes, easy_answers

    html = site["signal.html"]
    fx = _json.loads((site["_dir"] / "fixtures.json").read_text(encoding="utf-8"))
    ev = collect(generated_at="x")
    norm = {k: _re.sub(r"\s+", " ", v).strip() for k, v in load_corpus().items()}
    labels = [fx["regions"][c]["label"] for c in ev.extraction.target_regions
              if c in fx["regions"]]
    answers = easy_answers(_rule_quotes(ev.extraction), fx["constants"], norm, labels, True)
    assert len(answers) >= 4                      # 프리셋 질문 전부 커버
    for a in answers:
        assert a["easy"] in html, f"{a['id']}: 안내문이 화면에 없다"
        for c in a["cites"]:
            assert c["quote"] in norm[c["doc"]], f"{a['id']}: 인용이 원문에 없다"
    assert "미리 검수된 안내" in html             # 생성이 아니라 사전 작성임을 정직하게 표기
    assert 'id="modal"' in html                   # 원문 전체 모달
    assert "원문 전체" in html                    # 발췌 → 전체로 가는 길


def test_signal_fixes_from_phone_review(site):
    """폰 실사용 리뷰(2026-08-19) 3건 고정 — ③ 방향, 연락처 구간, 규제 외 질문."""
    import json as _json
    import re as _re
    html = site["signal.html"]
    # ① ③은 결과보다 위에 있다 — "아래 ③" 같은 방향 오류 대신 탭하면 스크롤되는 링크
    assert "아래 ③" not in html
    assert 'href="#gf"' in html and 'id="gf"' in html
    # ② 고객 화면 검색 색인에 담당자 연락처 구간(실명·전화)이 없다.
    #    공문 전체 보기(DOCS_FULL)에는 원문 그대로 남는다 — 문서 편집이 아니라 재료 선별.
    idx_json = html.split("const IDX_EXPORT = ", 1)[1].split(";\nconst QUOTES", 1)[0]
    chunks = _json.loads(idx_json)["chunks"]
    phone = _re.compile(r"0\d{1,2}-\d{3,4}-\d{4}")
    assert chunks, "고객 색인이 비었다"
    hits = [c["id"] for c in chunks if phone.search(c["text"])]
    assert not hits, f"고객 색인에 연락처 구간이 남아 있다: {hits[:3]}"
    # 연락처를 걷어내되 **그 청크의 본문은 살아 있어야 한다** — 처음엔 청크를 통째로 버려서
    # 고객이 가장 많이 묻는 값(비규제 70%/유주택 60%)까지 사라졌다.
    body = " ".join(c["text"] for c in chunks)
    assert "非규제지역(수도권 외) 무주택(처분조건부 1주택) 70% / 유주택 60%" in body
    # ③ 비규제/규제 외 질문에도 미리 검수된 쉬운 요약이 있다
    assert "규제 외" in html and "non-regulated" in html


def test_signal_excerpt_is_sentence_level(site):
    """발췌·강조는 청크 통째가 아니라 질문어가 걸린 **문장** 단위여야 한다 (2026-08-19 리뷰 2차).

    청크(420자)를 그대로 실으면 첫 줄이 앞 페이지 꼬리라 "여기가 답"으로 읽히지 않는다.
    """
    html = site["signal.html"]
    assert "function pickSentences" in html and "function sentences" in html
    assert "openDoc(t.doc, t.marks)" in html      # 강조 대상은 문장 목록
    assert "공문에서 질문 표현이 나온 문장" in html  # 화면이 할 수 있는 주장만 한다
    assert "질문과 무관할 수 있어요" in html        # 어휘 매칭의 한계를 고객에게 밝힌다


def test_signal_full_text_is_the_unedited_original(site):
    """모달의 '공문 전체'는 **원문 그대로**여야 한다 — 줄바꿈까지(2026-08-20 폰 리뷰:
    한 덩어리로 흘러 표가 사라졌다). 대신 발췌 문장은 공백을 합친 좌표에서 찾으므로,
    정규화하면 색인 본문이 전체 본문 안에 있어야 강조가 성립한다."""
    import json as _json
    import re as _re

    from regimpact.extractor.sources import load_corpus
    html = site["signal.html"]
    full = _json.loads(html.split("const DOCS_FULL = ", 1)[1].split(";\nconst IDX_EXPORT", 1)[0])
    idx = _json.loads(html.split("const IDX_EXPORT = ", 1)[1].split(";\nconst QUOTES", 1)[0])
    assert full and idx["chunks"]
    corpus = load_corpus()
    for doc, text in full.items():
        assert text == corpus[doc], f"{doc}: 모달 본문이 원문과 다르다 — 편집하지 않는다"
        assert "\n" in text, f"{doc}: 줄바꿈이 사라졌다 (표가 한 줄로 뭉개진다)"
    norm = {d: _re.sub(r"\s+", " ", t).strip() for d, t in full.items()}
    for c in idx["chunks"][:8]:
        assert c["text"][:60] in norm[c["doc_id"]], f"{c['id']}: 청크를 전체 본문에서 못 찾는다"
    assert "줄바꿈까지 원문 그대로이며 한 글자도 빼지 않았습니다" in html


def test_signal_fixes_from_phone_review_day2(site):
    """폰 실사용 리뷰(2026-08-20) 3건 고정 — 발췌 강조 정확도, 모달 가독성, 인용 출처.

    ① 어휘가 겹친 문단이 검수된 답과 같은 비중으로 놓이면, 검수 안 된 문단이 답처럼 보인다.
    ② 문장 점수는 겹친 개수가 아니라 희소성(idf)으로 매긴다.
    ③ 목차 줄이 근거로 실리지 않게, 인용 절단기는 앵커가 모호하면 실패한다.
    """
    html = site["signal.html"]
    # ① 검수된 답이 있으면 어휘 매칭 문단은 접어서 보조로
    assert "details class=\"more xtra\"" in html
    assert "검수된 답은 아니에요" in html
    # ② 문장 점수에 색인의 idf 를 쓴다 (개수 세기가 아니다)
    assert "INDEX.idf.get(t)" in html
    # ③ 원문 좌표 되돌리기 + 쪽 구분 (원문을 그대로 두고 강조만 얹는다)
    assert "function normMap(" in html and "function findSpan(" in html
    assert 'class="pg"' in html


def test_signal_citation_cutter_refuses_ambiguous_anchors():
    """목차와 본문에 같은 문장이 있는데 첫 것을 집으면 **목차 줄**이 근거로 실린다
    (2026-08-20 폰 리뷰에서 실제로 발생). 모호하면 실패하는 것이 정상 동작이다."""
    import re as _re

    from regimpact.extractor.sources import load_corpus
    from regimpact.ui.signal import _corpus_cut
    norm = {k: _re.sub(r"\s+", " ", v).strip() for k, v in load_corpus().items()}
    ambiguous = "3억원 초과 APT를 취득한 자의 전세대출 제한의 예외사유는?"
    with pytest.raises(ValueError, match="모호"):
        _corpus_cut(norm, "FAQ_20260630", ambiguous)
    body = _corpus_cut(norm, "FAQ_20260630", ambiguous, 60, nth=1)
    assert "불가피한 실수요" in body["quote"]      # 목차가 아니라 본문


def test_signal_answers_which_regions_were_added(site):
    """"어디가 추가된 거야" — 원문이 '수도권'이 아니라 시·구 이름으로 말하기 때문에
    어휘 검색으로는 답할 수 없는 질문이다. 사전 검수 안내가 evidence 의 지역으로 답한다."""
    import json as _json
    import re as _re

    from regimpact.extractor.sources import load_corpus
    from regimpact.report import collect
    from regimpact.ui.signal import _rule_quotes, easy_answers

    html = site["signal.html"]
    fx = _json.loads((site["_dir"] / "fixtures.json").read_text(encoding="utf-8"))
    ev = collect(generated_at="x")
    labels = [fx["regions"][c]["label"] for c in ev.extraction.target_regions
              if c in fx["regions"]]
    norm = {k: _re.sub(r"\s+", " ", v).strip() for k, v in load_corpus().items()}
    answers = easy_answers(_rule_quotes(ev.extraction), fx["constants"], norm, labels, True)
    which = next(a for a in answers if a["id"] == "which-regions")
    assert "어디" in which["keys"]
    for label in labels:                          # 지역명은 evidence 에서 온다
        assert label in which["easy"] and label in html
    for c in which["cites"]:                      # 근거는 원문 verbatim
        assert c["quote"] in norm[c["doc"]]


def test_signal_never_dead_ends_on_an_unanswerable_question(site):
    """답을 못 찾아도 **원문은 읽게** 해준다 — 화면을 비우는 건 도리가 아니다
    (2026-08-20 폰 리뷰: "뭐가바뀐거야?"에 아무것도 안 나옴)."""
    html = site["signal.html"]
    assert 'id="docrow"' in html and "function docBtns(" in html
    assert "공문 원문 그대로 읽기" in html
    assert "음영 없이 전체 보기" in html          # 강조 없이 원문만 여는 경로
    assert "tgt(doc, [])" in html                 # marks 를 비워서 연다
    # 못 찾았을 때의 안내가 막다른 길이 아니라 원문으로 이어진다
    assert "아래 <b>공문 원문 그대로 읽기</b>에서 전체 내용을 보실 수 있고" in html


def test_signal_answers_the_most_asked_question(site):
    """"뭐가 바뀐 거야"는 이 제품의 가장 흔한 질문인데 어휘 검색으로는 못 잡는다 —
    원문이 "바뀌다"가 아니라 "강화·적용"이라고 쓰기 때문. 사전 검수 안내가 답한다."""
    import json as _json
    import re as _re

    from regimpact.extractor.sources import load_corpus
    from regimpact.report import collect
    from regimpact.ui.signal import _rule_quotes, easy_answers

    fx = _json.loads((site["_dir"] / "fixtures.json").read_text(encoding="utf-8"))
    ev = collect(generated_at="x")
    norm = {k: _re.sub(r"\s+", " ", v).strip() for k, v in load_corpus().items()}
    answers = easy_answers(_rule_quotes(ev.extraction), fx["constants"], norm, ["구리시"], True)
    ids = [a["id"] for a in answers]
    assert "what-changed" in ids
    wc = next(a for a in answers if a["id"] == "what-changed")
    c = fx["constants"]
    for pct in (c["LTV_BASELINE"], c["LTV_REGULATED_STANDARD"], c["LTV_FIRST_HOME"]):
        assert f"{pct:.0%}" in wc["easy"], "비율이 엔진 상수에서 오지 않았다"
    assert c["GRANDFATHERING_CUTOFF"] in wc["easy"]
    for cite in wc["cites"]:
        assert cite["quote"] in norm[cite["doc"]]
    # 더 구체적인 질문은 여전히 그 질문의 안내가 이긴다 (일반 안내가 가로채지 않는다)
    def pick(q):
        best, bn = None, 0
        for a in answers:
            n = sum(1 for k in a["keys"] if k in q)
            if n > bn:
                best, bn = a, n
        return best["id"] if best else None
    assert pick("뭐가바뀐거야?") == "what-changed"
    assert pick("생애최초인데 한도가 줄어드나요") == "first-home"


def test_signal_total_affordability_is_grounded_and_honest(site):
    """인터뷰 반영(2026-08-20): LTV만이 아니라 총 가능금액. 단 — 값은 전부 확정 명세·원문에서,
    가정은 화면에 그대로, 결과 숫자는 엔진·포팅본이 그린다(HTML 에 미리 박지 않는다)."""
    import json as _json
    import re as _re

    from regimpact.extractor.sources import load_corpus
    html = site["signal.html"]
    # 화면 요소 — 총액·binding·한도 4종 입력
    assert "총 얼마까지 빌릴 수 있나" in html and "참고 추정" in html
    assert '<div id="aff-out"></div>' in html          # 결과는 JS 가 그린다
    assert "여기에 막혀요" in html                      # binding 규제 표시
    # 정직성 — 단순화 가정 명시
    assert "스트레스 금리 가산은 미반영" in html
    assert "보수적" in html and "은행 심사로 확정" in html
    # 상수는 픽스처에서 — 대조 프로브가 실려 있고 규제 값 리터럴은 JS 검증이 막는다
    fx = _json.loads((site["_dir"] / "fixtures.json").read_text(encoding="utf-8"))
    aff = fx["affordability"]
    assert len(aff["probes"]) >= 100
    assert aff["constants"]["max_loan_caps"][0] == [1_500_000_000, 600_000_000]
    # 근거 조문 4건이 원문 verbatim 으로 실려 있다
    norm = {k: _re.sub(r"\s+", " ", v).strip() for k, v in load_corpus().items()}
    for anchor, doc in [("주택가격별 대출한도 규제(15억원이하6억원", "FAQ_20260630"),
                        ("금융권 대출은 DSR 규제(은행권 40%", "FAQ_20260630"),
                        ("조정대상지역(아파트 限) 50% 투기과열지구 40%", "FAQ_20260630"),
                        ("최대한도 6억원 제한", "MOLIT_PRESS_20260630")]:
        assert anchor in norm[doc] and anchor in html, anchor


def test_signal_turns_diagnosis_into_action(site):
    """고객 조사(2026-08-20)의 공백 — 계산기는 "무엇에 막혔나"에서 멈춘다. 목표를 넣으면
    "그래서 얼마를 바꿔야 하나"를 규제별로 역산해 답한다."""
    import json as _json
    html = site["signal.html"]
    assert "이만큼 빌리고 싶어요" in html and 'id="goal-go"' in html
    assert "planForTarget(" in html                 # 대조된 포팅본이 계산한다
    assert '<div class="rx" id="rx"></div>' in html  # 처방은 JS 가 그린다
    assert "기존 대출 월 상환액을" in html            # 행동으로 잇는 처방
    assert "부부합산" in html                        # 소득 인정 축
    # 처방 역산도 Python 과 대조되는 프로브가 실려 있다
    fx = _json.loads((site["_dir"] / "fixtures.json").read_text(encoding="utf-8"))
    assert len(fx["affordability"]["plan_probes"]) >= 200


def test_signal_shows_my_actual_ratio_against_the_cap(site):
    """금액만으로는 왜 막혔는지 알 수 없다(2026-08-20 리뷰) — 규정 한도와 내 비율을 함께.
    "규정 한도는 40%인데 이 금액이면 58.4%가 돼요 — 18.4%p 초과"""
    html = site["signal.html"]
    assert "규정 한도" in html                      # 한도 막대마다 규제 기준 표기
    assert "ratiosFor(" in html                     # 대조된 포팅본이 계산한다
    assert "이 금액이면" in html and "초과" in html   # 초과 설명 문장(값은 런타임 조립)
    assert 'class="gauge"' in html and 'class="lim"' in html  # 한도 선이 있는 게이지
    assert "pct1" in html                           # 소수 한 자리 — 40%와 40.4%를 구분


def test_signal_matches_products_as_eligibility_not_recommendation(site):
    """상품 매칭은 추천이 아니라 자격 판정이다 — 금소법상 자문·권유가 아니라 정보 제공.
    소득·자산 요건은 공문에 없으므로 "가능합니다"라고 말하지 않는다."""
    html = site["signal.html"]
    assert "내게 가능한 상품 찾기" in html
    assert "추천이 아니라 자격 판정" in html
    assert "판정하지 않고 상담으로 안내" in html
    assert "없는 근거로" in html                     # 원칙을 화면에 명시
    assert '<div id="prod"></div>' in html          # 결과는 JS 가 그린다
    # 화면과 Python 규칙이 같은 상품군을 다루는가
    from regimpact.products import PRODUCTS
    for prod in PRODUCTS:
        assert prod["name"] in html, f"{prod['id']} 이 화면에 없다"


def test_signal_shows_limit_moves_beyond_the_announcement_day(site):
    """'시그널'이 발표일 전용 도구가 아님을 화면이 보여준다 — 한도를 움직인 이벤트 타임라인.
    날짜·지역은 정책 버전 DB 실데이터에서 온다."""
    import json as _json
    html = site["signal.html"]
    assert "내 한도를 움직인 일들" in html
    assert 'id="tl"' in html and "알림" in html
    fx = _json.loads((site["_dir"] / "fixtures.json").read_text(encoding="utf-8"))
    dated = {v["effective_from"] for e in fx["regions"].values() for v in e["versions"]
             if v.get("effective_from") and v.get("source_policy_id")}
    assert len(dated) >= 3, "타임라인에 쓸 정책 시점이 부족하다"


def test_signal_pitch_claims_both_customer_and_bank_sides(site):
    """지원서 어필(2026-08-20 인터뷰): 같은 엔진이 고객 화면과 현업 산출물을 모두 구동한다 —
    과장이 아니라 실태이므로 화면에 적고, 그 산출물 링크가 실제로 살아 있어야 한다."""
    html = site["signal.html"]
    assert "고객·현업 양면" in html
    assert "임팩트 매트릭스" in html and "검증보고서" in html
    assert 'href="validation_summary.html"' in html    # 현업 산출물로 가는 실제 경로


def test_signal_is_honest_with_customers(site):
    """고객 화면일수록 한계를 숨기면 안 된다 — 금융사고가 되는 지점이다."""
    html = site["signal.html"]
    assert "미반영" in html                 # DSR·최대한도 등 부가 규제 미반영 명시
    assert "전문 상담" in html              # 모르는 것은 상담으로
    assert "지어내" in html                 # 근거 없으면 답하지 않는다
    assert "PoC" in html                    # LLM 답변 생성은 배선 목표임을 명시


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
