"""지역 레지스트리 — 참고2 현황표 정합성과 UNKNOWN 의미론.

결함 R-01: 레지스트리에 6·30 신규 3곳만 있고 기존 규제지역이 빠져 있었다. 미등록 지역을
NON_REGULATED 로 간주하는 기본값과 결합해, 강남 무주택 차주가 LTV 70%를 받았다.
여기 테스트들은 (a) 현황표를 옮긴 결과가 원문과 맞는지 (b) 미등록이 다시 조용한
非규제로 되돌아가지 않는지를 고정한다.
"""
from datetime import date

import pytest

from regimpact.models import RegionStatus, RegulatedType
from regimpact.regions import (
    CAPITAL_AREA_REGIONS,
    REGION_VERSIONS,
    is_capital_area,
    normalize_region_name,
    resolve_region_status,
)

AFTER = date(2026, 8, 1)


# ---------- 현황표 정합성 ----------
def test_seoul_has_all_25_districts():
    """참고2 현황표 '서울(25곳)'. 강남4구 + 나머지 21개구."""
    seoul = [c for c in REGION_VERSIONS if c.startswith("SEOUL_")]
    assert len(seoul) == 25


def test_gyeonggi_has_15_after_six_thirty():
    """현황표 '경기(15곳)' — 기존 12곳 + 6·30 신규 3곳."""
    seoul = {c for c in REGION_VERSIONS if c.startswith("SEOUL_")}
    non_regulated = {"SEJONG", "CHEONGJU"}
    gyeonggi = set(REGION_VERSIONS) - seoul - non_regulated
    assert len(gyeonggi) == 15


@pytest.mark.parametrize("code", ["SEOUL_GANGNAM", "SEOUL_SEOCHO",
                                  "SEOUL_SONGPA", "SEOUL_YONGSAN"])
def test_gangnam_four_are_speculative_overheated_since_2017(code):
    """'17.8.3 투기과열지구. 이 4곳이 비규제로 나오던 것이 결함 R-01."""
    assert resolve_region_status(code, AFTER) == (
        RegionStatus.REGULATED, RegulatedType.SPECULATIVE_OVERHEATED,
    )


def test_gangnam_four_were_adjustment_only_between_2016_and_2017():
    """'16.11.3 조정대상 → '17.8.3 투기과열. 그 사이 구간이 살아있어야 한다."""
    assert resolve_region_status("SEOUL_GANGNAM", date(2017, 1, 1)) == (
        RegionStatus.REGULATED, RegulatedType.ADJUSTMENT,
    )


def test_region_status_is_versioned_not_static():
    """지정 전에는 같은 지역이 非규제다."""
    status, _ = resolve_region_status("SEOUL_GANGNAM", date(2016, 1, 1))
    assert status == RegionStatus.NON_REGULATED


def test_seoul_21_and_gyeonggi_12_designated_on_2025_10_16():
    for code in ("SEOUL_DOBONG", "SUWON_JANGAN", "UIWANG"):
        assert resolve_region_status(code, date(2025, 10, 15))[0] == \
            RegionStatus.NON_REGULATED
        assert resolve_region_status(code, date(2025, 10, 16))[0] == \
            RegionStatus.REGULATED


def test_six_thirty_regions_flip_on_effective_date():
    for code in ("GURI", "YONGIN_GIHEUNG", "HWASEONG_DONGTAN"):
        assert resolve_region_status(code, date(2026, 6, 30))[0] == \
            RegionStatus.NON_REGULATED
        assert resolve_region_status(code, date(2026, 7, 1))[0] == \
            RegionStatus.REGULATED


# ---------- UNKNOWN 의미론 ----------
def test_unregistered_region_is_unknown_not_non_regulated():
    """이 테스트가 결함 R-01의 재발을 막는 지점이다."""
    status, rtype = resolve_region_status("BUSAN_HAEUNDAE", AFTER)
    assert status == RegionStatus.UNKNOWN
    assert status != RegionStatus.NON_REGULATED
    assert rtype == RegulatedType.NONE


def test_known_non_regulated_is_explicit():
    """비규제는 '등록되지 않아서'가 아니라 '등록해서' 비규제여야 한다."""
    for code in ("SEJONG", "CHEONGJU"):
        assert code in REGION_VERSIONS
        assert resolve_region_status(code, AFTER)[0] == RegionStatus.NON_REGULATED


