"""정적 HTML 리포트 생성 — 실제 파이프라인 출력으로 (오프라인, API 키 불필요).

저장된 6·30 추출(`docs/eval/extractor_run_6_30_gemini.json`)을 입력으로:
  추출 → 정규화 → Impact Matrix + Assurance(grounding/gold) → HTML 리포트.
모든 값은 엔진/추출 실제 출력에서만 온다(Stitch 목업의 환각·하드코딩 문제 해결).

실행: python examples/gen_report.py   → docs/ui/report_6_30.html 생성
"""
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from regimpact.extractor import (  # noqa: E402
    RegChangeExtraction,
    check_citation_grounding,
    load_sources,
    score_against_gold,
)
from regimpact.impact import impact_from_extraction  # noqa: E402
from regimpact.report import render_report  # noqa: E402
from regimpact.rule_proposal import build_proposal  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
SAVED = REPO / "docs" / "eval" / "extractor_run_6_30_gemini.json"
GOLD = json.loads((REPO / "docs" / "eval" / "regchange_gold_6_30.json").read_text(encoding="utf-8"))
OUT = REPO / "docs" / "ui" / "report_6_30.html"


def main() -> None:
    extraction = RegChangeExtraction.from_dict(json.loads(SAVED.read_text(encoding="utf-8")))
    sources = load_sources()

    policy_impact = impact_from_extraction(extraction)
    grounding = check_citation_grounding(extraction, sources)
    gold = score_against_gold(extraction, GOLD)
    proposal = build_proposal(extraction, generated_on=date(2026, 8, 12))

    html = render_report(
        policy_impact,
        extraction=extraction,
        grounding=grounding,
        gold=gold,
        proposal=proposal,
        generated_on=date(2026, 8, 12),
    )
    OUT.write_text(html, encoding="utf-8")
    print(f"생성: {OUT.relative_to(REPO)}  ({len(html):,} bytes)")
    print(f"  임팩트 {len(policy_impact.matrix.rows)}행 · 지역 {policy_impact.regions}")
    print(f"  Assurance: Citation {grounding.citation_correctness:.0%} · "
          f"환각 {grounding.unsupported_claim_rate:.0%} · "
          f"예외재현 {gold.exception_recall:.0%} · Regions {'OK' if gold.regions_correct else 'MISS'}")
    pc = proposal.counts()
    print(f"  Rule Proposal: 반영 {pc['MAPPED_CONSISTENT']} · 코어밖 {pc['OUT_OF_SCOPE']} · "
          f"검토 {pc['MAPPED_DIVERGENT'] + pc['NEEDS_REVIEW']} · 승인={proposal.approval_status}")


if __name__ == "__main__":
    main()
