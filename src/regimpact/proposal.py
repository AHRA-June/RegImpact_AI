"""Rule Change Proposal — 구조화 규칙 변경 제안 (docs/00_BRIEF.md §6 [Rule Change Proposal]).

규제 변경(6·30)이 여신 룰엔진에 요구하는 변경을 **구조화된 제안 객체**로 정식화한다.
LLM이 실행 코드를 직접 수정하지 않는다: 이 제안은 사람 검토·승인 후에만 deterministic rule
registry에 반영된다(거버넌스). 제안의 값은 룰엔진 상수·regions·경과규정·Impact Matrix에서
**유도**되며, 화면/리포트에서 지어내지 않는다(LOCKED §4).

핵심 설계: 제안은 '무엇을 어떻게 바꾸는가'의 구조(파라미터 변경·대상·시행·근거·영향·escalation)
이고, DSL 코드 텍스트는 그 구조의 렌더링일 뿐이다(`render_rule_dsl`).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional

from .grandfathering import CUTOFF
from .impact import ImpactDirection, ImpactMatrix, build_impact_matrix
from .impact.segments import REGION_LABELS
from .regions import REG_EFFECTIVE, _SIX_THIRTY_REGIONS
from .rule_engine import (
    LTV_BASELINE,
    LTV_FIRST_HOME,
    LTV_MULTI,
    LTV_OWNER,
    LTV_REAL_DEMAND,
    LTV_REGULATED_STANDARD,
)

RULE_ID = "MORTGAGE_LTV_REGULATED_REGION"
POLICY_EVENT = "2026-06-30 규제지역 추가 지정"


class ApprovalStatus(str, Enum):
    """제안의 사람 검토 상태 (INFRA: Approval status field, 브리프 §16)."""
    DRAFT = "DRAFT"                      # AI 초안 생성됨
    REVIEW_REQUIRED = "REVIEW_REQUIRED"  # 사람 검토 대기
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class RuleParameterChange:
    """규칙 파라미터 하나의 Before→After (LTV 계층별)."""
    tier: str                    # 차주 계층 (무주택 표준·생애최초·서민실수요·유주택·다주택)
    before: Optional[float]      # 종전 값 (None=원문에 기준선 없음=명세부재)
    after: float                 # 신규 값
    reason_code: str
    note: str = ""

    @property
    def changed(self) -> bool:
        return self.before is None or self.before != self.after

    @property
    def before_label(self) -> str:
        return "명세부재" if self.before is None else f"{self.before:.0%}"

    @property
    def after_label(self) -> str:
        return f"{self.after:.0%}"


@dataclass(frozen=True)
class Escalation:
    """자동판정 불가 → 사람 검토 필요 (정직한 escalation, 지어내지 않음)."""
    reason_code: str
    description: str


@dataclass
class RuleChangeProposal:
    """구조화 규칙 변경 제안 (Rule Change Registry 반영 전 사람 승인 대상)."""
    rule_id: str
    policy_event: str
    effective_date: date
    grandfathering_cutoff: date
    target_regions: list[str]                       # region codes
    parameter_changes: list[RuleParameterChange]
    reason_codes: list[str]
    source_policy_ids: list[str]
    impact_summary: dict[str, int]                  # ImpactMatrix.summary
    escalations: list[Escalation] = field(default_factory=list)
    approval_status: ApprovalStatus = ApprovalStatus.REVIEW_REQUIRED
    generator: str = "RegImpact AI (AI초안→사람확정)"

    @property
    def target_region_labels(self) -> list[str]:
        return [REGION_LABELS.get(c, c) for c in self.target_regions]

    @property
    def impacted_segment_count(self) -> int:
        s = self.impact_summary
        return s.get("DOWNGRADE", 0) + s.get("NEW_RESTRICTION", 0)


# LTV 계층 정의: (tier, before(엔진), after(엔진), reason_code, note)
# before=None 은 원문에 기준선 없음(유주택/다주택 非규제 기준선 명세부재) → 정직 표기.
def _parameter_changes() -> list[RuleParameterChange]:
    return [
        RuleParameterChange("무주택 표준", LTV_BASELINE, LTV_REGULATED_STANDARD,
                            "LTV_REGULATED_40", "규제지역 표준 하향"),
        RuleParameterChange("생애최초", LTV_BASELINE, LTV_FIRST_HOME,
                            "EXCEPTION_FIRST_HOME", "예외 유지(변화 없음)"),
        RuleParameterChange("서민·실수요", LTV_BASELINE, LTV_REAL_DEMAND,
                            "EXCEPTION_REAL_DEMAND", "예외 완화폭 축소"),
        RuleParameterChange("유주택(비처분 1주택)", None, LTV_OWNER,
                            "LTV_OWNER_0", "非규제 기준선 명세부재 → 신규 제한"),
        RuleParameterChange("다주택", None, LTV_MULTI,
                            "LTV_MULTI_HOME_0", "非규제 기준선 명세부재 → 신규 제한"),
    ]


def _escalations(matrix: ImpactMatrix) -> list[Escalation]:
    """Impact Matrix에서 사람 검토 필요 사유를 수집(중복 제거)."""
    escs: dict[str, Escalation] = {}
    for row in matrix.rows:
        # before가 명세부재(NEEDS_HUMAN_REVIEW)였던 신규 제한 → OWNER_BASELINE_UNKNOWN
        if "OWNER_BASELINE_UNKNOWN" in row.before.reason_codes:
            escs.setdefault("OWNER_BASELINE_UNKNOWN", Escalation(
                "OWNER_BASELINE_UNKNOWN",
                "非규제 유주택 기준선이 원문에 정의되지 않아 룰엔진이 자동판정하지 않고 사람 검토로 escalate.",
            ))
        if row.direction == ImpactDirection.REVIEW:
            escs.setdefault("NEEDS_HUMAN_REVIEW", Escalation(
                "NEEDS_HUMAN_REVIEW", "기준 부재/모호로 사람 검토 필요.",
            ))
    return list(escs.values())


def build_rule_change_proposal(matrix: Optional[ImpactMatrix] = None) -> RuleChangeProposal:
    """엔진 상수·regions·경과규정·Impact Matrix에서 구조화 제안을 유도한다."""
    matrix = matrix if matrix is not None else build_impact_matrix()
    params = _parameter_changes()
    # reason_codes = 파라미터 근거 + 경과규정
    reason_codes = [p.reason_code for p in params] + ["GRANDFATHERED_ACCEPTED_OR_CONTRACT"]
    # source_policy_ids = Impact Matrix 코어 행이 인용한 정책 (중복 제거, 순서 보존)
    sources: list[str] = []
    for row in matrix.core_rows:
        for sid in row.after.source_policy_ids:
            if sid not in sources:
                sources.append(sid)
    return RuleChangeProposal(
        rule_id=RULE_ID,
        policy_event=POLICY_EVENT,
        effective_date=REG_EFFECTIVE,
        grandfathering_cutoff=CUTOFF,
        target_regions=list(_SIX_THIRTY_REGIONS),
        parameter_changes=params,
        reason_codes=reason_codes,
        source_policy_ids=sources,
        impact_summary=matrix.summary,
        escalations=_escalations(matrix),
        approval_status=ApprovalStatus.REVIEW_REQUIRED,
    )


def render_rule_dsl(proposal: RuleChangeProposal) -> tuple[list[str], list[str]]:
    """제안 → (BEFORE 규칙 DSL 라인, AFTER 규칙 DSL 라인). 구조의 렌더링일 뿐."""
    before = [
        'rule "MORTGAGE_LTV" {',
        "  when {",
        "    loan.purpose == HOME_PURCHASE",
        "    region.status == NON_REGULATED",
        "  }",
        "  then {",
        f"    set max_ltv = {LTV_BASELINE:.2f}   // 무주택 기준선",
        "  }",
        "}",
    ]
    region_list = ", ".join(f'"{r}"' for r in proposal.target_regions)
    after = [
        f'rule "{proposal.rule_id}" {{',
        "  when {",
        "    loan.purpose == HOME_PURCHASE",
        "    region.status == REGULATED",
        f"    // 신규 규제지역: {region_list}",
        f'    // 경과규정: application_date <= "{proposal.grandfathering_cutoff.isoformat()}" → 종전규정({LTV_BASELINE:.2f})',
        "    grandfathering.applies == false",
        "  }",
        "  then {",
    ]
    for p in proposal.parameter_changes:
        after.append(f"    set max_ltv[{p.tier}] = {p.after:.2f}   // {p.reason_code}")
    after.append("  }")
    after.append("}")
    return before, after
