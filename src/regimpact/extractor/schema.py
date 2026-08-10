"""RegChange Extractor 구조화 출력 스키마 (docs/00_BRIEF.md §9, §24-9).

모든 AI 출력은 구조화 schema로 정의한다. 여기서는 Pydantic 대신 dataclass +
JSON Schema dict를 쓴다(의존성 최소화 + structured output `output_config.format` 호환).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

# 변경 카테고리 — 평가셋 카테고리와 정렬 (docs/00_BRIEF.md §11)
CATEGORIES = [
    "LTV",             # 담보인정비율 변경
    "EXCEPTION",       # 예외(생애최초·서민실수요·정책대출 등)
    "GRANDFATHERING",  # 경과규정
    "EFFECTIVE_DATE",  # 시행일
    "REGION",          # 규제지역 지정
    "SCOPE_LIMIT",     # 전세/신용/중도금/사업자 등 제한(Discovery)
]

CITATION_SCHEMA = {
    "type": "object",
    "properties": {
        "source_doc_id": {"type": "string"},
        "quote": {"type": "string"},
    },
    "required": ["source_doc_id", "quote"],
    "additionalProperties": False,
}

ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "category": {"type": "string", "enum": CATEGORIES},
        "summary": {"type": "string"},
        "before": {"type": ["string", "null"]},
        "after": {"type": ["string", "null"]},
        "citation": CITATION_SCHEMA,
        "confidence": {"type": "number"},
    },
    "required": ["category", "summary", "before", "after", "citation", "confidence"],
    "additionalProperties": False,
}

# structured output용 JSON Schema (additionalProperties:false, 모든 키 required)
REGCHANGE_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "policy_id": {"type": "string"},
        "effective_from": {"type": ["string", "null"]},   # ISO date
        "target_regions": {"type": "array", "items": {"type": "string"}},
        "changes": {"type": "array", "items": ITEM_SCHEMA},
    },
    "required": ["policy_id", "effective_from", "target_regions", "changes"],
    "additionalProperties": False,
}


@dataclass
class Citation:
    source_doc_id: str
    quote: str

    @classmethod
    def from_dict(cls, d: dict) -> "Citation":
        return cls(source_doc_id=d["source_doc_id"], quote=d["quote"])


@dataclass
class RegChangeItem:
    category: str
    summary: str
    citation: Citation
    before: Optional[str] = None
    after: Optional[str] = None
    confidence: float = 1.0

    @classmethod
    def from_dict(cls, d: dict) -> "RegChangeItem":
        return cls(
            category=d["category"],
            summary=d["summary"],
            citation=Citation.from_dict(d["citation"]),
            before=d.get("before"),
            after=d.get("after"),
            confidence=float(d.get("confidence", 1.0)),
        )


@dataclass
class RegChangeExtraction:
    policy_id: str
    target_regions: list[str] = field(default_factory=list)
    effective_from: Optional[str] = None
    changes: list[RegChangeItem] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict) -> "RegChangeExtraction":
        return cls(
            policy_id=d["policy_id"],
            effective_from=d.get("effective_from"),
            target_regions=list(d.get("target_regions", [])),
            changes=[RegChangeItem.from_dict(c) for c in d.get("changes", [])],
        )
