"""층화 합성 포트폴리오 (docs/04_PLAN.md Phase 2, 브리프 §13).

**이것은 시장 분포 추정이 아니라 커버리지 격자(coverage grid)다.**
LOCKED §8에 따라 실제 고객데이터를 쓰지 않으므로, 현실 비중을 지어내면 그 숫자가
근거 없는 '영향 고객 수'로 둔갑한다. 그래서 여기서는 **완전요인(full factorial) 등가중**으로
차주 유형 × 지역군 × 경과규정 이벤트 × 가격구간을 빠짐없이 훑고, 산출물은
"몇 명이 영향받는다"가 아니라 **"어떤 세그먼트가 어떻게 바뀌는가"** 로 읽도록 설계했다.

실제 포트폴리오 분포가 생기면 `weight` 를 채워 가중집계로 바꾸면 된다(집계 함수는 이미 가중치를 받는다).

재현성: 난수를 쓰지 않는다. 같은 입력이면 항상 같은 포트폴리오(같은 순서, 같은 customer_id).
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass, replace
from datetime import date
from typing import Optional

from ..models import MortgageApplication
from ..regions import get_region

# --- 시나리오 기준 시점 ---
BEFORE_AS_OF = date(2026, 6, 30)   # 시행 전날 (종전규정)
AFTER_AS_OF = date(2026, 7, 2)     # 시행 후

# --- 지역군: 6·30 임팩트가 어떻게 갈리는지 보이는 4개 군 ---
REGION_GROUPS: dict[str, tuple[str, ...]] = {
    "6·30 신규 규제(경기 3곳)": ("GYEONGGI_HWASEONG_DONGTAN", "GYEONGGI_YONGIN_GIHEUNG",
                             "GYEONGGI_GURI"),
    "기존 규제(서울·경기)": ("SEOUL_GANGNAM", "SEOUL_NOWON", "GYEONGGI_GWACHEON"),
    "수도권 비규제": ("INCHEON_YEONSU", "GYEONGGI_PAJU", "GYEONGGI_PYEONGTAEK"),
    "비수도권 비규제": ("ULSAN_NAM", "JEJU_JEJU", "GYEONGNAM_GIMHAE"),
}

# --- 차주 유형 (05_RULE_SPEC §C 의 판정 분기를 모두 덮는 6종) ---
@dataclass(frozen=True)
class BorrowerProfile:
    key: str
    label: str
    house_count: int = 0
    disposal_condition_flag: bool = False
    first_home_buyer: bool = False
    real_demand_flag: bool = False


BORROWER_PROFILES: tuple[BorrowerProfile, ...] = (
    BorrowerProfile("no_house", "무주택 일반"),
    BorrowerProfile("first_home", "생애최초", first_home_buyer=True),
    BorrowerProfile("real_demand", "서민·실수요자", real_demand_flag=True),
    BorrowerProfile("disposal", "처분조건부 1주택", house_count=1, disposal_condition_flag=True),
    BorrowerProfile("owner", "유주택(비처분 1주택)", house_count=1),
    BorrowerProfile("multi", "다주택(2주택)", house_count=2),
)

# --- 경과규정 이벤트 (§F G1/G2/G3 + 미해당) ---
@dataclass(frozen=True)
class EventProfile:
    key: str
    label: str
    application_accepted_at: Optional[date] = None
    contract_signed_at: Optional[date] = None
    downpayment_paid_at: Optional[date] = None
    land_permit_target: bool = False
    land_permit_applied_at: Optional[date] = None


EVENT_PROFILES: tuple[EventProfile, ...] = (
    EventProfile("none", "이벤트 없음"),
    EventProfile("g1", "G1 전산접수 6.29", application_accepted_at=date(2026, 6, 29)),
    EventProfile("g2", "G2 계약+계약금 6.29",
                 contract_signed_at=date(2026, 6, 29), downpayment_paid_at=date(2026, 6, 29)),
    EventProfile("g3", "G3 토허제 신청 6.30",
                 land_permit_target=True, land_permit_applied_at=date(2026, 6, 30)),
)

# --- 가격구간 (억원) — 한도 변화 산출용 참고값 ---
PRICE_POINTS_EOK: tuple[float, ...] = (4.0, 6.0, 8.0, 10.0, 12.0, 15.0, 20.0)


@dataclass(frozen=True)
class PortfolioRow:
    """포트폴리오 1건. 엔진 입력(app) + 집계용 라벨·가격을 함께 들고 다닌다.

    가격은 엔진 스키마에 넣지 않는다 — 코어 판정(LTV)에 쓰이지 않는 참고값이기 때문이다.
    """
    customer_id: str
    region_group: str
    borrower: BorrowerProfile
    event: EventProfile
    price_eok: float
    app: MortgageApplication
    weight: float = 1.0          # 실제 분포가 생기면 여기에 비중을 채운다

    def as_of(self, d: date) -> MortgageApplication:
        return replace(self.app, evaluation_date=d)


def build_portfolio(
    region_groups: Optional[dict[str, tuple[str, ...]]] = None,
    price_points: Optional[tuple[float, ...]] = None,
) -> list[PortfolioRow]:
    """완전요인 층화 포트폴리오를 만든다(난수 없음, 순서 고정)."""
    groups = region_groups or REGION_GROUPS
    prices = price_points or PRICE_POINTS_EOK

    # 지역코드 오타를 조용히 UNKNOWN escalation 으로 흘려보내지 않는다.
    # (레지스트리 미등록을 조용한 기본값으로 처리하다 강남 70% 사고가 났다 — regions.py 참고)
    missing = sorted(c for codes in groups.values() for c in codes if get_region(c) is None)
    if missing:
        raise ValueError(f"레지스트리에 없는 지역코드: {missing}")

    rows: list[PortfolioRow] = []
    for group_name, codes in groups.items():
        for code, borrower, event, price in itertools.product(
            codes, BORROWER_PROFILES, EVENT_PROFILES, prices
        ):
            cid = f"{code}|{borrower.key}|{event.key}|{price:g}"
            rows.append(PortfolioRow(
                customer_id=cid,
                region_group=group_name,
                borrower=borrower,
                event=event,
                price_eok=price,
                app=MortgageApplication(
                    region_code=code,
                    evaluation_date=AFTER_AS_OF,
                    house_count=borrower.house_count,
                    disposal_condition_flag=borrower.disposal_condition_flag,
                    first_home_buyer=borrower.first_home_buyer,
                    real_demand_flag=borrower.real_demand_flag,
                    application_accepted_at=event.application_accepted_at,
                    contract_signed_at=event.contract_signed_at,
                    downpayment_paid_at=event.downpayment_paid_at,
                    land_permit_target=event.land_permit_target,
                    land_permit_applied_at=event.land_permit_applied_at,
                    customer_id=cid,
                ),
            ))
    return rows
