"""Deterministic 주담대 LTV 룰엔진 (docs/05_RULE_SPEC.md §H 알고리즘).

LOCKED §4: 이 엔진의 규칙 '값·우선순위'는 사람이 확정한 명세(05_RULE_SPEC.md v1,
regulatory_facts.md)에서 온다. LLM이 규칙을 생성하지 않는다. 이 코드는 확정 명세의 구현이며,
LLM 출력(RegChange Extractor 등)을 검증하는 기준점(ground truth)이다.

우선순위(short-circuit): P0 스코프 → P0b 정책대출=Discovery → **P0c 수도권 다주택** → P1 경과규정
→ P2 지역상태 → P3 다주택 → P4 유주택 → P5 생애최초 → P6 서민실수요 → P7 일반.
"""
from __future__ import annotations

from .grandfathering import is_grandfathered, is_owner
from .models import (
    EvaluationStatus,
    LoanPurpose,
    LtvDecision,
    MortgageApplication,
    ReasonCode,
    RegionStatus,
)
from .regions import is_capital_area, resolve_region_status

# 확정 LTV 값 (docs/05_RULE_SPEC.md §C, regulatory_facts.md FAQ Q2)
LTV_REGULATED_STANDARD = 0.40
LTV_FIRST_HOME = 0.70          # 생애최초 (좌동)
LTV_REAL_DEMAND = 0.60         # 서민·실수요자
LTV_OWNER = 0.00               # 유주택(비처분 1주택 이상)
LTV_MULTI = 0.00               # 다주택
LTV_BASELINE = 0.70            # 非규제 수도권 무주택 기준선 / 종전규정

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

    # P0c. 수도권 다주택 → 0% (지역 규제상태·시점 무관)
    #
    # 근거(원문 verbatim): FSC 보도참고자료 p2 / FAQ Q1 ※ —
    #   "다주택자는 수도권 內 주택구입시 **규제지역 여부와 무관하게** LTV 0% 적용"
    # 이 규칙은 6·30 지정으로 새로 생긴 것이 아니라 旣 마련된 규정이다(FSC p2:
    # "旣 마련된 규정에 따라 ... 7.1일부터 즉시 적용"). 따라서 시행 전(6.30)에도 동일하게 0%다.
    #
    # 경과규정(P1)보다 **앞에 두는 것이 필수**다. P1의 경과규정 분기는 유주택 전체를
    # (다주택 포함) '종전 非규제 수도권 유주택 기준값 부재'로 보고 escalate 하기 때문에,
    # P0c를 뒤로 옮기면 경과규정에 해당하는 수도권 다주택이 0%를 받지 못하고 사람 검토로 샌다.
    # (변이 테스트로 확인: 순서를 바꾸면 회귀 GF-MULTI-01 실패, 포트폴리오 escalation 447→480)
    # 개념적으로도 옳다 — 경과규정은 6·30 지정으로 **바뀐 것**으로부터 보호하는 장치인데
    # 수도권 다주택은 지정 전후 모두 0%라 보호할 변화가 없다.
    if app.house_count >= 2 and is_capital_area(app.region_code):
        return _decided(LTV_MULTI, "MULTI_0", ReasonCode.LTV_MULTI_HOME_0)

    # P1. 경과규정. 종전규정 = 非규제 수도권 무주택 70%.
    grandfathered, gf_reason = is_grandfathered(app)
    if grandfathered:
        if is_owner(app):
            # 非규제 수도권 유주택 기준선이 원문에 없음 → 사람 검토
            # (수도권 다주택은 P0c에서 이미 0%로 확정되어 여기 도달하지 않는다)
            reason = (
                ReasonCode.MULTI_HOME_BASELINE_UNKNOWN if app.house_count >= 2
                else ReasonCode.OWNER_BASELINE_UNKNOWN
            )
            return LtvDecision(
                status=EvaluationStatus.NEEDS_HUMAN_REVIEW,
                grandfathering_applied=True,
                reason_codes=[gf_reason, reason],
                source_policy_ids=list(SOURCE_6_30),
            )
        return LtvDecision(
            status=EvaluationStatus.DECIDED,
            max_ltv=LTV_BASELINE,
            applicable_rule_id="NONREG_STD_70",
            grandfathering_applied=True,
            reason_codes=[gf_reason],
            source_policy_ids=list(SOURCE_6_30),
        )

    # P2. 지역상태 (시점 해석)
    status, _regulated_type = resolve_region_status(app.region_code, app.evaluation_date)
    if status == RegionStatus.NON_REGULATED:
        return _baseline_rule(app)

    # --- 이하 REGULATED ---
    # P3. 다주택
    if app.house_count >= 2:
        return _decided(LTV_MULTI, "MULTI_0", ReasonCode.LTV_MULTI_HOME_0)

    # P4. 유주택(비처분 1주택 이상)
    if app.house_count >= 1 and not app.disposal_condition_flag:
        return _decided(LTV_OWNER, "REG_OWNER_0", ReasonCode.LTV_OWNER_0)

    # (처분조건부 1주택 = 무주택 기준으로 계속)
    # P5. 생애최초
    if app.first_home_buyer:
        return _decided(LTV_FIRST_HOME, "REG_FIRSTHOME", ReasonCode.EXCEPTION_FIRST_HOME)

    # P6. 서민·실수요자
    if app.real_demand_flag:
        return _decided(LTV_REAL_DEMAND, "REG_REALDEMAND", ReasonCode.EXCEPTION_REAL_DEMAND)

    # P7. 무주택 일반 / 처분조건부 1주택
    return _decided(LTV_REGULATED_STANDARD, "REG_STD", ReasonCode.LTV_REGULATED_40)


def _decided(ltv: float, rule_id: str, reason: ReasonCode) -> LtvDecision:
    return LtvDecision(
        status=EvaluationStatus.DECIDED,
        max_ltv=ltv,
        applicable_rule_id=rule_id,
        reason_codes=[reason],
        source_policy_ids=list(SOURCE_6_30),
    )


def _baseline_rule(app: MortgageApplication) -> LtvDecision:
    """비규제지역/시행 전 기준선 (docs/05_RULE_SPEC.md §C-2).

    FAQ Q2 표의 非규제지역(수도권) 열은 주1)에 따라 **무주택자(처분조건부 1주택 포함) 기준**이다.
    유주택 기준값은 원문에 없으므로 추정하지 않고 사람 검토로 올린다(LOCKED §4).
    MOLIT 참고1의 "非규제(수도권 外) 유주택 60%"는 **수도권 外** 맥락이라 여기 적용되지 않는다.

    수도권 다주택은 P0c에서 이미 0%로 확정되므로 여기 도달하지 않는다. 여기 남는 유주택은
    ①비처분 1주택(수도권·비수도권 모두) ②비수도권 다주택 두 종류이며, 사유를 구분해 라벨링한다
    — 무엇이 미확정인지 세지 못하면 명세 공백을 좁힐 수 없기 때문이다.
    """
    if is_owner(app):
        reason = (
            ReasonCode.MULTI_HOME_BASELINE_UNKNOWN if app.house_count >= 2
            else ReasonCode.OWNER_BASELINE_UNKNOWN
        )
        return LtvDecision(
            status=EvaluationStatus.NEEDS_HUMAN_REVIEW,
            reason_codes=[reason],
        )
    return LtvDecision(
        status=EvaluationStatus.DECIDED,
        max_ltv=LTV_BASELINE,
        applicable_rule_id="NONREG_STD_70",
        reason_codes=[ReasonCode.LTV_BASELINE_70],
    )
