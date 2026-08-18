"""Impact Analyzer 테스트 — 포트폴리오·고객영향·매트릭스 조립.

전부 오프라인·결정적(LLM 호출 없음). 매트릭스 수치가 실행마다 흔들리면 "검증 가능한
산출물"이 아니므로 결정성 자체를 테스트한다.
"""
from datetime import date

import pytest

from regimpact.extractor.evaluate import check_citation_grounding
from regimpact.extractor.schema import RegChangeExtraction
from regimpact.impact import (
    Owner,
    Phase,
    Priority,
    Segment,
    analyze_portfolio,
    build_impact_matrix,
    build_portfolio,
    composition,
    derive_rule_diff,
    format_matrix_markdown,
    format_matrix_text,
)
from regimpact.impact.portfolio import (
    AFTER_DATE,
    BEFORE_DATE,
    CONTROL_REGION,
    TARGET_REGIONS,
    PortfolioCustomer,
)
from regimpact.impact.schema import ApprovalStatus, Evidence, ImpactRow
from regimpact.models import LoanPurpose, MortgageApplication
from regimpact.tc_generator import run_regression


# ------------------------------------------------------------------ 포트폴리오

def test_portfolio_is_deterministic():
    """같은 seed → 완전히 같은 포트폴리오. 매트릭스 재현성의 전제."""
    a, b = build_portfolio(size=300, seed=7), build_portfolio(size=300, seed=7)
    assert a == b


def test_portfolio_seed_changes_composition():
    a, b = build_portfolio(size=300, seed=1), build_portfolio(size=300, seed=2)
    assert a != b


def test_portfolio_composition_matches_declared_strata():
    """선언한 층화 비율과 실제 조성이 대략 일치해야 한다(가정이 코드에 숨지 않도록)."""
    comp = composition(build_portfolio(size=3000, seed=11))
    assert comp["size"] == 3000
    assert comp["no_home"] == pytest.approx(0.55, abs=0.05)
    assert comp["multi_home"] == pytest.approx(0.15, abs=0.05)
    assert comp["policy_mortgage"] == pytest.approx(0.08, abs=0.03)
    assert comp["out_of_scope"] == pytest.approx(0.05, abs=0.03)


def test_portfolio_covers_target_and_control_regions():
    codes = {c.application.region_code for c in build_portfolio(size=500, seed=3)}
    assert set(TARGET_REGIONS) <= codes
    assert CONTROL_REGION in codes          # 음성 대조군이 반드시 있어야 한다


def test_as_of_changes_only_evaluation_date():
    cust = build_portfolio(size=1, seed=5)[0]
    before = cust.as_of(BEFORE_DATE)
    assert before.evaluation_date == BEFORE_DATE
    assert before.region_code == cust.application.region_code
    assert before.house_count == cust.application.house_count


# --------------------------------------------------------------- 고객 영향 분석

def _one(app: MortgageApplication, price: int = 1_000_000_000) -> list[PortfolioCustomer]:
    return [PortfolioCustomer(customer_id="C0", application=app, property_price=price)]


def test_control_region_customer_is_unaffected():
    """비대상 지역 고객은 시행 전후 LTV가 같아야 한다(음성 대조)."""
    rep = analyze_portfolio(_one(MortgageApplication(
        region_code=CONTROL_REGION, evaluation_date=AFTER_DATE, house_count=0,
    )))
    assert rep.impacts[0].segment == Segment.UNAFFECTED
    assert rep.impacts[0].limit_delta == 0


def test_target_region_no_home_customer_is_reduced():
    """신규 규제지역 무주택 일반: 70% → 40%, 담보 10억이면 한도 3억 감소."""
    rep = analyze_portfolio(_one(MortgageApplication(
        region_code="GURI", evaluation_date=AFTER_DATE, house_count=0,
    )))
    i = rep.impacts[0]
    assert i.segment == Segment.REDUCED
    assert i.before.max_ltv == 0.70 and i.after.max_ltv == 0.40
    assert i.limit_delta == -300_000_000


def test_grandfathered_customer_keeps_previous_rule():
    """6.30까지 접수 완료 → 시행일에 평가해도 종전규정 70% 유지."""
    rep = analyze_portfolio(_one(MortgageApplication(
        region_code="GURI", evaluation_date=AFTER_DATE, house_count=0,
        application_accepted_at=date(2026, 6, 30),
    )))
    i = rep.impacts[0]
    assert i.segment == Segment.GRANDFATHERED
    assert i.after.max_ltv == 0.70 and i.limit_delta == 0


def test_grandfathering_boundary_one_day_late_is_reduced():
    """7.1 접수는 경과규정 밖 — 하루 차이로 한도가 뒤집히는 경계."""
    rep = analyze_portfolio(_one(MortgageApplication(
        region_code="GURI", evaluation_date=AFTER_DATE, house_count=0,
        application_accepted_at=date(2026, 7, 1),
    )))
    assert rep.impacts[0].segment == Segment.REDUCED


