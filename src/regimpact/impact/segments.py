"""임팩트 분석용 대표 고객 세그먼트 (archetype) + 지역 인스턴스화.

archetype = 지역과 무관한 '고객 유형' 템플릿(무주택 일반, 생애최초, …). 지역 코드는
분석 대상(추출된 target_regions 또는 하드코딩)에서 주입한다 → 같은 유형을 여러 지역에 적용.

weight(비중)는 **예시값**이며 실측 포트폴리오가 아니다. 브리프의 가치제안 원칙
("정확한 자동화"가 아니라 "검증 가능한 초안화")에 따라 집계는 참고용으로만 쓴다.

각 archetype의 attrs는 evaluation_date·region_code를 제외한 MortgageApplication kwargs.
경과규정 archetype만 계약/접수 이벤트 날짜를 갖는다(시점·지역 무관 사실이므로 attrs에 포함).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from .matrix import CustomerSegment


@dataclass
class SegmentArchetype:
    """지역과 무관한 고객 유형 템플릿."""
    label: str
    attrs: dict = field(default_factory=dict)   # region_code·evaluation_date 제외
    weight: float = 1.0
    note: str = ""


# 6·30 대표 고객 유형 8종 (지역 미주입)
DEFAULT_ARCHETYPES: list[SegmentArchetype] = [
    SegmentArchetype("무주택 일반", dict(house_count=0), 0.40,
                     "기준선 70% → 규제 표준 40%"),
    SegmentArchetype("생애최초", dict(house_count=0, first_home_buyer=True), 0.12,
                     "예외로 70% 유지 (규제 후에도 좌동)"),
    SegmentArchetype("서민·실수요", dict(house_count=0, real_demand_flag=True), 0.10,
                     "70% → 60%"),
    SegmentArchetype("처분조건부 1주택", dict(house_count=1, disposal_condition_flag=True), 0.08,
                     "무주택 취급 → 70% → 40%"),
    SegmentArchetype("비처분 1주택(유주택)", dict(house_count=1), 0.12,
                     "규제 후 0%. 시행 전 非규제 유주택 기준선은 명세 여백 → 검토"),
    SegmentArchetype("다주택", dict(house_count=2), 0.06,
                     "규제 후 0%. 시행 전 非규제 기준선 여백 → 검토"),
    SegmentArchetype(
        "경과규정(계약+계약금)",
        dict(house_count=0,
             contract_signed_at=date(2026, 6, 29),
             downpayment_paid_at=date(2026, 6, 29)),
        0.07, "종전규정 적용 → 70% 유지(규제에 영향 안 받음)"),
    SegmentArchetype("정책대출(디딤돌)", dict(house_count=0, policy_mortgage_flag=True), 0.05,
                     "코어 밖 Discovery — 전/후 동일 라우팅"),
]


def segments_for_region(
    region_code: str,
    archetypes: list[SegmentArchetype] | None = None,
    label_region: bool = False,
) -> list[CustomerSegment]:
    """archetype 목록을 특정 지역 코드로 인스턴스화한 CustomerSegment 목록.

    label_region=True면 라벨에 지역을 붙인다(여러 지역을 한 매트릭스에 담을 때 구분용).
    """
    archetypes = archetypes if archetypes is not None else DEFAULT_ARCHETYPES
    out: list[CustomerSegment] = []
    for a in archetypes:
        label = f"{a.label}·{region_code}" if label_region else a.label
        out.append(CustomerSegment(
            label=label,
            attrs={**a.attrs, "region_code": region_code},
            weight=a.weight,
            note=a.note,
        ))
    return out


# 하위호환: 기존 데모/테스트가 쓰는 GURI 단일지역 대표 세그먼트(라벨에 지역 미표기)
SIX_THIRTY_SEGMENTS: list[CustomerSegment] = segments_for_region("GURI")
