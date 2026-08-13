"""Impact Matrix 데모 — 6·30 규제 변경의 세그먼트별 시행 전/후 영향.

실행: python examples/demo_impact_matrix.py   (repo 루트에서)
Walking Skeleton(04_PLAN Phase 1)의 Before/After → Impact Matrix 노드 산출물.
UI(Stitch) 연동 시 이 출력 구조를 실제 엔진 산출로 사용한다.
"""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from regimpact.impact import (  # noqa: E402
    DEFAULT_REGION,
    SIX_THIRTY_SEGMENTS,
    analyze_impact,
    format_matrix,
)


def main() -> None:
    matrix = analyze_impact(
        segments=SIX_THIRTY_SEGMENTS,
        region_code=DEFAULT_REGION,
        before_date=date(2026, 6, 30),   # 시행 전(규제 효력일 전일)
        after_date=date(2026, 7, 2),     # 시행 후(경과규정 미해당)
        policy_id="FSC_MOLIT_20260630",
    )
    print(format_matrix(matrix))


if __name__ == "__main__":
    main()
