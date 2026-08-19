"""Rule Change Proposal ↔ deterministic 룰엔진 일치 검증 (Assurance 연결).

거버넌스 루프: LLM이 제안한 변경안이, 사람이 확정한 deterministic 룰엔진(=승인된
rule registry)이 실제 구현하는 규칙과 일치하는가? 불일치 = LLM 추출 오류 또는
엔진 드리프트 → 사람 검토(NEEDS_REVIEW)로 승격. metrics_spec 'Rule Regression &
Conflict' / 'Policy-version Consistency' dimension과 정렬.

방향이 중요하다 — 변경안(LLM 산출)을 **엔진 쪽 진실**과 대조한다. 엔진 상수와
`impact.builder.derive_rule_diff()`(엔진에서 기계적으로 유도한 룰 diff)가 기준이고,
변경안이 거기 맞는지를 본다. 반대로 하면 LLM 출력이 기준이 되어 검증이 무의미해진다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional

from ..grandfathering import CUTOFF
from ..models import RegionStatus
from ..regions import REG_EFFECTIVE, REGION_VERSIONS, resolve_region_status
from ..rule_engine import (
    LTV_BASELINE,
    LTV_REGULATED_STANDARD,
)
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


def newly_designated_regions(as_of: date) -> set[str]:
    """`as_of` 에 **새로 규제지역이 된** 지역 = 전날 비규제 & 당일 규제.

    "그 시점에 규제지역인 지역 전체"(스냅샷)가 아니라 **이 정책이 바꾼 것**(델타)이다.
    변경안의 target_regions 는 정책 하나가 지정한 지역이므로 델타와 대조해야 한다.

    두 개념은 레지스트리에 6·30 신규 3곳만 있던 시절에는 우연히 같았고, 그래서 이
    검사는 스냅샷과 비교하고도 통과했다. 레지스트리에 기존 규제지역 40곳이 들어오면서
    (R-01 수정) 갈라졌다 — 스냅샷은 40곳, 델타는 3곳이다.
    """
    prev = as_of - timedelta(days=1)
    out: set[str] = set()
    for code in REGION_VERSIONS:
        was, _ = resolve_region_status(code, prev)
        now, _ = resolve_region_status(code, as_of)
        if now == RegionStatus.REGULATED and was != RegionStatus.REGULATED:
            out.add(code)
    return out


def check_proposal_consistency(
    proposal: RuleChangeProposal,
    rule_diff: Optional[list[dict]] = None,
) -> ConsistencyReport:
    """변경안을 엔진 상수(+선택적 rule_diff)와 교차검증한다.

    rule_diff 는 `impact.builder.derive_rule_diff()` 출력 — 엔진 상수에서 기계적으로
    유도한 룰 변경표다. 주어지면 변경안의 before/after 가 그 표와 맞는지도 본다.
    """
    checks: list[ConsistencyCheck] = []

    checks.append(ConsistencyCheck(
        "before.max_ltv == 엔진 기준선",
        proposal.before.max_ltv == LTV_BASELINE,
        LTV_BASELINE, proposal.before.max_ltv,
        "비규제 수도권 무주택 기준선",
    ))

    checks.append(ConsistencyCheck(
        "after.max_ltv == 엔진 규제표준",
        proposal.after.max_ltv == LTV_REGULATED_STANDARD,
        LTV_REGULATED_STANDARD, proposal.after.max_ltv,
        "규제지역 무주택 일반 LTV",
    ))

    eff = REG_EFFECTIVE.isoformat()
    checks.append(ConsistencyCheck(
        "effective_from == 엔진 시행일",
        proposal.after.effective_from == eff,
        eff, proposal.after.effective_from,
    ))

    gf_cutoff = proposal.grandfathering.cutoff_date if proposal.grandfathering else None
    checks.append(ConsistencyCheck(
        "grandfathering.cutoff == 엔진 CUTOFF",
        gf_cutoff == CUTOFF.isoformat(),
        CUTOFF.isoformat(), gf_cutoff,
    ))

    engine_new = newly_designated_regions(REG_EFFECTIVE)
    prop_regions = set(proposal.after.target_regions)
    checks.append(ConsistencyCheck(
        "target_regions == 엔진 신규지정 지역(델타)",
        prop_regions == engine_new,
        sorted(engine_new), sorted(prop_regions),
        f"누락 {sorted(engine_new - prop_regions)} / 초과 {sorted(prop_regions - engine_new)}",
    ))

    engine_exceptions = {"FIRST_HOME_BUYER", "REAL_DEMAND"}
    missing_exc = engine_exceptions - set(proposal.exceptions)
    checks.append(ConsistencyCheck(
        "exceptions ⊇ 엔진 예외경로",
        not missing_exc,
        sorted(engine_exceptions), sorted(proposal.exceptions),
        f"누락 {sorted(missing_exc)}" if missing_exc else "생애최초·서민실수요 포함",
    ))

    checks.append(ConsistencyCheck(
        "세그먼트 LTV 충돌 없음",
        not proposal.conflicts,
        [], list(proposal.conflicts),
        "같은 세그먼트에 서로 다른 값이 추출되면 최빈값을 쓰되 사람이 확인해야 한다",
    ))

    checks.append(ConsistencyCheck(
        "미매핑 변경항목 없음",
        not proposal.unmapped,
        [], list(proposal.unmapped),
        "LTV로 분류됐지만 비율이 아닌 항목(한도·만기·전입의무 등)은 별도 룰이라 사람이 배치해야 한다",
    ))

    if rule_diff is not None:
        checks.extend(_check_against_rule_diff(proposal, rule_diff))

    return ConsistencyReport(checks=checks)


def _check_against_rule_diff(
    proposal: RuleChangeProposal, rule_diff: list[dict]
) -> list[ConsistencyCheck]:
    """엔진에서 유도한 룰 diff(무주택 일반 행)와 변경안 before/after 대조."""
    std = next((d for d in rule_diff if d.get("rule_id") == "REG_STD"), None)
    if std is None:
        return [ConsistencyCheck(
            "rule_diff 에 REG_STD 행 존재", False, "REG_STD",
            sorted(d.get("rule_id", "?") for d in rule_diff),
            "엔진 룰 diff 의 무주택 일반 행을 찾지 못했다",
        )]
    return [
        ConsistencyCheck(
            "rule_diff REG_STD.before == before.max_ltv",
            std["before"] == proposal.before.max_ltv,
            std["before"], proposal.before.max_ltv,
        ),
        ConsistencyCheck(
            "rule_diff REG_STD.after == after.max_ltv",
            std["after"] == proposal.after.max_ltv,
            std["after"], proposal.after.max_ltv,
        ),
    ]


def apply_consistency_status(
    proposal: RuleChangeProposal, report: ConsistencyReport
) -> RuleChangeProposal:
    """검증 실패 시 변경안을 NEEDS_REVIEW로 승격(사람 검토 유도). DRAFT는 유지."""
    if not report.all_passed and proposal.status == ProposalStatus.DRAFT:
        proposal.status = ProposalStatus.NEEDS_REVIEW
    return proposal
