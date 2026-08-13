"""층화 합성 포트폴리오 — 룰엔진 평가셋을 100~120건으로 확대(04_PLAN Phase 2).

설계 원칙:
    - **오라클이 라벨러:** 정답은 독립 명세 오라클(`oracle.expected_outcome`)이 유도한다.
      → 100+건을 손으로 라벨하지 않고 차등검증(differential testing)으로 확장(핵심 이점).
    - **층화(stratified):** 입력 차원(지역·시점·house_count·예외·경과규정·스코프)을 체계적으로
      훑어 6개 카테고리(SCOPE/BASELINE/EXCEPTION/BOUNDARY/GRANDFATHERING/CONFLICT)를 커버.
    - **결정론적:** 난수 없이 중첩 루프 + 안정 case_id → 재현 가능(회귀 안정).
    - **split(DEV/LOCKED/CHALLENGE):** 라벨을 부여하되 **전량 측정**한다. 룰엔진은 결정론(튜닝
      루프 없음)이라 LOCKED/CHALLENGE를 열어도 누수 위험이 없다(04_PLAN §0-5 정합). LLM 추출용
      골드셋의 LOCKED/CHALLENGE 봉인 원칙과 별개.
    - split 배분: 브리프 §11/metrics_spec에 따라 CHALLENGE는 CONFLICT·GRANDFATHERING·BOUNDARY·
      EXCEPTION(적대적)을 가중, 나머지는 DEV/LOCKED로 균등 분할.
"""
from __future__ import annotations

import itertools
from dataclasses import replace
from datetime import date, timedelta
from enum import Enum

from ..models import LoanPurpose, MortgageApplication
from .generator import Category, GeneratedCase, _case

# 시점 상수 (generator와 정렬)
_CUTOFF = date(2026, 6, 30)         # 경과규정 경계
_EFFECTIVE = date(2026, 7, 1)       # 규제 효력일
_AFTER = date(2026, 7, 2)
_BEFORE = date(2026, 6, 15)
_REG_REGIONS = ("GURI", "YONGIN_GIHEUNG", "HWASEONG_DONGTAN")
_NONREG = "SEOUL_GANGNAM"           # 미등록 = 非규제


class Split(str, Enum):
    DEV = "DEV"
    LOCKED = "LOCKED"
    CHALLENGE = "CHALLENGE"


def _mk(case_id: str, category: Category, desc: str, **kw) -> GeneratedCase:
    """지역·시점을 kw로 받아 케이스를 만든다(정답은 오라클이 채움)."""
    base = dict(region_code=kw.pop("region_code", "GURI"),
                evaluation_date=kw.pop("evaluation_date", _AFTER))
    base.update(kw)
    return _case(case_id, category, desc, MortgageApplication(**base))


# ---------------------------------------------------------------------------
# 카테고리별 층화 생성기
# ---------------------------------------------------------------------------
def _scope() -> list[GeneratedCase]:
    out: list[GeneratedCase] = []
    # 주택구입목적 아님 → OUT_OF_SCOPE (지역·시점·house_count 훑기)
    i = 0
    for region in (_REG_REGIONS[0], _REG_REGIONS[2], _NONREG):
        for d in (_AFTER, _BEFORE):
            for hc in (0, 1):
                i += 1
                out.append(_mk(f"P-SCOPE-{i:02d}", Category.SCOPE,
                               f"비주택구입목적 {region}/{d.isoformat()}/hc{hc}",
                               region_code=region, evaluation_date=d,
                               house_count=hc, loan_purpose=LoanPurpose.OTHER))
    # 정책대출 → Discovery (다른 조건 무시 확인)
    for j, kw in enumerate([
        dict(house_count=0), dict(house_count=2), dict(house_count=3),
        dict(house_count=0, first_home_buyer=True),
        dict(house_count=1, real_demand_flag=True),
        dict(house_count=1, disposal_condition_flag=True),
    ], 1):
        out.append(_mk(f"P-SCOPE-P{j:02d}", Category.SCOPE,
                       f"정책대출 → Discovery ({kw})",
                       policy_mortgage_flag=True, **kw))
    return out


