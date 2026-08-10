"""독립 명세 오라클 (spec oracle) — 룰엔진 회귀의 '챌린저 모델'.

목적: `rule_engine.evaluate`가 확정 명세(docs/05_RULE_SPEC.md §H)를 정확히 구현했는지
**차등 검증(differential testing)** 하기 위한 독립 구현.

왜 별도 오라클인가?
    엔진이 스스로 만든 출력을 '기대값'으로 쓰면 회귀는 tautology(항상 통과)가 되어 의미가 없다.
    Model Risk / 모델검증 관점의 정석은 **독립적으로 유도된 기준(challenger)** 과 대조하는 것이다.
    이 오라클은 rule_engine·regions·grandfathering 을 **import 하지 않고**, 명세(05_RULE_SPEC)의
    표(§C)·우선순위(§E)·경과규정(§F)·지역 버전(regulatory_facts)을 독립 코드 경로로 재구현한다.
    → regions.py / grandfathering.py / rule_engine.py 어느 곳의 구현 오차든 disagreement로 드러난다.

독립성의 범위:
    - 지역상태 해석: regions.py 를 쓰지 않고 여기서 날짜 비교로 직접 판정.
    - 경과규정: grandfathering.py 를 쓰지 않고 여기서 G1/G2/G3 를 직접 판정.
    - 판정 로직: 명령형 short-circuit(엔진)과 달리, 우선순위 규칙을 '데이터 표'로 선언하고
      작은 범용 해석기로 평가한다(구조적 독립 → 전사 오류가 상관되지 않음).

권위 기준: §H 의사코드가 "엔진 구현의 기준"으로 명시(05_RULE_SPEC.md L154, L194)되어 있으므로
오라클도 §H 를 따른다. §E 주석의 '유주택+생애최초 충돌 → NEEDS_HUMAN_REVIEW'는 §H(P4 short-circuit)와
상충하는 알려진 모호성이며, ConflictCase 로 표면화하되 판정 권위는 §H 로 둔다(README·OPEN_QUESTIONS 참고).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from ..models import EvaluationStatus, LoanPurpose, MortgageApplication

# --- 명세 상수 (05_RULE_SPEC.md §C, §F, regulatory_facts.md — 엔진과 독립적으로 재기입) ---
_GF_CUTOFF = date(2026, 6, 30)          # 경과규정 경계 (<= 포함) — §F
_REG_EFFECTIVE = date(2026, 7, 1)       # 규제 효력일 — regulatory_facts C02/C03
_SIX_THIRTY_REGIONS = frozenset({"GURI", "YONGIN_GIHEUNG", "HWASEONG_DONGTAN"})

_LTV_REGULATED_STD = 0.40
_LTV_FIRST_HOME = 0.70
_LTV_REAL_DEMAND = 0.60
_LTV_OWNER = 0.00
_LTV_MULTI = 0.00
_LTV_BASELINE = 0.70


@dataclass(frozen=True)
class ExpectedOutcome:
    """오라클이 명세에서 유도한 기대 판정. 엔진 출력과 비교되는 기준값."""
    status: EvaluationStatus
    max_ltv: Optional[float] = None
    applicable_rule_id: Optional[str] = None
    grandfathering_applied: bool = False
    # 판정 근거로 반드시 포함돼야 하는 reason_code 라벨(부분 계약 검증용).
    must_include_reasons: tuple[str, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# 독립 재구현: 지역상태 · 경과규정 · 소유상태
# ---------------------------------------------------------------------------
def _region_is_regulated(region_code: str, as_of: date) -> bool:
    """지역 규제상태를 regions.py 없이 독립 판정 (regulatory_facts C02/C03).

    6·30 신규지정 3개 지역은 효력일(7.1)부터 REGULATED, 그 전엔 非규제.
    그 외(미등록) 지역은 이 시나리오에서 항상 非규제로 간주.
    """
    if region_code in _SIX_THIRTY_REGIONS and as_of >= _REG_EFFECTIVE:
        return True
    return False


def _is_grandfathered(app: MortgageApplication) -> Optional[str]:
    """경과규정 해당 시 근거 reason_code, 아니면 None (grandfathering.py 없이 독립 판정, §F)."""
    # G1. 전산 접수 완료 <= 6.30
    if app.application_accepted_at is not None and app.application_accepted_at <= _GF_CUTOFF:
        return "GRANDFATHERED_ACCEPTED_OR_CONTRACT"
    # G2. 계약 체결 <= 6.30 AND 계약금 납부 증빙 존재
    if (
        app.contract_signed_at is not None
        and app.contract_signed_at <= _GF_CUTOFF
        and app.downpayment_paid_at is not None
    ):
        return "GRANDFATHERED_ACCEPTED_OR_CONTRACT"
    # G3. 토허제 대상 + 허가 신청 접수 <= 6.30
    if (
        app.land_permit_target
        and app.land_permit_applied_at is not None
        and app.land_permit_applied_at <= _GF_CUTOFF
    ):
        return "GRANDFATHERED_LAND_PERMIT"
    return None


def _is_owner(app: MortgageApplication) -> bool:
    """유주택자(무주택·처분조건부 1주택이 아닌 자). 다주택 포함. §E P3/P4."""
    if app.house_count >= 2:
        return True
    if app.house_count >= 1 and not app.disposal_condition_flag:
        return True
    return False


# ---------------------------------------------------------------------------
# 오라클 판정 (§H 우선순위 P0~P7 — 선언적 재구현)
# ---------------------------------------------------------------------------
def expected_outcome(app: MortgageApplication) -> ExpectedOutcome:
    """명세(05_RULE_SPEC §H)에서 유도한 기대 판정. rule_engine 을 import 하지 않는다."""

    # P0. 스코프
    if app.loan_purpose != LoanPurpose.HOME_PURCHASE:
        return ExpectedOutcome(
            status=EvaluationStatus.OUT_OF_SCOPE,
            must_include_reasons=("OUT_OF_SCOPE_PRODUCT",),
        )

    # P0b. 정책대출 → Discovery
    if app.policy_mortgage_flag:
        return ExpectedOutcome(
            status=EvaluationStatus.DISCOVERY,
            must_include_reasons=("DISCOVERY_POLICY_LOAN",),
        )

    # P1. 경과규정 (최우선)
    gf_reason = _is_grandfathered(app)
    if gf_reason is not None:
        if _is_owner(app):
            # 非규제 수도권 유주택 기준선 부재 → escalation
            return ExpectedOutcome(
                status=EvaluationStatus.NEEDS_HUMAN_REVIEW,
                grandfathering_applied=True,
                must_include_reasons=(gf_reason, "OWNER_BASELINE_UNKNOWN"),
            )
        return ExpectedOutcome(
            status=EvaluationStatus.DECIDED,
            max_ltv=_LTV_BASELINE,
            applicable_rule_id="NONREG_STD_70",
            grandfathering_applied=True,
            must_include_reasons=(gf_reason,),
        )

    # P2. 지역상태
    if not _region_is_regulated(app.region_code, app.evaluation_date):
        # 기준선 표 C-2: 무주택 70%, 유주택 기준값 부재 → escalation
        if _is_owner(app):
            return ExpectedOutcome(
                status=EvaluationStatus.NEEDS_HUMAN_REVIEW,
                must_include_reasons=("OWNER_BASELINE_UNKNOWN",),
            )
        return ExpectedOutcome(
            status=EvaluationStatus.DECIDED,
            max_ltv=_LTV_BASELINE,
            applicable_rule_id="NONREG_STD_70",
            must_include_reasons=("LTV_BASELINE_70",),
        )

    # --- 이하 REGULATED ---
    # P3. 다주택
    if app.house_count >= 2:
        return ExpectedOutcome(
            status=EvaluationStatus.DECIDED,
            max_ltv=_LTV_MULTI,
            applicable_rule_id="MULTI_0",
            must_include_reasons=("LTV_MULTI_HOME_0",),
        )

    # P4. 유주택(비처분 1주택 이상)
    if app.house_count >= 1 and not app.disposal_condition_flag:
        return ExpectedOutcome(
            status=EvaluationStatus.DECIDED,
            max_ltv=_LTV_OWNER,
            applicable_rule_id="REG_OWNER_0",
            must_include_reasons=("LTV_OWNER_0",),
        )

    # (처분조건부 1주택 = 무주택 기준으로 계속)
    # P5. 생애최초
    if app.first_home_buyer:
        return ExpectedOutcome(
            status=EvaluationStatus.DECIDED,
            max_ltv=_LTV_FIRST_HOME,
            applicable_rule_id="REG_FIRSTHOME",
            must_include_reasons=("EXCEPTION_FIRST_HOME",),
        )

    # P6. 서민·실수요자
    if app.real_demand_flag:
        return ExpectedOutcome(
            status=EvaluationStatus.DECIDED,
            max_ltv=_LTV_REAL_DEMAND,
            applicable_rule_id="REG_REALDEMAND",
            must_include_reasons=("EXCEPTION_REAL_DEMAND",),
        )

    # P7. 무주택 일반 / 처분조건부 1주택
    return ExpectedOutcome(
        status=EvaluationStatus.DECIDED,
        max_ltv=_LTV_REGULATED_STD,
        applicable_rule_id="REG_STD",
        must_include_reasons=("LTV_REGULATED_40",),
    )
