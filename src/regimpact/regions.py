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
