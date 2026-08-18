"""독립 명세 오라클 (spec oracle) — 룰엔진 회귀의 '챌린저 모델'.

목적: `rule_engine.evaluate`가 확정 명세(docs/05_RULE_SPEC.md §H)를 정확히 구현했는지
**차등 검증(differential testing)** 하기 위한 독립 구현.

왜 별도 오라클인가?
    엔진이 스스로 만든 출력을 '기대값'으로 쓰면 회귀는 tautology(항상 통과)가 되어 의미가 없다.
    Model Risk / 모델검증 관점의 정석은 **독립적으로 유도된 기준(challenger)** 과 대조하는 것이다.
    이 오라클은 rule_engine·regions·grandfathering 을 **import 하지 않고**, 명세(05_RULE_SPEC)의
    표(§C)·우선순위(§E)·경과규정(§F)·지역 버전(regulatory_facts)을 독립 코드 경로로 재구현한다.
    → regions.py / grandfathering.py / rule_engine.py 어느 곳의 구현 오차든 disagreement로 드러난다.

독립성의 범위 (2026-08-18 갱신):
    - 지역상태 해석: **규제사실 데이터**(어느 지역이 언제부터 규제인가)는 `regions.REGISTRY` 하나를
      공유하고, **시점 해석 로직**은 여기서 독립 재구현한다(엔진은 구간 양끝을 검사, 오라클은
      "as_of 이하인 마지막 버전"을 고른다 — 알고리즘이 다르므로 경계 오차가 disagreement로 드러난다).
      전국 241개 지역표를 두 곳에 옮겨 적는 것은 검증가치가 아니라 전사 오류만 늘리므로,
      데이터 자체는 **공문 원문의 지역 수(서울 25 / 경기 12→15)와 대조하는 테스트**로 검증한다
      (`tests/test_regions.py`). `resolve_region_status`(엔진의 해석 함수)는 import 하지 않는다.
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

from ..models import EvaluationStatus, LoanPurpose, MortgageApplication, RegionStatus
from ..regions import REGISTRY, canonical_code   # 데이터만 공유 (해석 함수는 import 안 함)

# --- 명세 상수 (05_RULE_SPEC.md §C, §F, regulatory_facts.md — 엔진과 독립적으로 재기입) ---
_GF_CUTOFF = date(2026, 6, 30)          # 경과규정 경계 (<= 포함) — §F

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
def _region_state(region_code: str, as_of: date) -> RegionStatus:
    """지역 규제상태를 엔진의 해석 함수 없이 독립 판정.

    엔진(`regions.resolve_region_status`)은 각 버전의 [effective_from, effective_to] 양끝을
    검사한다. 오라클은 다른 전략을 쓴다 — 시작일이 as_of 이하인 버전 중 **가장 나중 것**을 고른다.
    데이터가 정상이면 두 방법은 같은 답을 내고, 경계 비교가 틀리면 서로 다른 답을 낸다.
    """
    region = REGISTRY.get(canonical_code(region_code))
    if region is None:
        return RegionStatus.UNKNOWN
    applicable = [
        v for v in region.versions
        if v.effective_from is None or as_of >= v.effective_from
    ]
    if not applicable:
        return RegionStatus.UNKNOWN
    latest = applicable[-1]
    # 마지막 버전이 이미 끝난 구간이면(뒤에 버전이 없는데 as_of가 그 뒤) 데이터 결손이다.
    if latest.effective_to is not None and as_of > latest.effective_to:
        return RegionStatus.UNKNOWN
    return latest.status


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
    state = _region_state(app.region_code, app.evaluation_date)
    if state is RegionStatus.UNKNOWN:
        return ExpectedOutcome(
            status=EvaluationStatus.NEEDS_HUMAN_REVIEW,
            must_include_reasons=("UNKNOWN_REGION",),
        )
    if state is RegionStatus.NON_REGULATED:
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
