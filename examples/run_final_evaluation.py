"""최종 평가 — LOCKED/CHALLENGE 최초·최종 개봉 (브리프 §12 Phase 3).

실행: python examples/run_final_evaluation.py

⚠️ 이것은 **일회성 거버넌스 이벤트**다. sealed 평가셋(LOCKED·CHALLENGE)을 처음이자 마지막으로
개봉해 공식 최종 성능을 기록한다(`docs/eval/gold_set/FINAL_EVAL.json`). 이후 엔진/명세를 바꿔도
동일 세트로 재튜닝·재보고하지 않는다 — 재개발 시 새 평가셋 버전이 필요하다.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from regimpact.eval import FINAL_EVAL_PATH, run_final_evaluation  # noqa: E402

OPENED_DATE = "2026-08-14"   # 개봉 일자(결정론적 기록)


def main() -> None:
    rec = run_final_evaluation(OPENED_DATE, save=True)
    print(f"■ 최종 평가 (개봉일 {rec['_meta']['opened_date']} · gold {rec['_meta']['gold_version']})")
    print(f"  엔진: {rec['_meta']['engine']}")
    print("-" * 60)
    for name in ("dev", "locked", "challenge"):
        s = rec["splits"][name]
        tag = "" if name == "dev" else " (개봉)"
        print(f"  {name.upper():<10}{tag:<6} {s['passed']:>3}/{s['total']:<3}  {s['pass_rate']:.0%}")
        for cat, (p, t, r) in sorted(s["by_category"].items()):
            print(f"      {cat:<16} {p}/{t} ({r:.0%})")
        for f in s["failures"]:
            print(f"      ✗ {f['id']}: {', '.join(f['mismatches'])}")
    o = rec["overall"]
    print("-" * 60)
    print(f"  전체(115): {o['passed']}/{o['total']}  {o['pass_rate']:.0%}")
    print(f"\n기록 → {FINAL_EVAL_PATH.relative_to(ROOT)}")
    print("이후 이 세트로 재튜닝·재보고 금지(§12). 재개발 시 새 평가셋 버전 필요.")


if __name__ == "__main__":
    main()
