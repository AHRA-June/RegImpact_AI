"""회귀 하네스 — 엔진 vs 오라클 차등 검증 + 카테고리별 Pass Rate 산출.

metrics_spec.md §3 지표 산출:
    - Rule-regression Pass Rate = 전체 통과 / 전체 (목표 100%)
    - Boundary-case Pass Rate  = BOUNDARY 카테고리 통과율
    - Conflict-case Pass Rate  = CONFLICT 카테고리 통과율
    - Expected vs Actual Match Rate = 전체 일치율(=Rule-regression Pass Rate와 동일 분모)

한 케이스가 '통과'라 함:
    엔진(rule_engine.evaluate) 출력이 오라클 기대값과
    status / max_ltv / applicable_rule_id / grandfathering_applied 에서 일치하고,
    기대 reason_code(must_include_reasons)를 모두 포함할 때.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ..models import LtvDecision
from ..rule_engine import evaluate
from .generator import Category, GeneratedCase, generate_all
from .oracle import ExpectedOutcome


@dataclass(frozen=True)
class CaseResult:
    case: GeneratedCase
    actual: LtvDecision
    passed: bool
    mismatches: tuple[str, ...]   # 불일치 필드 설명(있으면)


@dataclass
class RegressionReport:
    results: list[CaseResult] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failures(self) -> list[CaseResult]:
        return [r for r in self.results if not r.passed]

    @property
    def pass_rate(self) -> float:
        """Rule-regression Pass Rate. 케이스가 없으면 정의상 1.0."""
        return 1.0 if self.total == 0 else self.passed / self.total

    def pass_rate_by_category(self) -> dict[str, tuple[int, int, float]]:
        """카테고리 → (통과, 전체, 비율)."""
        out: dict[str, tuple[int, int, float]] = {}
        for cat in Category:
            subset = [r for r in self.results if r.case.category == cat]
            if not subset:
                continue
            p = sum(1 for r in subset if r.passed)
            out[cat.value] = (p, len(subset), p / len(subset))
        return out

    def category_pass_rate(self, category: Category) -> Optional[float]:
        by = self.pass_rate_by_category().get(category.value)
        return None if by is None else by[2]


def _compare(expected: ExpectedOutcome, actual: LtvDecision) -> tuple[bool, tuple[str, ...]]:
    """오라클 기대값과 엔진 출력을 비교. (통과여부, 불일치설명들)."""
    mm: list[str] = []

    if actual.status != expected.status:
        mm.append(f"status: expected={expected.status.value} actual={actual.status.value}")

    if actual.max_ltv != expected.max_ltv:
        mm.append(f"max_ltv: expected={expected.max_ltv} actual={actual.max_ltv}")

    # applicable_rule_id: 오라클이 명시한 경우만 검증(escalation/scope는 rule_id 없음)
    if expected.applicable_rule_id is not None and actual.applicable_rule_id != expected.applicable_rule_id:
        mm.append(
            f"rule_id: expected={expected.applicable_rule_id} actual={actual.applicable_rule_id}"
        )

    if actual.grandfathering_applied != expected.grandfathering_applied:
        mm.append(
            f"grandfathering: expected={expected.grandfathering_applied} "
            f"actual={actual.grandfathering_applied}"
        )

    missing = [rc for rc in expected.must_include_reasons if rc not in actual.reason_codes]
    if missing:
        mm.append(f"reason_codes missing {missing}; actual={actual.reason_codes}")

    return (not mm), tuple(mm)


def run_case(case: GeneratedCase) -> CaseResult:
    actual = evaluate(case.app)
    passed, mismatches = _compare(case.expected, actual)
    return CaseResult(case=case, actual=actual, passed=passed, mismatches=mismatches)


def run_regression(cases: Optional[list[GeneratedCase]] = None) -> RegressionReport:
    """전 케이스를 엔진에 돌려 오라클과 대조한 회귀 보고서를 만든다."""
    if cases is None:
        cases = generate_all()
    return RegressionReport(results=[run_case(c) for c in cases])


def format_report(report: RegressionReport) -> str:
    """사람이 읽는 회귀 요약(데모·CI 로그용)."""
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("RegImpact — Rule-Regression Report (engine ⟷ spec oracle)")
    lines.append("=" * 60)
    lines.append(
        f"Rule-regression Pass Rate: {report.passed}/{report.total} "
        f"= {report.pass_rate:.1%}"
    )
    lines.append("")
    lines.append("By category:")
    for cat, (p, n, rate) in report.pass_rate_by_category().items():
        lines.append(f"  {cat:<15} {p:>2}/{n:<2}  {rate:.0%}")

    if report.failures:
        lines.append("")
        lines.append(f"FAILURES ({len(report.failures)}):")
        for r in report.failures:
            lines.append(f"  ✗ {r.case.case_id} [{r.case.category.value}] {r.case.description}")
            for m in r.mismatches:
                lines.append(f"      - {m}")
    else:
        lines.append("")
        lines.append("✓ 전 케이스 통과 — 엔진이 확정 명세(§H)와 일치.")
    lines.append("=" * 60)
    return "\n".join(lines)
