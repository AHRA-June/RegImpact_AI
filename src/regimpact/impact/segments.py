"""6·30 시나리오 표준 고객 세그먼트 (Impact Matrix 입력).

demo_6_30.py 의 케이스 축과 정렬 — '누가 얼마나 영향받는가'의 서사를 만드는 대표 세그먼트.
프로필은 비시점·비지역 필드만 담는다(지역·시점은 분석기가 채움). 경과규정 이벤트 날짜는
넣지 않는다 → 이 세그먼트들은 '시행 후 신규 신청' 관점의 영향을 본다(경과규정 보호 없음).

값 출처: docs/05_RULE_SPEC.md §C / regulatory_facts.md. LOCKED §4(세그먼트는 '입력 프로필'일 뿐,
LTV 값은 엔진이 명세에서 판정).
"""
from __future__ import annotations

from .matrix import Segment

# 6·30 신규 규제지역(투기과열지구). 3개 지역은 동일 규칙 → 대표 1개로 분석 가능.
SIX_THIRTY_REGIONS = ("GURI", "YONGIN_GIHEUNG", "HWASEONG_DONGTAN")
DEFAULT_REGION = "GURI"

SIX_THIRTY_SEGMENTS: list[Segment] = [
    Segment("SEG-01", "무주택 일반", dict(house_count=0)),
    Segment("SEG-02", "생애최초", dict(house_count=0, first_home_buyer=True)),
    Segment("SEG-03", "서민·실수요", dict(house_count=0, real_demand_flag=True)),
    Segment("SEG-04", "비처분 1주택", dict(house_count=1)),
    Segment("SEG-05", "처분조건부 1주택", dict(house_count=1, disposal_condition_flag=True)),
    Segment("SEG-06", "다주택", dict(house_count=2)),
]
