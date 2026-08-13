"""Impact Matrix UI 생성 — 룰엔진 실제 산출로 HTML 페이지를 만든다.

실행: python examples/render_impact_ui.py   (repo 루트에서)
출력: docs/ui/generated/impact_matrix.html

Stitch 목업(`docs/ui/stitch_export/_1`)의 하드코딩·환각값("60%→50%" 등)을 대체하는
데이터바인딩 페이지. 모든 수치·근거는 ImpactMatrix 에서만 온다.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from regimpact.impact import render_6_30  # noqa: E402


def main() -> None:
    out_dir = ROOT / "docs" / "ui" / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "impact_matrix.html"
    out_path.write_text(render_6_30(), encoding="utf-8")
    print(f"생성됨: {out_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
