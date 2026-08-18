"""지역 규제상태의 시점 버전 관리 (docs/00_BRIEF.md §7, regulatory_facts.md '지역 버전').

지역 상태는 시점에 따라 달라지는 버전 데이터다. 6·30 건: 3개 지역이 2026-07-01부터 REGULATED.
값 출처: 사람이 확정한 regulatory_facts.md (C02, C03). LOCKED §4.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from .models import RegionStatus, RegulatedType

REG_EFFECTIVE = date(2026, 7, 1)   # 투기과열·조정 효력 (시행일)


@dataclass(frozen=True)
class RegionVersion:
    status: RegionStatus
    effective_from: Optional[date]   # None = 열림(과거)
    effective_to: Optional[date]     # None = 열림(현재)
    regulated_type: RegulatedType = RegulatedType.NONE
    source_policy_id: Optional[str] = None


# 6·30 신규 지정 3개 지역: 6.30까지 非규제(수도권) → 7.1부터 규제(투기과열지구)
_SIX_THIRTY_REGIONS = ("GURI", "YONGIN_GIHEUNG", "HWASEONG_DONGTAN")

REGION_VERSIONS: dict[str, list[RegionVersion]] = {
    code: [
        RegionVersion(RegionStatus.NON_REGULATED, None, date(2026, 6, 30)),
        RegionVersion(
            RegionStatus.REGULATED, REG_EFFECTIVE, None,
            RegulatedType.SPECULATIVE_OVERHEATED, "FSC_20260630",
        ),
    ]
    for code in _SIX_THIRTY_REGIONS
}


def resolve_region_status(
    region_code: str, as_of: date
) -> tuple[RegionStatus, RegulatedType]:
    """특정 시점의 지역 규제상태를 반환. 미등록 지역은 NON_REGULATED로 간주."""
    for v in REGION_VERSIONS.get(region_code, []):
        after_start = v.effective_from is None or as_of >= v.effective_from
        before_end = v.effective_to is None or as_of <= v.effective_to
        if after_start and before_end:
            return v.status, v.regulated_type
    return RegionStatus.NON_REGULATED, RegulatedType.NONE


# --------------------------------------------------------------- 명칭 → 코드 정규화
#
# LLM 추출기는 공문 원문의 **한글 지역명**("화성시 동탄구")을 내놓지만 룰엔진은
# **코드**("HWASEONG_DONGTAN")로 동작한다. 이 경계를 LLM에게 맡기면(프롬프트에 코드
# 어휘를 주면) 정답 후보를 흘리는 셈이 되므로, **결정적 별칭 테이블**로 변환한다.
# 매칭 실패는 조용히 버리지 않고 None을 돌려 호출측이 escalate 하게 한다.
#
# 이 표는 규제 "값"이 아니라 식별자 별칭이다(LOCKED §4의 규칙값 범위 밖). 신규 지역이
# 등장하면 여기에 추가한다.
REGION_ALIASES: dict[str, str] = {
    # 6·30 신규 지정 3곳
    "구리시": "GURI",
    "구리": "GURI",
    "용인시 기흥구": "YONGIN_GIHEUNG",
    "기흥구": "YONGIN_GIHEUNG",
    "용인기흥": "YONGIN_GIHEUNG",
    "화성시 동탄구": "HWASEONG_DONGTAN",
    "동탄구": "HWASEONG_DONGTAN",
    "화성동탄": "HWASEONG_DONGTAN",
    # 기존 규제지역·비교 대상 (별칭표가 정답 3곳만 담아 어휘 자체가 힌트가 되지 않도록)
    "서울특별시": "SEOUL",
    "강남구": "SEOUL_GANGNAM",
    "서초구": "SEOUL_SEOCHO",
    "송파구": "SEOUL_SONGPA",
    "용산구": "SEOUL_YONGSAN",
    "성동구": "SEOUL_SEONGDONG",
    "마포구": "SEOUL_MAPO",
    "과천시": "GWACHEON",
    "성남시 분당구": "SEONGNAM_BUNDANG",
    "분당구": "SEONGNAM_BUNDANG",
    "수원시 영통구": "SUWON_YEONGTONG",
    "안양시 동안구": "ANYANG_DONGAN",
    "광명시": "GWANGMYEONG",
    "하남시": "HANAM",
    "세종특별자치시": "SEJONG",
    "세종시": "SEJONG",
    "청주시": "CHEONGJU",
}

_ALIAS_STRIP = ("경기도", "경기", "인천광역시", "서울시", "특별자치시", "광역시")


def normalize_region_name(name: str) -> Optional[str]:
    """공문 표기 지역명을 룰엔진 지역코드로 변환한다. 모르면 None.

    이미 코드 형태("GURI")로 들어오면 그대로 통과시킨다. 광역 접두어("경기도 ")는
    떼고 매칭하며, 그래도 못 찾으면 별칭 키가 포함된 항목을 마지막으로 시도한다.
    """
    if not name:
        return None
    raw = name.strip()
    if raw in REGION_VERSIONS or (raw.isascii() and raw.isupper()):
        return raw

    cleaned = raw
    for prefix in _ALIAS_STRIP:
        cleaned = cleaned.replace(prefix, " ")
    cleaned = " ".join(cleaned.split())

    for candidate in (raw, cleaned):
        if candidate in REGION_ALIASES:
            return REGION_ALIASES[candidate]

    # 부분 포함(예: "경기도 화성시 동탄구 일원") — 가장 긴 별칭을 우선 매칭
    for alias in sorted(REGION_ALIASES, key=len, reverse=True):
        if alias in cleaned:
            return REGION_ALIASES[alias]
    return None
