"""Impact Matrix 데모 — 6·30 규제 변경의 Before/After 영향분석을 출력.

실행: python examples/demo_impact_matrix.py   (repo 루트에서)

이것이 제품의 핵심 E2E 출력이다: 룰엔진(deterministic)을 시행 전/후 두 시점에 관통시켜
세그먼트별 '기존 LTV → 변경 LTV / 방향 / 경과규정 / 근거코드'를 산출한다.
UI(Stitch 임팩트 매트릭스 화면)의 하드코딩 값은 이 출력으로 대체된다.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from regimpact.impact import build_impact_matrix, format_matrix  # noqa: E402


def main() -> None:
    matrix = build_impact_matrix()
    print(format_matrix(matrix))


if __name__ == "__main__":
    main()
