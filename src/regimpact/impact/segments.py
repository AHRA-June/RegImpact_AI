"""6·30 임팩트 분석용 대표 고객 세그먼트 (canonical fixture).

지역은 6·30으로 신규 규제지정된 3개 지역을 대표해 GURI 하나를 사용한다
(regions.py의 세 지역은 동일 버전 곡선 → 대표 1개로 충분).
weight(비중)는 **예시값**이며 실측 포트폴리오가 아니다. 브리프의 가치제안 원칙
("정확한 자동화"가 아니라 "검증 가능한 초안화")에 따라 집계는 참고용으로만 쓴다.

각 세그먼트는 evaluation_date를 갖지 않는다(임팩트의 축이므로 분석기가 주입).
경과규정 세그먼트만 계약/접수 이벤트 날짜를 갖는다(시점 무관 사실이므로 attrs에 포함).
"""
from __future__ import annotations

from datetime import date

from .matrix import CustomerSegment

_REGION = "GURI"   # 6·30 신규 규제지정 대표 지역


SIX_THIRTY_SEGMENTS: list[CustomerSegment] = [
    CustomerSegment(
        label="무주택 일반",
        attrs=dict(region_code=_REGION, house_count=0),
        weight=0.40,
        note="기준선 70% → 규제 표준 40%",
    ),
    CustomerSegment(
        label="생애최초",
        attrs=dict(region_code=_REGION, house_count=0, first_home_buyer=True),
        weight=0.12,
        note="예외로 70% 유지 (규제 후에도 좌동)",
    ),
    CustomerSegment(
        label="서민·실수요",
        attrs=dict(region_code=_REGION, house_count=0, real_demand_flag=True),
        weight=0.10,
        note="70% → 60%",
    ),
    CustomerSegment(
        label="처분조건부 1주택",
        attrs=dict(region_code=_REGION, house_count=1, disposal_condition_flag=True),
        weight=0.08,
        note="무주택 취급 → 70% → 40%",
    ),
    CustomerSegment(
        label="비처분 1주택(유주택)",
        attrs=dict(region_code=_REGION, house_count=1),
        weight=0.12,
        note="규제 후 0%. 시행 전 非규제 유주택 기준선은 명세 여백 → 검토",
    ),
    CustomerSegment(
        label="다주택",
        attrs=dict(region_code=_REGION, house_count=2),
        weight=0.06,
        note="규제 후 0%. 시행 전 非규제 기준선 여백 → 검토",
    ),
    CustomerSegment(
        label="경과규정(계약+계약금)",
        attrs=dict(
            region_code=_REGION,
            house_count=0,
            contract_signed_at=date(2026, 6, 29),
            downpayment_paid_at=date(2026, 6, 29),
        ),
        weight=0.07,
        note="종전규정 적용 → 70% 유지(규제에 영향 안 받음)",
    ),
    CustomerSegment(
        label="정책대출(디딤돌)",
        attrs=dict(region_code=_REGION, house_count=0, policy_mortgage_flag=True),
        weight=0.05,
        note="코어 밖 Discovery — 전/후 동일 라우팅",
    ),
]
