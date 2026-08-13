"""층화 합성 포트폴리오 생성기 — 룰엔진 차등검증을 seed 30건에서 수천 규모로 확대.

04_PLAN Phase 2("층화 합성 포트폴리오 2,000~5,000 + Rule regression 정식") 구현.
metrics_spec: 성공 기준은 '건수 채우기'가 아니라 **실패모드 카테고리 커버리지**다. 따라서
균일 난수가 아니라 **층화(stratified)** — 판정에 영향을 주는 5개 축을 곱집합으로 훑어
각 조합(stratum)을 최소 k건씩 보장하고, 세부값(정확한 날짜·주택수)만 seed 난수로 흔든다.

5개 층화 축:
    scope        : home / other(주택구입목적 아님) / policy(정책대출)
    region_time  : reg_after(규제 발효 후) / reg_before(같은 지역·발효 전=非규제) / nonreg(미등록 지역)
    ownership    : nohome / disposal_1home(처분조건부) / owner_1home(비처분) / multi_home
    exception    : none / first_home / real_demand
    grandfather  : none / g1(전산접수) / g2(계약+계약금) / g3(토허제)

각 케이스의 기대값은 **독립 명세 오라클**(oracle.expected_outcome)이 유도한다(생성기는 정답을
만들지 않는다). 따라서 기존 `run_regression(cases)` 에 그대로 흘려 엔진⟷오라클 차등검증이 된다.

결정적: 같은 (target_n, seed) 는 항상 동일 포트폴리오를 만든다(재현 가능·감사 가능).
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date, timedelta
from itertools import product

from ..models import LoanPurpose, MortgageApplication
from .generator import Category, GeneratedCase
from .oracle import expected_outcome

# --- 시나리오 경계 상수 (generator 와 동일 기준) ---
_CUTOFF = date(2026, 6, 30)      # 경과규정 경계
_EFFECTIVE = date(2026, 7, 1)    # 규제 효력일
_REG_REGIONS = ("GURI", "YONGIN_GIHEUNG", "HWASEONG_DONGTAN")
_NONREG_REGION = "SEOUL_GANGNAM"  # 미등록 → 항상 非규제

# region_time 버킷별 평가일 후보 (효력일 경계 강조)
_DATES_AFTER = (date(2026, 7, 1), date(2026, 7, 2), date(2026, 7, 10), date(2026, 8, 1))
_DATES_BEFORE = (date(2026, 6, 1), date(2026, 6, 15), date(2026, 6, 29), date(2026, 6, 30))
# 경과규정 이벤트일: 컷오프 양측(≤6.30 인정 / ≥7.1 불인정)을 섞어 경계 검증
_GF_EVENT_DATES = (date(2026, 6, 15), date(2026, 6, 29), date(2026, 6, 30),
                   date(2026, 7, 1), date(2026, 7, 2))

_SCOPES = ("home", "other", "policy")
_REGION_TIMES = ("reg_after", "reg_before", "nonreg")
_OWNERSHIPS = ("nohome", "disposal_1home", "owner_1home", "multi_home")
_EXCEPTIONS = ("none", "first_home", "real_demand")
_GRANDFATHERS = ("none", "g1", "g2", "g3")


@dataclass(frozen=True)
class Stratum:
    """층화 셀 — 5개 축의 좌표."""
    scope: str
    region_time: str
    ownership: str
    exception: str
    grandfather: str

    @property
    def label(self) -> str:
        return f"{self.scope}|{self.region_time}|{self.ownership}|{self.exception}|{self.grandfather}"


def all_strata() -> list[Stratum]:
    """5개 축의 곱집합(3×3×4×3×4 = 432 strata). 정렬 순서 고정(결정적)."""
    return [
        Stratum(*combo)
        for combo in product(_SCOPES, _REGION_TIMES, _OWNERSHIPS, _EXCEPTIONS, _GRANDFATHERS)
    ]


def _build_app(st: Stratum, rng: random.Random) -> MortgageApplication:
    """한 stratum 좌표 + seed 난수(세부값)로 MortgageApplication 1건을 만든다."""
    # region_time → region_code + evaluation_date
    if st.region_time == "reg_after":
        region = rng.choice(_REG_REGIONS)
        eval_date = rng.choice(_DATES_AFTER)
    elif st.region_time == "reg_before":
        region = rng.choice(_REG_REGIONS)
        eval_date = rng.choice(_DATES_BEFORE)
    else:  # nonreg
        region = _NONREG_REGION
        eval_date = rng.choice(_DATES_AFTER + _DATES_BEFORE)

    # ownership → house_count + disposal
    if st.ownership == "nohome":
        house_count, disposal = 0, False
    elif st.ownership == "disposal_1home":
        house_count, disposal = 1, True
    elif st.ownership == "owner_1home":
        house_count, disposal = 1, False
    else:  # multi_home
        house_count, disposal = rng.choice((2, 3)), False

    kw = dict(
        region_code=region,
        evaluation_date=eval_date,
        house_count=house_count,
        disposal_condition_flag=disposal,
        first_home_buyer=(st.exception == "first_home"),
        real_demand_flag=(st.exception == "real_demand"),
        policy_mortgage_flag=(st.scope == "policy"),
        loan_purpose=LoanPurpose.OTHER if st.scope == "other" else LoanPurpose.HOME_PURCHASE,
    )

    # grandfather → 경과규정 이벤트일(컷오프 양측 난수)
    if st.grandfather == "g1":
        kw["application_accepted_at"] = rng.choice(_GF_EVENT_DATES)
    elif st.grandfather == "g2":
        kw["contract_signed_at"] = rng.choice(_GF_EVENT_DATES)
        # 계약금 납부 증빙 유무도 흔든다(G2 성립 조건)
        if rng.random() < 0.7:
            kw["downpayment_paid_at"] = kw["contract_signed_at"]
    elif st.grandfather == "g3":
        kw["land_permit_target"] = True
        kw["land_permit_applied_at"] = rng.choice(_GF_EVENT_DATES)
        kw["contract_signed_at"] = _EFFECTIVE + timedelta(days=rng.randint(1, 20))

    return MortgageApplication(**kw)


def _classify(app: MortgageApplication) -> Category:
    """리포트용 카테고리 분류(기존 Category 재사용). 판정 정답이 아니라 '보고 버킷'.

    분류 우선순위는 명세 short-circuit 순서를 대략 반영(스코프→경과→경계→충돌→예외→기준선)."""
    if app.loan_purpose != LoanPurpose.HOME_PURCHASE or app.policy_mortgage_flag:
        return Category.SCOPE

    has_gf_event = (
        app.application_accepted_at is not None
        or (app.contract_signed_at is not None and app.downpayment_paid_at is not None)
        or (app.land_permit_target and app.land_permit_applied_at is not None)
    )
    owner = app.house_count >= 2 or (app.house_count >= 1 and not app.disposal_condition_flag)
    exc = app.first_home_buyer or app.real_demand_flag

    # 충돌: 유주택인데 예외플래그 동시, 또는 두 예외 동시
    if (owner and exc) or (app.first_home_buyer and app.real_demand_flag):
        return Category.CONFLICT
    if has_gf_event:
        return Category.GRANDFATHERING
    if _near_boundary(app):
        return Category.BOUNDARY
    reg_region = app.region_code in _REG_REGIONS
    if not (reg_region and app.evaluation_date >= _EFFECTIVE):
        return Category.BASELINE
    if exc or owner:
        return Category.EXCEPTION
    return Category.EXCEPTION


def _near_boundary(app: MortgageApplication) -> bool:
    """평가일 또는 경과규정 이벤트일이 컷오프/효력일 ±1일 이내인가."""
    anchors = (_CUTOFF, _EFFECTIVE)
    dates = [app.evaluation_date, app.application_accepted_at,
             app.contract_signed_at, app.land_permit_applied_at]
    for d in dates:
        if d is None:
            continue
        for a in anchors:
            if abs((d - a).days) <= 1:
                return True
    return False


def _samples_for(st: Stratum, home_per: int) -> int:
    """stratum 별 표본 수(가중 층화).

    scope=other/policy 는 다른 축과 무관하게 short-circuit(OUT_OF_SCOPE/DISCOVERY)이므로
    커버리지 확인용으로 1건만 둔다(선행 우선순위가 다른 조건을 덮는지만 검증). 물량은
    판정 관련(scope=home) 셀에 집중해 정보 밀도를 높인다."""
    return home_per if st.scope == "home" else 1


def generate_portfolio(target_n: int = 3000, seed: int = 20260630) -> list[GeneratedCase]:
    """가중 층화 합성 포트폴리오를 생성한다(결정적).

    모든 432 strata 를 최소 1건씩 채워 커버리지를 보장하되, 판정 관련(scope=home) 셀에
    표본을 집중한다. 실제 규모는 target_n 근처. 오라클(expected_outcome)이 기대값을 유도한다.
    """
    strata = all_strata()
    home_strata = sum(1 for st in strata if st.scope == "home")
    nonhome_strata = len(strata) - home_strata
    # target_n = home_strata*home_per + nonhome_strata*1  →  home_per 역산
    home_per = max(1, round((target_n - nonhome_strata) / home_strata))
    rng = random.Random(seed)

    cases: list[GeneratedCase] = []
    idx = 0
    for st in strata:
        for _ in range(_samples_for(st, home_per)):
            app = _build_app(st, rng)
            cases.append(
                GeneratedCase(
                    case_id=f"PF-{idx:05d}",
                    category=_classify(app),
                    description=f"[{st.label}] {app.region_code} {app.evaluation_date.isoformat()} "
                                f"hc={app.house_count}",
                    app=app,
                    expected=expected_outcome(app),
                )
            )
            idx += 1
    return cases


def portfolio_coverage(cases: list[GeneratedCase]) -> dict:
    """포트폴리오 커버리지 요약(카테고리·결과상태·경계·경과규정 분포).

    metrics_spec: 성공 기준은 건수가 아니라 실패모드 커버리지 → 이 분포가 그 증거."""
    from collections import Counter

    by_category = Counter(c.category.value for c in cases)
    by_status = Counter(c.expected.status.value for c in cases)
    gf_applied = sum(1 for c in cases if c.expected.grandfathering_applied)
    boundary = sum(1 for c in cases if _near_boundary(c.app))
    strata_hit = len({c.description.split("]")[0] + "]" for c in cases})
    return {
        "total": len(cases),
        "strata_total": len(all_strata()),
        "strata_hit": strata_hit,
        "by_category": dict(by_category),
        "by_status": dict(by_status),
        "grandfathering_applied": gf_applied,
        "boundary_cases": boundary,
    }


def format_coverage(cases: list[GeneratedCase]) -> str:
    """커버리지 요약을 사람이 읽는 텍스트로."""
    cov = portfolio_coverage(cases)
    L = [
        f"포트폴리오 규모      : {cov['total']}건",
        f"층화 커버리지        : {cov['strata_hit']}/{cov['strata_total']} strata "
        f"({cov['strata_hit'] / cov['strata_total']:.0%})",
        f"경계(±1일) 케이스    : {cov['boundary_cases']}건",
        f"경과규정 적용        : {cov['grandfathering_applied']}건",
        "카테고리 분포        :",
    ]
    for cat, n in sorted(cov["by_category"].items()):
        L.append(f"    {cat:<15} {n:>5}")
    L.append("결과 상태 분포       :")
    for stt, n in sorted(cov["by_status"].items()):
        L.append(f"    {stt:<20} {n:>5}")
    return "\n".join(L)