def _baseline() -> list[GeneratedCase]:
    out: list[GeneratedCase] = []
    i = 0
    # 非규제(미등록 지역 @ 후) + 규제지역 코드지만 시행 전(6.15/6.30 둘 다)
    combos = [(_NONREG, _AFTER)]
    for region in _REG_REGIONS:
        combos += [(region, _BEFORE), (region, _CUTOFF)]
    for region, d in combos:
        for hc in (0, 1, 2):
            i += 1
            out.append(_mk(f"P-BASE-{i:02d}", Category.BASELINE,
                           f"非규제/시행전 {region}/{d.isoformat()}/hc{hc}",
                           region_code=region, evaluation_date=d, house_count=hc))
    # 非규제 무주택 + 예외플래그(예외는 非규제 기준선에 영향 없음 확인)
    for j, kw in enumerate([
        dict(first_home_buyer=True), dict(real_demand_flag=True),
        dict(house_count=1, disposal_condition_flag=True),
        dict(first_home_buyer=True, real_demand_flag=True),
    ], 1):
        out.append(_mk(f"P-BASE-X{j:02d}", Category.BASELINE,
                       f"非규제 무주택+예외플래그 무영향 ({kw})",
                       region_code=_NONREG, evaluation_date=_AFTER, **kw))
    return out


def _exception() -> list[GeneratedCase]:
    out: list[GeneratedCase] = []
    i = 0
    # 규제지역 3곳 × 예외 프로필
    profiles = [
        ("무주택 일반", dict(house_count=0)),
        ("생애최초", dict(house_count=0, first_home_buyer=True)),
        ("서민실수요", dict(house_count=0, real_demand_flag=True)),
        ("처분조건부1주택", dict(house_count=1, disposal_condition_flag=True)),
        ("처분조건부+생애최초", dict(house_count=1, disposal_condition_flag=True, first_home_buyer=True)),
        ("처분조건부+서민실수요", dict(house_count=1, disposal_condition_flag=True, real_demand_flag=True)),
        ("생애최초+서민실수요(무주택)", dict(house_count=0, first_home_buyer=True, real_demand_flag=True)),
    ]
    for region in _REG_REGIONS:
        for label, kw in profiles:
            i += 1
            out.append(_mk(f"P-EXC-{i:02d}", Category.EXCEPTION,
                           f"{region} {label}",
                           region_code=region, evaluation_date=_AFTER, **kw))
    return out


def _boundary() -> list[GeneratedCase]:
    out: list[GeneratedCase] = []
    # 효력일 경계 ±1 (지역별)
    i = 0
    for region in _REG_REGIONS:
        for d in (_CUTOFF, _EFFECTIVE, _AFTER):
            i += 1
            out.append(_mk(f"P-BND-EFF-{i:02d}", Category.BOUNDARY,
                           f"효력일 경계 {region}/{d.isoformat()}",
                           region_code=region, evaluation_date=d, house_count=0))
    # 경과규정 접수일(G1) 컷오프 ±1 (무주택/유주택)
    k = 0
    for hc in (0, 1):
        for d in (_CUTOFF - timedelta(days=1), _CUTOFF, _CUTOFF + timedelta(days=1)):
            k += 1
            out.append(_mk(f"P-BND-G1-{k:02d}", Category.BOUNDARY,
                           f"전산접수일 {d.isoformat()} 경계 hc{hc}",
                           house_count=hc, application_accepted_at=d))
    # house_count 경계 0/1/2/3 (규제지역, 비처분)
    for hc in (0, 1, 2, 3):
        out.append(_mk(f"P-BND-HC-{hc}", Category.BOUNDARY,
                       f"house_count={hc} 경계",
                       house_count=hc))
    return out


def _grandfathering() -> list[GeneratedCase]:
    out: list[GeneratedCase] = []
    # G1 접수: 컷오프 이전/당일/이후 × 무주택/유주택
    k = 0
    for hc in (0, 1):
        for d in (date(2026, 6, 20), _CUTOFF, _EFFECTIVE):
            k += 1
            out.append(_mk(f"P-GF-G1-{k:02d}", Category.GRANDFATHERING,
                           f"G1 접수 {d.isoformat()} hc{hc}",
                           house_count=hc, application_accepted_at=d))
    # G2 계약+계약금: 계약금 유/무 × house_count
    for j, (dp, hc) in enumerate([
        (date(2026, 6, 29), 0), (None, 0), (date(2026, 6, 29), 1), (date(2026, 6, 29), 2),
    ], 1):
        kw = dict(house_count=hc, contract_signed_at=date(2026, 6, 29))
        if dp is not None:
            kw["downpayment_paid_at"] = dp
        out.append(_mk(f"P-GF-G2-{j:02d}", Category.GRANDFATHERING,
                       f"G2 계약+계약금{'유' if dp else '무'} hc{hc}", **kw))
    # G3 토허제: 대상 T/F × 신청일
    for j, (tgt, d) in enumerate([
        (True, _CUTOFF), (True, _EFFECTIVE), (False, _CUTOFF),
    ], 1):
        out.append(_mk(f"P-GF-G3-{j:02d}", Category.GRANDFATHERING,
                       f"G3 토허제 대상{tgt} 신청{d.isoformat()}",
                       house_count=0, land_permit_target=tgt,
                       land_permit_applied_at=d, contract_signed_at=date(2026, 7, 10)))
    return out


