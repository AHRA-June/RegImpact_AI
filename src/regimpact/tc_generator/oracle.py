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

권위 기준: §H 의사코드가 "엔진 구현의 기준"으로 명시되어 있으므로 오라클도 §H 를 따른다.
**Q8 해소(2026-08-18):** §E-139('유주택+생애최초 → NEEDS_HUMAN_REVIEW')는 §H 와 충돌하는
우선순위 규칙이 아니라 한 층 위의 **입력 유효성 규칙**이다(§E-138 이 '처분조건부 1주택+생애최초'를
유효 조합으로 명시하므로 §E 의 "유주택"은 is_owner() 의미). 따라서 규칙표 상단에 입력 무결성 규칙을
두고, 그 아래를 §H 그대로 유지한다 — 둘 다 참이다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Callable, Optional

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
_LTV_NONREG_OWNER = 0.60   # 非규제(수도권 外) 유주택 — MOLIT 참고1, Q9 확정


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
# ---------------------------------------------------------------------------
# 선언적 규칙표 + 범용 해석기 (엔진의 명령형 분기와 **구조적으로** 다른 경로)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class _Ctx:
    """판정에 쓰이는 파생 사실. 규칙표는 이 컨텍스트만 본다."""
    home_purchase: bool
    policy_loan: bool
    region: RegionStatus
    capital_area: bool
    houses: int          # 보유 주택 수 (무결성 검사용)
    disposal: bool       # 처분조건부 1주택 플래그
    multi: bool          # 2주택 이상
    owner: bool          # 유주택(비처분 1주택 이상, 다주택 포함)
    first_home: bool
    real_demand: bool

    @property
    def regulated(self) -> bool:
        return self.region is RegionStatus.REGULATED


@dataclass(frozen=True)
class _Rule:
    rule_id: Optional[str]
    cond: "Callable[[_Ctx], bool]"
    status: EvaluationStatus
    max_ltv: Optional[float] = None
    reasons: tuple[str, ...] = ()


# 위에서부터 첫 매치가 이긴다 = §E 우선순위. 조건은 순서에 기대지 않고 명시적으로 쓴다.
_RULE_TABLE: tuple[_Rule, ...] = (
    # P0 / P0b — 스코프
    _Rule(None, lambda c: not c.home_purchase, EvaluationStatus.OUT_OF_SCOPE,
          reasons=("OUT_OF_SCOPE_PRODUCT",)),
    _Rule(None, lambda c: c.policy_loan, EvaluationStatus.DISCOVERY,
          reasons=("DISCOVERY_POLICY_LOAN",)),
    # P0c — 입력 무결성(§E-139). 엔진의 validation.py 를 import 하지 않고 조건을 직접 쓴다
    #        (판정 구현 독립성 유지). 유주택 AND 생애최초 = 논리상 불가.
    _Rule(None, lambda c: c.houses < 0,
          EvaluationStatus.NEEDS_HUMAN_REVIEW, reasons=("INVALID_HOUSE_COUNT",)),
    _Rule(None, lambda c: c.owner and c.first_home,
          EvaluationStatus.NEEDS_HUMAN_REVIEW, reasons=("CONTRADICTION_OWNER_FIRST_HOME",)),
    _Rule(None, lambda c: c.disposal and c.houses == 0,
          EvaluationStatus.NEEDS_HUMAN_REVIEW, reasons=("CONTRADICTION_DISPOSAL_WITHOUT_HOUSE",)),
    _Rule(None, lambda c: c.disposal and c.houses >= 2,
          EvaluationStatus.NEEDS_HUMAN_REVIEW, reasons=("CONTRADICTION_DISPOSAL_MULTI_HOUSE",)),
    # P2 — 지역 미등록은 추측하지 않는다
    _Rule(None, lambda c: c.region is RegionStatus.UNKNOWN,
          EvaluationStatus.NEEDS_HUMAN_REVIEW, reasons=("UNKNOWN_REGION",)),
    # P3 — 다주택. 규제지역 또는 수도권이면 규제 여부 무관 0% (FSC p2 C06 / §C-1b R6)
    _Rule("MULTI_0", lambda c: c.multi and (c.regulated or c.capital_area),
          EvaluationStatus.DECIDED, _LTV_MULTI, ("LTV_MULTI_HOME_0",)),
    _Rule("NONREG_OWNER_60", lambda c: c.multi and not c.regulated and not c.capital_area,
          EvaluationStatus.DECIDED, _LTV_NONREG_OWNER, ("LTV_NONREG_OWNER_60",)),
    # P4 — 유주택(비처분 1주택)
    _Rule("REG_OWNER_0", lambda c: c.owner and c.regulated,
          EvaluationStatus.DECIDED, _LTV_OWNER, ("LTV_OWNER_0",)),
    _Rule("NONREG_OWNER_60", lambda c: c.owner and not c.regulated and not c.capital_area,
          EvaluationStatus.DECIDED, _LTV_NONREG_OWNER, ("LTV_NONREG_OWNER_60",)),
    # 수도권 비규제 유주택 — 원문은 '수도권 外'만 60%로 명시 → 근거 부재
    _Rule(None, lambda c: c.owner and not c.regulated and c.capital_area,
          EvaluationStatus.NEEDS_HUMAN_REVIEW, reasons=("OWNER_BASELINE_UNKNOWN",)),
    # P4b — 무주택(처분조건부 1주택 포함) 비규제 기준선
    _Rule("NONREG_STD_70", lambda c: not c.owner and not c.regulated,
          EvaluationStatus.DECIDED, _LTV_BASELINE, ("LTV_BASELINE_70",)),
    # P5~P7 — 규제지역 무주택 계층
    _Rule("REG_FIRSTHOME", lambda c: c.first_home,
          EvaluationStatus.DECIDED, _LTV_FIRST_HOME, ("EXCEPTION_FIRST_HOME",)),
    _Rule("REG_REALDEMAND", lambda c: c.real_demand,
          EvaluationStatus.DECIDED, _LTV_REAL_DEMAND, ("EXCEPTION_REAL_DEMAND",)),
    _Rule("REG_STD", lambda c: True,
          EvaluationStatus.DECIDED, _LTV_REGULATED_STD, ("LTV_REGULATED_40",)),
)


