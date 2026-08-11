"""Impact Matrix 세그먼트 정의 (6·30 앵커).

세그먼트 = "지역 × 차주유형" 대표 프로파일. 각 세그먼트는 룰엔진 입력
(MortgageApplication)의 부분 템플릿이며, before/after 두 시점에 각각 실행된다.

앵커 출처: docs/ui/stitch_review.md 의 정정된 Impacted Segments 표
(LOCKED §4 — 규칙값은 사람 확정 명세에서, 세그먼트는 6·30 사실 기준).
Discovery/Out-of-scope 행은 브리프 §5.2 — 매트릭스에 표시하되 코어 자동판정 제외.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from ..models import LoanPurpose, MortgageApplication

# 경과규정/시점 이벤트 키 — "before"(구규제 기준선) 평가 시 제거한다.
# 경과규정은 신규 규제가 존재할 때만 의미가 있으므로, 규제 시행 전 세계에는
# 적용하지 않는다(before에 grandfathering_applied=True가 찍히는 오해 방지).
TRANSITION_EVENT_KEYS = frozenset({
    "application_accepted_at",
    "contract_signed_at",
    "downpayment_paid_at",
    "land_permit_target",
    "land_permit_applied_at",
})


@dataclass(frozen=True)
class Segment:
    """Impact Matrix 한 행의 정의 = 대표 차주 프로파일."""

    segment_id: str
    borrower_type: str            # 표시용 라벨 (예: "다주택")
    region_code: str              # 룰엔진 지역코드 (예: "GURI")
    region_label: str             # 표시용 지역명 (예: "구리")
    attrs: dict[str, Any] = field(default_factory=dict)  # 그 외 MortgageApplication kwargs
    note: str = ""                # 세그먼트 설명(선택)

    def application(self, evaluation_date: date, *, drop_transition_events: bool = False) -> MortgageApplication:
        """이 세그먼트를 특정 시점의 룰엔진 입력으로 변환한다.

        drop_transition_events=True 이면 경과규정 관련 이벤트를 제거하여
        '구규제 기준선(before)'을 순수하게 평가한다.
        """
        kw = dict(self.attrs)
        if drop_transition_events:
            kw = {k: v for k, v in kw.items() if k not in TRANSITION_EVENT_KEYS}
        return MortgageApplication(
            region_code=self.region_code,
            evaluation_date=evaluation_date,
            customer_id=self.segment_id,
            **kw,
        )


# ── 6·30 앵커 세그먼트 ──────────────────────────────────────────────
# Core(자동판정) 세그먼트 — stitch_review.md 정정표 + 유주택/처분조건부/경과규정 확장.
ANCHOR_SEGMENTS: list[Segment] = [
    Segment(
        "SEG_MULTI_GURI", "다주택", "GURI", "구리",
        attrs=dict(house_count=2),
        note="다주택 → 규제지역 0%",
    ),
    Segment(
        "SEG_OWNER_YONGIN", "유주택(비처분 1주택)", "YONGIN_GIHEUNG", "용인 기흥",
        attrs=dict(house_count=1),
        note="비처분 1주택 → 규제지역 0%",
    ),
    Segment(
        "SEG_STD_YONGIN", "무주택 일반", "YONGIN_GIHEUNG", "용인 기흥",
        attrs=dict(house_count=0),
        note="무주택 일반 → 70%→40%",
    ),
    Segment(
        "SEG_FIRSTHOME_HWASEONG", "생애최초", "HWASEONG_DONGTAN", "화성 동탄",
        attrs=dict(house_count=0, first_home_buyer=True),
        note="생애최초 예외 → 70% 유지",
    ),
    Segment(
        "SEG_REALDEMAND_GURI", "서민·실수요", "GURI", "구리",
        attrs=dict(house_count=0, real_demand_flag=True),
        note="서민·실수요 예외 → 60%",
    ),
    Segment(
        "SEG_DISPOSAL_GURI", "처분조건부 1주택", "GURI", "구리",
        attrs=dict(house_count=1, disposal_condition_flag=True),
        note="처분조건부 1주택 = 무주택 기준 → 40%",
    ),
    Segment(
        "SEG_GRANDFATHERED_HWASEONG", "무주택 일반(경과규정)", "HWASEONG_DONGTAN", "화성 동탄",
        attrs=dict(
            house_count=0,
            contract_signed_at=date(2026, 6, 29),
            downpayment_paid_at=date(2026, 6, 29),
        ),
        note="6·30 이전 계약+계약금 → 종전규정(70%) 유지",
    ),
]

# Discovery/Out-of-scope 세그먼트 — 매트릭스에 표시하되 코어 자동판정 제외(브리프 §5.2).
DISCOVERY_SEGMENTS: list[Segment] = [
    Segment(
        "SEG_POLICY_GURI", "정책대출(디딤돌)", "GURI", "구리",
        attrs=dict(house_count=0, policy_mortgage_flag=True),
        note="정책대출 → Discovery(수동 검토)",
    ),
    Segment(
        "SEG_JEONSE_GURI", "전세대출", "GURI", "구리",
        attrs=dict(loan_purpose=LoanPurpose.OTHER),
        note="전세대출 = 주택구입목적 아님 → Out-of-scope",
    ),
]

# 6·30 시나리오 전체 세그먼트(Core + Discovery).
SIX_THIRTY_SEGMENTS: list[Segment] = ANCHOR_SEGMENTS + DISCOVERY_SEGMENTS
