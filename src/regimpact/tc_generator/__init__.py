"""TC Generator + Rule-Regression — 룰엔진을 독립 명세 오라클로 차등 검증.

핵심 진입점:
    generate_all()          -> list[GeneratedCase]   (경계·예외·충돌 케이스 체계 생성)
    run_regression(cases?)  -> RegressionReport       (엔진 ⟷ 오라클 비교, Pass Rate 산출)
    format_report(report)   -> str                    (사람이 읽는 요약)

설계: 엔진 출력을 기대값으로 쓰지 않고, 명세(05_RULE_SPEC §H)에서 독립 유도한
`oracle.expected_outcome` 을 기준(challenger)으로 삼는다 → 회귀가 tautology가 되지 않는다.
"""
from .generator import Category, GeneratedCase, generate_all
from .oracle import ExpectedOutcome, expected_outcome
from .regression import (
    CaseResult,
    RegressionReport,
    format_report,
    run_case,
    run_regression,
)
from .from_proposal import (
    FidelityReport,
    FidelityResult,
    ProposalClaim,
    ProposalTestSuite,
    TracedCase,
    check_proposal_fidelity,
    format_suite_report,
    generate_cases_for_proposal,
)

__all__ = [
    "Category",
    "GeneratedCase",
    "generate_all",
    "ExpectedOutcome",
    "expected_outcome",
    "CaseResult",
    "RegressionReport",
    "run_case",
    "run_regression",
    "format_report",
    # proposal → TC 연결
    "generate_cases_for_proposal",
    "check_proposal_fidelity",
    "format_suite_report",
    "ProposalTestSuite",
    "ProposalClaim",
    "TracedCase",
    "FidelityReport",
    "FidelityResult",
]
