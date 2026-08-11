"""Rule Change Proposal ↔ deterministic 룰엔진 일치 검증 (Assurance 연결).

거버넌스 루프: LLM이 제안한 변경안이, 사람이 확정한 deterministic 룰엔진(=승인된
rule registry)이 실제 구현하는 규칙과 일치하는가? 불일치 = LLM 추출 오류 또는
엔진 드리프트 → 사람 검토(NEEDS_REVIEW)로 승격. metrics_spec 'Rule Regression &
Conflict' / 'Policy-version Consistency' dimension과 정렬.

이 검증은 변경안(LLM 산출)을 엔진 상수·Impact Matrix(엔진 실측)와 교차대조한다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from ..grandfathering import CUTOFF
from ..regions import REG_EFFECTIVE, REGION_VERSIONS, resolve_region_status
from ..rule_engine import (
    LTV_BASELINE,
    LTV_FIRST_HOME,
    LTV_REAL_DEMAND,
    LTV_REGULATED_STANDARD,
)
from ..models import RegionStatus
from .schema import ProposalStatus, RuleChangeProposal


@dataclass
class ConsistencyCheck:
    name: str
    passed: bool
    expected: object
    actual: object
    detail: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "passed": self.passed,
            "expected": self.expected,
            "actual": self.actual,
            "detail": self.detail,
        }


@dataclass
class ConsistencyReport:
    checks: list[ConsistencyCheck] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        return all(c.passed for c in self.checks)

    @property
    def failed(self) -> list[ConsistencyCheck]:
        return [c for c in self.checks if not c.passed]

    def summary(self) -> dict:
        return {
            "total": len(self.checks),
            "passed": sum(1 for c in self.checks if c.passed),
            "failed": len(self.failed),
            "all_passed": self.all_passed,
        }

    def to_dict(self) -> dict:
        return {"summary": self.summary(), "checks": [c.to_dict() for c in self.checks]}


def _engine_regulated_regions(as_of: date) -> set[str]:
    """엔진이 특정 시점에 REGULATED로 판정하는 지역 집합."""
    out: set[str] = set()
    for code in REGION_VERSIONS:
        status, _ = resolve_region_status(code, as_of)
        if status == RegionStatus.REGULATED:
            out.add(code)
    return out


def check_proposal_consistency(
    proposal: RuleChangeProposal,
    matrix: Optional[object] = None,
) -> ConsistencyReport:
    """변경안을 엔진 상수(+선택적 Impact Matrix)와 교차검증한다.

    matrix가 주어지면 reason_code로 행을 찾아 제안값이 엔진 실측 LTV와 일치하는지도 본다.
    """
    checks: list[ConsistencyCheck] = []

    # 1. before LTV = 엔진 기준선(70%)
    checks.append(ConsistencyCheck(
        "before.max_ltv == 엔진 기준선",
        proposal.before.max_ltv == LTV_BASELINE,
        LTV_BASELINE, proposal.before.max_ltv,
        "비규제 수도권 무주택 기준선",
    ))

    # 2. after LTV = 엔진 규제표준(40%)
    checks.append(ConsistencyCheck(
        "after.max_ltv == 엔진 규제표준",
        proposal.after.max_ltv == LTV_REGULATED_STANDARD,
        LTV_REGULATED_STANDARD, proposal.after.max_ltv,
        "규제지역 무주택 일반 LTV",
    ))

    # 3. 시행일 = 엔진 REG_EFFECTIVE
    eff = REG_EFFECTIVE.isoformat()
    checks.append(ConsistencyCheck(
        "effective_from == 엔진 시행일",
        proposal.after.effective_from == eff,
        eff, proposal.after.effective_from,
    ))

    # 4. 경과규정 컷오프 = 엔진 CUTOFF
    gf_cutoff = proposal.grandfathering.cutoff_date if proposal.grandfathering else None
    checks.append(ConsistencyCheck(
        "grandfathering.cutoff == 엔진 CUTOFF",
        gf_cutoff == CUTOFF.isoformat(),
        CUTOFF.isoformat(), gf_cutoff,
    ))

    # 5. 대상지역 = 엔진 규제지역 집합 (시행일 기준)
    engine_regions = _engine_regulated_regions(REG_EFFECTIVE)
    prop_regions = set(proposal.after.target_regions)
    checks.append(ConsistencyCheck(
        "target_regions == 엔진 규제지역",
        prop_regions == engine_regions,
        sorted(engine_regions), sorted(prop_regions),
        f"누락 {sorted(engine_regions - prop_regions)} / 초과 {sorted(prop_regions - engine_regions)}",
    ))

    # 6. 예외 = 엔진이 지원하는 예외 경로
    engine_exceptions = {"FIRST_HOME_BUYER", "REAL_DEMAND"}
    missing_exc = engine_exceptions - set(proposal.exceptions)
    checks.append(ConsistencyCheck(
        "exceptions ⊇ 엔진 예외경로",
        not missing_exc,
        sorted(engine_exceptions), sorted(proposal.exceptions),
        f"누락 {sorted(missing_exc)}" if missing_exc else "생애최초·서민실수요 포함",
    ))

    # 7. (선택) Impact Matrix 실측값과 대조 — proposal ↔ 엔진 실측 E2E 연결
    if matrix is not None:
        matrix_checks = _check_against_matrix(proposal, matrix)
        checks.extend(matrix_checks)

    return ConsistencyReport(checks=checks)


def _find_row(matrix, reason_code):
    for r in matrix.rows:
        if reason_code in r.reason_codes:
            return r
    return None


def _check_against_matrix(proposal: RuleChangeProposal, matrix) -> list[ConsistencyCheck]:
    """Impact Matrix 행(엔진 실측)과 변경안 제안값 대조."""
    out: list[ConsistencyCheck] = []

    std = _find_row(matrix, "LTV_REGULATED_40")
    if std is not None:
        out.append(ConsistencyCheck(
            "matrix 무주택 after == after.max_ltv",
            std.ltv_after == proposal.after.max_ltv,
            proposal.after.max_ltv, std.ltv_after,
            "Impact Matrix 무주택 일반 변경 LTV",
        ))

    fh = _find_row(matrix, "EXCEPTION_FIRST_HOME")
    if fh is not None:
        out.append(ConsistencyCheck(
            "matrix 생애최초 after == 엔진 예외 LTV",
            fh.ltv_after == LTV_FIRST_HOME,
            LTV_FIRST_HOME, fh.ltv_after,
        ))

    rd = _find_row(matrix, "EXCEPTION_REAL_DEMAND")
    if rd is not None:
        out.append(ConsistencyCheck(
            "matrix 서민실수요 after == 엔진 예외 LTV",
            rd.ltv_after == LTV_REAL_DEMAND,
            LTV_REAL_DEMAND, rd.ltv_after,
        ))

    return out


def apply_consistency_status(
    proposal: RuleChangeProposal, report: ConsistencyReport
) -> RuleChangeProposal:
    """검증 실패 시 변경안을 NEEDS_REVIEW로 승격(사람 검토 유도). DRAFT는 유지."""
    if not report.all_passed and proposal.status == ProposalStatus.DRAFT:
        proposal.status = ProposalStatus.NEEDS_REVIEW
    return proposal
