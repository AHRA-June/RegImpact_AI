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
    """인용 대조용 정규화 — 공백을 **전부 제거**한다.

    처음에는 공백을 단일 공백으로 축약했는데, 그 기준으로 haiku-4-5의 인용 25%가
    "원문에 없음"으로 잡혔다. 실제로 확인해 보니 전부 원문에 있었고, 원인은 PDF/HWP 추출본이
    문장은 물론 **단어 중간에서도 줄을 바꾼다**는 것이었다("규제\n지역 내"). 모델이 이를 자연스러운
    "규제지역 내"로 옮겨 적으면 축약 기준에서는 불일치가 된다.

    공백은 추출 아티팩트이지 내용이 아니므로 대조에서 제외한다. 이 기준에서도 **다른 단어를
    지어낸 인용은 여전히 걸린다** — 환각 탐지력은 잃지 않는다.
    (2026-08-18 정정. 이전 기준으로 보고된 haiku Unsupported 25%는 측정 오차였다.)
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
    norm_sources = {doc_id: _norm(text) for doc_id, text in sources.items()}
    grounded = 0
    ungrounded: list[RegChangeItem] = []
    for item in extraction.changes:
        src = norm_sources.get(item.citation.source_doc_id)
        quote = _norm(item.citation.quote)
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
      required_changes: [{id, keywords:[...]}]            # keywords 중 하나라도 있으면 포착
                          또는 [{id, transition:{before,after}}]  # 값 전이를 before/after 필드에 직접 대조
      exceptions: [{name, keywords:[...]}]
      effective_from: "YYYY-MM-DD"
      target_regions: [...]
    """
    hay = [
        _norm(f"{c.summary} {c.before or ''} {c.after or ''}").lower()
        for c in extraction.changes
    ]

    def _transition_found(spec: dict) -> bool:
        """값 전이(before→after)를 항목의 before/after 필드에 **직접** 대조한다.

        키워드는 summary·before·after를 이어붙인 문자열을 훑기 때문에 "70%가 있다"까지만 볼 수
        있고, 그 70%가 시행 전 값인지 생애최초 값인지 구분하지 못한다. 이 제품의 핵심 주장이
        "무엇이 무엇으로 바뀌었는가"인 이상, 전이는 전이로 채점해야 한다.
        """
        want_b, want_a = _norm(spec.get("before", "")).lower(), _norm(spec.get("after", "")).lower()
        for c in extraction.changes:
            got_b, got_a = _norm(c.before or "").lower(), _norm(c.after or "").lower()
            if (not want_b or want_b == got_b) and (not want_a or want_a == got_a):
                if want_b or want_a:
                    return True
        return False

    def _found(keywords: list[str], categories: list[str] | None = None) -> bool:
        """키워드 중 **하나라도** 포착되면 히트. 여러 사실을 한 항목에 묶지 말고 별도 entry로 나눈다.

        키워드도 haystack과 같은 정규화를 거쳐야 한다 — 한쪽만 정규화하면 공백이 든 키워드
        ("7월 1일")가 영원히 매칭되지 않는다.
        """
        cats = {c.category for c in extraction.changes}
        if categories and not (set(categories) & cats):
            # 카테고리 힌트가 있으면 우선 확인하되, 키워드 매칭이 본판정
            pass
        return any(any(_norm(kw).lower() in h for kw in keywords) for h in hay)

    missed_changes, hit_changes = [], 0
    for req in gold.get("required_changes", []):
        if "transition" in req:
            hit = _transition_found(req["transition"])
        else:
            hit = _found(req["keywords"], req.get("categories"))
        if hit:
            hit_changes += 1
        else:
            # dict.get의 기본값은 **먼저 평가**되므로 req["keywords"][0]를 그대로 쓰면
            # keywords가 빈 entry(전이 전용)에서 IndexError가 난다.
            kws = req.get("keywords") or []
            missed_changes.append(req.get("id") or (kws[0] if kws else "?"))
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
