"""판별력(negative control) — 하니스가 '틀린 것'을 실제로 잡는지 고정한다.

정상 데이터의 100%는 하니스가 오류에 둔감해도 나온다. 지표가 둔감해지는 순간
여기서 실패로 드러나야 한다. 브리프 §12 "검증의 한계를 숨기지 않는다".
"""
import json
from pathlib import Path

import pytest

from regimpact import rule_engine
from regimpact.discrimination import corrupt_extraction, discriminate_extraction
from regimpact.extractor import extract_regchange, load_sources
from regimpact.extractor.backends import resolve_completion
from regimpact.extractor.postprocess import normalize_regions
from regimpact.impact.builder import derive_rule_diff
from regimpact.proposal import build_proposal_from_extraction, check_proposal_consistency
from regimpact.tc_generator import run_regression

REPO = Path(__file__).resolve().parents[1]
RUN = REPO / "docs" / "eval" / "runs" / "run_perdoc_sonnet5.json"


@pytest.fixture(scope="module")
def pipeline():
    sources = load_sources()
    complete = resolve_completion("replay", model=None, run_path=str(RUN))
    extraction = normalize_regions(extract_regchange(sources, complete=complete)).normalized
    gold = json.loads(
        (REPO / "docs" / "eval" / "regchange_gold_6_30.json").read_text(encoding="utf-8")
    )
    return extraction, sources, gold


# ---------- Extractor Assurance ----------
def test_every_extractor_metric_reacts_to_injected_errors(pipeline):
    report = discriminate_extraction(*pipeline)
    assert report.all_detected, (
        f"오류에 둔감한 지표: {[r.metric for r in report.blind]} — "
        "이 지표들의 100%는 아무것도 증명하지 않는다"
    )


def test_hallucinated_citation_is_caught(pipeline):
    report = discriminate_extraction(*pipeline)
    cc = next(r for r in report.results if r.metric == "Citation Correctness")
    assert cc.clean == 1.0
    assert cc.corrupted < 1.0


def test_field_level_metrics_go_to_zero_not_just_down(pipeline):
    """시행일·지역은 단일 값이라 틀리면 0%다 — 집계 지표보다 민감하다."""
    report = discriminate_extraction(*pipeline)
    for name in ("Effective-date Correct", "Regions Correct"):
        r = next(x for x in report.results if x.metric == name)
        assert r.clean == 1.0 and r.corrupted == 0.0


def test_aggregate_rates_are_insensitive_to_single_item_errors(pipeline):
    """집계 비율의 한계를 명시적으로 고정한다.

    추출 54건 중 인용 1건을 환각으로 바꿔도 Citation Correctness 는 2pp 만 움직인다.
    즉 **집계 100%는 소수 환각을 가릴 수 있다.** 그래서 항목 단위 검사(Exception
    Recall·Effective-date·Regions)가 함께 있어야 한다. 이 성질이 바뀌면 문서를
    같이 고치라고 알리는 테스트다(docs/eval/VALIDATION_LIMITS.md).
    """
    report = discriminate_extraction(*pipeline)
    cc = next(r for r in report.results if r.metric == "Citation Correctness")
    exc = next(r for r in report.results if r.metric == "Exception Recall")
    assert cc.gap < 0.10, "집계 지표가 단건 오류에 크게 반응하면 문서의 설명이 낡은 것"
    assert exc.gap >= 0.50, "항목 단위 지표는 크게 떨어져야 한다"


# ---------- 룰 회귀: 독립 오라클이 엔진 변조를 잡는가 ----------
@pytest.mark.parametrize("constant,mutated", [
    ("LTV_REGULATED_STANDARD", 0.50),
    ("LTV_BASELINE", 0.65),
    ("LTV_REAL_DEMAND", 0.70),
])
def test_regression_catches_mutated_engine_constant(monkeypatch, constant, mutated):
    assert run_regression().pass_rate == 1.0
    monkeypatch.setattr(rule_engine, constant, mutated)
    assert run_regression().pass_rate < 1.0, f"{constant} 변조를 오라클이 놓쳤다"


# ---------- 변경안 ↔ 엔진 ----------
def test_proposal_consistency_reacts_to_corrupted_extraction(pipeline):
    extraction, _, _ = pipeline
    diff = derive_rule_diff()

    def rate(ex):
        s = check_proposal_consistency(
            build_proposal_from_extraction(ex), rule_diff=diff
        ).summary()
        return s["passed"] / s["total"]

    assert rate(corrupt_extraction(extraction)) < rate(extraction)


# ---------- corrupt_extraction 자체가 실제로 오염시키는가 ----------
def test_corruption_actually_changes_the_extraction(pipeline):
    """오염 함수가 무력해지면 위 테스트 전부가 조용히 무의미해진다."""
    extraction, _, _ = pipeline
    bad = corrupt_extraction(extraction)
    assert bad.effective_from != extraction.effective_from
    assert len(bad.target_regions) < len(extraction.target_regions)
    assert len(bad.changes) < len(extraction.changes)
    assert not any(c.category == "EXCEPTION" for c in bad.changes)
