"""총 가능금액(참고 추정) — min(LTV 한도, 가격구간별 최대한도, DSR 한도, DTI 한도).

고객 인터뷰(2026-08-20): "LTV만이 아니라 DSR·DTI까지 합쳐서 내가 총 얼마 빌릴 수
있는지 한 번에 알고 싶다." 실무 심사가 실제로 하는 일이 min(한도들)이므로, 화면도
한도 4개를 나란히 놓고 **어느 규제에 막혔는지(binding)** 를 짚어준다.

값의 출처 (LOCKED §4 — 전부 확정 명세·원문, 지어낸 값 없음):
  - 가격구간별 최대한도 6/4/2억: 05_RULE_SPEC §C-1 주1 (FAQ Q2 주2, MOLIT "최대한도 6억원 제한")
    — 규제지역 조치이므로 규제지역 판정일 때만 적용한다.
  - DSR 은행권 40% / 2금융권 50%: FAQ 주3 ("금융권 대출은 DSR 규제(은행권 40%, 2금융권 50%,
    규제지역 동일) 적용 중")
  - DTI 투기과열 40% / 조정 50% / 그 외(비규제·생애최초·서민실수요) 60%, 아파트 限:
    05_RULE_SPEC §C-1 R1~R3 · §C-2 (FAQ Q2 표 — 사용자가 원본 이미지로 확정한 값)
  - 최대 만기 30년: MOLIT ("최대 만기 30년이내")

계산은 표준 원리금균등(annuity) 수식 — 도메인 값이 아니라 산수다. LTV 판정은 이 모듈이
하지 않는다: **판정자는 룰엔진 하나뿐**이고, 여기는 그 판정 결과를 입력으로 받는다.

단순화 가정(2026-08-20 사용자 확정 — 화면에 그대로 명시한다):
  ① 스트레스 금리 가산 미반영 — 실제 한도는 이보다 적을 수 있다.
  ② 기존 부채는 "월 상환액" 하나로 받아 DSR·DTI 분자에 전액 반영(보수적 단순화 —
     DTI 원칙은 기타부채 이자만이지만, 이자만 분리 입력받으면 고객이 모르는 숫자가 된다).
  ③ DTI는 아파트 기준(원문이 "아파트 限").
이 결과는 참고 추정이며 실제 가능 금액은 은행 심사로 확정된다.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

# 가격구간별 최대한도 (§C-1 주1: 15억↓6억 / 15~25억 4억 / 25억↑2억) — 규제지역 조치
MAX_LOAN_CAPS: tuple[tuple[Optional[int], int], ...] = (
    (1_500_000_000, 600_000_000),
    (2_500_000_000, 400_000_000),
    (None, 200_000_000),
)
DSR_RATES = {"BANK": 0.40, "NONBANK": 0.50}      # FAQ 주3, 규제지역 동일
DTI_BY_TYPE = {"SPECULATIVE_OVERHEATED": 0.40, "ADJUSTMENT": 0.50}   # §C-1 R1
DTI_OTHER = 0.60                                  # §C-1 R2·R3 (좌동) · §C-2 비규제 일반
MAX_TERM_YEARS = 30                               # MOLIT "최대 만기 30년이내"

# DTI 60%(완화 열)가 적용되는 예외 차주 — §C-1 R2(생애최초)·R3(서민·실수요)
_DTI_RELAXED_RULES = frozenset({"REG_FIRSTHOME", "REG_REALDEMAND", "NONREG_STD_70"})


def principal_from_annual_payment(annual_payment: float, annual_rate: float,
                                  term_years: int) -> int:
    """연 원리금 여력 → 원리금균등 기준 대출원금 (표준 annuity 역산)."""
    if annual_payment <= 0 or term_years <= 0:
        return 0
    n = term_years * 12
    pm = annual_payment / 12.0
    r = annual_rate / 12.0
    if r <= 0:
        return int(pm * n)
    return int(pm * (1.0 - (1.0 + r) ** -n) / r)


def cap_for_price(price: int) -> int:
    """가격구간별 최대한도 (규제지역 조치 — 호출자가 규제 여부를 판단해 넣는다)."""
    for upper, cap in MAX_LOAN_CAPS:
        if upper is None or price <= upper:
            return cap
    raise AssertionError("unreachable")


def dti_rate(rule_id: Optional[str], regulated_type: str) -> float:
    """차주·지역 유형별 DTI (§C — 아파트 限)."""
    if rule_id in _DTI_RELAXED_RULES:
        return DTI_OTHER
    return DTI_BY_TYPE.get(regulated_type, DTI_OTHER)


def estimate(
    *,
    price: int,
    max_ltv: float,
    rule_id: Optional[str],
    regulated: bool,
    regulated_type: str = "NONE",
    annual_income: Optional[int] = None,
    monthly_debt_service: int = 0,
    annual_rate: Optional[float] = None,
    term_years: int = MAX_TERM_YEARS,
    lender: str = "BANK",
) -> dict:
    """한도 4종과 binding 규제. 소득·금리가 없으면 DSR·DTI 는 None(미계산)으로 남긴다 —
    모르는 것을 0이나 무한대로 대체하지 않는다."""
    limits: dict[str, Optional[int]] = {
        "LTV": int(price * max_ltv),
        "CAP": cap_for_price(price) if regulated else None,
        "DSR": None,
        "DTI": None,
    }
    if annual_income and annual_rate is not None:
        debt_annual = monthly_debt_service * 12
        dsr_budget = annual_income * DSR_RATES[lender] - debt_annual
        limits["DSR"] = principal_from_annual_payment(dsr_budget, annual_rate, term_years)
        dti_budget = annual_income * dti_rate(rule_id, regulated_type) - debt_annual
        limits["DTI"] = principal_from_annual_payment(dti_budget, annual_rate, term_years)

    known = {k: v for k, v in limits.items() if v is not None}
    total = min(known.values()) if known else None
    binding = sorted(k for k, v in known.items() if v == total) if known else []
    return {"limits": limits, "total": total, "binding": binding,
            "dti_rate": dti_rate(rule_id, regulated_type),
            "dsr_rate": DSR_RATES[lender]}
