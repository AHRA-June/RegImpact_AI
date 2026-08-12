"""비중/가격 민감도·견고성 분석 테스트.

검증 축:
  1. 정합성 — sensitivity의 base 헤드라인이 실제 모듈(analyze_impact/compute_exposure)과 일치.
  2. 결정성 — 같은 seed의 몬테카를로는 재현 가능.
  3. 가격 불변성 — 여력 감소율(%)은 담보가격 수준에 불변, 1인당 억 금액은 비례 이동.
  4. 밴드 정렬 — P5 ≤ P50 ≤ P95, base는 밴드 근처.
  5. 견고성 — 여력 축소/1인당 감소는 전 표본 성립(방향 결론 견고).
  6. driver — 여력 감소율의 최대 driver는 아키타입 비중(무주택 일반), 가격 수준 아님.
"""
import math

from regimpact.impact import (
    analyze_impact,
    build_response_table,
    compute_exposure,
    compute_headline,
    enumerate_weighted_profiles,
    monte_carlo,
    oat_tornado,
    sensitivity_bands,
)
from regimpact.impact.exposure import PriceBand
from regimpact.impact.sensitivity import PRICE_BANDS

TABLE = build_response_table()


def test_base_matches_real_modules():
    base = compute_headline(TABLE)
    m = analyze_impact(enumerate_weighted_profiles())
    ex = compute_exposure(enumerate_weighted_profiles())
    assert abs(base.tightened_share - m.direction_weight_share()["TIGHTENED"]) < 1e-9
    assert abs(base.review_share - m.review_weight_share()) < 1e-9
    assert abs(base.mean_delta_pp - m.weighted_mean_delta() * 100) < 1e-9
    assert abs(base.exposure_pct_reduction - ex.pct_reduction) < 1e-9
    assert abs(base.per_unit_delta_eok - ex.per_unit_delta()) < 1e-9
    assert abs(base.undetermined_share - ex.undetermined_share) < 1e-9


def test_monte_carlo_deterministic():
    a = monte_carlo(TABLE, n=200, seed=7)
    b = monte_carlo(TABLE, n=200, seed=7)
    assert [x.exposure_pct_reduction for x in a] == [x.exposure_pct_reduction for x in b]


def test_price_level_invariance_of_pct_reduction():
    base = compute_headline(TABLE)
    # 담보가격 수준을 3배로 올려도 감소율(%)은 불변(가격이 세그먼트 독립·균일하므로 상쇄)
    scaled = [PriceBand(b.label, b.representative_price * 3.0, b.share) for b in PRICE_BANDS]
    hi = compute_headline(TABLE, bands=scaled)
    assert abs(hi.exposure_pct_reduction - base.exposure_pct_reduction) < 1e-9
    # 반면 1인당 억 금액은 3배로 비례
    assert abs(hi.per_unit_delta_eok - base.per_unit_delta_eok * 3.0) < 1e-9


def test_bands_ordered_and_bracket_base():
    sb = sensitivity_bands(TABLE, n=1500, seed=42)
    for f, (p5, p50, p95) in sb.bands.items():
        assert p5 <= p50 <= p95, f
        base_v = getattr(sb.base, f)
        # base는 밴드 범위 안(또는 경계)에 있어야 함
        assert p5 - 1e-6 <= base_v <= p95 + 1e-6, f


def test_direction_conclusions_robust():
    sb = sensitivity_bands(TABLE, n=2000, seed=42)
    # 여력 축소·1인당 감소는 전 표본에서 성립(방향 결론 견고)
    assert sb.robustness["여력 축소(감소율>0)"] == 1.0
    assert sb.robustness["1인당 여력 감소(Δ<0)"] == 1.0
    # '강화 과반'은 가정-취약(전 표본은 아님) — 정직 표기 확인
    assert 0.5 < sb.robustness["강화 과반(강화>50%)"] < 1.0


def test_pct_reduction_driver_is_weight_not_price():
    _, bars = oat_tornado(TABLE)
    by = {b.assumption: b.swing("exposure_pct_reduction") for b in bars}
    price_swing = by["담보가격 수준 ±30%"]
    top = max(by.items(), key=lambda kv: kv[1])
    assert price_swing < 1e-9                      # 가격 수준은 감소율에 영향 0
    assert "비중:무주택 일반" == top[0]              # 최대 driver는 무주택 일반 비중
    assert top[1] > 0.03


def test_per_unit_driver_includes_price():
    _, bars = oat_tornado(TABLE)
    by = {b.assumption: b.swing("per_unit_delta_eok") for b in bars}
    # 1인당 억 금액에서는 담보가격 수준이 최대(또는 최상위) driver
    top = max(by.items(), key=lambda kv: kv[1])
    assert top[0] == "담보가격 수준 ±30%"
