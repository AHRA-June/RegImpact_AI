"""AI 거버넌스 산출물 — 리스크 레지스터가 무력해지지 않도록 고정한다.

리스크 레지스터가 실패하는 가장 흔한 경로는 "통제 운영 중"이라고 적어놓고 근거가 없는
것이다. 여기 테스트는 통제가 **실재하는 코드·테스트를 가리키는지** 확인한다.
"""
from pathlib import Path

import pytest

from regimpact.governance import RISKS, ControlState, render_card, render_register, summary
from regimpact.governance.risk import Band, Control, Risk, band, heatmap
from regimpact.report import collect

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def evidence():
    return collect(generated_at="2026-01-01 00:00 UTC")


# ---------- 통제가 실재하는가 ----------
@pytest.mark.parametrize("risk", RISKS, ids=lambda r: r.risk_id)
def test_operating_controls_point_at_real_paths(risk):
    """'운영 중'이라고 적힌 통제는 실재하는 파일·디렉터리를 가리켜야 한다.

    이것이 없으면 레지스터는 희망사항 목록이 된다.
    """
    for c in risk.controls:
        if c.state is not ControlState.OPERATING:
            continue
        assert c.evidence, f"{risk.risk_id}: 운영 중 통제인데 근거 경로가 없다 — {c.description}"
        for path in c.evidence:
            assert (REPO / path).exists(), \
                f"{risk.risk_id}: 근거 경로가 없다 — {path}"


def test_planned_controls_are_not_claimed_as_evidence():
    """계획 단계 통제가 근거를 갖고 있으면 상태 표기가 틀린 것이다."""
    for r in RISKS:
        for c in r.controls:
            if c.state is ControlState.PLANNED:
                assert not c.evidence, f"{r.risk_id}: 계획 통제에 근거가 붙어 있다"


# ---------- 척도 정합성 ----------
def test_residual_never_exceeds_inherent():
    for r in RISKS:
        assert r.residual <= r.inherent, r.risk_id


def test_no_risk_claims_zero_residual():
    """잔여위험을 0으로 만들지 않는다 — 척도상 최소가 1×1=1."""
    for r in RISKS:
        assert r.residual >= 1, r.risk_id


def test_risk_without_controls_is_rejected():
    with pytest.raises(ValueError, match="통제 없는"):
        Risk("X", "cat", "t", "d", 3, 3, 2, 2, controls=())


def test_residual_greater_than_inherent_is_rejected():
    ctl = (Control("설계", "x", ControlState.PLANNED),)
    with pytest.raises(ValueError, match="잔여위험"):
        Risk("X", "cat", "t", "d", 1, 1, 5, 5, controls=ctl)


def test_out_of_range_score_is_rejected():
    ctl = (Control("설계", "x", ControlState.PLANNED),)
    with pytest.raises(ValueError, match="1~5"):
        Risk("X", "cat", "t", "d", 6, 1, 1, 1, controls=ctl)


@pytest.mark.parametrize("rating,expected", [
    (1, Band.LOW), (4, Band.LOW), (5, Band.MEDIUM), (9, Band.MEDIUM),
    (10, Band.HIGH), (15, Band.HIGH), (16, Band.CRITICAL), (25, Band.CRITICAL),
])
def test_band_thresholds(rating, expected):
    assert band(rating) is expected


def test_ids_are_unique():
    ids = [r.risk_id for r in RISKS]
    assert len(ids) == len(set(ids))


# ---------- 정직성 ----------
def test_realized_risks_are_marked():
    """실제로 발생한 리스크는 발견사항 ID 로 표시돼야 한다 — 가상의 목록이 아니라는 증거."""
    realized = {r.risk_id for r in RISKS if r.realized_as}
    assert realized, "실제 발생 이력이 하나도 없으면 레지스터가 사후 정리된 것인지 확인"
    assert "R-RUL-02" in realized, "R-01(명세 오독)이 기록돼야 한다"
    assert "R-RUL-03" in realized, "R-01(지역 데이터 누락)이 기록돼야 한다"


def test_the_uncatchable_risk_stays_high():
    """명세 자체의 오독은 차등검증으로 못 잡는다 — 잔여위험을 낮추면 안 된다."""
    r = next(x for x in RISKS if x.risk_id == "R-RUL-02")
    assert r.residual_band in (Band.HIGH, Band.CRITICAL)
    assert r.accepted_reason


def test_accepted_risks_state_a_reason():
    """잔여위험이 Medium 이상이면 수용 근거나 실제 발생 이력이 있어야 한다."""
    for r in RISKS:
        if r.residual_band in (Band.MEDIUM, Band.HIGH, Band.CRITICAL):
            assert r.accepted_reason or r.realized_as, \
                f"{r.risk_id}: 잔여 {r.residual_band.value} 인데 근거가 없다"


# ---------- 렌더링 ----------
def test_register_lists_every_risk(evidence):
    text = render_register(evidence)
    for r in RISKS:
        assert r.risk_id in text


def test_register_heatmap_places_every_risk():
    placed = {rid for ids in heatmap().values() for rid in ids}
    assert placed == {r.risk_id for r in RISKS}


def test_card_quantitative_numbers_match_evidence(evidence):
    card = render_card(evidence)
    g, r = evidence.grounding, evidence.regression
    assert f"{g.citation_correctness:.0%} ({g.grounded}/{g.total})" in card
    assert f"{r.pass_rate:.0%} ({r.passed}/{r.total})" in card
    assert f"{evidence.impact.impact_coverage:.1%}" in card


def test_card_and_register_agree_on_risk_counts(evidence):
    card, reg = render_card(evidence), render_register(evidence)
    s = summary()
    assert f"**{s['total']}건**" in card
    assert f"**{s['total']}건**" in reg


def test_card_states_out_of_scope_uses(evidence):
    """오용 방지 절은 Model Card 의 핵심이다 — 빠지면 안 된다."""
    card = render_card(evidence)
    assert "## A.4 범위 외" in card
    assert "사람 승인 없는 룰 반영" in card


def test_card_does_not_claim_llm_makes_decisions(evidence):
    card = render_card(evidence)
    assert "LLM 을 규제 판정에 쓰는 시스템이 아니다" in card
    assert "LLM 은 **사실 추출만** 한다" in card


def test_register_states_its_own_limits(evidence):
    """레지스터 자체의 한계도 적는다 — 1인 판단이고 외부 검증이 없다."""
    text = render_register(evidence)
    assert "## 5. 이 레지스터의 한계" in text
    assert "외부 검증을 받지 않았다" in text


def test_render_is_deterministic(evidence):
    assert render_card(evidence) == render_card(evidence)
    assert render_register(evidence) == render_register(evidence)
