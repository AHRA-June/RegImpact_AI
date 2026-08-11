"""E2E 데모 — Rule Change Proposal → Test Cases → Regression + Fidelity.

거버넌스 관통(끝단):
  추출 → 변경안(DRAFT) → [겨냥 테스트케이스 생성 + 추적성]
    → engine ⟷ oracle 회귀(명세 정확성)
    → engine ⟷ proposal fidelity(제안 충실성)
    → 커버리지(모든 주장이 테스트로 뒷받침)

실행: python examples/demo_proposal_to_tc.py   (repo 루트에서)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from regimpact.proposal import (  # noqa: E402
    build_proposal_from_extraction,
    six_thirty_extraction,
)
from regimpact.tc_generator import (  # noqa: E402
    check_proposal_fidelity,
    format_report,
    format_suite_report,
    generate_cases_for_proposal,
    run_regression,
)


def main() -> None:
    # 변경안 (실제로는 extractor LLM → builder; 여기선 canonical)
    proposal = build_proposal_from_extraction(six_thirty_extraction())

    # 변경안 → 겨냥 테스트케이스 + 추적성
    suite = generate_cases_for_proposal(proposal)

    # 1) 커버리지 + fidelity(engine ⟷ proposal)
    fidelity = check_proposal_fidelity(suite, proposal)
    print(format_suite_report(suite, fidelity))
    print()

    # 2) 기존 회귀 하네스 재사용 (engine ⟷ spec oracle)
    report = run_regression(suite.generated_cases())
    print(format_report(report))

    print()
    print("추적성 예시 (case_id → 검증하는 proposal 주장):")
    for t in suite.traced[:5]:
        print(f"  {t.case.case_id:<16} → {t.claim_id}")


if __name__ == "__main__":
    main()
