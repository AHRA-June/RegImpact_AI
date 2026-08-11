"""Impact Matrix E2E 데모 — 6·30 규제 변경의 세그먼트별 영향 매트릭스.

룰엔진을 시행 전(2026-06-30)·후(2026-07-02) 두 시점에 차등 실행해 매트릭스를 산출한다.
모든 LTV 값은 엔진 실제 출력이다(UI/Stitch 하드코딩값 교체용).

실행: python examples/demo_impact_matrix.py   (repo 루트에서)
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from regimpact.impact import build_impact_matrix, format_report  # noqa: E402


def main() -> None:
    matrix = build_impact_matrix()
    print(format_report(matrix))
    print()
    print("=== JSON (UI 연동용, 발췌) ===")
    d = matrix.to_dict()
    print(json.dumps(d["summary"], ensure_ascii=False, indent=2))
    print("첫 행:", json.dumps(d["rows"][0], ensure_ascii=False))


if __name__ == "__main__":
    main()
