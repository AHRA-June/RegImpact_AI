"""Assurance 4 dimension 원시 지표 계산 (결정론 오프라인).

기존 지표(citation·gold·regression)에 더해 **누락됐던 3종을 추가**해 4 dimension을 완성한다:
    ① Source Contradiction Rate — 인용은 grounded지만 주장한 LTV 값이 원문에 없는 비율(값 날조 프록시)
    ② Grandfathering Recall     — 골드 경과규정 항목 포착 비율(고위험, Change Completeness와 분리 노출)
    ③ Policy-version Consistency — 효력일 경계 시점 질의에서 엔진이 시점정합 버전을 반환하는 비율
                                   (독립 오라클로 검증 → 룰엔진 시점 해석의 일관성)
"""
from __future__ import annotations

import re
from datetime import date

from ..extractor.evaluate import _norm, check_citation_grounding, score_against_gold
from ..extractor.schema import RegChangeExtraction
from ..models import MortgageApplication
from ..rule_engine import evaluate
from ..tc_generator.oracle import expected_outcome

_PCT = re.compile(r"\d+\s*~\s*\d+%|\d+%")   # "70%", "60~70%"


def _pct_tokens(text) -> list[str]:
    if not text:
        return []
    return [_norm(t) for t in _PCT.findall(text)]


def source_contradiction_rate(extraction: RegChangeExtraction, sources: dict[str, str]) -> float:
    """인용이 grounded인 change 중, 주장한 LTV %값이 인용 원문에 없는 비율.

    '원문 근거 없는 수치 주장'(날조/모순의 결정론 프록시). 값이 없는 change는 분모에서 제외.
    """
    norm_sources = {k: _norm(v) for k, v in sources.items()}
    value_bearing = 0
    contradictions = 0
    for it in extraction.changes:
        tokens = _pct_tokens(it.before) + _pct_tokens(it.after)
        if not tokens:
            continue
        value_bearing += 1
        src = norm_sources.get(it.citation.source_doc_id, "")
        # 하나라도 원문에 없으면 모순/날조로 카운트
        if any(tok.replace(" ", "") not in src.replace(" ", "") for tok in tokens):
            contradictions += 1
    return contradictions / value_bearing if value_bearing else 0.0


def grandfathering_recall(extraction: RegChangeExtraction, gold: dict) -> float:
    """골드 경과규정(GRANDFATHERING) 항목 중 추출이 포착한 비율(고위험, 분리 노출).

    gold.required_changes 중 categories에 GRANDFATHERING 포함 항목만 대상.
    keywords 중 하나라도 추출 summary/after에 있으면 포착.
    """
    hay = [_norm(f"{c.summary} {c.after or ''}").lower() for c in extraction.changes]
    gf_items = [r for r in gold.get("required_changes", [])
                if "GRANDFATHERING" in (r.get("categories") or [])]
    if not gf_items:
        return 1.0
    hit = 0
    for r in gf_items:
        if any(any(kw.lower() in h for kw in r["keywords"]) for h in hay):
            hit += 1
    return hit / len(gf_items)


# 효력일 경계 시점정합 프로브 (regulatory_facts C02/C03: 7.1 효력)
_PROBE_REGIONS = ("GURI", "YONGIN_GIHEUNG", "HWASEONG_DONGTAN")
_PROBE_DATES = (date(2026, 6, 29), date(2026, 6, 30), date(2026, 7, 1), date(2026, 7, 2))


def policy_version_consistency() -> float:
    """효력일 경계 시점 질의에서 엔진이 시점정합 버전을 반환하는 비율.

    독립 오라클(expected_outcome)이 시점별 정답을 유도 → 엔진과 대조. 무주택 프로필로
    지역×날짜 격자를 훑어 규제 전/후 버전이 일관되게 뒤집히는지(6.30 非규제 → 7.1 규제) 검증.
    """
    agree = total = 0
    for region in _PROBE_REGIONS:
        for d in _PROBE_DATES:
            app = MortgageApplication(region_code=region, evaluation_date=d, house_count=0)
            eng = evaluate(app)
            orc = expected_outcome(app)
            total += 1
            if eng.status == orc.status and eng.max_ltv == orc.max_ltv:
                agree += 1
    return agree / total if total else 1.0


def compute_metrics(
    extraction: RegChangeExtraction,
    sources: dict[str, str],
    gold: dict,
    regression=None,
) -> dict[str, float]:
    """4 dimension 원시 지표를 모두 계산해 {key: value} 로 반환."""
    g = check_citation_grounding(extraction, sources)
    s = score_against_gold(extraction, gold)

    out: dict[str, float] = {
        # ① Source Grounding & Citation
        "citation_correctness": g.citation_correctness,
        "unsupported_claim_rate": g.unsupported_claim_rate,
        "source_contradiction_rate": source_contradiction_rate(extraction, sources),
        # ② Change & Exception Completeness
        "change_completeness": s.change_completeness,
        "exception_recall": s.exception_recall,
        "grandfathering_recall": grandfathering_recall(extraction, gold),
        # ③ Temporal / Policy-Version Consistency
        "effective_date_accuracy": 1.0 if s.effective_date_correct else 0.0,
        "region_completeness": 1.0 if s.regions_correct else 0.0,
        "policy_version_consistency": policy_version_consistency(),
    }

    # ④ Rule Regression & Conflict (regression 리포트가 있으면)
    if regression is not None:
        from ..tc_generator.generator import Category
        out["rule_regression_pass_rate"] = regression.pass_rate
        bnd = regression.category_pass_rate(Category.BOUNDARY)
        cfl = regression.category_pass_rate(Category.CONFLICT)
        out["boundary_pass_rate"] = 1.0 if bnd is None else bnd
        out["conflict_pass_rate"] = 1.0 if cfl is None else cfl
    return out
