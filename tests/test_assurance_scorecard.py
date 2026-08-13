"""Assurance 4 dimension 스코어카드 + 확정 임계값 테스트.

검증: ①4 dimension 12지표 구성 ②6·30 실측 전부 PASS·Overall PASS ③새 지표 3종 계산
④임계값 판정 로직(Strict) ⑤고위험 FAIL→전체 FAIL 종합 규칙 ⑥가드레일(열위 입력 시 FAIL 포착).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from regimpact.assurance import (  # noqa: E402
    THRESHOLDS,
    build_scorecard,
    format_scorecard_md,
)
from regimpact.assurance.metrics import (  # noqa: E402
    grandfathering_recall,
    policy_version_consistency,
    source_contradiction_rate,
)
from regimpact.assurance.thresholds import Status, overall_status  # noqa: E402
from regimpact.extractor import load_sources  # noqa: E402
from regimpact.extractor.schema import Citation, RegChangeExtraction, RegChangeItem  # noqa: E402
from regimpact.tc_generator import generate_grid, run_regression  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
GOLD = json.loads((ROOT / "docs/eval/regchange_gold_6_30.json").read_text(encoding="utf-8"))
EXTRACTED = json.loads((ROOT / "docs/eval/regchange_extracted_6_30.json").read_text(encoding="utf-8"))


def _ext():
    return RegChangeExtraction.from_dict(EXTRACTED)


def _sc(regression=None):
    return build_scorecard(_ext(), load_sources(), GOLD, regression)


# ---------- 구성 ----------
def test_scorecard_has_four_dimensions_twelve_metrics():
    sc = _sc(run_regression(generate_grid()))
    assert [d.dimension for d in sc.dimensions] == [1, 2, 3, 4]
    assert len(sc.all_metrics) == 12


def test_scorecard_6_30_all_pass():
    sc = _sc(run_regression(generate_grid()))
    assert sc.overall == Status.PASS
    for d in sc.dimensions:
        assert d.status == Status.PASS, d.name
    assert sc.failed == []


# ---------- 새 지표 3종 ----------
def test_source_contradiction_rate_zero_on_grounded():
    assert source_contradiction_rate(_ext(), load_sources()) == 0.0


def test_source_contradiction_detects_fabricated_value():
    """원문에 없는 LTV 값(예: 33%)을 주장하면 contradiction으로 잡혀야 한다."""
    cite = Citation(source_doc_id="FAQ_20260630",
                    quote="규제지역 내 주담대 취급시 강화된 LTV(70→40%) 적용")
    ext = RegChangeExtraction(
        policy_id="X", effective_from="2026-07-01", target_regions=["GURI"],
        changes=[RegChangeItem("LTV", "날조", cite, before="70%", after="33%")])
    assert source_contradiction_rate(ext, load_sources()) == 1.0


def test_grandfathering_recall_full():
    assert grandfathering_recall(_ext(), GOLD) == 1.0


def test_policy_version_consistency_full():
    assert policy_version_consistency() == 1.0


# ---------- 임계값 판정(Strict) ----------
def test_threshold_higher_bands():
    spec = THRESHOLDS["exception_recall"]  # higher, pass 0.95 warn 0.90
    assert spec.evaluate(1.0) == Status.PASS
    assert spec.evaluate(0.92) == Status.WARN
    assert spec.evaluate(0.5) == Status.FAIL


def test_threshold_lower_contradiction_no_warn_band():
    spec = THRESHOLDS["source_contradiction_rate"]  # lower, pass 0 warn 0
    assert spec.evaluate(0.0) == Status.PASS
    assert spec.evaluate(0.01) == Status.FAIL


def test_exact_metric_fails_below_one():
    spec = THRESHOLDS["policy_version_consistency"]  # exact 1.0
    assert spec.evaluate(1.0) == Status.PASS
    assert spec.evaluate(0.99) == Status.FAIL


# ---------- 종합 판정 규칙 ----------
def test_overall_high_risk_fail_makes_fail():
    assert overall_status([(Status.FAIL, True), (Status.PASS, False)]) == Status.FAIL


def test_overall_non_high_risk_fail_makes_warn():
    assert overall_status([(Status.FAIL, False), (Status.PASS, True)]) == Status.WARN


def test_overall_all_pass():
    assert overall_status([(Status.PASS, True), (Status.PASS, False)]) == Status.PASS


# ---------- 가드레일: 열위 추출은 FAIL로 잡힌다 ----------
def test_scorecard_fails_on_missing_exception():
    """서민·실수요 예외를 뺀 추출은 Exception Recall 고위험 FAIL → 전체 FAIL."""
    d = json.loads(json.dumps(EXTRACTED))
    d["changes"] = [c for c in d["changes"] if "서민" not in c["summary"]]
    ext = RegChangeExtraction.from_dict(d)
    sc = build_scorecard(ext, load_sources(), GOLD, run_regression(generate_grid()))
    labels = {m.spec.label: m.status for m in sc.all_metrics}
    assert labels["Exception Recall"] == Status.FAIL
    assert sc.overall == Status.FAIL


# ---------- 리포트 렌더 ----------
def test_format_scorecard_md():
    md = format_scorecard_md(_sc(run_regression(generate_grid())))
    assert "Assurance Scorecard" in md
    assert "종합 판정" in md
    assert "Policy-version Consistency" in md
    assert "Grandfathering Recall" in md
