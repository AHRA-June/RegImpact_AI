"""대출 여력 영향 금액 집계 테스트 (exposure).

검증 축:
  1. 밴드 정합 — PRICE_BANDS.share 합≈1.
  2. 여력 = 담보가격 × LTV — 단일 세그먼트로 손계산 대조.
  3. 방향 — 6·30에서 여력 총액은 축소(Δ<0), 감소율 양수.
  4. 산정불가 분리 — 명세 여백(비규제 유주택 before) 세그먼트는 undetermined로 분리(금액 0 아님).
  5. 밴드 배분 정합 — 판정가능 밴드 여력 합 = 전체 판정가능 여력.
  6. 수렴 — 몬테카를로 가격 부여 표본의 1인당 감소율이 정확 가중과 근접.
  7. 룰 무간섭 — property_price는 룰엔진 판정(max_ltv)에 영향 없음.
"""
from datetime import date

from regimpact.impact import (
    CustomerSegment,
    attach_sampled_prices,
    compute_exposure,
    enumerate_weighted_profiles,
    mean_property_price,
    sample_portfolio,
)
from regimpact.impact.exposure import PRICE_BANDS, PriceBand


def test_price_band_shares_sum_to_one():
    assert abs(sum(b.share for b in PRICE_BANDS) - 1.0) < 1e-9


def test_capacity_is_price_times_ltv_single_segment():
    # 무주택 일반 GURI: before 70%, after 40%. 단일 밴드(가격 10억, share 1.0)로 손계산.
    seg = CustomerSegment(
        label="무주택",
        attrs={"region_code": "GURI", "house_count": 0},
        weight=1.0,
    )
    band = [PriceBand("단일", 10.0, 1.0)]
    rep = compute_exposure([seg], bands=band)
    # before = 10 * 0.70 = 7.0, after = 10 * 0.40 = 4.0
    assert abs(rep.before_capacity - 7.0) < 1e-9
    assert abs(rep.after_capacity - 4.0) < 1e-9
    assert abs(rep.delta_capacity - (-3.0)) < 1e-9
    assert abs(rep.pct_reduction - (3.0 / 7.0)) < 1e-9


def test_6_30_capacity_tightens():
    rep = compute_exposure(enumerate_weighted_profiles())
    assert rep.delta_capacity < 0                # 여력 축소
    assert rep.pct_reduction is not None and rep.pct_reduction > 0
    assert rep.before_capacity > rep.after_capacity


def test_undetermined_separated_not_zeroed():
    # 비규제 유주택(house_count=1, 처분조건 없음): 시행 전 기준선 명세 여백 → before 판정불가.
    owner = CustomerSegment(
        label="비처분 1주택",
        attrs={"region_code": "GURI", "house_count": 1},
        weight=1.0,
    )
    rep = compute_exposure([owner])
    assert rep.undetermined_weight == 1.0
    assert rep.determinable_weight == 0.0
    assert rep.before_capacity == 0.0           # 금액 미산정(0으로 뭉갬 아님)
    assert rep.undetermined_share == 1.0
    seg = rep.by_segment[0]
    assert seg.determinable is False


def test_band_capacity_sums_to_total():
    rep = compute_exposure(enumerate_weighted_profiles())
    band_before = sum(b.before_capacity for b in rep.by_band)
    band_after = sum(b.after_capacity for b in rep.by_band)
    assert abs(band_before - rep.before_capacity) < 1e-6
    assert abs(band_after - rep.after_capacity) < 1e-6


def test_undetermined_weight_conserved():
    rep = compute_exposure(enumerate_weighted_profiles())
    assert abs(rep.determinable_weight + rep.undetermined_weight - rep.total_weight) < 1e-9
    band_undet = sum(b.undetermined_weight for b in rep.by_band)
    assert abs(band_undet - rep.undetermined_weight) < 1e-6


def test_paths_converge_on_reduction():
    exact = compute_exposure(enumerate_weighted_profiles())
    sampled = compute_exposure(attach_sampled_prices(sample_portfolio(8000, seed=3), seed=9))
    assert abs(exact.pct_reduction - sampled.pct_reduction) < 0.03


def test_price_does_not_affect_ruling():
    base = CustomerSegment(label="a", attrs={"region_code": "GURI", "house_count": 0}, weight=1.0)
    priced = CustomerSegment(label="a", attrs={"region_code": "GURI", "house_count": 0},
                             weight=1.0, property_price=99.0)
    r1 = compute_exposure([base], bands=[PriceBand("b", 10.0, 1.0)])
    r2 = compute_exposure([priced], bands=[PriceBand("b", 10.0, 1.0)])
    # property_price 필드가 있어도 LTV 판정은 동일(밴드 가격으로만 금액 환산)
    assert r1.by_segment[0].before_ltv == r2.by_segment[0].before_ltv
    assert r1.by_segment[0].after_ltv == r2.by_segment[0].after_ltv


def test_mean_property_price():
    expected = sum(b.representative_price * b.share for b in PRICE_BANDS)
    assert abs(mean_property_price() - expected) < 1e-9
