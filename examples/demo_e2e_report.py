"""데모 — 6·30 1건 E2E 관통 + Validation Report(Markdown) 생성.

실행: python examples/demo_e2e_report.py [출력경로.md]

API 키 없이 오프라인 stub 추출로 Source→…→Report 전 노드를 관통시킨다.
실제 LLM 추출로 돌리려면 run_e2e(complete=anthropic_completion())를 넘긴다.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from regimpact.report import render_markdown, run_e2e  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
GOLD = json.loads(
    (REPO / "docs" / "eval" / "regchange_gold_6_30.json").read_text(encoding="utf-8")
)


def main() -> None:
    rep = run_e2e(gold=GOLD)
    md = render_markdown(rep)

    out = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / "docs" / "eval" / "validation_report_6_30.md"
    out.write_text(md, encoding="utf-8")

    # 콘솔 요약
    print(f"E2E 관통: {'✅ 성공' if rep.e2e_ok else '❌ 실패'}")
    print(f"  Source Snapshot   : {len(rep.snapshots)} docs")
    print(f"  Region 전환       : {sum(t.newly_regulated for t in rep.transitions)} 신규규제")
    print(f"  RegChange         : {len(rep.extraction.changes)} 항목")
    print(f"  Impact Matrix     : n={rep.matrix.n}, 고임팩트={rep.matrix.n_high_impact}")
    print(f"  Rule Proposal     : {len(rep.proposal.ltv_lines)}행 ({rep.proposal.approval_status})")
    print(f"  Rule Regression   : {rep.regression.passed}/{rep.regression.total} "
          f"({rep.regression.pass_rate:.0%})")
    print(f"  Assurance         : grounding {rep.grounding.citation_correctness:.0%}, "
          f"completeness {rep.gold.change_completeness:.0%}, "
          f"exc_recall {rep.gold.exception_recall:.0%}")
    print(f"  Human Review 게이트: {len(rep.review_items)} 건")
    print(f"\n보고서 저장: {out}")


if __name__ == "__main__":
    main()
