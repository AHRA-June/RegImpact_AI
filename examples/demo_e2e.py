"""E2E 파이프라인 데모 — 6·30 1건이 원문→판정→영향→제안→검증까지 관통.

실행: python examples/demo_e2e.py   (repo 루트에서)
출력: 콘솔에 검증보고서(마크다운) + docs/reports/validation_6_30.md 저장.

노드: [2] Extractor → [3] Impact Matrix → [4] Rule Proposal → [7] Human Review
      → [5] Rule-Regression → [8] Validation Report.
LLM 없이 동작하도록 [2]는 골드 기반 확정 추출(RegChangeExtraction)을 수동 구성한다
(실제 LLM 추출은 examples/run_extractor.py, NEXT).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from regimpact.extractor.schema import (  # noqa: E402
    Citation,
    RegChangeExtraction,
    RegChangeItem,
)
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
from regimpact.validation import build_report, format_report_md  # noqa: E402


def build_gold_extraction() -> RegChangeExtraction:
    """[2] 대체: 골드(regchange_gold_6_30.json) 기반 확정 추출. LLM 없이 관통용."""
    cite = Citation(source_doc_id="FSC_20260630", quote="규제지역 LTV 70%→40%")
    return RegChangeExtraction(
        policy_id="FSC_20260630",
        effective_from="2026-07-01",
        target_regions=["GURI", "YONGIN_GIHEUNG", "HWASEONG_DONGTAN"],
        changes=[
            RegChangeItem("LTV", "규제지역 표준 LTV 70%→40%", cite, before="70%", after="40%"),
            RegChangeItem("EXCEPTION", "생애최초 70% 유지·서민실수요 60%", cite),
            RegChangeItem("GRANDFATHERING", "2026-06-30까지 접수/계약+계약금 종전규정", cite),
            RegChangeItem("EFFECTIVE_DATE", "시행일 2026-07-01", cite, after="2026-07-01"),
        ],
    )


def main() -> None:
    # [2] Extractor (골드 기반 확정 추출)
    extraction = build_gold_extraction()

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

    # [8] Validation Report
    report = build_report(
        scenario_title="2026-06-30 규제지역 추가 지정",
        extraction=extraction,
        matrix=matrix,
        proposal=proposal,
        regression=regression,
    )
    md = format_report_md(report)
    print(md)

    out_dir = ROOT / "docs" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "validation_6_30.md"
    out_path.write_text(md + "\n", encoding="utf-8")
    print(f"\n\n생성됨: {out_path.relative_to(ROOT)}  (pipeline_complete={report.is_pipeline_complete})")


if __name__ == "__main__":
    main()
