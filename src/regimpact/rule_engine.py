"""Deterministic 주담대 LTV 룰엔진 (docs/05_RULE_SPEC.md §H 알고리즘).

LOCKED §4: 이 엔진의 규칙 '값·우선순위'는 사람이 확정한 명세(05_RULE_SPEC.md v1,
regulatory_facts.md)에서 온다. LLM이 규칙을 생성하지 않는다. 이 코드는 확정 명세의 구현이며,
LLM 출력(RegChange Extractor 등)을 검증하는 기준점(ground truth)이다.

우선순위(short-circuit):
    P0  스코프(주택구입목적)
    P0b 정책대출 → Discovery
    P1  경과규정 → **종전규정 = 컷오프(2026-06-30) 시점 규정으로 재판정**
    P2  지역상태 해석 (미등록 코드 → 사람 검토)
    P3  다주택 — 규제지역 또는 수도권이면 0%, 비수도권 비규제는 유주택 60%
    P4  유주택(비처분 1주택) — 규제지역 0% / 비수도권 비규제 60% / 수도권 비규제는 기준 부재
    P4b 무주택·처분조건부 1주택이 비규제면 기준선 70%
    P5  생애최초 70% → P6 서민·실수요 60% → P7 규제지역 일반 40%

2026-08-18 변경 (Q9·Q10 확정 + 지역 레지스트리 도입에 따른 정합화):
    - P3(다주택)을 지역 분기 **앞**으로 이동. FSC p2 "다주택자는 수도권 內 주택구입시 규제지역
      여부와 무관하게 LTV 0%" (C06) / §C-1b R6. 종전 §H는 P3가 비규제 경로에서 도달 불가였다.
    - 비규제 유주택 = 60% 확정. MOLIT 참고1 "非규제지역(수도권 外) 무주택 70% / 유주택 60%".
      원문이 **수도권 外**를 명시하므로 수도권 비규제 유주택은 근거 부재 → 사람 검토 유지.
    - 경과규정의 '종전규정'을 70%로 하드코딩하지 않는다. 종전규정은 지역마다 다르다 —
      서울 25구·경기 12곳은 6·30 이전에도 이미 규제지역이었다. 컷오프 시점으로 재판정한다.
"""
from __future__ import annotations

from datetime import date

from .grandfathering import CUTOFF, is_grandfathered, is_owner
from .models import (
    EvaluationStatus,
    LoanPurpose,
    LtvDecision,
    MortgageApplication,
    ReasonCode,
    RegionStatus,
)
from .regions import get_region, resolve_region_status

# 확정 LTV 값 (docs/05_RULE_SPEC.md §C, regulatory_facts.md)
LTV_REGULATED_STANDARD = 0.40
LTV_FIRST_HOME = 0.70          # 생애최초 (좌동)
LTV_REAL_DEMAND = 0.60         # 서민·실수요자
LTV_OWNER = 0.00               # 규제지역 유주택(비처분 1주택 이상)
LTV_MULTI = 0.00               # 다주택 — 규제지역 또는 수도권
LTV_BASELINE = 0.70            # 非규제 무주택(처분조건부 1주택 포함)
LTV_NONREG_OWNER = 0.60        # 非규제(수도권 外) 유주택 — MOLIT 참고1, Q9 확정 2026-08-18

SOURCE_6_30 = ["FSC_20260630", "MOLIT_20260630"]


def evaluate(app: MortgageApplication) -> LtvDecision:
    """주택구입목적 주담대의 적용 LTV를 deterministic하게 판정한다."""

    # P0. 스코프 — 주택구입목적만 코어 판정
    if app.loan_purpose != LoanPurpose.HOME_PURCHASE:
        return LtvDecision(
            status=EvaluationStatus.OUT_OF_SCOPE,
            reason_codes=[ReasonCode.OUT_OF_SCOPE_PRODUCT],
        )

    # P0b. 정책대출 → Discovery (코어 자동판정 제외)
    if app.policy_mortgage_flag:
        return LtvDecision(
            status=EvaluationStatus.DISCOVERY,
            reason_codes=[ReasonCode.DISCOVERY_POLICY_LOAN],
        )

    # P1. 경과규정 (최우선). 종전규정 = **컷오프 시점의 규정**으로 재판정한다.
    #     '70% 고정'이 아니다 — 서울 25구·경기 12곳은 6·30 이전에도 이미 규제지역이었으므로
    #     그 지역의 종전규정은 40%다.
    grandfathered, gf_reason = is_grandfathered(app)
    if grandfathered:
        prior = _decide_by_region(app, CUTOFF)
        return LtvDecision(
            status=prior.status,
            max_ltv=prior.max_ltv,
            applicable_rule_id=prior.applicable_rule_id,
            grandfathering_applied=True,
            reason_codes=[gf_reason, *prior.reason_codes],
            source_policy_ids=_merge_sources(prior.source_policy_ids, SOURCE_6_30),
        )

    return _decide_by_region(app, app.evaluation_date)