def test_policy_mortgage_goes_to_discovery_not_core():
    rep = analyze_portfolio(_one(MortgageApplication(
        region_code="GURI", evaluation_date=AFTER_DATE, policy_mortgage_flag=True,
    )))
    assert rep.impacts[0].segment == Segment.DISCOVERY


def test_non_home_purchase_is_out_of_scope():
    rep = analyze_portfolio(_one(MortgageApplication(
        region_code="GURI", evaluation_date=AFTER_DATE, loan_purpose=LoanPurpose.OTHER,
    )))
    assert rep.impacts[0].segment == Segment.OUT_OF_SCOPE


def test_owner_without_baseline_escalates_to_human_review():
    """비규제 유주택 기준선이 명세에 없다 → 자동판정 중단(추정 금지)."""
    rep = analyze_portfolio(_one(MortgageApplication(
        region_code="GURI", evaluation_date=AFTER_DATE, house_count=1,
    )))
    assert rep.impacts[0].segment == Segment.NEEDS_HUMAN_REVIEW
    assert "OWNER_BASELINE_UNKNOWN" in rep.escalation_reasons


def test_report_aggregates_are_consistent():
    rep = analyze_portfolio(build_portfolio(size=500, seed=13), seed=13)
    assert sum(rep.segment_counts.values()) == len(rep.impacts) == 500
    assert rep.total_limit_reduction <= 0
    assert 0.0 <= rep.affected_rate <= 1.0
    assert all(i.limit_delta < 0 for i in rep.reduced)


def test_analysis_is_deterministic():
    a = analyze_portfolio(build_portfolio(size=400, seed=21), seed=21)
    b = analyze_portfolio(build_portfolio(size=400, seed=21), seed=21)
    assert a.segment_counts == b.segment_counts
    assert a.total_limit_reduction == b.total_limit_reduction


# --------------------------------------------------------------------- 룰 diff

def test_rule_diff_reads_engine_constants_not_hardcoded_values():
    """룰 diff는 엔진 상수(=사람 확정 명세)에서 읽어온다 — LOCKED §4."""
    from regimpact import rule_engine

    diff = {d["rule_id"]: d for d in derive_rule_diff()}
    assert diff["REG_STD"]["after"] == rule_engine.LTV_REGULATED_STANDARD
    assert diff["REG_STD"]["before"] == rule_engine.LTV_BASELINE
    assert diff["REG_FIRSTHOME"]["after"] == rule_engine.LTV_FIRST_HOME


# ------------------------------------------------------------------ 매트릭스

GOLD_EXTRACTION = {
    "policy_id": "FSC_20260630",
    "effective_from": "2026-07-01",
    "target_regions": ["GURI", "YONGIN_GIHEUNG", "HWASEONG_DONGTAN"],
    "changes": [
        {"category": "LTV", "summary": "규제지역 LTV 강화", "before": "70%", "after": "40%",
         "citation": {"source_doc_id": "D1", "quote": "LTV 강화"}, "confidence": 0.95},
        {"category": "REGION", "summary": "3곳 신규 지정", "before": None, "after": "투기과열지구",
         "citation": {"source_doc_id": "D1", "quote": "신규 지정"}, "confidence": 0.95},
        {"category": "GRANDFATHERING", "summary": "종전규정 적용", "before": None, "after": None,
         "citation": {"source_doc_id": "D1", "quote": "종전규정"}, "confidence": 0.9},
        {"category": "SCOPE_LIMIT", "summary": "전세대출 제한", "before": None, "after": None,
         "citation": {"source_doc_id": "D1", "quote": "전세대출 제한"}, "confidence": 0.9},
    ],
}


def _matrix(size: int = 400, seed: int = 42):
    ext = RegChangeExtraction.from_dict(GOLD_EXTRACTION)
    impact = analyze_portfolio(build_portfolio(size=size, seed=seed), seed=seed)
    grounding = check_citation_grounding(
        ext, {"D1": "LTV 강화 신규 지정 종전규정 전세대출 제한"}
    )
    return ext, impact, build_impact_matrix(
        ext, impact, grounding=grounding, regression=run_regression()
    )


def test_matrix_keeps_all_three_phases():
    """LOCKED §0-7: 시간축 삭제 금지. 세 Phase가 모두 살아 있어야 한다."""
    _, _, m = _matrix()
    for phase in Phase:
        assert m.by_phase(phase), f"{phase.value} 행이 사라졌다"


def test_matrix_covers_brief_section_10_areas():
    _, _, m = _matrix()
    areas = {r.area for r in m.rows}
    for expected in (
        "변경사항 식별·규정 해석", "고객·포트폴리오 영향 분석", "심사 Rule 변경",
        "전산 요건", "내규 개정", "경과규정 처리", "테스트", "현업 공지",
        "금리·한도 전략 재분석", "대외보고 집계 기준", "사후 모니터링",
    ):
        assert expected in areas, f"§10 행 누락: {expected}"


