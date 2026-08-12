"""Assurance 지표 — 추출 결과를 검증한다 (docs/metrics_spec.md).

두 축:
1) Citation grounding (deterministic, 오프라인): 인용 quote가 원문에 실제로 존재하는가?
   → Citation Correctness / Unsupported Claim Rate의 기반. LLM이 원문을 지어냈는지 실측.
2) Gold 대조: Change Completeness / Exception Recall — 사람이 확정한 정답지와 비교.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .schema import RegChangeExtraction, RegChangeItem


def _norm(s: str) -> str:
    """공백·개행을 단일 공백으로 정규화 (추출 텍스트 vs 원문 대조용)."""
    return re.sub(r"\s+", " ", s).strip()


def _squish(s: str) -> str:
    """모든 공백을 제거해 layout 무관 비교용 문자열을 만든다.

    근거: 원문은 PDF/HWP에서 추출돼 문장 중간에 줄바꿈이 섞인다(예: '전일(6.30일)'↵'까지').
    단순 공백정규화는 그 줄바꿈을 공백으로 바꿔, 모델이 정확히 인용해도('(6.30일)까지')
    substring 매칭에 실패해 **정확한 인용을 환각으로 오탐**한다. 공백을 전부 제거하면
    이 아티팩트가 사라진다(실제 지어낸 인용은 공백을 지워도 원문에 없으므로 여전히 잡힘).
    """
    return re.sub(r"\s+", "", s)


@dataclass
class GroundingReport:
    total: int
    grounded: int
    ungrounded: list[RegChangeItem]

    @property
    def citation_correctness(self) -> float:
        return self.grounded / self.total if self.total else 1.0

    @property
    def unsupported_claim_rate(self) -> float:
        return len(self.ungrounded) / self.total if self.total else 0.0


def check_citation_grounding(
    extraction: RegChangeExtraction, sources: dict[str, str]
) -> GroundingReport:
    """각 항목의 citation.quote가 해당 원문에 verbatim으로 존재하는지 확인한다.

    존재하지 않으면 unsupported(환각 가능성)로 분류. 완전 deterministic — 오프라인 실측.
    """
    squished_sources = {doc_id: _squish(text) for doc_id, text in sources.items()}
    grounded = 0
    ungrounded: list[RegChangeItem] = []
    for item in extraction.changes:
        src = squished_sources.get(item.citation.source_doc_id)
        quote = _squish(item.citation.quote)
        if src is not None and quote and quote in src:
            grounded += 1
        else:
            ungrounded.append(item)
    return GroundingReport(total=len(extraction.changes), grounded=grounded, ungrounded=ungrounded)


@dataclass
class GoldReport:
    change_completeness: float          # 골드 필수 변경 중 포착 비율
    exception_recall: float             # 골드 예외 중 포착 비율
    effective_date_correct: bool
    regions_correct: bool
    missed_changes: list[str]
    missed_exceptions: list[str]


def score_against_gold(extraction: RegChangeExtraction, gold: dict) -> GoldReport:
    """사람이 확정한 골드 정답지와 비교해 완전성·재현율을 계산한다.

    gold 형식(docs/eval/regchange_gold_6_30.json):
      required_changes: [{category, keywords:[...]}]  # keywords 중 하나라도 summary/after에 있으면 포착
      exceptions: [{name, keywords:[...]}]
      effective_from: "YYYY-MM-DD"
      target_regions: [...]
    """
    hay = [
        _norm(f"{c.summary} {c.before or ''} {c.after or ''}").lower()
        for c in extraction.changes
    ]

    def _found(keywords: list[str], categories: list[str] | None = None) -> bool:
        cats = {c.category for c in extraction.changes}
        if categories and not (set(categories) & cats):
            # 카테고리 힌트가 있으면 우선 확인하되, 키워드 매칭이 본판정
            pass
        return any(any(kw.lower() in h for kw in keywords) for h in hay)

    missed_changes, hit_changes = [], 0
    for req in gold.get("required_changes", []):
        if _found(req["keywords"], req.get("categories")):
            hit_changes += 1
        else:
            missed_changes.append(req.get("id", req["keywords"][0]))
    total_changes = len(gold.get("required_changes", [])) or 1

    missed_exc, hit_exc = [], 0
    for exc in gold.get("exceptions", []):
        if _found(exc["keywords"]):
            hit_exc += 1
        else:
            missed_exc.append(exc["name"])
    total_exc = len(gold.get("exceptions", [])) or 1

    regions_correct = set(extraction.target_regions) >= set(gold.get("target_regions", []))
    eff_correct = (extraction.effective_from or "") == gold.get("effective_from", "")

    return GoldReport(
        change_completeness=hit_changes / total_changes,
        exception_recall=hit_exc / total_exc,
        effective_date_correct=eff_correct,
        regions_correct=regions_correct,
        missed_changes=missed_changes,
        missed_exceptions=missed_exc,
    )
