"""검증보고서의 근거 수집 — 파이프라인을 **실제로 돌려** 수치를 모은다.

보고서에 손으로 적은 숫자가 하나라도 있으면 그 보고서는 시간이 지나면 거짓말이 된다.
그래서 여기서 한 번 돌리고, 렌더러는 이 객체에서만 값을 읽는다
(`tests/test_validation_report.py` 가 렌더러에 도메인 수치 리터럴이 없는지 확인한다).

브리프 §18 "코어 완성의 정의"의 종착점. 재현: `python examples/build_validation_report.py`
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional

from ..audit import Action, AuditLog
from ..discrimination import DiscriminationReport, discriminate_pipeline
from ..eval.goldset import load_split, split_stats
from ..eval.schema import Split
from ..eval.temporal import check_temporal_gold
from ..extractor import (
    check_citation_grounding,
    extract_regchange,
    load_sources,
    score_against_gold,
)
from ..extractor.backends import resolve_completion
from ..extractor.postprocess import normalize_regions
from ..impact import (
    analyze_portfolio,
    build_impact_matrix,
    build_portfolio,
    composition,
    derive_rule_diff,
)
from ..impact.portfolio import DEFAULT_SEED, DEFAULT_SIZE
from ..policy import (
    check_registry_matches_baseline,
    load_registry,
    preview_region_impact,
    previous_policy,
    timeline,
)
from ..proposal import (
    apply_consistency_status,
    build_proposal_from_extraction,
    check_proposal_consistency,
)
from ..regions import REGION_VERSIONS
from ..tc_generator import run_regression

REPO = Path(__file__).resolve().parents[3]
DEFAULT_RUN = REPO / "docs" / "eval" / "runs" / "run_perdoc_sonnet5.json"
GOLD_PATH = REPO / "docs" / "eval" / "regchange_gold_6_30.json"
SOURCES_MD = REPO / "docs" / "sources" / "SOURCES.md"


@dataclass
class ValidationEvidence:
    """한 번의 실행에서 나온 모든 실측치. 보고서는 여기서만 값을 읽는다."""

    generated_at: str
    provider: str
    run_path: str

    sources: dict
    source_table: str                       # SOURCES.md 의 해시 표 (원문 그대로)

    extraction: object
    grounding: object
    gold: dict
    gold_score: object
    region_mapping: dict
    region_unmapped: list

    registry: object
    policy_timeline: list
    this_policy: object
    previous: object
    region_preview: list
    drift: object

    portfolio: list
    portfolio_composition: dict
    impact: object
    matrix: object
    rule_diff: list

    regression: object
    proposal: object
    consistency: object
    discrimination: DiscriminationReport

    split_stats: list
    audit: AuditLog
    scorecard: object = None

    # 시점 질의 골드 ⟷ Temporal Policy Resolver 대조. `temporal_confirmed` 가 False 면
    # 골드가 아직 🤖 초안이라는 뜻이고, 그때는 대조가 정합이어도 **수치를 보고하지 않는다**
    # (스코어카드가 이 플래그를 보고 미측정으로 남긴다). 검수가 끝나 authored_by 가
    # human_confirmed 로 바뀌면 **코드를 고치지 않아도** 측정이 켜진다.
    temporal: object = None
    temporal_confirmed: bool = False

    baseline_region_count: int = 0
    notes: list[str] = field(default_factory=list)


def collect(
    *,
    provider: str = "replay",
    run_path: Optional[Path] = None,
    size: int = DEFAULT_SIZE,
    seed: int = DEFAULT_SEED,
    generated_at: Optional[str] = None,
    js_port_agreement: Optional[float] = None,
) -> ValidationEvidence:
    """파이프라인을 한 번 관통 실행하고 근거를 모은다."""
    run = Path(run_path or DEFAULT_RUN)
    audit = AuditLog()

    # 1. 원문
    sources = load_sources()
    for doc_id, text in sources.items():
        audit.record(Action.SOURCE_INGESTED, doc_id, {"chars": len(text)})

    # 2. 추출 + Citation Assurance
    kwargs = {"run_path": str(run)} if provider == "replay" else {}
    complete = resolve_completion(provider, model=None, **kwargs)
    raw = extract_regchange(sources, complete=complete)
    norm = normalize_regions(raw)
    extraction = norm.normalized
    audit.record(Action.EXTRACTION, extraction.policy_id,
                 {"provider": provider, "changes": len(extraction.changes)})

    grounding = check_citation_grounding(extraction, sources)
    gold = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    gold_score = score_against_gold(extraction, gold)

    # 3. 정책 시점 해석
    registry = load_registry()
    as_of = date.fromisoformat(extraction.effective_from or "2026-07-01")
    this_policy = registry.get(extraction.policy_id)
    drift = check_registry_matches_baseline(registry)
    audit.record(Action.POLICY_RESOLVED, "policy_registry",
                 {"policies": len(registry.policies), "drift_ok": drift.ok})

    # 4. 포트폴리오 · 고객 영향
    portfolio = build_portfolio(size=size, seed=seed)
    impact = analyze_portfolio(portfolio)
    audit.record(Action.IMPACT_ANALYZED, extraction.policy_id,
                 {"portfolio": size, "decision_coverage": round(impact.decision_coverage, 4)})

    # 5. 룰 회귀 (독립 오라클)
    regression = run_regression()
    audit.record(Action.REGRESSION_RUN, "tc_generator",
                 {"total": regression.total, "pass_rate": regression.pass_rate})

    # 6. 구조화 변경안 + 엔진 교차검증
    rule_diff = derive_rule_diff()
    proposal = build_proposal_from_extraction(extraction)
    # 시점 질의 골드 대조 — 골드가 아직 🤖 초안이면 수치를 쓰지 않는다(플래그로 전달).
    temporal_items = load_split(Split.TEMPORAL)
    temporal = check_temporal_gold(temporal_items)
    temporal_confirmed = bool(temporal_items) and all(
        i.authored_by == "human_confirmed" for i in temporal_items)

    consistency = check_proposal_consistency(proposal, rule_diff=rule_diff)
    proposal = apply_consistency_status(proposal, consistency)
    audit.record(Action.PROPOSAL_CREATED, proposal.rule_id,
                 {"status": proposal.status.value, "consistency": consistency.summary()})

    # 7. 매트릭스
    matrix = build_impact_matrix(extraction, impact, grounding=grounding,
                                 regression=regression)
    audit.record(Action.ASSURANCE_SCORED, extraction.policy_id, {
        "citation_correctness": grounding.citation_correctness,
        "automation_rate": round(matrix.automation_rate, 4),
    })

    # 8. 판별력 (오류 주입 후 재측정)
    discrimination = discriminate_pipeline(extraction, sources, gold, rule_diff=rule_diff)

    evidence = ValidationEvidence(
        generated_at=generated_at or "",
        provider=provider,
        run_path=str(run.relative_to(REPO)) if run.is_relative_to(REPO) else str(run),
        sources=sources,
        source_table=_source_table(),
        extraction=extraction,
        grounding=grounding,
        gold=gold,
        gold_score=gold_score,
        region_mapping=dict(norm.mapping),
        region_unmapped=list(norm.unmapped),
        registry=registry,
        policy_timeline=timeline(registry, as_of),
        this_policy=this_policy,
        previous=previous_policy(registry, this_policy) if this_policy else None,
        region_preview=preview_region_impact(this_policy) if this_policy else [],
        drift=drift,
        portfolio=portfolio,
        portfolio_composition=composition(portfolio),
        impact=impact,
        matrix=matrix,
        rule_diff=rule_diff,
        regression=regression,
        proposal=proposal,
        consistency=consistency,
        temporal=temporal,
        temporal_confirmed=temporal_confirmed,
        discrimination=discrimination,
        split_stats=[split_stats(s) for s in Split],
        audit=audit,
        baseline_region_count=len(REGION_VERSIONS),
    )

    # Assurance 스코어카드 — 실측을 임계와 대조한다.
    # js_port_agreement 는 별도 도구(node)가 필요하므로 여기서는 넣지 않는다.
    # 대조를 돌리지 않았으면 통과가 아니라 **미측정**으로 남는 것이 맞다.
    from ..assurance.scorecard import score as _score
    evidence.scorecard = _score(evidence, js_port_agreement=js_port_agreement)
    return evidence


def _source_table() -> str:
    """SOURCES.md 의 해시 표를 그대로 가져온다(원문 무결성 절에 인용)."""
    text = SOURCES_MD.read_text(encoding="utf-8")
    rows = [ln for ln in text.splitlines() if ln.startswith("| ")]
    return "\n".join(rows)
