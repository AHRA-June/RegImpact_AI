"""검증보고서(15~20쪽) 생성 → docs/VALIDATION_REPORT.md.

실행: python examples/build_report_doc.py   (repo 루트에서)

브리프 §18 '코어 완성의 정의' 산출물. 지금까지의 실측(룰엔진·추출·Assurance·골드셋·
영향분석·포트폴리오)을 하나의 Model-Validation-Report 급 문서로 종합한다. 값은 손으로 적지
않고 전부 실제 산출물에서 유도된다.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from regimpact.report_doc import build_validation_document  # noqa: E402


def main() -> None:
    doc = build_validation_document()
    out = ROOT / "docs" / "VALIDATION_REPORT.md"
    out.write_text(doc, encoding="utf-8")
    lines = doc.count("\n") + 1
    headings = doc.count("\n#")
    tables = doc.count("\n|---")
    # 렌더 페이지 추정: 표·헤딩이 세로 공간을 크게 차지 → 줄 기반이 char 기반보다 정확.
    est_pages = round(lines / 33)
    print(f"검증보고서 생성 → {out.relative_to(ROOT)}")
    print(f"  {lines} 줄 · {len(doc):,} 자 · 헤딩 {headings} · 표 {tables}")
    print(f"  렌더 분량 추정: 약 {est_pages}쪽 (브리프 §18 목표 15~20쪽)")


if __name__ == "__main__":
    main()
