"""총 가능금액(참고 추정) — min(LTV, 최대한도, DSR, DTI)와 binding 규제.

세 축을 본다: ① 산수가 맞는가(원리금균등 역산·경계) ② 모르는 것을 지어내지 않는가
(소득·금리 없으면 None, 0이나 무한대로 대체 금지) ③ 값이 확정 명세·원문과 갈라지지
않는가 — 상수를 손으로 고치면 여기서 잡힌다.
"""
import re

import pytest

from regimpact.affordability import (
    DSR_RATES,
    DTI_BY_TYPE,
    DTI_OTHER,
    MAX_LOAN_CAPS,
    MAX_TERM_YEARS,
    cap_for_price,
    dti_rate,
    estimate,
    principal_from_annual_payment,
)


# ---------- 산수 ----------
def test_annuity_inverse_roundtrip():
    """원금 → 연 원리금 → 역산했을 때 원금이 돌아와야 한다 (표준 annuity 정합)."""
    principal, rate, years = 300_000_000, 0.04, 30
    r, n = rate / 12, years * 12
    monthly = principal * r / (1 - (1 + r) ** -n)
    back = principal_from_annual_payment(monthly * 12, rate, years)
    assert abs(back - principal) <= 2          # 정수 절사 오차만 허용


def test_zero_rate_is_simple_division():
    assert principal_from_annual_payment(12_000_000, 0.0, 10) == 120_000_000


def test_negative_budget_is_zero_not_negative():
    """기존 부채가 소득 여력을 넘으면 한도는 0 — 음수 한도라는 허구를 만들지 않는다."""
    assert principal_from_annual_payment(-1, 0.04, 30) == 0


@pytest.mark.parametrize("price,expected", [
    (1_500_000_000, 600_000_000),      # 15억 이하 → 6억 (경계 포함)
    (1_500_000_001, 400_000_000),      # 15억 초과 → 4억
    (2_500_000_000, 400_000_000),      # 25억 이하 → 4억 (경계 포함)
    (2_500_000_001, 200_000_000),      # 25억 초과 → 2억
])
def test_price_cap_boundaries(price, expected):
    assert cap_for_price(price) == expected


def test_dti_rate_by_borrower_and_region():
    """§C-1: 일반은 투과 40/조정 50, 생애최초·서민실수요·비규제는 60 (완화 열)."""
    assert dti_rate("REG_STD", "SPECULATIVE_OVERHEATED") == 0.40
    assert dti_rate("REG_STD", "ADJUSTMENT") == 0.50
    assert dti_rate("REG_FIRSTHOME", "SPECULATIVE_OVERHEATED") == 0.60
    assert dti_rate("REG_REALDEMAND", "SPECULATIVE_OVERHEATED") == 0.60
    assert dti_rate("NONREG_STD_70", "NONE") == 0.60


# ---------- 모르는 것을 지어내지 않는다 ----------
def test_without_income_dsr_and_dti_stay_none():
    r = estimate(price=800_000_000, max_ltv=0.4, rule_id="REG_STD",
                 regulated=True, regulated_type="SPECULATIVE_OVERHEATED")
    assert r["limits"]["DSR"] is None and r["limits"]["DTI"] is None
    assert r["total"] == r["limits"]["LTV"]        # 아는 것들 중 최솟값만 주장


def test_cap_applies_only_when_regulated():
    """최대한도는 규제지역 조치(§C-1 주1) — 비규제·경과규정엔 걸지 않는다."""
    reg = estimate(price=800_000_000, max_ltv=0.4, rule_id="REG_STD",
                   regulated=True, regulated_type="SPECULATIVE_OVERHEATED")
    non = estimate(price=800_000_000, max_ltv=0.7, rule_id="NONREG_STD_70",
                   regulated=False)
    assert reg["limits"]["CAP"] == 600_000_000
    assert non["limits"]["CAP"] is None


def test_binding_identifies_the_lowest_limit():
    """인터뷰 요구의 핵심 — '얼마'만이 아니라 '무엇에 막혔는지'."""
    r = estimate(price=800_000_000, max_ltv=0.4, rule_id="REG_STD",
                 regulated=True, regulated_type="SPECULATIVE_OVERHEATED",
                 annual_income=50_000_000, monthly_debt_service=1_000_000,
                 annual_rate=0.04, term_years=30)
    assert r["binding"] and min(v for v in r["limits"].values() if v is not None) == r["total"]
    for k in r["binding"]:
        assert r["limits"][k] == r["total"]


# ---------- 값이 명세·원문과 갈라지지 않는가 ----------
def test_constants_match_the_confirmed_spec(tmp_path):
    from pathlib import Path
    spec = (Path(__file__).resolve().parents[1] / "docs" / "05_RULE_SPEC.md").read_text(
        encoding="utf-8")
    assert "15억↓6억/15~25억4억/25억↑2억" in spec          # §C-1 주1
    assert MAX_LOAN_CAPS[0] == (1_500_000_000, 600_000_000)
    assert MAX_LOAN_CAPS[1] == (2_500_000_000, 400_000_000)
    assert MAX_LOAN_CAPS[2][1] == 200_000_000
    assert "투기과열 0.40 / 조정 0.50" in spec               # §C-1 R1 (DTI)
    assert DTI_BY_TYPE == {"SPECULATIVE_OVERHEATED": 0.40, "ADJUSTMENT": 0.50}
    assert DTI_OTHER == 0.60


def test_constants_match_the_source_documents():
    """DSR 40/50 과 만기 30년은 6·30 원문에 있다 — 코퍼스와 대조."""
    from regimpact.extractor.sources import load_corpus
    norm = {k: re.sub(r"\s+", " ", v) for k, v in load_corpus().items()}
    assert "DSR 규제(은행권 40% , 2금융권 50%, 규제지역 동일)" in norm["FAQ_20260630"]
    assert DSR_RATES == {"BANK": 0.40, "NONBANK": 0.50}
    assert "최대 만기 30년이내" in norm["MOLIT_PRESS_20260630"]
    assert MAX_TERM_YEARS == 30
