"""회귀 픽스처 export — Python 엔진의 판정을 JSON 으로 고정한다.

실행:  python tools/export_fixtures.py [--out site/fixtures.json]

용도: 브라우저에서 도는 룰엔진 JS 포팅본을 **실제 Python 엔진 실행 결과**와 대조하기 위한
기준값이다. 골든 기대값을 사람이 손으로 적지 않는 것이 요점 — 손으로 적으면 그 값이
틀렸을 때 아무도 모른다.

담기는 것:
  constants      LTV 상수·경계 날짜 (JS 가 자기 값을 갖지 않게)
  regions        지역 레지스트리 (시점 버전 그대로)
  cases          TC 생성기 케이스 + 엔진 판정
  region_probe   지역 × 시점 격자의 상태 (시간축 해석이 어긋나면 여기서 드러난다)
  affordability  참고 한도(LTV·최대한도·DSR·DTI) 상수 + 계산 프로브 (통합 계산기 포팅 대조)
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from regimpact import affordability, rule_engine                     # noqa: E402
from regimpact.grandfathering import CUTOFF                          # noqa: E402
from regimpact.models import RegionStatus                            # noqa: E402
from regimpact.regions import (                                      # noqa: E402
    REG_EFFECTIVE,
    REGION_LABELS,
    REGION_VERSIONS,
    CAPITAL_AREA_REGIONS,
    resolve_region_status,
)
from regimpact.rule_engine import evaluate                           # noqa: E402
from regimpact.tc_generator import generate_all                      # noqa: E402

# 시간축 해석을 확인할 시점들. 지정일 경계 앞뒤를 반드시 포함한다.
PROBE_DATES = (
    date(2015, 1, 1),
    date(2016, 11, 2), date(2016, 11, 3),
    date(2017, 8, 2), date(2017, 8, 3),
    date(2025, 10, 15), date(2025, 10, 16),
    date(2026, 6, 30), date(2026, 7, 1),
    date(2027, 1, 1),
)

# 레지스트리에 없는 코드 — UNKNOWN 으로 나와야 한다(비규제로 새면 안 된다).
UNREGISTERED_PROBES = ("BUSAN_HAEUNDAE", "SEOUL", "DAEGU_SUSEONG")


def _jsonable(v):
    if isinstance(v, date):
        return v.isoformat()
    if hasattr(v, "value"):
        return v.value
    if dataclasses.is_dataclass(v) and not isinstance(v, type):
        return {k: _jsonable(x) for k, x in dataclasses.asdict(v).items()}
    if isinstance(v, (list, tuple)):
        return [_jsonable(x) for x in v]
    if isinstance(v, dict):
        return {k: _jsonable(x) for k, x in v.items()}
    return v


def build() -> dict:
    constants = {
        "LTV_REGULATED_STANDARD": rule_engine.LTV_REGULATED_STANDARD,
        "LTV_FIRST_HOME": rule_engine.LTV_FIRST_HOME,
        "LTV_REAL_DEMAND": rule_engine.LTV_REAL_DEMAND,
        "LTV_OWNER": rule_engine.LTV_OWNER,
        "LTV_MULTI": rule_engine.LTV_MULTI,
        "LTV_BASELINE": rule_engine.LTV_BASELINE,
        "GRANDFATHERING_CUTOFF": CUTOFF.isoformat(),
        "REG_EFFECTIVE": REG_EFFECTIVE.isoformat(),
        "SOURCE_POLICY_IDS": list(rule_engine.SOURCE_6_30),
    }

    regions = {
        code: {
            "label": REGION_LABELS.get(code, code),
            "capital_area": code in CAPITAL_AREA_REGIONS,
            "versions": [_jsonable(v) for v in versions],
        }
        for code, versions in sorted(REGION_VERSIONS.items())
    }

    cases = []
    for c in generate_all():
        app = c.app
        cases.append({
            "case_id": c.case_id,
            "category": c.category.value,
            "description": c.description,
            "input": _jsonable(app),
            "engine": _jsonable(evaluate(app)),
        })

    probe = {}
    for code in list(REGION_VERSIONS) + list(UNREGISTERED_PROBES):
        probe[code] = {
            d.isoformat(): _jsonable(resolve_region_status(code, d)[0])
            for d in PROBE_DATES
        }

    aff_constants = {
        "max_loan_caps": [list(c) for c in affordability.MAX_LOAN_CAPS],
        "dsr_rates": dict(affordability.DSR_RATES),
        "dti_by_type": dict(affordability.DTI_BY_TYPE),
        "dti_other": affordability.DTI_OTHER,
        "dti_relaxed_rules": sorted(affordability._DTI_RELAXED_RULES),
        "max_term_years": affordability.MAX_TERM_YEARS,
    }
    # 프로브 격자 — 최대한도 경계(15억·25억), 소득 유무, 금리 0, 2금융, 차주 유형별 DTI 를 덮는다
    aff_probes = []
    profiles = [
        (0.40, "REG_STD", True, "SPECULATIVE_OVERHEATED"),
        (0.40, "REG_STD", True, "ADJUSTMENT"),
        (0.70, "REG_FIRSTHOME", True, "SPECULATIVE_OVERHEATED"),
        (0.60, "REG_REALDEMAND", True, "SPECULATIVE_OVERHEATED"),
        (0.00, "REG_OWNER_0", True, "SPECULATIVE_OVERHEATED"),
        (0.70, "NONREG_STD_70", False, "NONE"),
    ]
    moneys = [
        (None, 0, None, "BANK"),
        (60_000_000, 0, 0.04, "BANK"),
        (60_000_000, 1_500_000, 0.04, "BANK"),
        (120_000_000, 0, 0.035, "NONBANK"),
        (50_000_000, 2_000_000, 0.0, "BANK"),
    ]
    for price in (400_000_000, 1_500_000_000, 1_500_000_001, 2_500_000_000, 2_600_000_000):
        for max_ltv, rule_id, regulated, rtype in profiles:
            for income, debt, rate, lender in moneys:
                inp = dict(price=price, max_ltv=max_ltv, rule_id=rule_id,
                           regulated=regulated, regulated_type=rtype,
                           annual_income=income, monthly_debt_service=debt,
                           annual_rate=rate, term_years=30, lender=lender)
                aff_probes.append({"input": inp, "expected": affordability.estimate(**inp)})

    return {
        "_note": "tools/export_fixtures.py 가 Python 엔진을 실제로 실행해 만든 기준값. "
                 "손으로 고치지 말 것 — 재생성하면 덮어쓴다.",
        "constants": constants,
        "capital_area": sorted(CAPITAL_AREA_REGIONS),
        "regions": regions,
        "cases": cases,
        "region_probe": probe,
        "affordability": {"constants": aff_constants, "probes": aff_probes},
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(REPO / "site" / "fixtures.json"))
    args = ap.parse_args()

    data = build()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    n_unknown = sum(
        1 for code in UNREGISTERED_PROBES
        if data["region_probe"][code]["2026-07-01"] == RegionStatus.UNKNOWN.value
    )
    print(f"  {out}")
    print(f"  케이스 {len(data['cases'])} · 지역 {len(data['regions'])} "
          f"· 프로브 {len(data['region_probe'])}×{len(PROBE_DATES)}")
    print(f"  미등록 프로브 {n_unknown}/{len(UNREGISTERED_PROBES)} 가 UNKNOWN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
