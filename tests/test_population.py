"""가중 합성 모집단 테스트 — 비중 실측화 + 수천 건 확장.

검증 축:
  1. 비중 정합 — 아키타입 점유율 합≈1, 정확 가중 프로파일 weight 합≈1.
  2. 결정성 — sample_portfolio(seed)는 재현 가능.
  3. 분포 수렴 — 대표본에서 아키타입 빈도가 비중 모델에 근접.
  4. 가중 일치 — 몬테카를로 표본의 가중 통계가 정확 가중 프로파일과 근접.
  5. 회귀 — 5,000명 표본이 독립 오라클과 100% 일치(수천 건 분모).
"""
from collections import Counter
from datetime import date

from regimpact import evaluate
from regimpact.impact import (
    analyze_impact,
    enumerate_weighted_profiles,
    sample_portfolio,
)
from regimpact.impact.population import ARCHETYPE_SHARE, REGION_MIX
from regimpact.tc_generator.oracle import expected_outcome

AFTER = date(2026, 7, 2)


def test_shares_sum_to_one():
    assert abs(sum(ARCHETYPE_SHARE.values()) - 1.0) < 1e-9
    assert abs(sum(REGION_MIX.values()) - 1.0) < 1e-9


def test_enumerate_weights_sum_to_one():
    prof = enumerate_weighted_profiles()
    assert abs(sum(s.weight for s in prof) - 1.0) < 1e-9
    assert len(prof) == len(ARCHETYPE_SHARE) * len(REGION_MIX)


def test_sample_is_deterministic():
    a = sample_portfolio(500, seed=7)
    b = sample_portfolio(500, seed=7)
    assert [s.attrs for s in a] == [s.attrs for s in b]


def test_sample_distribution_converges():
    sample = sample_portfolio(6000, seed=1)
    # 아키타입 라벨은 "무주택 일반#123" → '#' 앞부분
    freq = Counter(s.label.split("#")[0] for s in sample)
    for label, share in ARCHETYPE_SHARE.items():
        got = freq[label] / len(sample)
        assert abs(got - share) < 0.05, f"{label}: {got:.3f} vs {share:.3f}"


def test_weighted_summary_matches_between_paths():
    exact = analyze_impact(enumerate_weighted_profiles())
    sampled = analyze_impact(sample_portfolio(8000, seed=3))
    de, dsamp = exact.direction_weight_share(), sampled.direction_weight_share()
    for k in ("TIGHTENED", "UNCHANGED", "NEEDS_REVIEW"):
        assert abs(de[k] - dsamp[k]) < 0.03, f"{k}: {de[k]:.3f} vs {dsamp[k]:.3f}"
    assert abs(exact.weighted_mean_delta() - sampled.weighted_mean_delta()) < 0.02
    assert abs(exact.review_weight_share() - sampled.review_weight_share()) < 0.03


def test_direction_weight_share_sums_to_one():
    m = analyze_impact(enumerate_weighted_profiles())
    assert abs(sum(m.direction_weight_share().values()) - 1.0) < 1e-9


def test_population_regression_matches_oracle():
    sample = sample_portfolio(5000, seed=42)
    mism = 0
    for seg in sample:
        app = seg.application(AFTER)
        exp, act = expected_outcome(app), evaluate(app)
        if act.status != exp.status or act.max_ltv != exp.max_ltv:
            mism += 1
    assert mism == 0, f"{mism} 불일치"