def test_matrix_numbers_come_from_real_components():
    """하드코딩이 아니라 실제 엔진·회귀 출력을 싣는지 확인."""
    _, impact, m = _matrix()
    customer_row = next(r for r in m.rows if r.area == "고객·포트폴리오 영향 분석")
    assert customer_row.metrics["segments"] == impact.segment_counts
    assert customer_row.metrics["total_limit_reduction_won"] == impact.total_limit_reduction

    test_row = next(r for r in m.rows if r.area == "테스트")
    assert test_row.metrics["total_cases"] == run_regression().total
    assert test_row.metrics["pass_rate"] == 1.0


def test_scope_limit_becomes_discovery_row_not_core_rule():
    """브리프 §24-12: Discovery 항목은 매트릭스에만 표시하고 코어 룰엔진에 넣지 않는다."""
    _, _, m = _matrix()
    disc = [r for r in m.rows if r.area.startswith("[Discovery]")]
    assert len(disc) == 1
    assert disc[0].automatable is False
    assert "Discovery Scope" in disc[0].human_review_reason
    # 룰 diff에는 Discovery 항목이 들어가지 않는다
    assert not any("전세" in d["condition"] for d in derive_rule_diff())


def test_spec_gap_row_appears_when_escalations_exist():
    _, impact, m = _matrix()
    assert impact.human_review_count > 0
    gap = next(r for r in m.rows if r.area == "규정 해석 공백 해소")
    assert gap.automatable is False
    assert gap.priority == Priority.REQUIRED and gap.phase == Phase.D_MINUS
    assert gap.metrics["escalation_reasons"] == impact.escalation_reasons


def test_evidence_carries_grounding_verdict():
    _, _, m = _matrix()
    ev = next(r for r in m.rows if r.area == "변경사항 식별·규정 해석").evidence
    assert ev and all(e.grounded is True for e in ev)


def test_row_without_automation_must_state_human_review_reason():
    """자동처리 불가인데 사유가 없으면 매트릭스가 통제 문서로서 무의미해진다."""
    with pytest.raises(ValueError, match="사유가 필요"):
        ImpactRow(area="테스트행", change="x", automatable=False)


def test_all_human_review_rows_have_reasons():
    _, _, m = _matrix()
    assert m.human_review_rows
    assert all(r.human_review_reason for r in m.human_review_rows)


def test_committee_row_is_never_automatable():
    """내규 개정은 거버넌스 절차 — 자동화 대상이 아니다."""
    _, _, m = _matrix()
    row = next(r for r in m.rows if r.area == "내규 개정")
    assert row.owner == Owner.COMMITTEE
    assert row.automatable is False
    assert row.approval_status == ApprovalStatus.PENDING_APPROVAL


def test_d_minus_required_is_the_deadline_workload():
    _, _, m = _matrix()
    rows = m.d_minus_required
    assert rows and all(
        r.phase == Phase.D_MINUS and r.priority == Priority.REQUIRED for r in rows
    )


def test_matrix_is_deterministic():
    _, _, a = _matrix(seed=99)
    _, _, b = _matrix(seed=99)
    assert format_matrix_markdown(a) == format_matrix_markdown(b)


def test_renderers_produce_output():
    _, _, m = _matrix()
    md = format_matrix_markdown(m)
    assert "임팩트 매트릭스" in md and "Human Review" in md
    for phase in Phase:
        assert phase.value in md
    assert "임팩트 매트릭스" in format_matrix_text(m)


def test_evidence_short_marks_ungrounded():
    assert "⚠" in Evidence("D1", "없는 인용", grounded=False).short()
    assert "✓" in Evidence("D1", "있는 인용", grounded=True).short()


def test_evidence_is_deduped_across_items_citing_same_sentence():
    """지역 3곳처럼 여러 항목이 같은 문장을 인용해도 근거는 1회만 실린다."""
    from regimpact.impact.builder import _evidence

    same = {"source_doc_id": "D1", "quote": "3곳을 신규 지정"}
    ext = RegChangeExtraction.from_dict({
        "policy_id": "P", "effective_from": "2026-07-01", "target_regions": [],
        "changes": [
            {"category": "REGION", "summary": f"지역{i}", "before": None, "after": None,
             "citation": same, "confidence": 0.9}
            for i in range(3)
        ],
    })
    assert len(_evidence(ext, ("REGION",))) == 1


def test_evidence_short_flattens_newlines_for_table_cells():
    """원문 개행이 마크다운 표 셀을 깨뜨리지 않아야 한다."""
    text = Evidence("D1", "규제지역 내 3억원 초과\nAPT 취득 제한").short()
    assert "\n" not in text and "초과 APT" in text