def _decide_by_region(app: MortgageApplication, as_of: date) -> LtvDecision:
    """P2~P7 — 특정 시점(as_of)의 지역상태를 기준으로 판정. 경과규정은 여기서 다루지 않는다."""

    # P2. 지역상태 (시점 해석)
    status, _regulated_type = resolve_region_status(app.region_code, as_of)
    if status is RegionStatus.UNKNOWN:
        # 레지스트리에 없는 지역코드 = 데이터 품질 문제. 비규제로 넘겨짚지 않는다.
        # (넘겨짚었더니 규제지역인 강남이 70%로 판정된 사고가 있었다 — regions.py 참고)
        return LtvDecision(
            status=EvaluationStatus.NEEDS_HUMAN_REVIEW,
            reason_codes=[ReasonCode.UNKNOWN_REGION],
        )

    regulated = status is RegionStatus.REGULATED
    region = get_region(app.region_code)
    capital_area = bool(region and region.capital_area)

    # P3. 다주택 — 규제지역 또는 수도권이면 규제 여부 무관 0% (FSC p2 C06, §C-1b R6)
    if app.house_count >= 2:
        if regulated or capital_area:
            return _decided(LTV_MULTI, "MULTI_0", ReasonCode.LTV_MULTI_HOME_0)
        # 비수도권 비규제 다주택 = 유주택 기준(60%)
        return _decided(LTV_NONREG_OWNER, "NONREG_OWNER_60",
                        ReasonCode.LTV_NONREG_OWNER_60, sources=False)

    # P4. 유주택(비처분 1주택)
    if is_owner(app):
        if regulated:
            return _decided(LTV_OWNER, "REG_OWNER_0", ReasonCode.LTV_OWNER_0)
        if not capital_area:
            return _decided(LTV_NONREG_OWNER, "NONREG_OWNER_60",
                            ReasonCode.LTV_NONREG_OWNER_60, sources=False)
        # 수도권 비규제 유주택 — 원문은 '수도권 外'만 60%로 명시. 근거 부재 → 사람 검토.
        return LtvDecision(
            status=EvaluationStatus.NEEDS_HUMAN_REVIEW,
            reason_codes=[ReasonCode.OWNER_BASELINE_UNKNOWN],
        )

    # --- 이하 무주택 (처분조건부 1주택 포함) ---
    # P4b. 비규제 기준선
    if not regulated:
        return _decided(LTV_BASELINE, "NONREG_STD_70",
                        ReasonCode.LTV_BASELINE_70, sources=False)

    # P5. 생애최초
    if app.first_home_buyer:
        return _decided(LTV_FIRST_HOME, "REG_FIRSTHOME", ReasonCode.EXCEPTION_FIRST_HOME)

    # P6. 서민·실수요자
    if app.real_demand_flag:
        return _decided(LTV_REAL_DEMAND, "REG_REALDEMAND", ReasonCode.EXCEPTION_REAL_DEMAND)

    # P7. 무주택 일반 / 처분조건부 1주택
    return _decided(LTV_REGULATED_STANDARD, "REG_STD", ReasonCode.LTV_REGULATED_40)


def _decided(ltv: float, rule_id: str, reason: ReasonCode, *, sources: bool = True) -> LtvDecision:
    """판정 확정. sources=False는 6·30 공문이 근거가 아닌 기준선 판정(비규제 경로)."""
    return LtvDecision(
        status=EvaluationStatus.DECIDED,
        max_ltv=ltv,
        applicable_rule_id=rule_id,
        reason_codes=[reason],
        source_policy_ids=list(SOURCE_6_30) if sources else [],
    )


def _merge_sources(*groups: list[str]) -> list[str]:
    out: list[str] = []
    for g in groups:
        for s in g:
            if s not in out:
                out.append(s)
    return out
