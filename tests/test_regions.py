"""지역 레지스트리 검증 — 공문 원문의 '지역 수'와 대조한다.

왜 이 테스트가 필요한가:
    오라클과 엔진이 지역 **데이터**(REGISTRY)를 공유하므로, 데이터 자체가 틀리면 차등 검증이
    잡아내지 못한다. 그 구멍을 여기서 막는다 — 기준은 코드가 아니라 **공문 원문 참고2 표**다.

    docs/sources/raw/molit_press_20260630.txt 참고2 "투기과열지구 및 조정대상지역 현황"
      추가지정 전(6월말):  서울 25곳 / 경기 12곳
      추가지정 후(7.1~):   서울 25곳 / 경기 15곳  (+화성동탄·용인기흥·구리)
"""
from __future__ import annotations

from datetime import date

import pytest

from regimpact.models import RegionStatus, RegulatedType
from regimpact.regions import (
    REGISTRY,
    canonical_code,
    get_region,
    regions_by_sido,
    regulated_codes,
    resolve_region_status,
)

BEFORE = date(2026, 6, 30)   # 추가지정 전 (6월말)
AFTER = date(2026, 7, 1)     # 추가지정 후


def _by_sido(codes: list[str], sido: str) -> list[str]:
    return [c for c in codes if REGISTRY[c].sido == sido]


# --- 원문 지역 수 대조 (이 파일의 핵심) ---------------------------------------
def test_seoul_all_25_districts_regulated_before_and_after():
    """서울 25곳 — 6·30 추가지정과 무관하게 지정 전에도 후에도 전부 규제지역."""
    for as_of in (BEFORE, AFTER):
        assert len(_by_sido(regulated_codes(as_of), "서울특별시")) == 25
    assert len([r for r in REGISTRY.values() if r.sido == "서울특별시"]) == 25


def test_gyeonggi_regulated_count_12_before_15_after():
    assert len(_by_sido(regulated_codes(BEFORE), "경기도")) == 12
    assert len(_by_sido(regulated_codes(AFTER), "경기도")) == 15


def test_six_thirty_additions_are_exactly_three():
    added = set(regulated_codes(AFTER)) - set(regulated_codes(BEFORE))
    assert added == {
        "GYEONGGI_HWASEONG_DONGTAN",
        "GYEONGGI_YONGIN_GIHEUNG",
        "GYEONGGI_GURI",
    }


def test_no_regulated_region_outside_seoul_gyeonggi():
    """원문 표에 서울·경기 외 지역은 없다. 인천·부산·울산·제주 등은 전부 비규제."""
    for as_of in (BEFORE, AFTER):
        sidos = {REGISTRY[c].sido for c in regulated_codes(as_of)}
        assert sidos == {"서울특별시", "경기도"}


# --- 사고 재발 방지 -----------------------------------------------------------
def test_gangnam_is_regulated_not_baseline():
    """2026-08-18 사고: 강남이 '미등록 → 非규제'로 떨어져 70%로 판정됐다."""
    status, rtype = resolve_region_status("SEOUL_GANGNAM", AFTER)
    assert status is RegionStatus.REGULATED
    assert rtype is RegulatedType.SPECULATIVE_OVERHEATED


def test_unknown_code_is_unknown_not_non_regulated():
    status, _ = resolve_region_status("ATLANTIS_XX", AFTER)
    assert status is RegionStatus.UNKNOWN


# --- 시점 경계 ----------------------------------------------------------------
@pytest.mark.parametrize(
    "code,d,expected",
    [
        # 6·30 신규 지정 3곳: 6.30까지 비규제, 7.1부터 규제
        ("GYEONGGI_GURI", date(2026, 6, 30), RegionStatus.NON_REGULATED),
        ("GYEONGGI_GURI", date(2026, 7, 1), RegionStatus.REGULATED),
        # '25.10.16 지정분: 전일까지 비규제
        ("SEOUL_NOWON", date(2025, 10, 15), RegionStatus.NON_REGULATED),
        ("SEOUL_NOWON", date(2025, 10, 16), RegionStatus.REGULATED),
        ("GYEONGGI_GWACHEON", date(2025, 10, 15), RegionStatus.NON_REGULATED),
        ("GYEONGGI_GWACHEON", date(2025, 10, 16), RegionStatus.REGULATED),
        # 강남4구: 조정('16.11.3) → 투기과열('17.8.3)
        ("SEOUL_GANGNAM", date(2016, 11, 2), RegionStatus.NON_REGULATED),
        ("SEOUL_GANGNAM", date(2016, 11, 3), RegionStatus.REGULATED),
        # 비규제는 언제나 비규제
        ("ULSAN_NAM", date(2026, 7, 1), RegionStatus.NON_REGULATED),
        ("JEJU_JEJU", date(2026, 7, 1), RegionStatus.NON_REGULATED),
    ],
)
def test_region_status_at_boundaries(code, d, expected):
    assert resolve_region_status(code, d)[0] is expected


def test_gangnam4_regulated_type_switches_in_2017():
    assert resolve_region_status("SEOUL_SEOCHO", date(2017, 8, 2))[1] is RegulatedType.ADJUSTMENT
    assert (resolve_region_status("SEOUL_SEOCHO", date(2017, 8, 3))[1]
            is RegulatedType.SPECULATIVE_OVERHEATED)


# --- 레지스트리 위생 ----------------------------------------------------------
def test_legacy_codes_alias_to_current():
    for old, new in (("GURI", "GYEONGGI_GURI"),
                     ("YONGIN_GIHEUNG", "GYEONGGI_YONGIN_GIHEUNG"),
                     ("HWASEONG_DONGTAN", "GYEONGGI_HWASEONG_DONGTAN")):
        assert canonical_code(old) == new
        assert get_region(old) is REGISTRY[new]


def test_capital_area_flag():
    assert all(REGISTRY[c].capital_area for c in REGISTRY if REGISTRY[c].sido
               in {"서울특별시", "경기도", "인천광역시"})
    assert not REGISTRY["ULSAN_NAM"].capital_area
    assert not REGISTRY["JEJU_JEJU"].capital_area


def test_every_region_resolves_for_the_scenario_date():
    """전 지역이 시나리오 시점에 UNKNOWN 없이 해석돼야 한다(버전 구간 누락 탐지)."""
    for code in REGISTRY:
        assert resolve_region_status(code, AFTER)[0] is not RegionStatus.UNKNOWN


def test_sido_grouping_covers_registry():
    grouped = sum(len(items) for _, items in regions_by_sido())
    assert grouped == len(REGISTRY)