def _conflict() -> list[GeneratedCase]:
    out: list[GeneratedCase] = []
    specs = [
        ("생애최초+서민실수요 → P5 생애최초", dict(house_count=0, first_home_buyer=True, real_demand_flag=True)),
        ("경과규정+생애최초 → 경과규정 우선", dict(house_count=0, first_home_buyer=True, application_accepted_at=_CUTOFF)),
        ("경과규정+서민실수요 → 경과규정 우선", dict(house_count=0, real_demand_flag=True, application_accepted_at=_CUTOFF)),
        ("경과규정+다주택 → 유주택 기준값 부재 escalation", dict(house_count=2, application_accepted_at=date(2026, 6, 20))),
        ("경과규정(G2)+유주택 → escalation", dict(house_count=1, contract_signed_at=date(2026, 6, 29), downpayment_paid_at=date(2026, 6, 29))),
        ("다주택+서민실수요 → P3 다주택 0%", dict(house_count=2, real_demand_flag=True)),
        ("다주택+생애최초 → P3 다주택 0%", dict(house_count=3, first_home_buyer=True)),
        ("다주택+생애최초+서민실수요 → P3 0%", dict(house_count=2, first_home_buyer=True, real_demand_flag=True)),
        ("정책대출+경과규정 → P0b Discovery 우선", dict(house_count=0, policy_mortgage_flag=True, application_accepted_at=_CUTOFF)),
    ]
    for i, (desc, kw) in enumerate(specs, 1):
        note = None
        if "유주택" in desc and kw.get("first_home_buyer"):
            note = "§H P4 short-circuit 채택(Q8 모호성)."
        c = _mk(f"P-CFL-{i:02d}", Category.CONFLICT, desc, **kw)
        if note:
            c = replace(c, spec_note=note)
        out.append(c)
    # 유주택(비처분1주택)+생애최초 = §H P4 0% (Q8 표면화)
    out.append(replace(
        _mk("P-CFL-Q8", Category.CONFLICT,
            "유주택(비처분1주택)+생애최초 → §H(P4) 0%",
            house_count=1, disposal_condition_flag=False, first_home_buyer=True),
        spec_note="알려진 §E vs §H 모호성. §H(P4) 0% 채택. 03_OPEN_QUESTIONS Q8."))
    return out


# ---------------------------------------------------------------------------
# split 배분 + 통합 생성
# ---------------------------------------------------------------------------
def _assign_splits(cases: list[GeneratedCase], challenge_target: int = 35) -> list[GeneratedCase]:
    """split을 결정론적으로 부여. CHALLENGE는 적대적 카테고리 가중, 나머지 DEV/LOCKED 균등."""
    by_id = sorted(cases, key=lambda c: c.case_id)
    challenge_ids: set[str] = set()
    # 가중 우선순위: CONFLICT → GRANDFATHERING → BOUNDARY → EXCEPTION
    for cat in (Category.CONFLICT, Category.GRANDFATHERING, Category.BOUNDARY, Category.EXCEPTION):
        for c in by_id:
            if len(challenge_ids) >= challenge_target:
                break
            if c.category == cat:
                challenge_ids.add(c.case_id)

    out: list[GeneratedCase] = []
    rest_idx = 0
    for c in by_id:
        if c.case_id in challenge_ids:
            out.append(replace(c, split=Split.CHALLENGE.value))
        else:
            split = Split.DEV.value if rest_idx % 2 == 0 else Split.LOCKED.value
            out.append(replace(c, split=split))
            rest_idx += 1
    return out


def generate_portfolio() -> list[GeneratedCase]:
    """층화 합성 포트폴리오(~106건)를 생성한다. case_id 안정·유일, split 부여."""
    cases: list[GeneratedCase] = []
    cases += _scope()
    cases += _baseline()
    cases += _exception()
    cases += _boundary()
    cases += _grandfathering()
    cases += _conflict()

    seen: set[str] = set()
    for c in cases:
        if c.case_id in seen:
            raise ValueError(f"중복 case_id: {c.case_id}")
        seen.add(c.case_id)

    return _assign_splits(cases)


