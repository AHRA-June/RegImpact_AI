"""E2E 파이프라인 오케스트레이터 — 6·30 1건을 끝까지 관통(Walking Skeleton).

브리프 §18 코어 완성선:
    Source Snapshot → Policy Version Resolution → Before/After(RegChange)
    → Impact Matrix → Structured Rule Proposal → Test Cases
    → Deterministic Rule Regression → Assurance → Human Review → Validation Report

`04_PLAN.md` Phase 1: "각 노드 stub 허용. 목표는 파이프라인이 끝까지 연결되는지 확인."
이 모듈은 각 실제 노드(rule_engine·impact·tc_generator·extractor)를 배선하고, LLM 추출만
오프라인 stub(주입 가능)으로 두어 **API 키 없이** E2E가 관통되게 한다. 실제 LLM은 `complete` 주입.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from ..extractor import (
    check_citation_grounding,
    extract_regchange,
    load_sources,
    score_against_gold,
)
from ..extractor.evaluate import GoldReport, GroundingReport
from ..extractor.extractor import CompletionFn
from ..extractor.schema import RegChangeExtraction
from ..impact import ImpactMatrix, analyze_portfolio
from ..impact.analyzer import DEFAULT_AFTER_DATE, DEFAULT_BEFORE_DATE
from ..models import MortgageApplication
from ..regions import REGION_VERSIONS, RegionStatus, resolve_region_status
from ..tc_generator import RegressionReport, run_regression
from .proposal import RuleChangeProposal, build_proposal

_REG_REGIONS = ("GURI", "YONGIN_GIHEUNG", "HWASEONG_DONGTAN")


# ---------------------------------------------------------------------------
# Stage 1 — Source Snapshot (원문 무결성 지문)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class SourceSnapshot:
    doc_id: str
    n_chars: int
    raw_sha256: str   # 추출 텍스트(raw/*.txt)의 해시 = 엔진이 실제로 소비한 입력의 지문


def snapshot_sources(sources: dict[str, str]) -> list[SourceSnapshot]:
    return [
        SourceSnapshot(
            doc_id=doc_id,
            n_chars=len(text),
            raw_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        )
        for doc_id, text in sorted(sources.items())
    ]


# ---------------------------------------------------------------------------
# Stage 2 — Policy Version Resolution (지역 규제상태 시점 해석)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class RegionTransition:
    region_code: str
    before_status: str
    after_status: str
    newly_regulated: bool


def resolve_transitions(
    before_date: date, after_date: date
) -> list[RegionTransition]:
    out: list[RegionTransition] = []
    for code in REGION_VERSIONS:
        b, _ = resolve_region_status(code, before_date)
        a, _ = resolve_region_status(code, after_date)
        out.append(RegionTransition(
            region_code=code,
            before_status=b.value,
            after_status=a.value,
            newly_regulated=(b == RegionStatus.NON_REGULATED and a == RegionStatus.REGULATED),
        ))
    return out


# ---------------------------------------------------------------------------
# Offline stub extraction (Walking Skeleton — LLM 대체, 원문 grounded)
# ---------------------------------------------------------------------------
def _grounded_quote(text: str, start: int, length: int = 50) -> str:
    return text[start:start + length]


def offline_stub_extraction(sources: dict[str, str]) -> dict:
    """API 키 없이 E2E를 관통시키는 손수 작성 stub. 인용은 실제 원문 substring이라
    grounding=1.0(환각 없음). 실제 LLM 추출로 교체 시 `complete` 인자를 주입한다.
    """
    fsc = sources.get("FSC_PRESS_20260630", "")
    faq = sources.get("FAQ_20260630", "")
    return {
        "policy_id": "FSC_20260630",
        "effective_from": "2026-07-01",
        "target_regions": list(_REG_REGIONS),
        "changes": [
            {"category": "LTV", "summary": "규제지역 주담대 LTV 70% → 40%",
             "before": "70%", "after": "40%", "confidence": 0.95,
             "citation": {"source_doc_id": "FSC_PRESS_20260630",
                          "quote": _grounded_quote(fsc, 200)}},
            {"category": "EFFECTIVE_DATE", "summary": "시행일 2026-07-01",
             "before": None, "after": "2026-07-01", "confidence": 0.9,
             "citation": {"source_doc_id": "FSC_PRESS_20260630",
                          "quote": _grounded_quote(fsc, 400)}},
            {"category": "REGION", "summary": "구리·용인기흥·화성동탄 규제지역 지정",
             "before": None, "after": "REGULATED", "confidence": 0.9,
             "citation": {"source_doc_id": "FSC_PRESS_20260630",
                          "quote": _grounded_quote(fsc, 600)}},
            {"category": "GRANDFATHERING",
             "summary": "6.30까지 접수/계약+계약금은 종전규정(경과규정)",
             "before": None, "after": "종전규정", "confidence": 0.85,
             "citation": {"source_doc_id": "FSC_PRESS_20260630",
                          "quote": _grounded_quote(fsc, 800)}},
            {"category": "EXCEPTION", "summary": "생애최초·서민실수요는 완화 LTV",
             "before": None, "after": "생애최초 70% / 서민실수요 60%", "confidence": 0.8,
             "citation": {"source_doc_id": "FAQ_20260630",
                          "quote": _grounded_quote(faq, 300)}},
        ],
    }


# ---------------------------------------------------------------------------
# Skeleton 포트폴리오 (Impact Matrix 입력)
# ---------------------------------------------------------------------------
def default_6_30_portfolio() -> list[MortgageApplication]:
    """실패모드 층화 대표 포트폴리오(신규 규제지역 GURI 중심)."""
    def a(cid: str, **kw) -> MortgageApplication:
        base = dict(region_code="GURI", evaluation_date=DEFAULT_AFTER_DATE, customer_id=cid)
        base.update(kw)   # region_code 등 개별 오버라이드 허용
        return MortgageApplication(**base)

    return [
        a("C01", house_count=0),
        a("C02", house_count=0),
        a("C03", house_count=0, first_home_buyer=True),
        a("C04", house_count=0, real_demand_flag=True),
        a("C05", house_count=1),                              # 유주택 → 0%
        a("C06", house_count=2),                              # 다주택 → 0%
        a("C07", house_count=1, disposal_condition_flag=True),  # 처분조건부 → 40%
        a("C08", house_count=0, application_accepted_at=date(2026, 6, 30)),  # 경과규정
        a("C09", region_code="SEOUL_GANGNAM", house_count=0),  # 비규제 변화없음
        a("C10", house_count=0, policy_mortgage_flag=True),    # Discovery
    ]


# ---------------------------------------------------------------------------
# Human Review gate — 자동판정 불가/고위험 표면화
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ReviewItem:
    source: str        # IMPACT / ASSURANCE
    ref: str           # customer_id 또는 항목 식별
    reason: str


def collect_review_items(
    matrix: ImpactMatrix, grounding: GroundingReport
) -> list[ReviewItem]:
    items: list[ReviewItem] = []
    for r in matrix.rows:
        st = r.after.status.value
        if st in ("NEEDS_HUMAN_REVIEW", "DISCOVERY"):
            items.append(ReviewItem("IMPACT", r.customer_id or "?",
                                    f"엔진 자동판정 불가 → {st}"))
        elif r.high_impact:
            items.append(ReviewItem("IMPACT", r.customer_id or "?",
                                    f"고임팩트({r.direction.value}) — 검토 권장"))
    for u in grounding.ungrounded:
        items.append(ReviewItem("ASSURANCE", u.category,
                                f"인용 미검증(환각 가능): {u.summary}"))
    return items


# ---------------------------------------------------------------------------
# Validation Report (전 노드 산출물 집계)
# ---------------------------------------------------------------------------
@dataclass
class ValidationReport:
    scenario: str
    before_date: date
    after_date: date
    used_live_llm: bool
    snapshots: list[SourceSnapshot]
    transitions: list[RegionTransition]
    extraction: RegChangeExtraction
    matrix: ImpactMatrix
    proposal: RuleChangeProposal
    regression: RegressionReport
    grounding: GroundingReport
    gold: Optional[GoldReport]
    review_items: list[ReviewItem] = field(default_factory=list)

    @property
    def e2e_ok(self) -> bool:
        """관통 성공 = 모든 노드가 산출물을 냈고 회귀가 통과."""
        return (
            bool(self.snapshots)
            and bool(self.transitions)
            and len(self.extraction.changes) > 0
            and self.matrix.n > 0
            and len(self.proposal.ltv_lines) > 0
            and self.regression.total > 0
            and self.regression.pass_rate == 1.0
        )


def run_e2e(
    complete: Optional[CompletionFn] = None,
    apps: Optional[list[MortgageApplication]] = None,
    gold: Optional[dict] = None,
    before_date: date = DEFAULT_BEFORE_DATE,
    after_date: date = DEFAULT_AFTER_DATE,
    raw_dir: Optional[str] = None,
) -> ValidationReport:
    """6·30 시나리오를 E2E로 관통시켜 Validation Report를 만든다.

    complete=None 이면 오프라인 stub 추출(API 키 불필요). 실제 LLM은 complete 주입.
    """
    # 1. Source Snapshot
    sources = load_sources(raw_dir)
    snapshots = snapshot_sources(sources)

    # 2. Policy Version Resolution
    transitions = resolve_transitions(before_date, after_date)

    # 3. Before/After (RegChange 추출)
    used_live_llm = complete is not None
    fn: CompletionFn = complete or (lambda s, u: offline_stub_extraction(sources))
    extraction = extract_regchange(sources, complete=fn)

    # 4. Impact Matrix
    portfolio = apps if apps is not None else default_6_30_portfolio()
    matrix = analyze_portfolio(portfolio, before_date, after_date)

    # 5. Structured Rule Proposal
    proposal = build_proposal(extraction)

    # 6~7. Test Cases + Deterministic Rule Regression
    regression = run_regression()

    # 8. Assurance
    grounding = check_citation_grounding(extraction, sources)
    gold_report = score_against_gold(extraction, gold) if gold else None

    # 9. Human Review gate
    review_items = collect_review_items(matrix, grounding)

    return ValidationReport(
        scenario="6·30 규제지역 추가지정 (LTV 70%→40%)",
        before_date=before_date,
        after_date=after_date,
        used_live_llm=used_live_llm,
        snapshots=snapshots,
        transitions=transitions,
        extraction=extraction,
        matrix=matrix,
        proposal=proposal,
        regression=regression,
        grounding=grounding,
        gold=gold_report,
        review_items=review_items,
    )
