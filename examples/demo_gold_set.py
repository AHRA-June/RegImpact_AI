"""Gold Set DEV 회귀 데모 — 엔진을 DEV 평가셋으로 채점.

실행: python examples/demo_gold_set.py   (repo 루트에서)

DEV split만 사용한다(개발 중 상시 회귀). LOCKED/CHALLENGE는 sealed(브리프 §12 누수 방지) —
코어 완성 후 최종 1회 실행 시에만 unlock. 정답은 독립 명세 오라클에서 유도(엔진과 독립).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from regimpact.eval import load_manifest, run_gold_regression  # noqa: E402
from regimpact.eval.gold_set import format_report  # noqa: E402


def main() -> None:
    m = load_manifest()
    print(f"Gold Set {m['version']} · freeze {m['freeze_date']} · 총 {m['total']}문항")
    print(f"  DEV {m['splits']['dev']['count']} / LOCKED {m['splits']['locked']['count']}(sealed) "
          f"/ CHALLENGE {m['splits']['challenge']['count']}(sealed)")
    print()
    print(format_report(run_gold_regression("dev")))
    print("\n(LOCKED·CHALLENGE는 sealed — 최종 보고 시 unlock=True로 1회 실행)")


if __name__ == "__main__":
    main()