def test_out_of_range_date_is_unknown_not_lenient():
    """버전 구간 어디에도 안 걸리면 관대한 기본값 대신 UNKNOWN."""
    assert resolve_region_status("SEOUL_GANGNAM", date(1900, 1, 1))[0] in (
        RegionStatus.NON_REGULATED, RegionStatus.UNKNOWN,
    )


# ---------- 수도권 ----------
def test_capital_area_covers_every_registered_capital_region():
    """레지스트리에 있는 서울·경기 지역은 전부 수도권으로 잡혀야 한다."""
    non_capital = {"SEJONG", "CHEONGJU"}
    for code in REGION_VERSIONS:
        if code in non_capital:
            assert not is_capital_area(code)
        else:
            assert is_capital_area(code), code


def test_wide_area_codes_are_capital_area():
    """시군구를 몰라도 '서울특별시'는 수도권인 것이 확실하다."""
    assert is_capital_area("SEOUL")
    assert "SEOUL" not in REGION_VERSIONS   # 규제상태는 판정 불가


# ---------- 별칭 ----------
@pytest.mark.parametrize("name,code", [
    ("강남구", "SEOUL_GANGNAM"),
    ("서울 도봉", "SEOUL_DOBONG"),
    ("중구", "SEOUL_JUNG"),
    ("중랑구", "SEOUL_JUNGNANG"),      # "중구"에 잡아먹히면 안 된다
    ("구로구", "SEOUL_GURO"),
    ("구리시", "GURI"),                # 구로/구리 혼동 금지
    ("경기도 의왕시", "UIWANG"),
    ("수원장안", "SUWON_JANGAN"),
    ("수원시 팔달구", "SUWON_PALDAL"),
    ("청주시", "CHEONGJU"),
])
def test_alias_resolution(name, code):
    assert normalize_region_name(name) == code


def test_unknown_name_returns_none_not_a_guess():
    assert normalize_region_name("울산광역시 남구") is None


# ------------------------------------------------ 2020 6·17 신설 코드 (검수 확정 2026-08-19)

def test_homonym_gu_aliases_resolve_by_city():
    """검수 중 발견된 결함의 회귀 고정 — '대전 중구'가 서울 중구로 오매핑되던 문제.

    광역시의 동명 구는 시명 한정 별칭만 등록한다. 맨 '중구'는 기존대로 서울이다
    (6·30 코퍼스 문맥 — 바꾸면 기존 추출 재생·골드 매핑이 갈라진다)."""
    from regimpact.regions import normalize_region_name as n
    assert n("대전 중구") == "DAEJEON_JUNG"
    assert n("대전광역시 중구") == "DAEJEON_JUNG"
    assert n("대전 서구") == "DAEJEON_SEO"
    assert n("인천 서구") == "INCHEON_SEO"
    assert n("중구") == "SEOUL_JUNG"          # 기존 동작 유지
    assert n("서울 중구") == "SEOUL_JUNG"


def test_2020_pending_codes_are_unknown_until_release_docs():
    """신설 코드는 버전 구간이 없다 — 해제 원문 확보 전이므로 UNKNOWN(사람 검토)이 정직한 상태.

    NON_REGULATED 로 두면 2020~해제 사이가 조용히 비규제로 판정되고,
    REGULATED 로 두면 해제 이후가 계속 규제로 판정된다. 둘 다 지어낸 값이다."""
    from datetime import date
    from regimpact.models import RegionStatus
    from regimpact.regions import resolve_region_status
    for code in ("GUNPO", "ANSAN_DANWON", "SUWON_GWONSEON", "DAEJEON_YUSEONG", "INCHEON_SEO"):
        status, _ = resolve_region_status(code, date(2021, 6, 1))
        assert status is RegionStatus.UNKNOWN, code


def test_2020_capital_area_membership():
    """수도권 여부는 법령상 확실한 사실 — 규제 구간 미확정과 무관하게 등록한다."""
    from regimpact.regions import is_capital_area
    for code in ("GUNPO", "ANSAN_DANWON", "SUWON_GWONSEON", "ANYANG_MANAN",
                 "INCHEON_YEONSU", "INCHEON_NAMDONG", "INCHEON_SEO"):
        assert is_capital_area(code), code
    for code in ("DAEJEON_DONG", "DAEJEON_JUNG", "DAEJEON_SEO", "DAEJEON_YUSEONG"):
        assert not is_capital_area(code), code
