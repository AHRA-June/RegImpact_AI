"""Rule Change Proposal 구조화 스키마 (docs/00_BRIEF.md §9).

거버넌스 원칙(LOCKED): LLM은 실행 코드(룰엔진)를 직접 수정하지 않는다.
LLM은 인용 근거가 붙은 사실만 추출하고, 그 추출을 deterministic 코드가 이 구조화
변경안(proposal)으로 조립한다. 변경안은 항상 status=DRAFT로 생성되며,
사람 승인(APPROVED) 후에야 deterministic rule registry에 반영된다.

extractor.schema 와 동일 패턴: dataclass + JSON Schema dict(의존성 최소화).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ChangeType(str, Enum):
    MODIFY = "MODIFY"   # 기존 룰 수정
    ADD = "ADD"         # 신규 룰 추가
    REMOVE = "REMOVE"   # 룰 삭제


class ProposalStatus(str, Enum):
    """변경안 승인 상태 (거버넌스 스텝퍼). 생성 시 항상 DRAFT."""
    DRAFT = "DRAFT"                 # AI초안 (사람 미검토)
    NEEDS_REVIEW = "NEEDS_REVIEW"   # 검토 필요 표식(consistency 실패 등)
    APPROVED = "APPROVED"           # 사람 승인 (registry 반영 가능)
    REJECTED = "REJECTED"


@dataclass
class ProposalSource:
    """변경안 필드의 근거 인용 (Assurance ① citation grounding 연결)."""
    field_name: str          # 이 근거가 뒷받침하는 proposal 필드 (예: "after.max_ltv")
    policy_id: str
    source_doc_id: str
    evidence_span: str       # 원문 인용

    def to_dict(self) -> dict:
        return {
            "field_name": self.field_name,
            "policy_id": self.policy_id,
            "source_doc_id": self.source_doc_id,
            "evidence_span": self.evidence_span,
        }


@dataclass
class RuleState:
    """before/after 상태. 필드는 nullable(변경 유형에 따라 일부만 존재)."""
    region_status: Optional[str] = None      # NON_REGULATED / REGULATED
    max_ltv: Optional[float] = None
    target_regions: list[str] = field(default_factory=list)
    effective_from: Optional[str] = None     # ISO date

    def to_dict(self) -> dict:
        return {
            "region_status": self.region_status,
            "max_ltv": self.max_ltv,
            "target_regions": list(self.target_regions),
            "effective_from": self.effective_from,
        }


@dataclass
class Grandfathering:
    cutoff_date: Optional[str] = None        # ISO date
    conditions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"cutoff_date": self.cutoff_date, "conditions": list(self.conditions)}


@dataclass
class RuleChangeProposal:
    """구조화 정책 변경안 (docs/00_BRIEF.md §9). LLM 제안 → 사람 승인 → registry."""

    rule_id: str
    change_type: ChangeType
    before: RuleState
    after: RuleState
    exceptions: list[str] = field(default_factory=list)
    grandfathering: Optional[Grandfathering] = None
    sources: list[ProposalSource] = field(default_factory=list)
    status: ProposalStatus = ProposalStatus.DRAFT
    summary: str = ""

    def __post_init__(self) -> None:
        if isinstance(self.change_type, str):
            self.change_type = ChangeType(self.change_type)
        if isinstance(self.status, str):
            self.status = ProposalStatus(self.status)

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "change_type": self.change_type.value,
            "status": self.status.value,
            "summary": self.summary,
            "before": self.before.to_dict(),
            "after": self.after.to_dict(),
            "exceptions": list(self.exceptions),
            "grandfathering": self.grandfathering.to_dict() if self.grandfathering else None,
            "sources": [s.to_dict() for s in self.sources],
        }


# structured output용 JSON Schema (LLM 직접 생성 경로를 쓸 경우 대비; 기본 경로는
# builder가 RegChangeExtraction에서 조립). additionalProperties:false, 키 required.
RULE_STATE_SCHEMA = {
    "type": "object",
    "properties": {
        "region_status": {"type": ["string", "null"]},
        "max_ltv": {"type": ["number", "null"]},
        "target_regions": {"type": "array", "items": {"type": "string"}},
        "effective_from": {"type": ["string", "null"]},
    },
    "required": ["region_status", "max_ltv", "target_regions", "effective_from"],
    "additionalProperties": False,
}

RULE_CHANGE_PROPOSAL_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "rule_id": {"type": "string"},
        "change_type": {"type": "string", "enum": [c.value for c in ChangeType]},
        "summary": {"type": "string"},
        "before": RULE_STATE_SCHEMA,
        "after": RULE_STATE_SCHEMA,
        "exceptions": {"type": "array", "items": {"type": "string"}},
        "grandfathering": {
            "type": ["object", "null"],
            "properties": {
                "cutoff_date": {"type": ["string", "null"]},
                "conditions": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["cutoff_date", "conditions"],
            "additionalProperties": False,
        },
    },
    "required": ["rule_id", "change_type", "summary", "before", "after", "exceptions", "grandfathering"],
    "additionalProperties": False,
}
