"""데모 — 6·30 규제 변경의 Impact Matrix (Before/After, 룰엔진 실측).

실행: python examples/demo_impact_matrix.py

목적: `04_PLAN.md` Phase 1 Walking Skeleton의 "Impact Matrix(1~2행)"를
Stitch 하드코딩값이 아니라 **룰엔진 실제 출력**으로 산출하는 E2E 노드 시연.
소규모 대표 포트폴리오(신규규제지역 GURI 중심)를 before/after로 평가한다.
"""
from __future__ import annotations

from datetime import date

from regimpact.impact import analyze_portfolio, format_matrix
from regimpact.models import LoanPurpose, MortgageApplication

_REG = "GURI"                      # 6·30 신규 규제지역 (7.1부터 투기과열)
_NONREG = "SEOUL_GANGNAM"          # 미등록 → 비규제(데모용)
_AFTER = date(2026, 7, 2)


def _a(cid: str, **kw) -> MortgageApplication:
    base = dict(region_code=_REG, evaluation_date=_AFTER, customer_id=cid)
    base.update(kw)
    return MortgageApplication(**base)


def sample_portfolio() -> list[MortgageApplication]:
    """대표 포트폴리오 (실패모드 층화: 예외·다주택·경과규정·비규제)."""
    return [
        # 신규 규제지역 — 무주택 일반: 70% → 40% (강화·고임팩트)
        _a("C01", house_count=0),
        _a("C02", house_count=0),
        _a("C03", house_count=0),
        # 신규 규제지역 — 생애최초: 70% → 70% (예외 보호, 변화 없음)
        _a("C04", house_count=0, first_home_buyer=True),
        _a("C05", house_count=0, first_home_buyer=True),
        # 신규 규제지역 — 서민·실수요: 70% → 60% (완만한 강화)
        _a("C06", house_count=0, real_demand_flag=True),
        # 신규 규제지역 — 유주택 1주택(비처분): baseline 검토불가 → 0% (강화·고임팩트)
        _a("C07", house_count=1),
        # 신규 규제지역 — 다주택: → 0% (강화·고임팩트)
        _a("C08", house_count=2),
        _a("C09", house_count=3),
        # 경과규정(G1 전산접수 6.30) — after에도 종전 70% 유지 → 변화 없음
        _a("C10", house_count=0, application_accepted_at=date(2026, 6, 30)),
        # 경과규정(G2 계약+계약금 6.29) — 종전 70% 유지 → 변화 없음
        _a("C11", house_count=0, contract_signed_at=date(2026, 6, 29),
           downpayment_paid_at=date(2026, 6, 29)),
        # 처분조건부 1주택 — 무주택 기준 → 40% (강화)
        _a("C12", house_count=1, disposal_condition_flag=True),
        # 비규제지역 무주택 — 변화 없음(70% 유지)
        _a("C13", region_code=_NONREG, house_count=0),
        # 정책대출 — Discovery (자동판정 제외, 별도 처리)
        _a("C14", house_count=0, policy_mortgage_flag=True),
        # 주택구입목적 아님 — OUT_OF_SCOPE
        _a("C15", house_count=0, loan_purpose=LoanPurpose.OTHER),
    ]


def main() -> None:
    matrix = analyze_portfolio(sample_portfolio())
    print(format_matrix(matrix))
    print()
    print("건별 상세:")
    for r in matrix.rows:
        delta = "" if r.ltv_delta is None else f"  Δ={r.ltv_delta:+.0%}"
        flag = "  [고임팩트]" if r.high_impact else ""
        gf = "  [경과규정]" if r.grandfathered else ""
        print(
            f"  {r.customer_id:>4}  {r.direction.value:<11} "
            f"before={r.before.status.value}/{r.before.max_ltv} "
            f"after={r.after.status.value}/{r.after.max_ltv}{delta}{gf}{flag}"
        )


if __name__ == "__main__":
    main()
