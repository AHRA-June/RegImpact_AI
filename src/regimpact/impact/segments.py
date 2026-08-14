"""6·30 영향분석 대상 세그먼트 (대표 차주 유형).

각 세그먼트는 '지역 × 차주유형'의 대표 프로파일이다. Impact Matrix는 이 프로파일을
동일하게 유지한 채 evaluation_date만 Before/After로 바꿔 룰엔진에 넣는다. 지역의
규제상태(시점 버전)는 regions.resolve_region_status가 날짜로 해석하므로, 같은 차주가
6·30 이전엔 非규제 기준선, 이후엔 규제 규칙을 받는 '변경 전/후'가 자연스럽게 나온다.

세그먼트 목록은 docs/ui/stitch_review.md의 Impacted Segments 표와 정합한다(그 표의
하드코딩 값을 이 엔진 실제 출력으로 대체하기 위함).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..models import LoanPurpose

# 신규 규제지역 3곳의 표시명 (regions.py 코드 → 한글 라벨)
REGION_LABELS: dict[str, str] = {
    "GURI": "구리",
    "YONGIN_GIHEUNG": "용인 기흥",
    "HWASEONG_DONGTAN": "화성 동탄",
}


@dataclass(frozen=True)
class Segment:
    """영향분석 한 행의 입력 프로파일(날짜 제외).

    profile 은 MortgageApplication 생성 kwargs 이되 region_code·evaluation_date 는
    Impact Matrix 빌더가 채운다(세그먼트는 '차주 유형', 지역·시점은 빌더가 결정).
    """
    key: str                       # 안정 식별자 (테스트/집계용)
    borrower_type: str             # 차주 유형 표시명
    region_code: str               # 대상 지역 코드
    profile: dict[str, Any] = field(default_factory=dict)  # 차주 속성(주택수·예외·경과 등)
    note: str = ""                 # 서사용 부연(선택)

    @property
    def region_label(self) -> str:
        return REGION_LABELS.get(self.region_code, self.region_code)


# 6·30 시나리오 대표 세그먼트.
# 순서/구성은 stitch Impacted Segments 표 + demo_6_30 케이스를 아우른다.
SIX_THIRTY_SEGMENTS: list[Segment] = [
    Segment(
        key="NO_HOME_STANDARD",
        borrower_type="무주택 일반",
        region_code="YONGIN_GIHEUNG",
        profile=dict(house_count=0),
        note="표준 하향의 대표 케이스 (70→40)",
    ),
    Segment(
        key="FIRST_HOME",
        borrower_type="생애최초",
        region_code="HWASEONG_DONGTAN",
        profile=dict(house_count=0, first_home_buyer=True),
        note="예외 유지 (70→70, 변화 없음)",
    ),
    Segment(
        key="REAL_DEMAND",
        borrower_type="서민·실수요",
        region_code="GURI",
        profile=dict(house_count=0, real_demand_flag=True),
        note="예외 완화폭 축소 (70→60)",
    ),
    Segment(
        key="OWNER_1_NON_DISPOSAL",
        borrower_type="유주택(비처분 1주택)",
        region_code="YONGIN_GIHEUNG",
        profile=dict(house_count=1),
        note="유주택 규제 (→0)",
    ),
    Segment(
        key="DISPOSAL_1_HOME",
        borrower_type="처분조건부 1주택",
        region_code="GURI",
        profile=dict(house_count=1, disposal_condition_flag=True),
        note="처분조건부는 무주택 기준으로 표준 하향 (70→40)",
    ),
    Segment(
        key="MULTI_HOME",
        borrower_type="다주택",
        region_code="GURI",
        profile=dict(house_count=2),
        note="다주택 규제 (→0)",
    ),
    Segment(
        key="GRANDFATHERED_CONTRACT",
        borrower_type="무주택 일반(경과규정)",
        region_code="HWASEONG_DONGTAN",
        profile=dict(
            house_count=0,
            contract_signed_at="2026-06-29",   # 빌더가 date로 변환
            downpayment_paid_at="2026-06-29",
        ),
        note="컷오프 이전 계약+계약금 → 종전규정 유지 (70)",
    ),
    Segment(
        key="POLICY_LOAN",
        borrower_type="정책대출(디딤돌)",
        region_code="GURI",
        profile=dict(house_count=0, policy_mortgage_flag=True),
        note="정책대출 → Discovery(자동판정 제외)",
    ),
    Segment(
        key="JEONSE_LOAN",
        borrower_type="전세자금대출",
        region_code="GURI",
        profile=dict(loan_purpose=LoanPurpose.OTHER),
        note="주택구입목적 아님 → Discovery Scope(수동 정책검토)",
    ),
]
