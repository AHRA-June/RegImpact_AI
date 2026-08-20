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
    caps = {
        "LTV": max_ltv,
        "CAP": cap_for_price(price) if regulated else None,
        "DSR": DSR_RATES[lender] if (annual_income and annual_rate is not None) else None,
        "DTI": dti_rate(rule_id, regulated_type) if (annual_income and annual_rate is not None)
               else None,
    }
    return {"limits": limits, "total": total, "binding": binding,
            "caps": caps,
            "dti_rate": dti_rate(rule_id, regulated_type),
            "dsr_rate": DSR_RATES[lender]}


def ratios_for(
    principal: int,
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
    """**이 금액을 빌리면 내 비율이 몇 %가 되는가** — 규제 한도와 나란히 돌려준다.

    고객 리뷰(2026-08-20): 금액만 보여주면 왜 막혔는지 모른다. "규정 한도는 40%인데
    당신은 55%"라고 말해 줘야 다음 행동이 보인다. 한도 계산이 min(...)의 결과라면,
    이것은 그 반대 방향 — 주어진 금액에서 각 규제 비율을 되짚는다.

    금액 상한(CAP)은 비율이 아니라 금액이므로 `is_amount=True` 로 구분해 돌려준다.
    """
    out: dict[str, dict] = {
        "LTV": {"actual": (principal / price) if price else None, "cap": max_ltv,
                "is_amount": False},
    }
    if regulated:
        cap_amt = cap_for_price(price)
        out["CAP"] = {"actual": principal, "cap": cap_amt, "is_amount": True}
    if annual_income and annual_rate is not None:
        pay = annual_payment_for_principal(principal, annual_rate, term_years)
        debt_annual = monthly_debt_service * 12
        used = (pay + debt_annual) / annual_income
        out["DSR"] = {"actual": used, "cap": DSR_RATES[lender], "is_amount": False}
        out["DTI"] = {"actual": used, "cap": dti_rate(rule_id, regulated_type),
                      "is_amount": False}
    for v in out.values():
        if v["actual"] is None or v["cap"] is None:
            v["over"] = None
            v["gap"] = None
        else:
            v["over"] = v["actual"] > v["cap"]
            v["gap"] = v["actual"] - v["cap"]
    return out


def annual_payment_for_principal(principal: int, annual_rate: float, term_years: int) -> float:
    """대출원금 → 연 원리금 (principal_from_annual_payment 의 역함수)."""
    if principal <= 0 or term_years <= 0:
        return 0.0
    n = term_years * 12
    r = annual_rate / 12.0
    monthly = principal / n if r <= 0 else principal * r / (1.0 - (1.0 + r) ** -n)
    return monthly * 12.0


def plan_for_target(
    *,
    target: int,
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
    """목표 금액에 도달하려면 무엇을 얼마나 바꿔야 하는가 — 각 규제별로 **역산**한다.

    고객 조사(2026-08-20)에서 드러난 공백: 계산기·아티클은 "기존 대출을 정리하라"고
    말하지만 **얼마를 줄여야 하는지**는 아무도 계산해 주지 않는다. 진단(무엇에 막혔나)에서
    행동(그래서 얼마)으로 잇는 다리다.

    반환하는 처방은 전부 **이미 확정된 규제 값과 표준 상환식에서 역산**한 것이다 —
    새 도메인 값을 만들지 않는다. 규제 자체가 막는 것(LTV·최대한도)은 "이 조건으로는
    불가"라고 정직하게 말하고 대안 축(가격 조정)을 제시한다.
    """
    now = estimate(
        price=price, max_ltv=max_ltv, rule_id=rule_id, regulated=regulated,
        regulated_type=regulated_type, annual_income=annual_income,
        monthly_debt_service=monthly_debt_service, annual_rate=annual_rate,
        term_years=term_years, lender=lender,
    )
    if now["total"] is None:
        return {"target": target, "reachable": None, "now": now, "actions": []}
    if now["total"] >= target:
        return {"target": target, "reachable": True, "now": now, "actions": [],
                "headroom": now["total"] - target}

    actions: list[dict] = []
    limits = now["limits"]

    # ① LTV — 비율은 규제가 정한다. 바꿀 수 있는 축은 주택가격(자기자금)뿐이다.
    if limits["LTV"] is not None and limits["LTV"] < target and max_ltv > 0:
        actions.append({
            "limit": "LTV", "kind": "price",
            "need_price": int(target / max_ltv),
            "detail": "담보 비율은 규제가 정한 값이라 바꿀 수 없어요. "
                      "같은 금액을 빌리려면 주택가격 기준이 더 높아야 합니다.",
        })

    # ② 가격구간별 최대한도 — 구간 상한 자체가 천장. 넘을 방법이 없다.
    if limits["CAP"] is not None and limits["CAP"] < target:
        actions.append({
            "limit": "CAP", "kind": "hard",
            "detail": "규제지역 가격구간별 최대한도라 조건을 바꿔도 이 금액을 넘을 수 없어요.",
        })

    # ③④ DSR·DTI — 소득 여력의 문제라 세 갈래로 역산한다.
    if annual_income and annual_rate is not None:
        need_annual = annual_payment_for_principal(target, annual_rate, term_years)
        for key, rate in (("DSR", DSR_RATES[lender]),
                          ("DTI", dti_rate(rule_id, regulated_type))):
            if limits[key] is None or limits[key] >= target:
                continue
            # (a) 기존 부채를 얼마나 줄이면 되나
            allow_debt_annual = annual_income * rate - need_annual
            cut = monthly_debt_service - allow_debt_annual / 12.0
            # (b) 만기를 최대로 늘리면 도달하나
            by_term = None
            if term_years < MAX_TERM_YEARS:
                longer = principal_from_annual_payment(
                    annual_income * rate - monthly_debt_service * 12,
                    annual_rate, MAX_TERM_YEARS)
                by_term = {"years": MAX_TERM_YEARS, "limit": longer,
                           "enough": longer >= target}
            # (c) 소득이 얼마여야 하나 (부부합산 등)
            need_income = int((need_annual + monthly_debt_service * 12) / rate)
            actions.append({
                "limit": key, "kind": "income",
                "cut_monthly_debt": int(cut) if 0 < cut <= monthly_debt_service else None,
                "impossible_by_debt": cut > monthly_debt_service,
                "by_term": by_term,
                "need_income": need_income,
                "need_income_delta": need_income - annual_income,
            })

    return {"target": target, "reachable": False, "now": now, "actions": actions,
            "at_target": ratios_for(
                target, price=price, max_ltv=max_ltv, rule_id=rule_id, regulated=regulated,
                regulated_type=regulated_type, annual_income=annual_income,
                monthly_debt_service=monthly_debt_service, annual_rate=annual_rate,
                term_years=term_years, lender=lender),
            "shortfall": target - now["total"]}
