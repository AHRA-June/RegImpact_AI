"""Rule Change Proposal — 규제 변경을 '무엇을 고쳐야 하는가'로 구조화한 제안.

브리프 §9/§18 / 04_PLAN Phase 1: "Rule Change Proposal(고정 스키마 1개)".
두 출처를 명시적으로 분리해 담는다(provenance):

  - narrative_changes: RegChange 추출(LLM)에서 온 서술적 변경 항목. citation 보존
    → Assurance ①(Citation grounding)이 이 항목들을 검증한다.
  - segment_impacts: Impact Matrix(deterministic 룰엔진)에서 온 세그먼트별 before/after.
    LLM이 만든 값이 아니다.

LOCKED §4(AI초안→사람확정): 제안 전체의 기본 상태는 AI_DRAFT다. 사람이 검토·확정하기
전까지 어떤 값도 '확정'이 아니다. approval_status가 이 통제를 코드로 강제한다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from ..extractor.schema import Citation, RegChangeExtraction
from .matrix import ImpactRow


class ApprovalStatus(str, Enum):
    """LOCKED §4 운영방식의 코드화."""
    AI_DRAFT = "AI_DRAFT"                # AI 초안 (기본값)
    HUMAN_CONFIRMED = "HUMAN_CONFIRMED"  # 사람 확정
    REJECTED = "REJECTED"               # 사람 반려


class Provenance(str, Enum):
    EXTRACTION_LLM = "EXTRACTION_LLM"          # LLM 추출(검증 대상)
    RULE_ENGINE_DETERMINISTIC = "RULE_ENGINE"  # 룰엔진(확정 명세, auditable)


@dataclass
class ProposedRuleChange:
    """제안된 규칙 변경 1건 (고정 스키마)."""
    field_id: str                       # 변경 대상 식별자(규칙 필드/지역/세그먼트)
    category: str                        # 변경 카테고리(LTV/EXCEPTION/REGION/...)
    summary: str
    provenance: Provenance
    before_value: Optional[str] = None
    after_value: Optional[str] = None
    segment: Optional[str] = None
    citations: list[Citation] = field(default_factory=list)
    confidence: Optional[float] = None

    def to_dict(self) -> dict:
        return {
            "field_id": self.field_id,
            "category": self.category,
            "summary": self.summary,
            "provenance": self.provenance.value,
            "before_value": self.before_value,
            "after_value": self.after_value,
            "segment": self.segment,
            "citations": [{"source_doc_id": c.source_doc_id, "quote": c.quote} for c in self.citations],
            "confidence": self.confidence,
        }


@dataclass
class RuleChangeProposal:
    """구조화 Rule Change Proposal. 사람 검토 대기 상태(AI_DRAFT)로 태어난다."""
    proposal_id: str
    policy_id: str
    effective_from: Optional[str]
    target_regions: list[str]
    narrative_changes: list[ProposedRuleChange] = field(default_factory=list)
    segment_impacts: list[ProposedRuleChange] = field(default_factory=list)
    approval_status: ApprovalStatus = ApprovalStatus.AI_DRAFT
    reviewer_note: Optional[str] = None

    @property
    def is_confirmed(self) -> bool:
        return self.approval_status == ApprovalStatus.HUMAN_CONFIRMED

    def confirm(self, reviewer_note: Optional[str] = None) -> "RuleChangeProposal":
        """사람 확정(LOCKED §4). 실제 운영에선 감사로그와 함께 호출된다."""
        self.approval_status = ApprovalStatus.HUMAN_CONFIRMED
        self.reviewer_note = reviewer_note
        return self

    def to_dict(self) -> dict:
        return {
            "proposal_id": self.proposal_id,
            "policy_id": self.policy_id,
            "effective_from": self.effective_from,
            "target_regions": list(self.target_regions),
            "approval_status": self.approval_status.value,
            "reviewer_note": self.reviewer_note,
            "narrative_changes": [c.to_dict() for c in self.narrative_changes],
            "segment_impacts": [c.to_dict() for c in self.segment_impacts],
        }


def _fmt_ltv(v: Optional[float]) -> str:
    return "-" if v is None else f"{v:.0%}"


def build_proposal(
    extraction: RegChangeExtraction,
    impact_matrix: list[ImpactRow],
    proposal_id: str = "PROP-6-30",
) -> RuleChangeProposal:
    """추출(LLM) + Impact Matrix(룰엔진)로부터 구조화 제안을 조립한다.

    narrative_changes: 추출 항목을 provenance=EXTRACTION_LLM으로, citation 보존.
    segment_impacts: 세그먼트별로 지역을 가로질러 요약(before/after가 갈리면 지역별로).
    """
    narrative = [
        ProposedRuleChange(
            field_id=f"CHANGE-{i+1:02d}",
            category=item.category,
            summary=item.summary,
            provenance=Provenance.EXTRACTION_LLM,
            before_value=item.before,
            after_value=item.after,
            citations=[item.citation],
            confidence=item.confidence,
        )
        for i, item in enumerate(extraction.changes)
    ]

    # 세그먼트별 영향 요약: (segment, region)별 before→after LTV/status를 deterministic으로.
    segment_impacts: list[ProposedRuleChange] = []
    for row in impact_matrix:
        before_s = _fmt_ltv(row.before_ltv) if row.before.max_ltv is not None else row.before.status.value
        after_s = _fmt_ltv(row.after_ltv) if row.after.max_ltv is not None else row.after.status.value
        delta = row.delta_ltv
        delta_s = "" if delta is None else f" (Δ{delta:+.0%})"
        segment_impacts.append(
            ProposedRuleChange(
                field_id=f"IMPACT-{row.persona_id}-{row.region_code}",
                category="LTV",
                summary=f"{row.segment_label} @ {row.region_code}: {before_s} → {after_s}{delta_s}"
                + ("  [고영향]" if row.high_impact else ""),
                provenance=Provenance.RULE_ENGINE_DETERMINISTIC,
                before_value=before_s,
                after_value=after_s,
                segment=row.segment_label,
            )
        )

    return RuleChangeProposal(
        proposal_id=proposal_id,
        policy_id=extraction.policy_id,
        effective_from=extraction.effective_from,
        target_regions=list(extraction.target_regions),
        narrative_changes=narrative,
        segment_impacts=segment_impacts,
        approval_status=ApprovalStatus.AI_DRAFT,
    )
