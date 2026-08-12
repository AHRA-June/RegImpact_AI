"""지역 규제상태의 시점 버전 관리 (docs/00_BRIEF.md §7, regulatory_facts.md '지역 버전').

지역 상태는 시점에 따라 달라지는 버전 데이터다. 6·30 건: 3개 지역이 2026-07-01부터 REGULATED.
값 출처: 사람이 확정한 regulatory_facts.md (C02, C03). LOCKED §4.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable, Optional

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


# --------------------------------------------------------------------------- #
# 지역명 → canonical code 정규화 계층
# --------------------------------------------------------------------------- #
# LLM 추출/사람 입력은 지역을 한글명("경기도 화성시 동탄구")으로 주지만, 룰엔진·골드는
# canonical code(GURI 등)를 쓴다. 추출은 올바르되 표현형만 다른 문제이므로, 정규화를
# 별도 계층으로 분리한다(추출 원본은 훼손하지 않고 비교 시점에만 코드로 변환).
#
# 매칭은 **distinctive token 포함** 방식: 6·30 3개 지역은 서로 겹치지 않는 고유 지명
# ('구리'/'기흥'/'동탄')을 가져 접두("경기도"·"시"·"구")에 견고하다. LOCKED §4: 이 사전은
# 사람이 확정하는 지역 도메인 사실이다(regulatory_facts.md '지역 버전').
_CODE_MATCH_TOKENS: dict[str, tuple[str, ...]] = {
    "GURI": ("구리",),
    "YONGIN_GIHEUNG": ("기흥",),
    "HWASEONG_DONGTAN": ("동탄",),
}

KNOWN_REGION_CODES: frozenset[str] = frozenset(_CODE_MATCH_TOKENS)


def resolve_region_code(name: str) -> Optional[str]:
    """지역명(또는 이미 code)을 canonical code로 정규화. 미상이면 None.

    - 이미 code면 그대로(idempotent). 한글명이면 distinctive token으로 매칭.
    - 확정 불가는 None → 호출부가 '조용히 버리지 말고' 표면화한다.
    """
    if not name:
        return None
    s = name.strip()
    if s.upper() in KNOWN_REGION_CODES:
        return s.upper()
    for code, tokens in _CODE_MATCH_TOKENS.items():
        if all(tok in s for tok in tokens):
            return code
    return None


def normalize_regions(names: Iterable[str]) -> tuple[list[str], list[str]]:
    """지역명 목록을 (정규화된 code 목록, 매핑 실패한 원본명 목록)으로 변환.

    code는 입력 순서 보존·중복 제거. 실패 목록은 조용한 누락을 막기 위해 반환한다.
    """
    codes: list[str] = []
    unmapped: list[str] = []
    seen: set[str] = set()
    for n in names:
        code = resolve_region_code(n)
        if code is None:
            unmapped.append(n)
        elif code not in seen:
            seen.add(code)
            codes.append(code)
    return codes, unmapped
