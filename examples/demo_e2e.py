"""E2E 파이프라인 데모 — 6·30 1건이 원문→판정→영향→제안→검증까지 관통.

실행: python examples/demo_e2e.py   (repo 루트에서)
출력: 콘솔에 검증보고서(마크다운) + docs/reports/validation_6_30.md 저장.

노드: [2] Extractor → [3] Impact Matrix → [4] Rule Proposal → [7] Human Review
      → [5] Rule-Regression → [6] Assurance → [8] Validation Report.
[2]는 실제 grounded 추출 산출(docs/eval/regchange_extracted_6_30.json)을 로드한다
(Claude Code 세션 수동 추출; 자동 claude-opus-5 API는 키 확보 후 run_extractor.py).
[6] Assurance는 결정론 채점 하네스로 실측한 수치를 보고서에 싣는다.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from regimpact.extractor import (  # noqa: E402
    check_citation_grounding,
    load_sources,
    score_against_gold,
)
from regimpact.extractor.schema import RegChangeExtraction  # noqa: E402
from regimpact.impact import (  # noqa: E402
    DEFAULT_REGION,
    SIX_THIRTY_SEGMENTS,
    analyze_from_extraction,
)
from regimpact.proposal import (  # noqa: E402
    ApprovalStatus,
    build_proposal,
    record_decision,
)
from regimpact.tc_generator import run_regression  # noqa: E402
from regimpact.validation import (  # noqa: E402
    build_report,
    format_report_md,
    render_report_html,
)

GOLD = json.loads((ROOT / "docs/eval/regchange_gold_6_30.json").read_text(encoding="utf-8"))
EXTRACTED = json.loads((ROOT / "docs/eval/regchange_extracted_6_30.json").read_text(encoding="utf-8"))


def measure_assurance(ext: RegChangeExtraction) -> dict:
    """[6] Assurance — 결정론 채점 하네스로 실측 지표를 만든다."""
    sources = load_sources()
    g = check_citation_grounding(ext, sources)
    s = score_against_gold(ext, GOLD)
    return {
        "Citation Correctness": f"{g.citation_correctness:.0%}",
        "Unsupported Claim Rate": f"{g.unsupported_claim_rate:.0%}",
        "Change Completeness": f"{s.change_completeness:.0%}",
        "Exception Recall": f"{s.exception_recall:.0%}"
        + (f" (놓침 {s.missed_exceptions})" if s.missed_exceptions else ""),
        "Effective-date": "OK" if s.effective_date_correct else "MISS",
        "Region": "OK" if s.regions_correct else "MISS",
    }


def main() -> None:
    # [2] Extractor (실제 grounded 추출 로드)
    extraction = RegChangeExtraction.from_dict(EXTRACTED)

    # [3] Impact Matrix (Extractor 시점 유도 → 룰엔진 temporal diff)
    matrix = analyze_from_extraction(extraction, SIX_THIRTY_SEGMENTS, DEFAULT_REGION)

    # [4] Rule Change Proposal (AI초안)
    proposal = build_proposal(matrix, extraction)

    # [7] Human Review (사람 확정 — 데모에서는 승인으로 기록)
    proposal = record_decision(
        proposal, ApprovalStatus.APPROVED, reviewer="심사역", note="6·30 표준 변경 확인"
    )

    # [5] Rule-Regression (엔진 ⟷ 독립 오라클)
    regression = run_regression()

    # [6] Assurance (결정론 채점 실측)
    assurance = measure_assurance(extraction)

    # [8] Validation Report
    report = build_report(
        scenario_title="2026-06-30 규제지역 추가 지정",
        extraction=extraction,
        matrix=matrix,
        proposal=proposal,
        regression=regression,
        assurance=assurance,
    )
    md = format_report_md(report)
    print(md)

    out_dir = ROOT / "docs" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / "validation_6_30.md"
    md_path.write_text(md + "\n", encoding="utf-8")
    html_path = out_dir / "validation_6_30.html"
    html_path.write_text(render_report_html(report), encoding="utf-8")
    print(f"\n\n생성됨: {md_path.relative_to(ROOT)}, {html_path.relative_to(ROOT)}  "
          f"(pipeline_complete={report.is_pipeline_complete})")


if __name__ == "__main__":
    main()
