"""전체 UI 화면을 엔진 산출물로 렌더 → docs/ui/generated/.

실행: python examples/render_ui.py   (repo 루트에서)

5개 화면(규제 변경 분석·임팩트 매트릭스·Rule 변경안·검증·포트폴리오 영향) + 인덱스를
생성한다. 각 화면 데이터는 rule_engine·RegChange gold·tc_generator 회귀·합성 포트폴리오
집계에서 오며, 화면에 값을 하드코딩하지 않는다. Stitch 목업(../stitch_export)을 대체한다.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from regimpact.ui import render_all  # noqa: E402


def main() -> None:
    written = render_all()
    print(f"UI 렌더 완료 → {(ROOT / 'docs' / 'ui' / 'generated').relative_to(ROOT)}/")
    for p in written:
        print(f"  - {p.name}")


if __name__ == "__main__":
    main()
