"""6·30 시나리오 End-to-End 파이프라인 (docs/00_BRIEF.md §18 '코어 완성의 정의').

    Source Snapshot → Policy Version Resolution → Before/After Change Extraction
    → Impact Matrix → Customer Impact → Structured Rule Proposal → Test Cases
    → Deterministic Rule Regression → Assurance Evaluation → Human Review → Validation Report

**각 단계의 실행 여부를 숨기지 않는다.** LLM 추출은 API 키가 있을 때만 돌고, 없으면
`MISSING` 으로 남는다 — 안 돌린 단계를 돌린 것처럼 보이게 만드는 순간 이 파이프라인은
포트폴리오가 아니라 마케팅이 된다. 키 없이도 나머지 9단계는 전부 실제로 돈다.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

from ..extractor import (
    check_citation_grounding,
    extract_regchange,
    load_sources,
    score_against_gold,
)
from ..extractor.schema import RegChangeExtraction
from ..regions import regulated_codes
from ..tc_generator import RegressionReport, generate_all, run_regression
from .customer_impact import AFTER_AS_OF, BEFORE_AS_OF, CustomerImpactReport, analyze_customer_impact
from .matrix import ImpactMatrix, build_impact_matrix
from .portfolio import build_portfolio

REPO = Path(__file__).resolve().parents[3]


class StageStatus(str, Enum):
    DONE = "완료"
    MISSING = "미실행"          # 선행조건(API 키 등) 부재 — 채워넣지 않는다
    ATTENTION = "확인 필요"      # 돌았으나 사람 검토가 필요한 결과


@dataclass
class Stage:
    name: str
    status: StageStatus
    detail: str
    metrics: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class RuleChangeProposal:
    """구조화 Rule Change Proposal 1건 — 포트폴리오에서 실제로 관측된 rule_id 전이."""
    rule_id_before: Optional[str]
    rule_id_after: Optional[str]
    ltv_before: Optional[float]
    ltv_after: Optional[float]
    affected: float
    segments: tuple[str, ...]
    source_policy_ids: tuple[str, ...]
    requires_human_approval: bool = True     # LOCKED §4·§9 — 항상 사람 확정

    @property
    def label(self) -> str:
        return f"{self.rule_id_before} → {self.rule_id_after}"


@dataclass
class E2EResult:
    stages: list[Stage]
    source_digests: dict[str, str]
    policy_version_diff: dict[str, list[str]]
    extraction: Optional[RegChangeExtraction]
    grounding: Any
    gold_score: Any
    impact: CustomerImpactReport
    regression: RegressionReport
    proposals: list[RuleChangeProposal]
    matrix: ImpactMatrix

    @property
    def completed(self) -> bool:
        return all(s.status is not StageStatus.MISSING for s in self.stages)

    def stage(self, name: str) -> Optional[Stage]:
        return next((s for s in self.stages if s.name == name), None)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _proposals_from_impact(impact: CustomerImpactReport) -> list[RuleChangeProposal]:
    """관측된 전이별로 Rule Change Proposal 을 만든다(엔진 산출 → 사람 확정 대상)."""
    grouped: dict[str, list] = {}
    for r in impact.rows:
        if r.impacted:
            grouped.setdefault(r.transition, []).append(r)

    out: list[RuleChangeProposal] = []
    for _label, items in sorted(grouped.items(), key=lambda kv: -len(kv[1])):
        head = items[0]
        out.append(RuleChangeProposal(
            rule_id_before=head.before.applicable_rule_id,
            rule_id_after=head.after.applicable_rule_id,
            ltv_before=head.before.max_ltv,
            ltv_after=head.after.max_ltv,
            affected=sum(i.row.weight for i in items),
            segments=tuple(sorted({f"{i.row.region_group} / {i.row.borrower.label}" for i in items})),
            source_policy_ids=tuple(head.after.source_policy_ids),
        ))
    return out


def run_e2e(
    *,
    complete: Optional[Callable[[str, str], dict]] = None,
    gold: Optional[dict] = None,
) -> E2EResult:
    """6·30 시나리오를 끝까지 관통시킨다.

    complete: LLM 호출 함수. None 이면 RegChange 추출·Citation Assurance 단계는 `MISSING`.
    """
    stages: list[Stage] = []

    # 1. Source Snapshot
    sources = load_sources()
    digests = {doc_id: _sha256(text)[:16] for doc_id, text in sources.items()}
    stages.append(Stage(
        "Source Snapshot",
        StageStatus.DONE if sources else StageStatus.MISSING,
        f"공문 원문 {len(sources)}건 로드 · SHA-256 기록",
        {doc_id: d for doc_id, d in digests.items()},
    ))

    # 2. Policy Version Resolution — 시행 전/후 규제지역 집합 차이
    before_codes = set(regulated_codes(BEFORE_AS_OF))
    after_codes = set(regulated_codes(AFTER_AS_OF))
    diff = {
        "added": sorted(after_codes - before_codes),
        "removed": sorted(before_codes - after_codes),
        "unchanged_count": [str(len(before_codes & after_codes))],
    }
    stages.append(Stage(
        "Policy Version Resolution",
        StageStatus.DONE,
        f"{BEFORE_AS_OF} 규제 {len(before_codes)}곳 → {AFTER_AS_OF} 규제 {len(after_codes)}곳",
        {"신규 지정": ", ".join(diff["added"]) or "없음",
         "지정 해제": ", ".join(diff["removed"]) or "없음",
         "변동 없음": f"{len(before_codes & after_codes)}곳"},
    ))

    # 3. Before/After Change Extraction (LLM) + 9. Assurance 일부
    extraction = grounding = gold_score = None
    if complete is not None:
        extraction = extract_regchange(sources, complete=complete)
        grounding = check_citation_grounding(extraction, sources)
        if gold:
            gold_score = score_against_gold(extraction, gold)
        stages.append(Stage(
            "Before/After Change Extraction",
            StageStatus.DONE,
            f"변경 {len(extraction.changes)}건 추출 (구조화 출력)",
            {"시행일": str(extraction.effective_from),
             "대상지역": ", ".join(extraction.target_regions)},
        ))
    else:
        stages.append(Stage(
            "Before/After Change Extraction",
            StageStatus.MISSING,
            "LLM 미실행 — ANTHROPIC_API_KEY 없음. 근거는 사람 확정 골드로 대체하며 "
            "매트릭스의 원문 인용 행은 '사람 확정(골드)' 출처로 표시된다.",
        ))

    # 5. Customer Impact
    portfolio = build_portfolio()
    impact = analyze_customer_impact(portfolio)
    no_event = impact.no_event_only()
    stages.append(Stage(
        "Customer Impact",
        StageStatus.ATTENTION if impact.escalation_rate else StageStatus.DONE,
        f"합성 포트폴리오 {impact.total:,.0f}건 Before/After 2회 판정",
        {"영향률(경과규정 미해당 층)": f"{no_event.impacted_rate:.1%}",
         "한도 변화 합계": f"{no_event.limit_delta_sum_eok:,.1f}억",
         "경과규정 적용": f"{impact.grandfathered:,.0f}건",
         "유예로 판정이 달라진 건": f"{impact.protected_by_grandfathering:,.0f}건",
         "자동판정 거부": f"{impact.escalation_rate:.1%}"},
    ))

    # 6. Structured Rule Proposal
    proposals = _proposals_from_impact(impact)
    stages.append(Stage(
        "Structured Rule Proposal",
        StageStatus.ATTENTION,
        f"Rule 변경 제안 {len(proposals)}건 — 전부 사람 승인 대기 (LOCKED §4·§9)",
        {p.label: f"{p.ltv_before:.0%} → {p.ltv_after:.0%} · {p.affected:,.0f}건"
         for p in proposals},
    ))

    # 7~8. Test Cases + Deterministic Rule Regression
    cases = generate_all()
    regression = run_regression(cases)
    stages.append(Stage(
        "Test Cases",
        StageStatus.DONE,
        f"경계·예외·충돌 TC {len(cases)}건 생성 (6개 분류)",
        {cat: str(len([c for c in cases if c.category.value == cat]))
         for cat in sorted({c.category.value for c in cases})},
    ))
    stages.append(Stage(
        "Deterministic Rule Regression",
        StageStatus.DONE if not regression.failures else StageStatus.ATTENTION,
        f"엔진 ⟷ 독립 명세 오라클 차등 검증 · Pass Rate {regression.pass_rate:.1%}",
        {cat: f"{p}/{n}" for cat, (p, n, _r) in regression.pass_rate_by_category().items()},
    ))

    # 9. Assurance Evaluation
    if grounding is not None:
        assurance_metrics = {
            "Citation Correctness": f"{grounding.citation_correctness:.0%}",
            "Unsupported Claim Rate": f"{grounding.unsupported_claim_rate:.0%}",
        }
        if gold_score is not None:
            assurance_metrics["Change Completeness"] = f"{gold_score.change_completeness:.0%}"
            assurance_metrics["Exception Recall"] = f"{gold_score.exception_recall:.0%}"
        assurance_metrics["Rule-regression Pass Rate"] = f"{regression.pass_rate:.0%}"
        stages.append(Stage("Assurance Evaluation", StageStatus.DONE,
                            "4개 dimension 중 Citation·Completeness·Regression 측정",
                            assurance_metrics))
    else:
        stages.append(Stage(
            "Assurance Evaluation", StageStatus.ATTENTION,
            "Rule-regression 만 측정 — Citation/Completeness 는 추출 미실행으로 산출 불가",
            {"Rule-regression Pass Rate": f"{regression.pass_rate:.0%}",
             "Citation Correctness": "N/A (추출 미실행)",
             "Change Completeness": "N/A (추출 미실행)"},
        ))

    # 4. Impact Matrix
    gold_ids = tuple(c["id"] for c in (gold or {}).get("required_changes", []))
    grounded_map = None
    if grounding is not None and extraction is not None:
        ungrounded_quotes = {i.citation.quote for i in grounding.ungrounded}
        grounded_map = {i.citation.quote: i.citation.quote not in ungrounded_quotes
                        for i in extraction.changes}
    matrix = build_impact_matrix(
        impact, regression,
        extraction=extraction, grounding=grounded_map,
        gold_change_ids=gold_ids,
        changed_region_codes=tuple(diff["added"]),
    )
    stages.append(Stage(
        "Impact Matrix",
        StageStatus.ATTENTION if matrix.blocked() else StageStatus.DONE,
        f"업무 {len(matrix.rows)}행 (Phase 3구간) · 자동처리 믹스 {matrix.automation_mix()}",
        {ph.value: str(len(matrix.by_phase(ph))) for ph in
         sorted({r.phase for r in matrix.rows}, key=lambda p: p.value)},
    ))

    # 10. Human Review
    stages.append(Stage(
        "Human Review",
        StageStatus.ATTENTION,
        f"사람 검토 필요 행 {len(matrix.needs_human_review())}건 · "
        f"선행작업 대기 {len(matrix.blocked())}건 · "
        f"자동판정 거부 {impact.escalated:,.0f}건",
        {r.area: r.human_review_reason for r in matrix.needs_human_review()},
    ))

    return E2EResult(
        stages=stages, source_digests=digests, policy_version_diff=diff,
        extraction=extraction, grounding=grounding, gold_score=gold_score,
        impact=impact, regression=regression, proposals=proposals, matrix=matrix,
    )
