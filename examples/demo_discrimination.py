"""판별력(negative control) 실측 — 하니스에 이빨이 있는지 확인한다.

실행:  python examples/demo_discrimination.py

정상 100% 는 하니스가 오류에 둔감해도 나온다. 그래서 의도적으로 오류를 주입해
각 지표가 실제로 떨어지는지를 잰다. 떨어지지 않는 지표는 그 100% 가 아무것도
증명하지 않는다는 뜻이다.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from regimpact.discrimination import discriminate_pipeline           # noqa: E402
from regimpact.extractor import extract_regchange, load_sources      # noqa: E402
from regimpact.extractor.backends import resolve_completion          # noqa: E402
from regimpact.extractor.postprocess import normalize_regions        # noqa: E402
from regimpact.impact.builder import derive_rule_diff                # noqa: E402

DEFAULT_RUN = REPO / "docs" / "eval" / "runs" / "run_perdoc_sonnet5.json"


def main() -> int:
    sources = load_sources()
    complete = resolve_completion("replay", model=None, run_path=str(DEFAULT_RUN))
    extraction = normalize_regions(extract_regchange(sources, complete=complete)).normalized
    gold = json.loads(
        (REPO / "docs" / "eval" / "regchange_gold_6_30.json").read_text(encoding="utf-8")
    )

    report = discriminate_pipeline(extraction, sources, gold, rule_diff=derive_rule_diff())


    print("=" * 78)
    print("판별력(negative control) — 정상 데이터 vs 오류 주입")
    print("=" * 78)
    print(f"{'지표':<40} {'정상':>8} {'오염':>8}  감지")
    print("-" * 78)
    for r in report.results:
        mark = "✅" if r.detected else "❌ 둔감"
        print(f"{r.metric:<40} {r.clean:>7.0%} {r.corrupted:>8.0%}  {mark}")
    print("-" * 78)

    if report.all_detected:
        print("모든 지표가 오류에 반응했다 — 정상 100%가 의미를 갖는다.")
    else:
        print("⚠ 오류를 감지하지 못한 지표:")
        for r in report.blind:
            print(f"   · {r.metric} — 이 지표의 100%는 아무것도 증명하지 않는다")
    return 0 if report.all_detected else 1


if __name__ == "__main__":
    raise SystemExit(main())
