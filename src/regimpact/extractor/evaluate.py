"""Assurance 지표 — 추출 결과를 검증한다 (docs/metrics_spec.md).

두 축:
1) Citation grounding (deterministic, 오프라인): 인용 quote가 원문에 실제로 존재하는가?
   → Citation Correctness / Unsupported Claim Rate의 기반. LLM이 원문을 지어냈는지 실측.
2) Gold 대조: Change Completeness / Exception Recall — 사람이 확정한 정답지와 비교.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from .schema import RegChangeExtraction, RegChangeItem

_EVAL_DIR = Path(__file__).resolve().parents[3] / "docs" / "eval"
GOLD_PATH = _EVAL_DIR / "regchange_gold_6_30.json"
# RegChange Extractor 1회 실제 LLM 실행 산출물 (claude-opus-4-8이 원문만 읽고 생성).
RECORDED_EXTRACTION_PATH = _EVAL_DIR / "regchange_extraction_6_30.json"


def load_gold(path: str | Path | None = None) -> dict:
    """RegChange 골드 정답지(사람 확정, LOCKED §4)를 로드한다."""
    return json.loads(Path(path or GOLD_PATH).read_text(encoding="utf-8"))


def load_recorded_extraction(path: str | Path | None = None):
    """실측 추출 산출물을 로드한다. 없으면 None(→ Assurance '실측 대기')."""
    from .schema import RegChangeExtraction

    p = Path(path or RECORDED_EXTRACTION_PATH)
    if not p.exists():
        return None
    return RegChangeExtraction.from_dict(json.loads(p.read_text(encoding="utf-8")))


def _norm(s: str) -> str:
    """공백·개행을 단일 공백으로 정규화 (추출 텍스트 vs 원문 대조용)."""
    return re.sub(r"\s+", " ", s).strip()


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


@dataclass
class MeasuredAssurance:
    """실측 추출 1회에 대한 Assurance 지표(결정론적 재계산). RegChange DEEP dimension ①②③."""
    n_changes: int
    citation_correctness: float       # ① grounding
    unsupported_claim_rate: float
    change_completeness: float        # ② 완전성
    exception_recall: float           # ③ 예외 재현율
    grandfathering_captured: bool     # ③ 경과규정 포착
    effective_date_correct: bool
    regions_correct: bool
    model: str = "unknown"
    run_date: str = "unknown"


def measured_assurance(
    extraction=None, sources: dict[str, str] | None = None, gold: dict | None = None,
    meta: dict | None = None,
) -> "MeasuredAssurance | None":
    """기록된(또는 주어진) 추출을 결정론적 채점기로 재계산해 실측 지표를 낸다.

    추출 산출물이 없으면 None → Assurance 화면/리포트는 '실측 대기'로 표시.
    지표는 저장값이 아니라 항상 (추출 + 원문 + gold)에서 재계산 → 재현 가능·신뢰.
    """
    from .sources import load_sources

    if extraction is None:
        extraction = load_recorded_extraction()
        if extraction is None:
            return None
        if meta is None:
            import json as _json
            raw = _json.loads(RECORDED_EXTRACTION_PATH.read_text(encoding="utf-8"))
            meta = raw.get("_meta", {})
    sources = sources if sources is not None else load_sources()
    gold = gold if gold is not None else load_gold()
    meta = meta or {}

    g = check_citation_grounding(extraction, sources)
    s = score_against_gold(extraction, gold)
    gf_captured = any(c.category == "GRANDFATHERING" for c in extraction.changes)
    return MeasuredAssurance(
        n_changes=len(extraction.changes),
        citation_correctness=g.citation_correctness,
        unsupported_claim_rate=g.unsupported_claim_rate,
        change_completeness=s.change_completeness,
        exception_recall=s.exception_recall,
        grandfathering_captured=gf_captured,
        effective_date_correct=s.effective_date_correct,
        regions_correct=s.regions_correct,
        model=meta.get("model", "unknown"),
        run_date=meta.get("run_date", "unknown"),
    )
