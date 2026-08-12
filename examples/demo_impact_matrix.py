"""6·30 Impact Matrix E2E 데모 — Walking Skeleton 관통 출력.

같은 대표 세그먼트를 시행 전(2026-06-30)·후(2026-07-02)로 룰엔진에 돌려
LTV delta·상태전이·중대영향을 표로 낸다. UI 연동 시 Stitch 하드코딩값을
이 출력(엔진 실제 산출)으로 교체한다.

실행: python examples/demo_impact_matrix.py   (repo 루트에서)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from regimpact import analyze_impact, format_report  # noqa: E402
from regimpact.impact import SIX_THIRTY_SEGMENTS  # noqa: E402


def main() -> None:
    matrix = analyze_impact(SIX_THIRTY_SEGMENTS, policy_id="6_30_2026")
    print(format_report(matrix))


if __name__ == "__main__":
    main()
