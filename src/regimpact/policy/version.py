"""정책 버전 모델 (docs/00_BRIEF.md §7 — Temporal Policy Resolver 최소 메타데이터).

브리프 §7이 확정한 스키마를 그대로 따른다:

    policy_id · source_document_id · title · issuer · published_at · effective_from ·
    effective_to · supersedes_policy_id · jurisdiction · policy_scope · version ·
    source_url · source_hash · retrieved_at

지역 버전도 §7 스키마 그대로:

    region_code · region_name · region_status · effective_from · effective_to · source_policy_id

## 왜 정책이 '문서'가 아니라 '버전'인가
RegChange AI는 새 문서 하나를 요약하는 시스템이 아니다. 핵심 질문은
**"이번 정책이 시행되는 시점에, 직전까지 유효했던 정책과 무엇이 달라졌는가?"** 다.
그래서 정책은 시행일 구간을 갖는 버전이고, 서로 supersede 관계로 연결된다.

## 사람 확정 표시 (LOCKED §4)
`status` 가 `CONFIRMED` 여야 판정에 쓰인다. 업로드 직후는 `DRAFT` 이며, AI가 초안을 만들었으면
`provenance=AI_DRAFT` 로 남는다. AI 초안이 사람 확정 없이 규제상태를 바꾸는 일은 없다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional

from ..models import RegionStatus, RegulatedType


class PolicyStatus(str, Enum):
    DRAFT = "DRAFT"            # 업로드·추출 직후. 판정에 쓰이지 않는다.
    CONFIRMED = "CONFIRMED"    # 사람이 확정. 이때부터 유효.
    SUPERSEDED = "SUPERSEDED"  # 후속 정책이 대체


class Provenance(str, Enum):
    HUMAN_CONFIRMED = "HUMAN_CONFIRMED"   # 사람이 원문 대조로 확정
    AI_DRAFT = "AI_DRAFT"                 # LLM 추출 초안 — 확정 전


@dataclass(frozen=True)
class SourceDocument:
    """원문 스냅샷 (브리프 §7 source_* 필드)."""
    source_document_id: str
    title: str
    source_hash: str                     # sha256
    retrieved_at: Optional[date] = None
    source_url: Optional[str] = None
    filename: Optional[str] = None
    byte_size: Optional[int] = None


@dataclass(frozen=True)
class RegionDelta:
    """이 정책이 만든 지역 규제상태 변경 1건 (§7 지역 버전 스키마)."""
    region_code: str
    region_name: str
    region_status: RegionStatus
    effective_from: date
    effective_to: Optional[date] = None
    regulated_type: RegulatedType = RegulatedType.NONE

    def as_dict(self) -> dict:
        return {
            "region_code": self.region_code,
            "region_name": self.region_name,
            "region_status": self.region_status.value,
            "effective_from": self.effective_from.isoformat(),
            "effective_to": self.effective_to.isoformat() if self.effective_to else None,
            "regulated_type": self.regulated_type.value,
        }

    @staticmethod
    def from_dict(d: dict) -> "RegionDelta":
        return RegionDelta(
            region_code=d["region_code"],
            region_name=d["region_name"],
            region_status=RegionStatus(d["region_status"]),
            effective_from=date.fromisoformat(d["effective_from"]),
            effective_to=date.fromisoformat(d["effective_to"]) if d.get("effective_to") else None,
            regulated_type=RegulatedType(d.get("regulated_type", "NONE")),
        )


@dataclass(frozen=True)
class RuleNote:
    """이 정책이 건드린 룰 항목 (참고·추적용).

    **룰 '값'의 권위는 여기가 아니라 `docs/05_RULE_SPEC.md` 와 엔진에 있다** (LOCKED §4).
    이 필드는 "무엇이 바뀌었다고 문서가 말하는가"를 추적하기 위한 메모다.
    """
    field: str                # 예: "LTV_규제지역_무주택"
    before: Optional[str]
    after: Optional[str]
    citation: Optional[str] = None

    def as_dict(self) -> dict:
        return {"field": self.field, "before": self.before,
                "after": self.after, "citation": self.citation}

    @staticmethod
    def from_dict(d: dict) -> "RuleNote":
        return RuleNote(field=d["field"], before=d.get("before"),
                        after=d.get("after"), citation=d.get("citation"))


@dataclass
class PolicyVersion:
    policy_id: str
    title: str
    issuer: str
    published_at: date
    effective_from: date
    effective_to: Optional[date] = None
    supersedes_policy_id: Optional[str] = None
    jurisdiction: str = "KR"
    policy_scope: str = "MORTGAGE_LTV"
    version: str = "1"
    status: PolicyStatus = PolicyStatus.DRAFT
    provenance: Provenance = Provenance.AI_DRAFT
    sources: list[SourceDocument] = field(default_factory=list)
    region_deltas: list[RegionDelta] = field(default_factory=list)
    rule_notes: list[RuleNote] = field(default_factory=list)
    notes: str = ""

    # --- 시점 해석 ---
    def is_active_at(self, as_of: date) -> bool:
        """이 시점에 유효한가. **CONFIRMED 만 유효하다** (LOCKED §4)."""
        if self.status is not PolicyStatus.CONFIRMED:
            return False
        if as_of < self.effective_from:
            return False
        return self.effective_to is None or as_of <= self.effective_to

    @property
    def is_pending(self) -> bool:
        """확정됐지만 아직 시행 전 — '다음 정책'."""
        return self.status is PolicyStatus.CONFIRMED

    def as_dict(self) -> dict:
        return {
            "policy_id": self.policy_id,
            "title": self.title,
            "issuer": self.issuer,
            "published_at": self.published_at.isoformat(),
            "effective_from": self.effective_from.isoformat(),
            "effective_to": self.effective_to.isoformat() if self.effective_to else None,
            "supersedes_policy_id": self.supersedes_policy_id,
            "jurisdiction": self.jurisdiction,
            "policy_scope": self.policy_scope,
            "version": self.version,
            "status": self.status.value,
            "provenance": self.provenance.value,
            "sources": [
                {"source_document_id": s.source_document_id, "title": s.title,
                 "source_hash": s.source_hash,
                 "retrieved_at": s.retrieved_at.isoformat() if s.retrieved_at else None,
                 "source_url": s.source_url, "filename": s.filename,
                 "byte_size": s.byte_size}
                for s in self.sources
            ],
            "region_deltas": [d.as_dict() for d in self.region_deltas],
            "rule_notes": [r.as_dict() for r in self.rule_notes],
            "notes": self.notes,
        }

    @staticmethod
    def from_dict(d: dict) -> "PolicyVersion":
        return PolicyVersion(
            policy_id=d["policy_id"], title=d["title"], issuer=d["issuer"],
            published_at=date.fromisoformat(d["published_at"]),
            effective_from=date.fromisoformat(d["effective_from"]),
            effective_to=date.fromisoformat(d["effective_to"]) if d.get("effective_to") else None,
            supersedes_policy_id=d.get("supersedes_policy_id"),
            jurisdiction=d.get("jurisdiction", "KR"),
            policy_scope=d.get("policy_scope", "MORTGAGE_LTV"),
            version=d.get("version", "1"),
            status=PolicyStatus(d.get("status", "DRAFT")),
            provenance=Provenance(d.get("provenance", "AI_DRAFT")),
            sources=[
                SourceDocument(
                    source_document_id=s["source_document_id"], title=s["title"],
                    source_hash=s["source_hash"],
                    retrieved_at=date.fromisoformat(s["retrieved_at"]) if s.get("retrieved_at") else None,
                    source_url=s.get("source_url"), filename=s.get("filename"),
                    byte_size=s.get("byte_size"))
                for s in d.get("sources", [])
            ],
            region_deltas=[RegionDelta.from_dict(x) for x in d.get("region_deltas", [])],
            rule_notes=[RuleNote.from_dict(x) for x in d.get("rule_notes", [])],
            notes=d.get("notes", ""),
        )
