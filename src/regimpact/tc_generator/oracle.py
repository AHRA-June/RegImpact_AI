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
    - 수도권 판정: regions.py 의 CAPITAL_AREA_REGIONS 를 쓰지 않고 여기서 독립 집합으로 재기입.
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

# 지정 현황 — regions.py 를 import 하지 않고 **원문에서 독립 재기입**한다.
# 출처: docs/sources/raw/molit_press_20260630.txt p5 참고2 「투기과열지구 및 조정대상지역 현황」
# 같은 원문을 두 번 옮겨적는 것이 차등검증의 요점이다. 한쪽이 잘못 옮기면 불일치로 드러난다.
#
# ⚠️ 이전 버전은 "미등록 지역은 항상 非규제"라고 적었고 엔진도 같은 가정을 갖고 있어서,
#    강남을 비규제로 보는 결함이 양쪽에 동시에 있었는데도 일치율 100%가 나왔다.
#    같은 가정을 공유하면 차등검증은 아무것도 잡지 못한다.

# 서울 강남·서초·송파·용산 — 조정 '16.11.3, 투기과열 '17.8.3
_SEOUL_EARLY = frozenset({
    "SEOUL_GANGNAM", "SEOUL_SEOCHO", "SEOUL_SONGPA", "SEOUL_YONGSAN",
})
# 서울 나머지 21개구 — '25.10.16
_SEOUL_LATE = frozenset({
    "SEOUL_SEONGDONG", "SEOUL_MAPO", "SEOUL_GANGDONG", "SEOUL_YEONGDEUNGPO",
    "SEOUL_YANGCHEON", "SEOUL_DONGJAK", "SEOUL_GWANGJIN", "SEOUL_JUNG",
    "SEOUL_JONGNO", "SEOUL_SEODAEMUN", "SEOUL_GANGSEO", "SEOUL_NOWON",
    "SEOUL_SEONGBUK", "SEOUL_GURO", "SEOUL_DONGDAEMUN", "SEOUL_GWANAK",
    "SEOUL_EUNPYEONG", "SEOUL_JUNGNANG", "SEOUL_GEUMCHEON", "SEOUL_GANGBUK",
    "SEOUL_DOBONG",
})
# 경기 12곳 — '25.10.16
_GYEONGGI_LATE = frozenset({
    "SUWON_JANGAN", "SUWON_PALDAL", "SUWON_YEONGTONG",
    "SEONGNAM_SUJEONG", "SEONGNAM_JUNGWON", "SEONGNAM_BUNDANG",
    "ANYANG_DONGAN", "GWACHEON", "YONGIN_SUJI", "GWANGMYEONG",
    "HANAM", "UIWANG",
})
_D_EARLY_ADJ = date(2016, 11, 3)
_D_EARLY_SPEC = date(2017, 8, 3)
_D_LATE = date(2025, 10, 16)

# 비규제임이 확인된 지역(현황표 어느 열에도 없음). UNKNOWN 과 구분해 명시 등록.
_NON_REGULATED_KNOWN = frozenset({"SEJONG", "CHEONGJU"})

# 수도권(서울·인천·경기) — FSC p2 / FAQ Q1 ※ "다주택자는 수도권 內 ... 규제지역 여부와 무관".
# 광역 표기("SEOUL")는 시군구를 몰라도 수도권인 것은 확실하다.
_CAPITAL_AREA = (
    _SEOUL_EARLY | _SEOUL_LATE | _GYEONGGI_LATE | _SIX_THIRTY_REGIONS
    | {"SEOUL", "INCHEON"}
)

# 레지스트리에 있는(=규제상태를 판정할 수 있는) 지역 전체
_KNOWN_REGIONS = (
    _SEOUL_EARLY | _SEOUL_LATE | _GYEONGGI_LATE | _SIX_THIRTY_REGIONS
    | _NON_REGULATED_KNOWN
)

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
    """지역 규제상태를 regions.py 없이 독립 판정 (참고2 현황표)."""
    if region_code in _SIX_THIRTY_REGIONS:
        return as_of >= _REG_EFFECTIVE
    if region_code in _SEOUL_EARLY:
        return as_of >= _D_EARLY_ADJ
    if region_code in _SEOUL_LATE or region_code in _GYEONGGI_LATE:
        return as_of >= _D_LATE
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


def _baseline_gap_reason(app: MortgageApplication) -> str:
    """非규제 기준선 표(C-2)에 값이 없는 유주택의 사유 라벨 — §D.

    C-2는 주1)에 따라 무주택 기준이므로 유주택 값이 없다. 남는 두 종류를 구분한다:
    비처분 1주택(Q10 잔여 미결) / 비수도권 다주택(수도권 규칙 적용 밖).
    """
    return "MULTI_HOME_BASELINE_UNKNOWN" if app.house_count >= 2 else "OWNER_BASELINE_UNKNOWN"


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

    # P0c. 수도권 다주택 → 0% (지역 규제상태·시점·경과규정 무관) — §E P0c
    # 원문: "다주택자는 수도권 內 주택구입시 규제지역 여부와 무관하게 LTV 0% 적용"
    # 旣 마련된 규정이므로 6.30 이전에도 동일.
    # P1(경과규정)보다 앞에 와야 한다 — P1은 유주택 전체를 기준값 부재로 escalate 하므로
    # 뒤에 두면 경과규정 해당 수도권 다주택이 0%를 받지 못한다(회귀 GF-MULTI-01 이 고정).
    if app.house_count >= 2 and app.region_code in _CAPITAL_AREA:
        return ExpectedOutcome(
            status=EvaluationStatus.DECIDED,
            max_ltv=_LTV_MULTI,
            applicable_rule_id="MULTI_0",
            must_include_reasons=("LTV_MULTI_HOME_0",),
        )

    # P0d. 지역 미상 → 사람 검토 (§H P0d)
    # 레지스트리에 없으면 규제상태를 알 수 없다. 非규제로 간주하면 데이터 누락이
    # 관대한 판정으로 새어나간다. P0c 뒤인 이유: 수도권 다주택은 규제 여부와 무관하게
    # 0%라 시군구를 몰라도 판정이 선다.
    if app.region_code not in _KNOWN_REGIONS:
        return ExpectedOutcome(
            status=EvaluationStatus.NEEDS_HUMAN_REVIEW,
            must_include_reasons=("REGION_UNKNOWN",),
        )

    # P1. 경과규정
    gf_reason = _is_grandfathered(app)
    if gf_reason is not None:
        if _is_owner(app):
            # 非규제 수도권 유주택 기준선 부재 → escalation
            # (수도권 다주택은 P0c 에서 이미 확정되어 도달하지 않음 → 여기 남는 다주택은 비수도권)
            return ExpectedOutcome(
                status=EvaluationStatus.NEEDS_HUMAN_REVIEW,
                grandfathering_applied=True,
                must_include_reasons=(gf_reason, _baseline_gap_reason(app)),
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
                must_include_reasons=(_baseline_gap_reason(app),),
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
