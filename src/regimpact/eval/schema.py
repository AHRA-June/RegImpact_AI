"""골드 평가셋 스키마 (docs/00_BRIEF.md §11).

브리프가 요구하는 문항 필드를 그대로 타입으로 고정한다:
    질문/입력 · 골드 정답 · 근거 문서 · 원문 위치 · 평가 카테고리 ·
    기대 human escalation 여부 · 적용 정책 버전 · 관련 rule_id

**원문 위치**는 별도 offset 필드로 적지 않고 `citations[].quote`(verbatim)로 표현한다.
문자 offset은 원문 재추출 때 조용히 어긋나지만, verbatim 인용은 검증기가 매번 원문과
대조해 깨진 것을 즉시 드러낸다(`validate_items`). 위치의 진실은 문자열이지 숫자가 아니다.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Optional


class Category(str, Enum):
    """평가 카테고리 (브리프 §11)."""
    NORMAL = "NORMAL"                    # 원칙 규정
    EXCEPTION = "EXCEPTION"              # 예외(생애최초·서민실수요·정책대출 등)
    GRANDFATHERING = "GRANDFATHERING"    # 경과규정
    EFFECTIVE_DATE = "EFFECTIVE_DATE"    # 시행일·기준일
    REGION = "REGION"                    # 규제지역 지정·범위
    BORROWER_TYPE = "BORROWER_TYPE"      # 차주 유형(무주택·유주택·다주택)
    LOAN_PURPOSE = "LOAN_PURPOSE"        # 대출 목적·상품 범위
    CONFLICT = "CONFLICT"                # 규정 간 충돌·우선순위
    NO_CHANGE = "NO_CHANGE"              # 바뀌지 않은 것(오탐 유도)
    AMBIGUOUS = "AMBIGUOUS"              # 원문에 답이 없음 → escalation 기대


class Split(str, Enum):
    DEV = "DEV"                # 튜닝에 쓰는 유일한 셋
    LOCKED = "LOCKED"          # 최종 성능평가 — 개발 중 열람 금지
    CHALLENGE = "CHALLENGE"    # 적대적 평가 — 마지막에 1회
    TEMPORAL = "TEMPORAL"      # 시점 질의 — Policy-version Consistency 가동용 (DEV처럼 비봉인)


# 브리프 §11 "설계 철학": 예외·경과규정·시행일·충돌을 놓치는 것이 가장 무섭다.
HIGH_RISK_CATEGORIES = frozenset({
    Category.EXCEPTION, Category.GRANDFATHERING,
    Category.EFFECTIVE_DATE, Category.CONFLICT,
})


@dataclass(frozen=True)
class Citation:
    source_doc_id: str
    quote: str          # 원문 verbatim (공백 정규화 후 대조)


@dataclass(frozen=True)
class GoldItem:
    id: str
    split: Split
    category: Category
    question: str                       # 질문 / 입력
    gold_answer: str                    # 사람이 읽는 골드 정답
    gold_facts: tuple[str, ...]         # 자동 채점 앵커(답변에 반드시 포함돼야 할 사실 조각)
    citations: tuple[Citation, ...]     # 근거 문서 + 원문 위치
    expect_escalation: bool             # 기대되는 human escalation 여부
    policy_version: str                 # 적용 정책 버전
    rule_id: Optional[str] = None       # 관련 rule_id (룰엔진 경로 밖이면 None)
    authored_by: str = "ai_draft"       # ai_draft(🤖) → human_confirmed(✅)
    note: str = ""
    # 시점 질의 전용: 문항이 상정하는 조회 시점(YYYY-MM-DD). 있으면 Temporal Policy
    # Resolver의 답(current_policy)과 policy_version이 정합해야 한다(eval/temporal.py).
    # 문서 사실을 묻는 문항(시행일이 언제인가 등)은 조회 시점이 없으므로 None.
    as_of: Optional[str] = None

    @property
    def is_high_risk(self) -> bool:
        return self.category in HIGH_RISK_CATEGORIES

    def to_dict(self) -> dict:
        d = asdict(self)
        d["split"] = self.split.value
        d["category"] = self.category.value
        d["gold_facts"] = list(self.gold_facts)
        d["citations"] = [asdict(c) for c in self.citations]
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "GoldItem":
        return cls(
            id=d["id"],
            split=Split(d["split"]),
            category=Category(d["category"]),
            question=d["question"],
            gold_answer=d["gold_answer"],
            gold_facts=tuple(d.get("gold_facts", ())),
            citations=tuple(Citation(**c) for c in d.get("citations", ())),
            expect_escalation=bool(d["expect_escalation"]),
            policy_version=d["policy_version"],
            rule_id=d.get("rule_id"),
            authored_by=d.get("authored_by", "ai_draft"),
            note=d.get("note", ""),
            as_of=d.get("as_of"),
        )


@dataclass
class ValidationReport:
    """골드셋 무결성 검사 결과. errors가 비어야 셋을 쓸 수 있다."""
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    checked: int = 0

    @property
    def ok(self) -> bool:
        return not self.errors

    def summary(self) -> str:
        head = f"{self.checked}문항 검사 — {'✅ 통과' if self.ok else f'❌ 오류 {len(self.errors)}건'}"
        if self.warnings:
            head += f" · ⚠ 경고 {len(self.warnings)}건"
        return head
