"""Assurance Evaluation — 4 dimension 집계 + gate + escalation.

각 노드가 낸 검증 신호(citation grounding, gold 대조, proposal consistency,
rule regression, proposal fidelity, coverage)를 metrics_spec.md의 **깊은 4 dimension**
으로 집계하고, 임계(threshold) 대비 pass/fail과 사람 escalation 사유를 산출한다.

깊은 4 dimension (metrics_spec §구현 깊이 정책):
  ① Source Grounding & Citation
  ② Change & Exception Completeness
  ③ Temporal / Policy-Version Consistency
  ④ Rule Regression & Conflict

임계값은 docs/metrics_spec.md(2026-08-11 확정)의 tier 체계를 따른다: 안전핵심(T0)은
하드(0/100%), 고위험 recall(T1)·완전성(T2)은 Gate 90~95%. 개별 miss는 항상 escalation으로
쌓여 gate를 REVIEW_REQUIRED로 만든다 → Gate 수치와 무관하게 silent error 불가.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class AssuranceGate(str, Enum):
    PASS = "PASS"                       # 전 dimension 통과 — 사람 승인 절차로
    REVIEW_REQUIRED = "REVIEW_REQUIRED"  # 하나 이상 실패/escalation — 사람 검토 필수


@dataclass(frozen=True)
class AssuranceThresholds:
    """확정 임계값 (docs/metrics_spec.md 2026-08-11, tier 체계).

    차등 철학: 안전핵심(T0)은 하드(0/100%), 고위험 recall(T1)·완전성(T2)은 Gate + Target.
    개별 miss는 항상 escalation으로 쌓이므로 Gate 수치와 무관하게 silent error가 불가능하다
    (per-case gate). 아래는 그 tier의 구현값.
    """
    citation_correctness_min: float = 0.95   # T2 (Unsupported Claim Rate ≤ 5%와 동치)
    change_completeness_min: float = 0.90     # T2
    exception_recall_min: float = 0.95        # T1
    regression_pass_rate_min: float = 1.0     # T0 (deterministic 하드)
    require_regions_correct: bool = True      # T1 (대상지역 완전)
    require_effective_date_correct: bool = True   # T1 시행일
    require_consistency: bool = True          # T0/T1 policy-version consistency
    require_fidelity: bool = True             # T0 engine⟷proposal 하드
    require_coverage: bool = True             # 제안 주장 전수 테스트


DEFAULT_THRESHOLDS = AssuranceThresholds()


@dataclass
class DimensionResult:
    dim_id: str
    title: str
    metrics: dict = field(default_factory=dict)     # 지표명 → 값
    checks: list[tuple[str, bool, str]] = field(default_factory=list)  # (이름, 통과, 상세)
    escalations: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(ok for _, ok, _ in self.checks)

    def to_dict(self) -> dict:
        return {
            "dim_id": self.dim_id,
            "title": self.title,
            "passed": self.passed,
            "metrics": self.metrics,
            "checks": [{"name": n, "passed": ok, "detail": d} for n, ok, d in self.checks],
            "escalations": list(self.escalations),
        }


@dataclass
class AssuranceReport:
    dimensions: list[DimensionResult] = field(default_factory=list)
    escalations: list[str] = field(default_factory=list)   # 게이트를 막는 검증 실패
    notes: list[str] = field(default_factory=list)          # 참고(설계상 정직한 gap 등, 게이트 무관)
    thresholds: AssuranceThresholds = DEFAULT_THRESHOLDS

    @property
    def gate(self) -> AssuranceGate:
        """검증 실패(escalations)가 없고 전 dimension 통과면 PASS.

        notes(설계상 정직한 gap, 예: 유주택 기준부재)는 게이트를 막지 않는다 —
        그것은 AI 검증 실패가 아니라 사람 확정 대기 항목으로 보고서에 노출된다.
        """
        if all(d.passed for d in self.dimensions) and not self.escalations:
            return AssuranceGate.PASS
        return AssuranceGate.REVIEW_REQUIRED

    def dimension(self, dim_id: str) -> Optional[DimensionResult]:
        return next((d for d in self.dimensions if d.dim_id == dim_id), None)

    def summary(self) -> dict:
        return {
            "gate": self.gate.value,
            "dimensions_total": len(self.dimensions),
            "dimensions_passed": sum(1 for d in self.dimensions if d.passed),
            "escalation_count": len(self.escalations),
            "note_count": len(self.notes),
        }

    def to_dict(self) -> dict:
        return {
            "summary": self.summary(),
            "dimensions": [d.to_dict() for d in self.dimensions],
            "escalations": list(self.escalations),
            "notes": list(self.notes),
        }


def evaluate_assurance(
    *,
    grounding,          # extractor.GroundingReport
    gold,               # extractor.GoldReport
    consistency,        # proposal.ConsistencyReport
    regression,         # tc_generator.RegressionReport
    fidelity,           # tc_generator.FidelityReport
    coverage: dict,     # ProposalTestSuite.coverage()
    matrix=None,        # impact.ImpactMatrix (선택 — escalation note)
    thresholds: AssuranceThresholds = DEFAULT_THRESHOLDS,
) -> AssuranceReport:
    """전 노드 신호를 4 dimension으로 집계한다."""
    dims: list[DimensionResult] = []
    escalations: list[str] = []
    notes: list[str] = []

    # ① Source Grounding & Citation
    d1 = DimensionResult("D1", "Source Grounding & Citation")
    d1.metrics = {
        "citation_correctness": round(grounding.citation_correctness, 4),
        "unsupported_claim_rate": round(grounding.unsupported_claim_rate, 4),
        "total_claims": grounding.total,
    }
    d1.checks.append((
        "citation_correctness ≥ 임계",
        grounding.citation_correctness >= thresholds.citation_correctness_min,
        f"{grounding.citation_correctness:.0%} (min {thresholds.citation_correctness_min:.0%})",
    ))
    for item in grounding.ungrounded:
        esc = f"근거 없는 변경 주장(환각 가능): [{item.category}] {item.citation.quote[:30]}"
        d1.escalations.append(esc)
        escalations.append(esc)
    dims.append(d1)

    # ② Change & Exception Completeness
    d2 = DimensionResult("D2", "Change & Exception Completeness")
    d2.metrics = {
        "change_completeness": round(gold.change_completeness, 4),
        "exception_recall": round(gold.exception_recall, 4),
        "regions_correct": gold.regions_correct,
    }
    d2.checks.append((
        "change_completeness ≥ 임계",
        gold.change_completeness >= thresholds.change_completeness_min,
        f"{gold.change_completeness:.0%} (min {thresholds.change_completeness_min:.0%})",
    ))
    d2.checks.append((
        "exception_recall ≥ 임계",
        gold.exception_recall >= thresholds.exception_recall_min,
        f"{gold.exception_recall:.0%} (min {thresholds.exception_recall_min:.0%})",
    ))
    if thresholds.require_regions_correct:
        d2.checks.append(("대상지역 완전", gold.regions_correct, str(gold.regions_correct)))
    for mc in gold.missed_changes:
        esc = f"골드 변경 누락: {mc}"
        d2.escalations.append(esc)
        escalations.append(esc)
    for me in gold.missed_exceptions:
        esc = f"골드 예외 누락: {me}"
        d2.escalations.append(esc)
        escalations.append(esc)
    dims.append(d2)

    # ③ Temporal / Policy-Version Consistency
    d3 = DimensionResult("D3", "Temporal / Policy-Version Consistency")
    cons_sum = consistency.summary()
    d3.metrics = {
        "consistency_checks_passed": cons_sum["passed"],
        "consistency_checks_total": cons_sum["total"],
        "effective_date_correct": gold.effective_date_correct,
    }
    if thresholds.require_consistency:
        d3.checks.append((
            "proposal↔엔진 consistency 전부 통과",
            consistency.all_passed,
            f"{cons_sum['passed']}/{cons_sum['total']}",
        ))
    if thresholds.require_effective_date_correct:
        d3.checks.append(("시행일 정확", gold.effective_date_correct, str(gold.effective_date_correct)))
    for c in consistency.failed:
        esc = f"정책버전/시점 불일치: {c.name} (expected={c.expected} actual={c.actual})"
        d3.escalations.append(esc)
        escalations.append(esc)
    dims.append(d3)

    # ④ Rule Regression & Conflict
    d4 = DimensionResult("D4", "Rule Regression & Conflict")
    fid_sum = fidelity.summary()
    d4.metrics = {
        "regression_pass_rate": round(regression.pass_rate, 4),
        "regression_total": regression.total,
        "fidelity_passed": fid_sum["passed"],
        "fidelity_total": fid_sum["total"],
        "coverage_covered": coverage.get("covered", False),
        "claims_covered": f"{coverage.get('covered_claims', 0)}/{coverage.get('total_claims', 0)}",
    }
    d4.checks.append((
        "rule-regression pass rate ≥ 임계",
        regression.pass_rate >= thresholds.regression_pass_rate_min,
        f"{regression.pass_rate:.0%} (min {thresholds.regression_pass_rate_min:.0%})",
    ))
    if thresholds.require_fidelity:
        d4.checks.append((
            "proposal fidelity 전부 통과",
            fidelity.all_passed,
            f"{fid_sum['passed']}/{fid_sum['total']}",
        ))
    if thresholds.require_coverage:
        d4.checks.append((
            "제안 주장 전부 테스트 커버",
            coverage.get("covered", False),
            f"{coverage.get('covered_claims', 0)}/{coverage.get('total_claims', 0)}"
            + (f" 미커버 {coverage['uncovered']}" if coverage.get("uncovered") else ""),
        ))
    for r in regression.failures:
        esc = f"룰 회귀 실패: {r.case.case_id} {r.mismatches}"
        d4.escalations.append(esc)
        escalations.append(esc)
    for r in fidelity.failures:
        esc = f"제안 충실성 실패: {r.claim_id} [{r.case_id}] {r.detail}"
        d4.escalations.append(esc)
        escalations.append(esc)
    dims.append(d4)

    # (부가) Impact Matrix의 검토필요/기준부재 행 — 설계상 정직한 gap(게이트 무관, 참고 note)
    if matrix is not None:
        s = matrix.summary()
        n = s.get("review_required", 0) + s.get("baseline_gap", 0)
        if n:
            notes.append(
                f"설계상 정직한 gap: 기준부재/검토필요 세그먼트 {n}건 "
                f"— 유주택 '기존 LTV' 명세 부재 등, 사람 확정 대기(AI 검증 실패 아님)"
            )

    return AssuranceReport(
        dimensions=dims, escalations=escalations, notes=notes, thresholds=thresholds
    )
