"""6·30 End-to-End 오케스트레이터 — 코어 완성 파이프라인 관통(브리프 §18).

Source Snapshot → RegChange 추출 → Impact Matrix → Rule Change Proposal →
Test Cases → Rule Regression → Assurance Evaluation → Validation Report.

기본은 오프라인(canonical 추출 + 원문 스냅샷)이라 API 키 없이 전 구간이 돈다.
실제 파이프라인은 extraction 자리에 extractor LLM 출력을 물리면 된다.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .assurance import AssuranceReport, evaluate_assurance
from .extractor import check_citation_grounding, load_sources, score_against_gold
from .extractor.schema import RegChangeExtraction
from .impact import build_impact_matrix
from .proposal import (
    apply_consistency_status,
    build_proposal_from_extraction,
    check_proposal_consistency,
    six_thirty_extraction,
)
from .report import ReportMeta, ValidationReport, build_validation_report
from .tc_generator import (
    check_proposal_fidelity,
    generate_cases_for_proposal,
    run_regression,
)

_GOLD_PATH = Path(__file__).resolve().parents[2] / "docs" / "eval" / "regchange_gold_6_30.json"


@dataclass
class E2EResult:
    """파이프라인 전 노드의 산출물 번들(테스트·UI 검사용)."""
    extraction: RegChangeExtraction
    proposal: object
    matrix: object
    suite: object
    grounding: object
    gold_report: object
    consistency: object
    regression: object
    fidelity: object
    assurance: AssuranceReport
    report: ValidationReport


def run_six_thirty_e2e(
    extraction: Optional[RegChangeExtraction] = None,
    *,
    gold_path: Path = _GOLD_PATH,
    meta: Optional[ReportMeta] = None,
) -> E2EResult:
    """6·30 시나리오를 끝까지 관통시키고 검증보고서를 산출한다.

    extraction 미지정 시 canonical(six_thirty_extraction) 사용(오프라인).
    """
    if extraction is None:
        extraction = six_thirty_extraction()

    # Source Snapshot + Assurance 입력
    sources = load_sources()
    gold = json.loads(gold_path.read_text(encoding="utf-8"))
    grounding = check_citation_grounding(extraction, sources)
    gold_report = score_against_gold(extraction, gold)

    # Impact Matrix (엔진 실측)
    matrix = build_impact_matrix()

    # Rule Change Proposal (조립 → 엔진 일치 검증 → 상태 승격)
    proposal = build_proposal_from_extraction(extraction)
    consistency = check_proposal_consistency(proposal, matrix=matrix)
    apply_consistency_status(proposal, consistency)

    # Test Cases → Regression + Fidelity
    suite = generate_cases_for_proposal(proposal)
    regression = run_regression(suite.generated_cases())
    fidelity = check_proposal_fidelity(suite, proposal)

    # Assurance Evaluation (4 dimension 집계)
    assurance = evaluate_assurance(
        grounding=grounding,
        gold=gold_report,
        consistency=consistency,
        regression=regression,
        fidelity=fidelity,
        coverage=suite.coverage(),
        matrix=matrix,
    )

    # Validation Report 조립
    report = build_validation_report(
        proposal=proposal,
        matrix=matrix,
        coverage=suite.coverage(),
        regression=regression,
        fidelity=fidelity,
        grounding=grounding,
        gold=gold_report,
        assurance=assurance,
        policy_id=extraction.policy_id,
        sources=sources,
        meta=meta,
    )

    return E2EResult(
        extraction=extraction,
        proposal=proposal,
        matrix=matrix,
        suite=suite,
        grounding=grounding,
        gold_report=gold_report,
        consistency=consistency,
        regression=regression,
        fidelity=fidelity,
        assurance=assurance,
        report=report,
    )
