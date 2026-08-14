"""합성 포트폴리오 영향 집계 — 층화 합성 차주를 룰엔진에 관통시켜 분포·집계 산출.

⚠️ **합성 데이터(synthetic)** — 실제 고객·회사 데이터가 아니다(LOCKED §8). 층화 비율은
포트폴리오 규모감을 보이기 위한 가정이며, 각 차주의 Before/After LTV는 모두 rule_engine
실제 판정이다(집계 수치를 지어내지 않음).

결정론적: 난수를 쓰지 않고 층화 비율 × 규모로 정수 배분한다(재현 가능).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Optional

from ..models import EvaluationStatus, LoanPurpose, LtvDecision
from ..rule_engine import evaluate
from .matrix import (
    AFTER_DATE,
    BEFORE_DATE,
    ImpactDirection,
    _build_application_from_profile,
    classify_direction,
)

# 층화 정의: (차주유형, 프로파일, 비율). 비율 합 = 1.00.
# 프로파일은 MortgageApplication kwargs (region_code·evaluation_date 제외).
STRATA: list[tuple[str, dict[str, Any], float]] = [
    ("무주택 일반", dict(house_count=0), 0.34),
    ("생애최초", dict(house_count=0, first_home_buyer=True), 0.14),
    ("서민·실수요", dict(house_count=0, real_demand_flag=True), 0.10),
    ("유주택(비처분 1주택)", dict(house_count=1), 0.12),
    ("다주택", dict(house_count=2), 0.06),
    ("처분조건부 1주택", dict(house_count=1, disposal_condition_flag=True), 0.05),
    ("무주택(경과규정)", dict(house_count=0, contract_signed_at="2026-06-29",
                          downpayment_paid_at="2026-06-29"), 0.07),
    ("정책대출(디딤돌)", dict(house_count=0, policy_mortgage_flag=True), 0.08),
    ("전세자금대출", dict(loan_purpose=LoanPurpose.OTHER), 0.04),
]

# 집계 표시용 그룹핑: 세부 차주유형 → 대분류(스티치 _3 차트와 정렬)
_TYPE_GROUP = {
    "무주택 일반": "무주택",
    "무주택(경과규정)": "무주택",
    "생애최초": "생애최초",
    "서민·실수요": "서민·실수요",
    "유주택(비처분 1주택)": "유주택",
    "다주택": "다주택",
    "처분조건부 1주택": "유주택(처분조건부)",
    "정책대출(디딤돌)": "정책대출(Discovery)",
    "전세자금대출": "전세(Discovery)",
}

_REGIONS = ("GURI", "YONGIN_GIHEUNG", "HWASEONG_DONGTAN")


@dataclass
class Applicant:
    borrower_type: str
    region_code: str
    profile: dict[str, Any]


@dataclass
class PortfolioImpact:
    size: int
    before_date: date
    after_date: date
    by_borrower_type: dict[str, int] = field(default_factory=dict)
    before_ltv_dist: dict[str, int] = field(default_factory=dict)
    after_ltv_dist: dict[str, int] = field(default_factory=dict)
    impacted: int = 0            # DOWNGRADE + NEW_RESTRICTION
    grandfathered: int = 0       # 경과규정 보호
    discovery: int = 0           # 자동판정 제외
    high_risk: int = 0           # after LTV == 0% (사실상 신규취급 불가)


def build_synthetic_portfolio(size: int = 2000) -> list[Applicant]:
    """층화 비율 × size로 결정론적 합성 포트폴리오 생성(난수 없음)."""
    out: list[Applicant] = []
    for i, (btype, profile, weight) in enumerate(STRATA):
        count = round(weight * size)
        for j in range(count):
            region = _REGIONS[(i + j) % len(_REGIONS)]   # 지역 순환(LTV엔 무영향, 표시용)
            out.append(Applicant(borrower_type=btype, region_code=region, profile=dict(profile)))
    return out


def _ltv_bucket(decision: LtvDecision) -> str:
    if decision.max_ltv is not None:
        return f"{decision.max_ltv:.0%}"
    return {
        EvaluationStatus.DISCOVERY: "Discovery",
        EvaluationStatus.OUT_OF_SCOPE: "범위외",
        EvaluationStatus.NEEDS_HUMAN_REVIEW: "명세부재",
    }.get(decision.status, "기타")


def analyze_portfolio(
    portfolio: Optional[list[Applicant]] = None,
    before_date: date = BEFORE_DATE,
    after_date: date = AFTER_DATE,
) -> PortfolioImpact:
    """포트폴리오를 Before/After 두 시점에 관통 → 분포·집계."""
    portfolio = portfolio if portfolio is not None else build_synthetic_portfolio()
    result = PortfolioImpact(size=len(portfolio), before_date=before_date, after_date=after_date)
    for app in portfolio:
        group = _TYPE_GROUP.get(app.borrower_type, app.borrower_type)
        result.by_borrower_type[group] = result.by_borrower_type.get(group, 0) + 1

        before = evaluate(_build_application_from_profile(app.profile, app.region_code, before_date))
        after = evaluate(_build_application_from_profile(app.profile, app.region_code, after_date))
        bb, ab = _ltv_bucket(before), _ltv_bucket(after)
        result.before_ltv_dist[bb] = result.before_ltv_dist.get(bb, 0) + 1
        result.after_ltv_dist[ab] = result.after_ltv_dist.get(ab, 0) + 1

        direction = classify_direction(before, after)
        if direction in (ImpactDirection.DOWNGRADE, ImpactDirection.NEW_RESTRICTION):
            result.impacted += 1
        if after.grandfathering_applied:
            result.grandfathered += 1
        if direction == ImpactDirection.DISCOVERY:
            result.discovery += 1
        if after.max_ltv == 0.0:
            result.high_risk += 1
    return result
