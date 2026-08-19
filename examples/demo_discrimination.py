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

from regimpact import rule_engine                                    # noqa: E402
from regimpact.discrimination import (                               # noqa: E402
    Discrimination,
    DiscriminationReport,
    corrupt_extraction,
    discriminate_extraction,
)
from regimpact.extractor import extract_regchange, load_sources      # noqa: E402
from regimpact.extractor.backends import resolve_completion          # noqa: E402
from regimpact.extractor.postprocess import normalize_regions        # noqa: E402
from regimpact.impact.builder import derive_rule_diff                # noqa: E402
from regimpact.proposal import (                                     # noqa: E402
    build_proposal_from_extraction,
    check_proposal_consistency,
)
from regimpact.tc_generator import run_regression                    # noqa: E402

DEFAULT_RUN = REPO / "docs" / "eval" / "runs" / "run_perdoc_sonnet5.json"


def _regression_under_mutation(constant: str, value: float) -> float:
    """룰엔진 상수를 변조한 상태의 회귀 Pass Rate."""
    original = getattr(rule_engine, constant)
    setattr(rule_engine, constant, value)
    try:
        return run_regression().pass_rate
    finally:
        setattr(rule_engine, constant, original)


def main() -> int:
    sources = load_sources()
    complete = resolve_completion("replay", model=None, run_path=str(DEFAULT_RUN))
    extraction = normalize_regions(extract_regchange(sources, complete=complete)).normalized
    gold = json.loads(
        (REPO / "docs" / "eval" / "regchange_gold_6_30.json").read_text(encoding="utf-8")
    )

    results: list[Discrimination] = list(
        discriminate_extraction(extraction, sources, gold).results
    )

    # 룰 회귀 — 엔진 상수를 변조하면 독립 오라클이 잡아야 한다
    clean_rate = run_regression().pass_rate
    results.append(Discrimination(
        "Rule Regression (LTV 40%→50% 변조)",
        clean_rate, _regression_under_mutation("LTV_REGULATED_STANDARD", 0.50),
    ))
    results.append(Discrimination(
        "Rule Regression (기준선 70%→65% 변조)",
        clean_rate, _regression_under_mutation("LTV_BASELINE", 0.65),
    ))

    # 변경안 ↔ 엔진 일치 — 오염된 추출로 만든 변경안은 통과율이 떨어져야 한다
    diff = derive_rule_diff()

    def _consistency_rate(ex) -> float:
        rep = check_proposal_consistency(build_proposal_from_extraction(ex), rule_diff=diff)
        s = rep.summary()
        return s["passed"] / s["total"]

    results.append(Discrimination(
        "Proposal Consistency",
        _consistency_rate(extraction), _consistency_rate(corrupt_extraction(extraction)),
    ))

    report = DiscriminationReport(results)

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
