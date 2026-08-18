"""Impact Analyzer 테스트 — 포트폴리오 · 고객영향 · 임팩트 매트릭스 · E2E 파이프라인.

여기서 지키려는 계약 세 가지:
    ① 합성 포트폴리오는 **재현 가능**해야 한다(난수 금지). 매번 다른 숫자가 나오는 임팩트 분석은 감사 불가.
    ② 임팩트 매트릭스의 **시간축(Phase)** 은 LOCKED §7이다. 사라지면 테스트가 깨져야 한다.
    ③ 안 돌린 단계를 돌린 것처럼 표시하면 안 된다(추출 미실행 → MISSING + 근거 출처가 골드로 표시).
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from regimpact.impact import (
    Phase,
    Provenance,
    StageStatus,
    analyze_customer_impact,
    build_impact_matrix,
    build_portfolio,
    render_report,
    run_e2e,
)
from regimpact.impact.customer_impact import AFTER_AS_OF, BEFORE_AS_OF
from regimpact.tc_generator import run_regression

REPO = Path(__file__).resolve().parents[1]
GOLD = json.loads((REPO / "docs" / "eval" / "regchange_gold_6_30.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def impact():
    return analyze_customer_impact()


@pytest.fixture(scope="module")
def matrix(impact):
    return build_impact_matrix(
        impact, run_regression(),
        gold_change_ids=tuple(c["id"] for c in GOLD["required_changes"]),
        changed_region_codes=("GYEONGGI_GURI",),
    )


# ---------- 포트폴리오 ----------
def test_portfolio_is_deterministic():
    a, b = build_portfolio(), build_portfolio()
    assert [r.customer_id for r in a] == [r.customer_id for r in b]


def test_portfolio_size_in_planned_range():
    """04_PLAN Phase 2: 층화 합성 포트폴리오 2,000~5,000."""
    assert 2000 <= len(build_portfolio()) <= 5000


def test_portfolio_rejects_unregistered_region_code():
    """지역코드 오타가 조용히 UNKNOWN escalation 으로 흘러가면 안 된다."""
    with pytest.raises(ValueError, match="레지스트리에 없는 지역코드"):
        build_portfolio(region_groups={"오타": ("NOWHERE_XX",)})


def test_portfolio_covers_every_borrower_and_event():
    rows = build_portfolio()
    assert len({r.borrower.key for r in rows}) == 6
    assert len({r.event.key for r in rows}) == 4
    assert len({r.region_group for r in rows}) == 4


# ---------- 고객 영향 (앵커) ----------
def test_before_after_dates_bracket_the_effective_date():
    assert BEFORE_AS_OF == date(2026, 6, 30) and AFTER_AS_OF > date(2026, 7, 1)


def test_only_six_thirty_group_is_impacted(impact):
    """6·30은 경기 3곳만 바꿨다. 기존 규제·비규제 지역군은 영향 0이어야 한다."""
    by_group = impact.by_region_group()
    assert by_group["6·30 신규 규제(경기 3곳)"].impacted > 0
    for label in ("기존 규제(서울·경기)", "수도권 비규제", "비수도권 비규제"):
        assert by_group[label].impacted == 0, label


def test_first_home_buyer_is_not_impacted(impact):
    """생애최초는 규제지역에서도 70% 좌동 → 6·30으로 LTV가 바뀌지 않는다."""
    assert impact.by_borrower()["생애최초"].impacted == 0


def test_impacted_rows_are_all_tightening(impact):
    """6·30은 강화 대책이다. 완화된 건이 나오면 판정 어딘가가 잘못된 것."""
    assert impact.loosened() == 0
    assert impact.tightened() > 0
    assert impact.no_event_only().limit_delta_sum_eok < 0


def test_rule_transitions_are_observed_not_hardcoded(impact):
    t = impact.rule_transitions()
    assert "NONREG_STD_70 → REG_STD" in t
    assert all(v > 0 for v in t.values())


def test_escalation_is_confined_to_capital_non_regulated_owners(impact):
    """자동판정 거부는 '수도권 비규제 유주택' 명세 공백에서만 나와야 한다."""
    assert set(impact.escalation_reasons()) == {"OWNER_BASELINE_UNKNOWN"}
    for r in impact.rows:
        if r.escalated:
            assert r.row.borrower.key == "owner"
            assert r.row.region_group in ("6·30 신규 규제(경기 3곳)", "수도권 비규제")


def test_grandfathering_counterfactual_is_narrower_than_grandfathered(impact):
    """경과규정 대상 전부가 '유예 덕에 살아난' 건은 아니다 — 반사실로 구분해야 한다."""
    assert 0 < impact.protected_by_grandfathering < impact.grandfathered


def test_grandfathered_rows_keep_prior_regime(impact):
    for r in impact.rows:
        if r.grandfathered and r.decided_both:
            assert r.ltv_after == r.ltv_before, r.row.customer_id


def test_segment_averages_are_read_from_the_no_event_stratum(impact):
    """세그먼트 평균 LTV는 경과규정 미해당 층에서 읽어야 한다.

    전체 격자로 평균 내면 경과규정 건(3/4)이 섞여 '70% → 63%' 같은 값이 나오는데,
    그건 규제 변경의 크기가 아니라 격자 설계의 부산물이다. 실제 변경은 70% → 40%.
    """
    segs = {(s.region_group, s.borrower_label): s for s in impact.no_event_only().segments}
    std = segs[("6·30 신규 규제(경기 3곳)", "무주택 일반")]
    assert std.avg_ltv_before == 0.70 and std.avg_ltv_after == 0.40
    assert std.avg_ltv_delta == -0.30
    assert std.top_transition == "NONREG_STD_70 → REG_STD"

    real = segs[("6·30 신규 규제(경기 3곳)", "서민·실수요자")]
    assert real.avg_ltv_after == 0.60 and real.avg_ltv_delta == -0.10

    # 전체 격자로 재면 같은 세그먼트가 희석된다 — 그래서 층을 나눠 읽는다
    blended = {(s.region_group, s.borrower_label): s for s in impact.segments}
    assert blended[("6·30 신규 규제(경기 3곳)", "무주택 일반")].avg_ltv_delta > -0.30


def test_escalated_segments_have_no_average_ltv(impact):
    """양쪽 중 하나가 사람 검토면 평균 LTV를 만들지 않는다(빈 값을 0으로 채우지 않는다)."""
    for s in impact.no_event_only().segments:
        if s.escalation_rate == 1.0:
            assert s.avg_ltv_delta is None


# ---------- 임팩트 매트릭스 ----------
def test_matrix_keeps_all_three_phases(matrix):
    """LOCKED §7 — 시간축은 삭제하지 않는다."""
    present = {r.phase for r in matrix.rows}
    assert present == {Phase.BEFORE_DDAY, Phase.AFTER_EFFECTIVE, Phase.SEPARATE_TRIGGER}


def test_matrix_has_the_eleven_brief_rows(matrix):
    """브리프 §10의 11개 업무 행이 모두 있어야 한다(Discovery 행은 별도)."""
    areas = [r.area for r in matrix.rows if not r.area.startswith("[Discovery]")]
    assert len(areas) == 11
    for expected in ("변경사항 식별·규정 해석", "고객·포트폴리오 영향 분석", "심사 Rule 변경",
                     "전산 요건", "내규 개정", "경과규정 처리", "테스트", "현업 공지",
                     "금리·한도 전략 재분석", "대외보고 집계 기준", "사후 모니터링"):
        assert expected in areas


def test_discovery_rows_are_flagged_manual_and_not_auto_decided(matrix):
    """브리프 §5.2·§24-11 — Discovery 는 표시만, 코어 엔진에 넣지 않는다."""
    rows = [r for r in matrix.rows if r.area.startswith("[Discovery]")]
    assert len(rows) == 4
    for r in rows:
        assert r.automation.value == "수동"
        assert "manual policy review required" in r.deliverable


def test_external_report_row_is_on_separate_trigger(matrix):
    """대외보고 기준 변경은 별도 트리거로 나중에 도착한다(브리프 §3)."""
    row = next(r for r in matrix.rows if r.area == "대외보고 집계 기준")
    assert row.phase is Phase.SEPARATE_TRIGGER
    assert row.approval.value == "선행작업 대기"


def test_matrix_rows_carry_evidence_and_provenance(matrix):
    for r in matrix.rows:
        assert r.evidence, f"근거 없는 행: {r.area}"
        assert r.provenance is not Provenance.NOT_RUN, r.area


def test_matrix_without_extraction_does_not_claim_ai_provenance(matrix):
    """추출을 안 돌렸으면 어떤 행도 'AI 추출'을 근거로 내세우면 안 된다."""
    assert all(r.provenance is not Provenance.AI_EXTRACTION for r in matrix.rows)


def test_customer_impact_row_reflects_engine_numbers(impact, matrix):
    row = next(r for r in matrix.rows if r.area == "고객·포트폴리오 영향 분석")
    assert f"{impact.no_event_only().impacted_rate:.1%}" in row.metrics["영향률(경과규정 미해당 층)"]
    assert row.provenance is Provenance.ENGINE


# ---------- E2E 파이프라인 ----------
def test_e2e_runs_every_stage_except_llm_extraction():
    result = run_e2e(gold=GOLD)
    names = [s.name for s in result.stages]
    for expected in ("Source Snapshot", "Policy Version Resolution",
                     "Before/After Change Extraction", "Customer Impact",
                     "Structured Rule Proposal", "Test Cases",
                     "Deterministic Rule Regression", "Assurance Evaluation",
                     "Impact Matrix", "Human Review"):
        assert expected in names
    missing = [s for s in result.stages if s.status is StageStatus.MISSING]
    assert [s.name for s in missing] == ["Before/After Change Extraction"]
    assert result.completed is False        # 안 돌린 단계를 감추지 않는다


def test_e2e_policy_version_diff_matches_the_official_table():
    result = run_e2e(gold=GOLD)
    assert result.policy_version_diff["added"] == [
        "GYEONGGI_GURI", "GYEONGGI_HWASEONG_DONGTAN", "GYEONGGI_YONGIN_GIHEUNG"]
    assert result.policy_version_diff["removed"] == []


def test_e2e_source_snapshot_hashes_three_documents():
    result = run_e2e(gold=GOLD)
    assert len(result.source_digests) == 3
    assert all(len(h) == 16 for h in result.source_digests.values())


def test_e2e_proposals_require_human_approval():
    result = run_e2e(gold=GOLD)
    assert result.proposals
    assert all(p.requires_human_approval for p in result.proposals)


def test_e2e_with_injected_llm_fills_extraction_and_assurance():
    """가짜 LLM 을 주입하면 추출·Citation Assurance 단계가 실제로 채워진다(API 키 불필요)."""
    from test_extractor import _fake_extraction_dict  # 같은 tests/ 디렉터리
    from regimpact.extractor import load_sources

    sources = load_sources()
    result = run_e2e(complete=lambda _s, _u: _fake_extraction_dict(sources), gold=GOLD)

    assert result.completed is True
    assert result.extraction is not None
    assert result.grounding is not None and result.gold_score is not None
    assurance = result.stage("Assurance Evaluation")
    assert assurance.status is StageStatus.DONE
    assert "Citation Correctness" in assurance.metrics
    # 추출이 있으면 원문 인용 행의 출처가 'AI 추출'로 바뀐다
    ident = next(r for r in result.matrix.rows if r.area == "변경사항 식별·규정 해석")
    assert ident.provenance is Provenance.AI_EXTRACTION


# ---------- 검증보고서 ----------
def test_report_renders_phases_and_flags_missing_stage():
    text = render_report(run_e2e(gold=GOLD))
    for phase in (Phase.BEFORE_DDAY, Phase.AFTER_EFFECTIVE, Phase.SEPARATE_TRIGGER):
        assert phase.value in text
    assert "미실행" in text
    assert "AI 추출 미실행" in text
    assert "합성 포트폴리오" in text
