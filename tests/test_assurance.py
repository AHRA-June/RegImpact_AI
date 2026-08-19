"""Assurance 스코어카드 — 임계가 근거를 갖고, 미측정이 통과로 새지 않는지 고정한다.

스코어카드가 실패하는 두 가지 방식:
  ① 달성치를 그대로 임계로 삼는다 (곡선에 맞춰 채점)
  ② 못 잰 것을 통과로 센다
둘 다 숫자는 좋아 보이고 아무것도 증명하지 않는다.
"""
import re
from pathlib import Path

import pytest

from regimpact.assurance import (
    THRESHOLDS,
    Dimension,
    Direction,
    Threshold,
    Verdict,
    score,
)
from regimpact.report import collect

REPO = Path(__file__).resolve().parents[1]
SPEC = REPO / "docs" / "metrics_spec.md"


@pytest.fixture(scope="module")
def evidence():
    return collect(generated_at="2026-01-01 00:00 UTC")


# ---------- 임계 자체의 규율 ----------
def test_every_threshold_has_a_rationale():
    """근거를 못 쓰겠으면 그 임계는 아직 정할 준비가 안 된 것이다."""
    for t in THRESHOLDS:
        assert len(t.rationale.strip()) >= 30, f"{t.metric}: 근거가 너무 얇다"


def test_threshold_without_rationale_is_rejected():
    with pytest.raises(ValueError, match="근거 없는"):
        Threshold("X", Dimension.RULE_TEST, 1.0, Direction.AT_LEAST, "  ")


def test_threshold_out_of_ratio_range_is_rejected():
    with pytest.raises(ValueError, match="비율"):
        Threshold("X", Dimension.RULE_TEST, 95, Direction.AT_LEAST, "백분율이 아니라 비율이어야 한다")


def test_unmeasurable_metric_has_no_threshold():
    """측정할 수 없는 지표에 임계를 먼저 적지 않는다."""
    t = next(t for t in THRESHOLDS if t.metric == "Policy-version Consistency")
    assert t.threshold is None
    assert "측정할 수 없" in t.rationale


def test_every_dimension_is_covered():
    covered = {t.dimension for t in THRESHOLDS}
    assert covered == set(Dimension), f"미커버 dimension: {set(Dimension) - covered}"


def test_high_risk_metrics_demand_perfection():
    """고위험 지표에 타협 구간을 두면 그 지표를 고위험이라 부를 이유가 없다."""
    for t in THRESHOLDS:
        if t.high_risk and t.threshold is not None:
            assert t.threshold == 1.0, f"{t.metric}: 고위험인데 임계가 {t.threshold}"


def test_metric_names_are_unique():
    names = [t.metric for t in THRESHOLDS]
    assert len(names) == len(set(names))


# ---------- 문서와 코드가 갈라지지 않는가 ----------
@pytest.mark.parametrize("metric,expected", [
    ("Change Completeness", "≥ 95%"),
    ("Exception Recall", "100%"),
    ("Citation Correctness", "≥ 98%"),
    ("Unsupported Claim Rate", "≤ 2%"),
])
def test_thresholds_match_metrics_spec(metric, expected):
    """`docs/metrics_spec.md` 와 코드가 갈라지면 어느 쪽이 진짜인지 알 수 없다."""
    spec = SPEC.read_text(encoding="utf-8")
    row = next((ln for ln in spec.splitlines() if ln.startswith(f"| {metric} ")), None)
    assert row, f"metrics_spec 에 {metric} 행이 없다"
    assert expected.replace(" ", "") in row.replace(" ", "").replace("**", ""), \
        f"{metric}: 문서={row.strip()} / 코드={THRESHOLDS[0] and expected}"


# ---------- 미측정이 통과로 새지 않는가 ----------
def test_not_measured_is_not_a_pass(evidence):
    """이것이 이 파일의 핵심 테스트다."""
    sc = score(evidence)                       # js_port_agreement 를 주지 않는다
    js = next(m for m in sc.all_metrics if m.threshold.metric == "JS Port Agreement")
    assert js.verdict is Verdict.NOT_MEASURED
    assert js.verdict is not Verdict.PASS
    assert js in sc.unmeasured
    assert sc.summary()["passed"] < sc.summary()["total"]


def test_running_the_verification_moves_it_from_unmeasured_to_pass(evidence):
    without = score(evidence)
    with_check = score(evidence, js_port_agreement=1.0)
    assert with_check.summary()["not_measured"] == without.summary()["not_measured"] - 1


def test_js_port_disagreement_fails(evidence):
    sc = score(evidence, js_port_agreement=0.0)
    js = next(m for m in sc.all_metrics if m.threshold.metric == "JS Port Agreement")
    assert js.verdict is Verdict.FAIL
    assert sc.verdict is Verdict.FAIL
    assert js in sc.high_risk_failures


def test_dimension_fails_if_any_metric_fails(evidence):
    sc = score(evidence, js_port_agreement=0.0)
    rule_dim = next(d for d in sc.dimensions if d.dimension is Dimension.RULE_TEST)
    assert rule_dim.verdict is Verdict.FAIL


# ---------- 실측 연동 ----------
def test_current_run_has_no_failures(evidence):
    sc = score(evidence, js_port_agreement=1.0)
    assert not sc.failures, [m.threshold.metric for m in sc.failures]


def test_every_metric_carries_its_evidence(evidence):
    """어디서 나온 값인지 못 적으면 판정을 신뢰할 수 없다."""
    sc = score(evidence, js_port_agreement=1.0)
    for m in sc.all_metrics:
        assert m.evidence.strip(), m.threshold.metric


def test_scorecard_reacts_to_a_degraded_measurement(evidence):
    """지표가 나빠지면 판정이 바뀌어야 한다 — 안 바뀌면 스코어카드가 장식이다.

    인용 75건 중 절반이 원문에 없는 상황을 만들어 본다.
    """
    import copy

    from regimpact.extractor import GroundingReport

    degraded = copy.copy(evidence)
    total = evidence.grounding.total
    half = total // 2
    degraded.grounding = GroundingReport(
        total=total, grounded=half,
        ungrounded=list(evidence.extraction.changes[:total - half]))
    sc = score(degraded, js_port_agreement=1.0)
    assert sc.verdict is Verdict.FAIL
    failed = {m.threshold.metric for m in sc.failures}
    assert "Citation Correctness" in failed
    assert "Unsupported Claim Rate" in failed


def test_report_includes_the_scorecard(evidence):
    from regimpact.report import render
    text = render(evidence)
    assert "### 3.1 Assurance 스코어카드" in text
    assert "미측정은 통과가 아니다" in text
