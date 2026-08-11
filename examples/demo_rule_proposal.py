"""Rule Change Proposal E2E 데모 — 추출 → 구조화 변경안 → 엔진 일치 검증.

거버넌스 관통: (LLM)추출 → deterministic 조립(변경안 DRAFT) → 엔진(Impact Matrix)과
consistency 교차검증 → 실패 시 NEEDS_REVIEW 승격. API 키 없이 canonical 추출로 실행.

실행: python examples/demo_rule_proposal.py   (repo 루트에서)
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from regimpact.impact import build_impact_matrix  # noqa: E402
from regimpact.proposal import (  # noqa: E402
    apply_consistency_status,
    build_proposal_from_extraction,
    check_proposal_consistency,
    six_thirty_extraction,
)


def main() -> None:
    # 1) 추출 (실제 파이프라인은 extractor LLM 출력; 여기선 사람 확정 canonical)
    extraction = six_thirty_extraction()

    # 2) 구조화 변경안 조립 (deterministic, status=DRAFT)
    proposal = build_proposal_from_extraction(extraction)

    # 3) 엔진(Impact Matrix)과 일치 검증
    matrix = build_impact_matrix()
    report = check_proposal_consistency(proposal, matrix=matrix)
    apply_consistency_status(proposal, report)

    print("=== Rule Change Proposal (DRAFT) ===")
    print(json.dumps(proposal.to_dict(), ensure_ascii=False, indent=2))
    print()
    print("=== Consistency vs deterministic 엔진 ===")
    s = report.summary()
    print(f"status={proposal.status.value}  checks {s['passed']}/{s['total']} pass  "
          f"(all_passed={s['all_passed']})")
    for c in report.checks:
        mark = "✓" if c.passed else "✗"
        extra = "" if c.passed else f"  [expected={c.expected} actual={c.actual}]"
        print(f"  {mark} {c.name}{extra}")


if __name__ == "__main__":
    main()
