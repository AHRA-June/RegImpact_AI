"""골드 평가셋 아이템 스키마 (docs/00_BRIEF.md §11).

브리프 §11이 명시한 8개 필드를 dataclass로 고정한다:
    질문/입력 · 골드정답 · 근거문서 · 원문위치 · 카테고리 · escalation · 정책버전 · rule_id

LOCKED §4(AI초안→사람확정): 각 아이템은 `status`로 확정 여부를 코드로 통제한다.
regulatory_facts.md의 사실이 아직 "검수대기"이므로, 여기서 파생한 골드 정답은
기본 AI_DRAFT다. 사람이 원문 대조로 확정하기 전까지 최종 성능 보고에 쓰지 않는다.

LOCKED §4 금지선: 채점은 결정적이어야 한다(LLM이 LLM을 채점 금지). 그래서 각 아이템은
가능하면 `scenario_input`(구조화 입력)을 들고 다녀 룰엔진으로 결정적 채점하거나,
`source_quote`(원문 verbatim)로 grounding 채점한다.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class Split(str, Enum):
    DEV = "DEV"                # 프롬프트·extractor 튜닝 (개발 중 사용 허용)
    LOCKED = "LOCKED"          # 최종 성능평가 (개발 중 튜닝 금지)
    CHALLENGE = "CHALLENGE"    # 예외·경계·충돌·모호 적대적 평가 (마지막 1회)


class GoldCategory(str, Enum):
    """브리프 §11 카테고리."""
    NORMAL = "NORMAL"
    EXCEPTION = "EXCEPTION"
    GRANDFATHERING = "GRANDFATHERING"
    EFFECTIVE_DATE = "EFFECTIVE_DATE"
    REGION = "REGION"
    BORROWER_TYPE = "BORROWER_TYPE"
    LOAN_PURPOSE = "LOAN_PURPOSE"
    CONFLICT = "CONFLICT"
    NO_CHANGE = "NO_CHANGE"
    AMBIGUOUS = "AMBIGUOUS"


# CHALLENGE에서 가중하는 카테고리 (브리프 §11 설계철학)
CHALLENGE_WEIGHTED = frozenset({
    GoldCategory.EXCEPTION, GoldCategory.GRANDFATHERING,
    GoldCategory.EFFECTIVE_DATE, GoldCategory.CONFLICT,
})


class Status(str, Enum):
    AI_DRAFT = "AI_DRAFT"              # AI 1차 초안 (사람 확정 대기) — 기본값
    HUMAN_CONFIRMED = "HUMAN_CONFIRMED"  # 사람이 원문 대조로 확정


@dataclass
class GoldItem:
    """골드 평가셋 1문항 (브리프 §11 8필드 + LOCKED §4 status + 추적 메타)."""
    item_id: str
    split: Split
    category: GoldCategory
    question: str                                # 질문 / 입력 (자연어)
    gold_answer: str                             # 골드 정답
    policy_version: str                          # 적용 정책 버전
    expects_escalation: bool                     # 기대 human escalation 여부
    source_doc_id: Optional[str] = None          # 근거 문서 id
    source_quote: Optional[str] = None           # 원문 위치(verbatim, grounding 채점용)
    rule_id: Optional[str] = None                # 관련 rule_id

    # 결정적 채점을 위한 구조화 입력(있으면 룰엔진으로 채점) — LOCKED §4 금지선 준수
    scenario_input: Optional[dict] = None        # MortgageApplication 필드 dict
    expected_ltv: Optional[float] = None         # 기대 max_ltv (scenario)
    expected_status: Optional[str] = None        # 기대 EvaluationStatus 값 (scenario)
    answer_keywords: list[str] = field(default_factory=list)  # 정답 확인 키워드(비-scenario)

    status: Status = Status.AI_DRAFT
    claim_refs: list[str] = field(default_factory=list)       # regulatory_facts claim id (C01..)
    note: Optional[str] = None

    @property
    def is_scenario(self) -> bool:
        return self.scenario_input is not None

    @classmethod
    def from_dict(cls, d: dict) -> "GoldItem":
        return cls(
            item_id=d["item_id"],
            split=Split(d["split"]),
            category=GoldCategory(d["category"]),
            question=d["question"],
            gold_answer=d["gold_answer"],
            policy_version=d["policy_version"],
            expects_escalation=bool(d["expects_escalation"]),
            source_doc_id=d.get("source_doc_id"),
            source_quote=d.get("source_quote"),
            rule_id=d.get("rule_id"),
            scenario_input=d.get("scenario_input"),
            expected_ltv=d.get("expected_ltv"),
            expected_status=d.get("expected_status"),
            answer_keywords=list(d.get("answer_keywords", [])),
            status=Status(d.get("status", "AI_DRAFT")),
            claim_refs=list(d.get("claim_refs", [])),
            note=d.get("note"),
        )

    def to_dict(self) -> dict:
        out = {
            "item_id": self.item_id,
            "split": self.split.value,
            "category": self.category.value,
            "question": self.question,
            "gold_answer": self.gold_answer,
            "policy_version": self.policy_version,
            "expects_escalation": self.expects_escalation,
            "source_doc_id": self.source_doc_id,
            "source_quote": self.source_quote,
            "rule_id": self.rule_id,
            "scenario_input": self.scenario_input,
            "expected_ltv": self.expected_ltv,
            "expected_status": self.expected_status,
            "answer_keywords": self.answer_keywords,
            "status": self.status.value,
            "claim_refs": self.claim_refs,
            "note": self.note,
        }
        return {k: v for k, v in out.items() if v is not None and v != []}


_GOLDSET_DIR = Path(__file__).resolve().parents[3] / "docs" / "eval" / "goldset"
_SPLIT_FILES = {
    Split.DEV: "dev.jsonl",
    Split.LOCKED: "locked.jsonl",
    Split.CHALLENGE: "challenge.jsonl",
}


def load_split(split: Split, goldset_dir: str | Path | None = None) -> list[GoldItem]:
    """한 split 파일(jsonl)을 로드한다. 파일이 없으면 빈 리스트."""
    base = Path(goldset_dir) if goldset_dir else _GOLDSET_DIR
    path = base / _SPLIT_FILES[split]
    if not path.exists():
        return []
    items: list[GoldItem] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("//"):
            continue
        items.append(GoldItem.from_dict(json.loads(line)))
    return items


def load_goldset(
    goldset_dir: str | Path | None = None,
    splits: Optional[list[Split]] = None,
) -> list[GoldItem]:
    """여러 split을 로드한다. 기본은 DEV만(개발 중 LOCKED/CHALLENGE 미개봉 — 브리프 §12).

    LOCKED/CHALLENGE를 명시적으로 요청할 때만 로드해 누수를 구조적으로 방지한다.
    """
    splits = splits if splits is not None else [Split.DEV]
    items: list[GoldItem] = []
    for sp in splits:
        items.extend(load_split(sp, goldset_dir))
    return items
