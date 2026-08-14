"""임팩트 매트릭스 UI 화면을 엔진 실제 출력으로 렌더 → docs/ui/generated/impact_matrix.html.

실행: python examples/render_impact_ui.py   (repo 루트에서)

이 스크립트가 만드는 HTML이 Stitch 하드코딩 목업(`docs/ui/stitch_export/_1`)을 대체하는
'살아있는' 임팩트 매트릭스 화면이다. 디자인 시스템은 그대로 보존하고 표 데이터만
rule_engine → build_impact_matrix() 실제 판정으로 채운다.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from regimpact.impact import build_impact_matrix, write_impact_matrix_html  # noqa: E402


def main() -> None:
    matrix = build_impact_matrix()
    out = ROOT / "docs" / "ui" / "generated" / "impact_matrix.html"
    write_impact_matrix_html(out, matrix)
    print(f"임팩트 매트릭스 렌더 완료 → {out.relative_to(ROOT)}")
    print(f"  세그먼트 {matrix.summary['TOTAL']}건 (Core {matrix.summary['CORE']}, "
          f"Discovery {matrix.summary['DISCOVERY']})")


if __name__ == "__main__":
    main()
