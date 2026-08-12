"""마크다운 문서 → 자체완결 HTML 렌더 (검증보고서 · 포트폴리오 커버).

zero-dep 렌더러(src/regimpact/docrender.py)로 인쇄 친화적 HTML을 만든다.
브라우저에서 열어 보거나 인쇄→PDF 저장으로 배포한다.

실행: python examples/render_docs.py
  → docs/validation/VALIDATION_REPORT.html, docs/PORTFOLIO.html
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from regimpact.docrender import markdown_to_html  # noqa: E402

REPO = Path(__file__).resolve().parent.parent

DOCS = [
    (REPO / "docs" / "validation" / "VALIDATION_REPORT.md",
     REPO / "docs" / "validation" / "VALIDATION_REPORT.html",
     "RegImpact AI 시스템 검증보고서 v1.0",
     "RegImpact AI · 시스템 검증보고서 (Validation Report)"),
    (REPO / "docs" / "PORTFOLIO.md",
     REPO / "docs" / "PORTFOLIO.html",
     "RegImpact AI — 포트폴리오 요약",
     "RegImpact AI · 포트폴리오 요약 (Portfolio)"),
]


def main() -> None:
    for src, out, title, kicker in DOCS:
        html = markdown_to_html(src.read_text(encoding="utf-8"), title=title, kicker=kicker)
        out.write_text(html, encoding="utf-8")
        print(f"생성: {out.relative_to(REPO)}  ({len(html):,} bytes)")


if __name__ == "__main__":
    main()
