"""Deterministic 주담대 LTV 룰엔진 (docs/05_RULE_SPEC.md §H 알고리즘).

LOCKED §4: 이 엔진의 규칙 '값·우선순위'는 사람이 확정한 명세(05_RULE_SPEC.md v1,
regulatory_facts.md)에서 온다. LLM이 규칙을 생성하지 않는다. 이 코드는 확정 명세의 구현이며,
LLM 출력(RegChange Extractor 등)을 검증하는 기준점(ground truth)이다.

우선순위(short-circuit): P0 스코프 → P0b 정책대출=Discovery → P1 경과규정 → P2 지역상태
→ P3 다주택 → P4 유주택 → P5 생애최초 → P6 서민실수요 → P7 일반.

지역상태는 `regions.REGISTRY`(전국 시·군·구, 시점 버전)에서 해석한다. 미등록 코드는
NON_REGULATED로 넘겨짚지 않고 NEEDS_HUMAN_REVIEW로 escalate 한다(regions.py 상단 참고).
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
from .regions import resolve_region_status

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

    # P1. 경과규정 (최우선). 종전규정 = 非규제 수도권 무주택 70%.
    grandfathered, gf_reason = is_grandfathered(app)
    if grandfathered:
        if is_owner(app):
            # 非규제 수도권 유주택 기준선이 원문에 없음 → 사람 검토
            return LtvDecision(
                status=EvaluationStatus.NEEDS_HUMAN_REVIEW,
                grandfathering_applied=True,
                reason_codes=[gf_reason, ReasonCode.OWNER_BASELINE_UNKNOWN],
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
    if status == RegionStatus.UNKNOWN:
        # 레지스트리에 없는 지역코드 = 데이터 품질 문제. 비규제로 넘겨짚지 않는다.
        # (넘겨짚었더니 규제지역인 강남이 70%로 판정된 사고가 있었다 — regions.py 참고)
        return LtvDecision(
            status=EvaluationStatus.NEEDS_HUMAN_REVIEW,
            reason_codes=[ReasonCode.UNKNOWN_REGION],
        )
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

    명세는 무주택 기준 70%만 정의. 유주택은 기준값 부재 → 사람 검토(정직한 escalation).
    """
    if is_owner(app):
        return LtvDecision(
            status=EvaluationStatus.NEEDS_HUMAN_REVIEW,
            reason_codes=[ReasonCode.OWNER_BASELINE_UNKNOWN],
        )
    return LtvDecision(
        status=EvaluationStatus.DECIDED,
        max_ltv=LTV_BASELINE,
        applicable_rule_id="NONREG_STD_70",
        reason_codes=[ReasonCode.LTV_BASELINE_70],
    )
