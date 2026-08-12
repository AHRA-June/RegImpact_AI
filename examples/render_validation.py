"""검증보고서(마크다운) → 자체완결 HTML 렌더.

VALIDATION_REPORT.md 를 프로젝트 디자인 언어의 인쇄 친화적 HTML로 변환한다(zero-dep).
브라우저에서 열어 그대로 보거나 인쇄(PDF 저장)하면 된다.

실행: python examples/render_validation.py  → docs/validation/VALIDATION_REPORT.html
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from regimpact.docrender import markdown_to_html  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "docs" / "validation" / "VALIDATION_REPORT.md"
OUT = REPO / "docs" / "validation" / "VALIDATION_REPORT.html"


def main() -> None:
    md = SRC.read_text(encoding="utf-8")
    html = markdown_to_html(
        md,
        title="RegImpact AI 시스템 검증보고서 v1.0",
        kicker="RegImpact AI · 시스템 검증보고서 (Validation Report)",
    )
    OUT.write_text(html, encoding="utf-8")
    print(f"생성: {OUT.relative_to(REPO)}  ({len(html):,} bytes)")
    print(f"  원본 {len(md):,} chars → HTML {len(html):,} bytes")
    print("  브라우저에서 열기 또는 인쇄→PDF 저장으로 배포 가능")


if __name__ == "__main__":
    main()
