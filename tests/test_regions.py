"""지역명 → canonical code 정규화 계층 테스트.

추출/사람 입력의 한글 지역명("경기도 화성시 동탄구")을 룰엔진·골드의 code(HWASEONG_DONGTAN)로
정규화한다. 6·30 실측에서 Regions MISS(한글명↔코드 불일치)를 잡기 위해 추가됨(발견 3).
"""
import pytest

from regimpact import (
    KNOWN_REGION_CODES,
    normalize_regions,
    resolve_region_code,
)


# ---------- resolve_region_code ----------
@pytest.mark.parametrize(
    "name,expected",
    [
        ("구리시", "GURI"),
        ("경기도 구리시", "GURI"),
        ("용인시 기흥구", "YONGIN_GIHEUNG"),
        ("경기도 용인시 기흥구", "YONGIN_GIHEUNG"),
        ("화성시 동탄구", "HWASEONG_DONGTAN"),
        ("경기도 화성시 동탄구", "HWASEONG_DONGTAN"),
        ("  구리 ", "GURI"),               # 공백 견고
    ],
)
def test_resolve_korean_names(name, expected):
    assert resolve_region_code(name) == expected


def test_resolve_is_idempotent_on_codes():
    for code in KNOWN_REGION_CODES:
        assert resolve_region_code(code) == code
    assert resolve_region_code("guri") == "GURI"   # 대소문자 무관


def test_resolve_unknown_returns_none():
    # 6·30 대상이 아닌 지역은 미상(None) — 조용히 코드로 만들지 않는다
    assert resolve_region_code("서울시 강남구") is None
    assert resolve_region_code("부산시 해운대구") is None
    assert resolve_region_code("") is None


# ---------- normalize_regions ----------
def test_normalize_maps_all_six_thirty_names():
    names = ["화성시 동탄구", "용인시 기흥구", "구리시"]
    codes, unmapped = normalize_regions(names)
    assert set(codes) == {"HWASEONG_DONGTAN", "YONGIN_GIHEUNG", "GURI"}
    assert unmapped == []


def test_normalize_preserves_order_and_dedups():
    codes, _ = normalize_regions(["구리시", "구리", "용인 기흥"])
    assert codes == ["GURI", "YONGIN_GIHEUNG"]   # 중복 제거 + 순서 보존


def test_normalize_surfaces_unmapped():
    codes, unmapped = normalize_regions(["구리시", "세종특별자치시"])
    assert codes == ["GURI"]
    assert unmapped == ["세종특별자치시"]          # 조용한 누락 금지
