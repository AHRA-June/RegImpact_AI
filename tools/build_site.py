"""정적 사이트 빌드 — GitHub Pages 로 올릴 `site/` 를 만든다.

실행:  python tools/build_site.py [--out site]

파이프라인을 한 번 실행하고, 그 결과로 화면 5종 · 문서 3종 · 랜딩을 만든다.
**빌드 시점에 계산이 끝나므로 배포된 페이지는 서버가 필요 없다.**

사이트에 들어가는 것은 HTML 뿐이다. 원문 스냅샷(PDF/HWP)·소스·테스트는 올리지 않는다 —
정적 호스트로 대용량 바이너리가 새어 나가지 않게 한다.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))


def _load_fixture_builder():
    """export_fixtures.py 의 build() 를 재사용한다 (픽스처 정의를 두 곳에 두지 않는다)."""
    spec = importlib.util.spec_from_file_location(
        "_export_fixtures", REPO / "tools" / "export_fixtures.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.build


build_fixtures = _load_fixture_builder()

from regimpact.extractor.sources import load_sources             # noqa: E402
from regimpact.governance import render_card, render_register    # noqa: E402
from regimpact.graph import build_graph                          # noqa: E402
from regimpact.report import collect                             # noqa: E402
from regimpact.retrieval import BM25Index, chunk_sources, citation_recall  # noqa: E402
from regimpact.report.validation_report import render as render_report  # noqa: E402
from regimpact.ui.docrender import markdown_to_html              # noqa: E402
from regimpact.ui.graphview import render as render_graph        # noqa: E402
from regimpact.ui.intake import render as render_intake          # noqa: E402
from regimpact.ui.searchpage import render as render_search      # noqa: E402
from regimpact.ui.landing import render as render_landing        # noqa: E402
from regimpact.ui.playground import render as render_playground  # noqa: E402
from regimpact.ui.site import render_site                        # noqa: E402
from regimpact.ui.summary import render as render_summary        # noqa: E402

# 마크다운 문서 → 사이트 파일명
DOCS = {
    "validation_report.html": ("검증보고서", render_report),
    "model_system_card.html": ("모델·시스템 카드", render_card),
    "ai_risk_register.html": ("AI 리스크 레지스터", render_register),
}


def _verify_js_port(fixtures_path: Path) -> float | None:
    """JS 포팅본을 Python 엔진과 대조한다. node 가 없으면 None(미측정).

    통과를 1.0, 불일치를 0.0 으로 돌린다 — 부분 점수를 주지 않는 이유는 임계가 100% 라서,
    한 건이라도 어긋나면 화면이 이미 거짓말을 하고 있기 때문이다.
    """
    if shutil.which("node") is None:
        print("  ⚠ node 없음 — JS 포팅 대조를 건너뛴다 (스코어카드에서 미측정으로 남는다)")
        return None
    r = subprocess.run(
        ["node", str(REPO / "tools" / "verify_js_port.mjs"), str(fixtures_path)],
        cwd=REPO, capture_output=True, text=True,
    )
    print("  " + (r.stdout or r.stderr).strip().splitlines()[0])
    return 1.0 if r.returncode == 0 else 0.0


def _commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                              cwd=REPO, capture_output=True, text=True,
                              check=True).stdout.strip()
    except Exception:
        return ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(REPO / "site"))
    args = ap.parse_args()

    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # 픽스처를 먼저 만들고 JS 포팅 대조를 돌린다. 그 결과가 스코어카드의
    # "JS Port Agreement" 실측치가 된다 — 대조를 안 돌리면 통과가 아니라 미측정으로 남는다.
    fixtures = build_fixtures()
    out.mkdir(parents=True, exist_ok=True)
    fixtures_path = out / "fixtures.json"
    fixtures_path.write_text(
        json.dumps(fixtures, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    agreement = _verify_js_port(fixtures_path)

    ev = collect(generated_at=stamp, js_port_agreement=agreement)

    # 1. 화면 5종 — 같은 evidence 로 렌더한다.
    #    화면과 문서가 각자 파이프라인을 돌리면 seed 는 같아도 수치 서술이 갈라질 수 있다.
    pages = render_site(
        extraction=ev.extraction, grounding=ev.grounding, scored=ev.gold_score,
        impact=ev.impact, matrix=ev.matrix, regression=ev.regression,
    )
    for name, html in pages.items():
        (out / name).write_text(html, encoding="utf-8")

    # 2. 문서 3종 — 마크다운 렌더러로, 화면과 같은 셸(사이드바) 안에
    for filename, (title, renderer) in DOCS.items():
        md = renderer(ev)
        (out / filename).write_text(
            markdown_to_html(md, title=title, active=filename), encoding="utf-8")

    # 3. 플레이그라운드 (픽스처는 위에서 이미 썼다)
    (out / "playground.html").write_text(
        render_playground(ev, fixtures), encoding="utf-8")

    # 3b. 규제 문서 등록 — 스냅샷 해시·정책 타임라인은 저장소 실데이터에서 계산
    (out / "sources.html").write_text(
        render_intake(ev.extraction), encoding="utf-8")

    # 3d. 영향 지식그래프 — 검증된 산출물에서 결정적으로 조립
    g = build_graph(ev.extraction, ev.impact, ev.regression, registry=ev.registry)
    (out / "graph.html").write_text(
        render_graph(g, portfolio_size=len(ev.impact.impacts)), encoding="utf-8")

    # 3e. 규제 원문 검색 — BM25 색인 + recall@k 실측 + JS 포팅 대조
    sources = load_sources()
    index = BM25Index(chunk_sources(sources))
    reports = {flag: citation_recall(index, sources, expand=flag) for flag in (False, True)}
    for flag in (False, True):
        print(f"  검색 {'확장 ON ' if flag else '확장 OFF'}: {reports[flag].summary()}")
    export = index.export()
    probes = []
    from regimpact.eval import Split as _Split, load_split as _load_split
    for item in _load_split(_Split.DEV):
        for flag in (False, True):
            top = index.search(item.question, k=10, expand=flag)
            probes.append({"query": item.question, "expand": flag,
                           "expected": [{"id": s.chunk.id, "score": s.score} for s in top]})
    search_fx = out / "search_fixtures.json"
    search_fx.write_text(json.dumps({"index": export, "probes": probes},
                                    ensure_ascii=False) + "\n", encoding="utf-8")
    if shutil.which("node") is not None:
        r = subprocess.run(["node", str(REPO / "tools" / "verify_search_port.mjs"),
                            str(search_fx)], cwd=REPO, capture_output=True, text=True)
        print("  " + (r.stdout or r.stderr).strip().splitlines()[0])
        if r.returncode != 0:
            raise SystemExit("검색 JS 포팅본이 Python 과 어긋난다 — 배포 중단")
    else:
        print("  ⚠ node 없음 — 검색 포팅 대조를 건너뛴다")
    (out / "search.html").write_text(
        render_search(export, reports), encoding="utf-8")

    # 3c. 검증 요약 — 보고서의 1페이지 요약. QA 골드 검수 진행률도 실데이터에서.
    from regimpact.eval import Split, load_split
    dev = load_split(Split.DEV)
    (out / "validation_summary.html").write_text(
        render_summary(
            ev,
            qa_confirmed=sum(1 for i in dev if i.authored_by == "human_confirmed"),
            qa_total=len(dev),
        ), encoding="utf-8")

    # 4. 랜딩 — 진입점
    (out / "index.html").write_text(
        render_landing(ev, commit=_commit(), playground=True), encoding="utf-8")

    # 5. Jekyll 처리 비활성화 (GitHub Pages 는 기본으로 Jekyll 을 돌린다)
    (out / ".nojekyll").write_text("", encoding="utf-8")

    total = sum(f.stat().st_size for f in out.iterdir() if f.is_file())
    for f in sorted(out.iterdir()):
        if f.suffix == ".html":
            print(f"  {f.name:<28} {f.stat().st_size:>8,} bytes")
    print(f"\n  {out.relative_to(REPO) if out.is_relative_to(REPO) else out} "
          f"— {len(list(out.glob('*.html')))}쪽 · {total:,} bytes")
    print(f"  빌드 {_commit()} · provider {ev.provider} · LLM 호출 0회")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
