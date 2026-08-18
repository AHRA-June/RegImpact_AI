"""합성 포트폴리오 — "우리 고객 중 누가 영향받는가"를 계산하기 위한 모의 신청건 집합.

브리프 §0-8(LOCKED): 실제 회사 내부문서·고객데이터를 사용하지 않는다. 따라서 포트폴리오는
**층화 합성 데이터**로 만든다. 비율은 하드코딩된 상수로 노출해 구성이 감사 가능하게 한다
(랜덤 시드에 조성이 숨지 않도록).

결정적이다: 같은 seed → 같은 포트폴리오. 임팩트 매트릭스의 수치가 실행마다 흔들리면
"검증 가능한 산출물"이 아니게 되므로 시드를 고정하고 그 값을 매트릭스에 함께 기록한다.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, replace
from datetime import date, timedelta

from ..grandfathering import CUTOFF
from ..models import LoanPurpose, MortgageApplication

DEFAULT_SEED = 20260630
DEFAULT_SIZE = 2000

# 6·30 신규 규제지역 3곳 + 대조군(비대상 지역). 대조군은 "영향 없음"이 실제로
# 영향 없음으로 나오는지 확인하는 음성 대조(negative control)다.
TARGET_REGIONS = ("GURI", "YONGIN_GIHEUNG", "HWASEONG_DONGTAN")
# 대조군은 6·30 대상이 아닌 실재 지역. Stitch가 환각했던 지역명(세종·부산·강남·분당)은
# UI grounding 테스트의 금지어이므로 대조군으로 쓰지 않는다.
CONTROL_REGION = "CHEONGJU"        # REGION_VERSIONS 미등록 → 항상 NON_REGULATED

# ---- 층화 비율 (합계 1.0). 실제 통계가 아니라 **명시된 가정**이다. ----
P_CONTROL_REGION = 0.16            # 대조군 비중
P_HOUSE_COUNT = {0: 0.55, 1: 0.30, 2: 0.15}
P_DISPOSAL_IF_ONE_HOME = 0.30      # 1주택 중 처분조건부
P_FIRST_HOME_IF_NO_HOME = 0.25     # 무주택 중 생애최초
P_REAL_DEMAND_IF_NO_HOME = 0.20    # 무주택(생애최초 아님) 중 서민·실수요자
P_POLICY_MORTGAGE = 0.08           # 정책대출 → Discovery
P_OTHER_PURPOSE = 0.05             # 주택구입목적 아님 → Out of scope
P_GRANDFATHERING_EVENT = 0.22      # 경과규정 사유 보유
P_LAND_PERMIT_TARGET = 0.10        # 토지거래허가 대상 물건

# 담보가액 구간(원) — FAQ Q2 최대한도 구간과 대략 정렬
PRICE_BANDS = (
    (300_000_000, 600_000_000, 0.35),
    (600_000_000, 900_000_000, 0.30),
    (900_000_000, 1_500_000_000, 0.25),
    (1_500_000_000, 2_500_000_000, 0.10),
)

BEFORE_DATE = date(2026, 6, 30)    # 시행 전일 (종전 규정)
AFTER_DATE = date(2026, 7, 1)      # 시행일 (신규 규정)


@dataclass(frozen=True)
class PortfolioCustomer:
    """합성 신청건 1건 — 룰엔진 입력 + 한도 계산에 필요한 담보가액."""
    customer_id: str
    application: MortgageApplication
    property_price: int

    def as_of(self, evaluation_date: date) -> MortgageApplication:
        """같은 신청건을 다른 시점 기준으로 평가하기 위한 사본."""
        return replace(self.application, evaluation_date=evaluation_date)


def _pick(rng: random.Random, weighted: dict) -> object:
    r, acc = rng.random(), 0.0
    for value, weight in weighted.items():
        acc += weight
        if r < acc:
            return value
    return list(weighted)[-1]


def _price(rng: random.Random) -> int:
    r, acc = rng.random(), 0.0
    for lo, hi, w in PRICE_BANDS:
        acc += w
        if r < acc:
            return int(rng.uniform(lo, hi) // 1_000_000 * 1_000_000)
    lo, hi, _ = PRICE_BANDS[-1]
    return int(rng.uniform(lo, hi) // 1_000_000 * 1_000_000)


def _grandfathering_events(rng: random.Random) -> dict:
    """경과규정 이벤트를 만든다. 경계 근처(6.28~7.3)를 의도적으로 많이 뽑는다.

    경계에서 갈리는 건이 실무에서 가장 위험하고(하루 차이로 한도가 뒤집힘) 테스트
    가치도 높으므로, 균등 분포 대신 컷오프 주변에 밀도를 준다.
    """
    if rng.random() >= P_GRANDFATHERING_EVENT:
        return {}
    # 컷오프 기준 -2 ~ +3일에 집중, 나머지는 넓게
    if rng.random() < 0.6:
        offset = rng.choice((-2, -1, 0, 1, 2, 3))
    else:
        offset = rng.randint(-60, 10)
    event_day = CUTOFF + timedelta(days=offset)

    kind = _pick(rng, {"accepted": 0.45, "contract": 0.40, "land_permit": 0.15})
    if kind == "accepted":
        return {"application_accepted_at": event_day}
    if kind == "contract":
        ev = {"contract_signed_at": event_day}
        # 계약금 미납부 건도 섞는다 — G2는 계약만으로는 성립하지 않는다(음성 케이스)
        if rng.random() < 0.85:
            ev["downpayment_paid_at"] = event_day + timedelta(days=rng.randint(0, 2))
        return ev
    return {"land_permit_target": True, "land_permit_applied_at": event_day}


def build_portfolio(
    size: int = DEFAULT_SIZE, seed: int = DEFAULT_SEED
) -> list[PortfolioCustomer]:
    """층화 합성 포트폴리오를 만든다 (결정적)."""
    rng = random.Random(seed)
    out: list[PortfolioCustomer] = []

    for i in range(size):
        region = (
            CONTROL_REGION if rng.random() < P_CONTROL_REGION
            else TARGET_REGIONS[i % len(TARGET_REGIONS)]
        )
        house_count = int(_pick(rng, P_HOUSE_COUNT))
        disposal = house_count == 1 and rng.random() < P_DISPOSAL_IF_ONE_HOME

        first_home = house_count == 0 and rng.random() < P_FIRST_HOME_IF_NO_HOME
        real_demand = (
            house_count == 0 and not first_home
            and rng.random() < P_REAL_DEMAND_IF_NO_HOME
        )

        events = _grandfathering_events(rng)
        if rng.random() < P_LAND_PERMIT_TARGET:
            events.setdefault("land_permit_target", True)

        app = MortgageApplication(
            region_code=region,
            evaluation_date=AFTER_DATE,
            house_count=house_count,
            disposal_condition_flag=disposal,
            first_home_buyer=first_home,
            real_demand_flag=real_demand,
            policy_mortgage_flag=rng.random() < P_POLICY_MORTGAGE,
            loan_purpose=(
                LoanPurpose.OTHER if rng.random() < P_OTHER_PURPOSE
                else LoanPurpose.HOME_PURCHASE
            ),
            customer_id=f"C{i:05d}",
            **events,
        )
        out.append(
            PortfolioCustomer(
                customer_id=f"C{i:05d}", application=app, property_price=_price(rng)
            )
        )
    return out


def composition(portfolio: list[PortfolioCustomer]) -> dict:
    """실제로 만들어진 조성을 집계한다 — 가정한 비율과 대조하기 위한 값."""
    n = len(portfolio) or 1
    apps = [c.application for c in portfolio]
    return {
        "size": len(portfolio),
        "target_region": sum(a.region_code in TARGET_REGIONS for a in apps) / n,
        "no_home": sum(a.house_count == 0 for a in apps) / n,
        "one_home": sum(a.house_count == 1 for a in apps) / n,
        "multi_home": sum(a.house_count >= 2 for a in apps) / n,
        "first_home_buyer": sum(a.first_home_buyer for a in apps) / n,
        "real_demand": sum(a.real_demand_flag for a in apps) / n,
        "policy_mortgage": sum(a.policy_mortgage_flag for a in apps) / n,
        "out_of_scope": sum(a.loan_purpose != LoanPurpose.HOME_PURCHASE for a in apps) / n,
    }
