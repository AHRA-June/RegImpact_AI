"""6·30 시나리오 데모 — 룰엔진을 몇 가지 케이스로 실행해 출력.

실행: python examples/demo_6_30.py   (repo 루트에서)
Walking Skeleton / UI 연동 시 이 출력 구조를 그대로 쓴다.
"""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from regimpact import MortgageApplication, evaluate  # noqa: E402

CASES = [
    ("무주택 일반 · 구리 · 시행후", dict(region_code="GURI", evaluation_date=date(2026, 7, 2), house_count=0)),
    ("생애최초 · 구리 · 시행후", dict(region_code="GURI", evaluation_date=date(2026, 7, 2), house_count=0, first_home_buyer=True)),
    ("서민·실수요 · 화성동탄", dict(region_code="HWASEONG_DONGTAN", evaluation_date=date(2026, 7, 2), house_count=0, real_demand_flag=True)),
    ("비처분 1주택 · 용인기흥", dict(region_code="YONGIN_GIHEUNG", evaluation_date=date(2026, 7, 2), house_count=1)),
    ("처분조건부 1주택 · 구리", dict(region_code="GURI", evaluation_date=date(2026, 7, 2), house_count=1, disposal_condition_flag=True)),
    ("다주택 · 구리", dict(region_code="GURI", evaluation_date=date(2026, 7, 2), house_count=2)),
    ("경과규정(계약+계약금) · 구리", dict(region_code="GURI", evaluation_date=date(2026, 7, 2), house_count=0, contract_signed_at=date(2026, 6, 29), downpayment_paid_at=date(2026, 6, 29))),
    ("정책대출(디딤돌) · 구리", dict(region_code="GURI", evaluation_date=date(2026, 7, 2), house_count=0, policy_mortgage_flag=True)),
]


def main() -> None:
    print(f"{'케이스':<28} {'status':<18} {'LTV':>5}  {'rule_id':<14} reason")
    print("-" * 92)
    for label, kw in CASES:
        d = evaluate(MortgageApplication(**kw))
        ltv = "-" if d.max_ltv is None else f"{d.max_ltv:.0%}"
        gf = " (GF)" if d.grandfathering_applied else ""
        print(f"{label:<28} {d.status.value:<18} {ltv:>5}  {str(d.applicable_rule_id or '-'):<14} {','.join(d.reason_codes)}{gf}")


if __name__ == "__main__":
    main()
