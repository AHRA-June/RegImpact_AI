"""정적 사이트 빌드 — GitHub Pages 로 올릴 `site/` 를 만든다.

실행:  python tools/build_site.py [--out site]

파이프라인을 한 번 실행하고, 그 결과로 화면 5종 · 문서 3종 · 랜딩을 만든다.
**빌드 시점에 계산이 끝나므로 배포된 페이지는 서버가 필요 없다.**

사이트에 들어가는 것은 HTML 뿐이다. 원문 스냅샷(PDF/HWP)·소스·테스트는 올리지 않는다 —
정적 호스트로 대용량 바이너리가 새어 나가지 않게 한다.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from regimpact.governance import render_card, render_register    # noqa: E402
from regimpact.report import collect                             # noqa: E402
from regimpact.report.validation_report import render as render_report  # noqa: E402
from regimpact.ui.docrender import markdown_to_html              # noqa: E402
from regimpact.ui.landing import render as render_landing        # noqa: E402
from regimpact.ui.site import render_site                        # noqa: E402

# 마크다운 문서 → 사이트 파일명
DOCS = {
    "validation_report.html": ("검증보고서", render_report),
    "model_system_card.html": ("Model & System Card", render_card),
    "ai_risk_register.html": ("AI Risk Register", render_register),
}


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
    ev = collect(generated_at=stamp)

    # 1. 화면 5종 — 같은 evidence 로 렌더한다.
    #    화면과 문서가 각자 파이프라인을 돌리면 seed 는 같아도 수치 서술이 갈라질 수 있다.
    pages = render_site(
        extraction=ev.extraction, grounding=ev.grounding, scored=ev.gold_score,
        impact=ev.impact, matrix=ev.matrix, regression=ev.regression,
    )
    for name, html in pages.items():
        (out / name).write_text(html, encoding="utf-8")

    # 2. 문서 3종 — 마크다운 렌더러로 같은 디자인 언어로
    for filename, (title, renderer) in DOCS.items():
        md = renderer(ev)
        (out / filename).write_text(
            markdown_to_html(md, title=title), encoding="utf-8")

    # 3. 랜딩 — 진입점
    (out / "index.html").write_text(
        render_landing(ev, commit=_commit()), encoding="utf-8")

    # 4. Jekyll 처리 비활성화 (GitHub Pages 는 기본으로 Jekyll 을 돌린다)
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