# ---------------------------------------------------------------------------
# 대규모 조합 격자 (수천 건) — 결정론적 cartesian, 오라클 라벨
# ---------------------------------------------------------------------------
_GRID_REGIONS = (*_REG_REGIONS, _NONREG)
_GRID_DATES = (_BEFORE, _CUTOFF, _EFFECTIVE, _AFTER)
_GRID_HC = (0, 1, 2, 3)
_GRID_GF = (
    {},
    {"application_accepted_at": _CUTOFF},
    {"application_accepted_at": _EFFECTIVE},
    {"contract_signed_at": date(2026, 6, 29), "downpayment_paid_at": date(2026, 6, 29)},
    {"contract_signed_at": date(2026, 6, 29)},                       # 계약금 미납
    {"land_permit_target": True, "land_permit_applied_at": _CUTOFF,
     "contract_signed_at": date(2026, 7, 10)},
)


def _has_gf(app: MortgageApplication) -> bool:
    return bool(
        app.application_accepted_at or app.contract_signed_at
        or app.downpayment_paid_at or app.land_permit_target or app.land_permit_applied_at
    )


def _categorize(app: MortgageApplication) -> Category:
    """격자 케이스를 구조적 특징으로 근사 분류(통계 라벨용, 우선순위 순)."""
    if app.loan_purpose != LoanPurpose.HOME_PURCHASE or app.policy_mortgage_flag:
        return Category.SCOPE
    if _has_gf(app):
        return Category.GRANDFATHERING
    excs = int(app.first_home_buyer) + int(app.real_demand_flag)
    owner = app.house_count >= 2 or (app.house_count >= 1 and not app.disposal_condition_flag)
    if excs >= 2 or (owner and excs >= 1):
        return Category.CONFLICT
    if app.evaluation_date in (_CUTOFF, _EFFECTIVE):
        return Category.BOUNDARY
    if app.region_code not in _REG_REGIONS or app.evaluation_date < _EFFECTIVE:
        return Category.BASELINE
    return Category.EXCEPTION


def _grid_split(index: int, category: Category) -> str:
    """결정론적 split 배분(index 기반). 적대적 카테고리를 CHALLENGE로 가중."""
    adversarial = category in (Category.GRANDFATHERING, Category.CONFLICT, Category.BOUNDARY)
    if adversarial and index % 3 == 0:
        return Split.CHALLENGE.value
    return Split.DEV.value if index % 2 == 0 else Split.LOCKED.value


def _grid_apps() -> list[MortgageApplication]:
    apps: list[MortgageApplication] = []
    # 코어 LTV 격자 (주택구입목적·비정책): 실제 판정 로직을 넓게 훑음
    for region, d, hc, disp, fh, rd, gf in itertools.product(
        _GRID_REGIONS, _GRID_DATES, _GRID_HC,
        (False, True), (False, True), (False, True), _GRID_GF,
    ):
        kw = dict(region_code=region, evaluation_date=d, house_count=hc,
                  disposal_condition_flag=disp, first_home_buyer=fh, real_demand_flag=rd)
        kw.update(gf)
        apps.append(MortgageApplication(**kw))
    # 스코프 격자: 비주택구입목적 / 정책대출 short-circuit 분기
    for region, d, hc in itertools.product(_GRID_REGIONS, _GRID_DATES, _GRID_HC):
        apps.append(MortgageApplication(region_code=region, evaluation_date=d,
                                        house_count=hc, loan_purpose=LoanPurpose.OTHER))
        apps.append(MortgageApplication(region_code=region, evaluation_date=d,
                                        house_count=hc, policy_mortgage_flag=True))
    return apps


def generate_grid() -> list[GeneratedCase]:
    """대규모 조합 격자(수천 건)를 결정론적으로 생성한다. 정답은 오라클이 유도.

    코어 LTV 격자(지역·시점·house_count·처분·생애최초·서민실수요·경과규정) + 스코프 격자.
    case_id는 안정적(G-#####). 손라벨 없이 넓은 입력공간을 차등검증한다.
    """
    cases: list[GeneratedCase] = []
    for i, app in enumerate(_grid_apps()):
        cat = _categorize(app)
        case = _case(f"G-{i:05d}", cat, f"grid {cat.value}", app)
        cases.append(replace(case, split=_grid_split(i, cat)))
    return cases


def coverage(cases: list[GeneratedCase]) -> dict[str, int]:
    """포트폴리오가 커버하는 판정 다양성(통계 신뢰도 근거)."""
    statuses = {c.expected.status.value for c in cases}
    rule_ids = {c.expected.applicable_rule_id for c in cases if c.expected.applicable_rule_id}
    reasons: set[str] = set()
    for c in cases:
        reasons.update(c.expected.must_include_reasons)
    return {
        "distinct_status": len(statuses),
        "distinct_rule_id": len(rule_ids),
        "distinct_reason_code": len(reasons),
    }