def _context(app: MortgageApplication, as_of: date) -> _Ctx:
    region = _region_state(app.region_code, as_of)
    entry = REGISTRY.get(canonical_code(app.region_code))
    return _Ctx(
        home_purchase=app.loan_purpose == LoanPurpose.HOME_PURCHASE,
        policy_loan=app.policy_mortgage_flag,
        region=region,
        capital_area=bool(entry and entry.capital_area),
        houses=app.house_count,
        disposal=app.disposal_condition_flag,
        multi=app.house_count >= 2,
        owner=_is_owner(app),
        first_home=app.first_home_buyer,
        real_demand=app.real_demand_flag,
    )


def _apply(ctx: _Ctx) -> _Rule:
    """규칙표를 위에서부터 훑어 첫 매치를 고른다(범용 해석기)."""
    for rule in _RULE_TABLE:
        if rule.cond(ctx):
            return rule
    raise AssertionError("규칙표가 모든 경우를 덮지 못함 — 마지막 규칙은 항상 참이어야 한다")


def expected_outcome(app: MortgageApplication) -> ExpectedOutcome:
    """명세(05_RULE_SPEC §H)에서 유도한 기대 판정. rule_engine 을 import 하지 않는다.

    경과규정(§F)이 성립하면 **종전규정** — 즉 컷오프(2026-06-30) 시점의 지역상태로 —
    같은 규칙표를 다시 평가한다. 종전규정을 70%로 고정하지 않는 이유는 지역마다 다르기 때문이다
    (서울 25구·경기 12곳은 6·30 이전에도 이미 규제지역이었다).
    """
    gf_reason = _is_grandfathered(app)
    as_of = _GF_CUTOFF if gf_reason is not None else app.evaluation_date

    ctx = _context(app, as_of)
    # 스코프·정책대출은 경과규정보다 앞선다(P0/P0b) — 규칙표 상단이 그 순서를 담고 있다.
    rule = _apply(ctx)

    # 스코프 밖·Discovery·입력 모순은 '경과규정이 적용된 판정'이 아니다.
    contradiction = any(r.startswith(("CONTRADICTION_", "INVALID_")) for r in rule.reasons)
    grandfathered = (gf_reason is not None and not contradiction and rule.status not in (
        EvaluationStatus.OUT_OF_SCOPE, EvaluationStatus.DISCOVERY))
    reasons = (gf_reason, *rule.reasons) if grandfathered else rule.reasons

    return ExpectedOutcome(
        status=rule.status,
        max_ltv=rule.max_ltv,
        applicable_rule_id=rule.rule_id,
        grandfathering_applied=grandfathered,
        must_include_reasons=tuple(reasons),
    )
