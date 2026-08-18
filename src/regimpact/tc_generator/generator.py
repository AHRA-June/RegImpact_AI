"""테스트케이스 생성기 (TC Generator).

브리프 §13.3 / metrics_spec §3: 룰엔진 회귀를 위한 경계·예외·충돌 케이스를 **체계적으로** 생성한다.
각 케이스는 (입력, 카테고리, 오라클 기대값)을 함께 들고 다니므로, 회귀 하네스가 엔진과 오라클을
차등 비교할 수 있다. 오라클 기대값은 이 파일이 아니라 `oracle.expected_outcome` 이 유도한다
(생성기는 '입력을 어떻게 훑을지'만 책임지고, '정답이 무엇인지'는 명세 오라클이 책임진다 = 관심사 분리).

카테고리(metrics_spec §3와 정렬):
    SCOPE          — P0/P0b 스코프·정책대출 분기
    BASELINE       — 非규제/시행 전/미등록 지역 기준선
    EXCEPTION      — 무주택 예외 계층(생애최초·서민실수요·처분조건부)
    BOUNDARY       — 경계값(경과규정 날짜 컷오프, 효력일, house_count 0/1/2)
    GRANDFATHERING — G1/G2/G3 경과규정
    CONFLICT       — 동시 충족·우선순위 충돌·escalation(유주택+생애최초 등)
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum
from typing import Optional

from ..models import LoanPurpose, MortgageApplication
from .oracle import ExpectedOutcome, expected_outcome

# 시나리오 기준 날짜
_AFTER = date(2026, 7, 2)     # 시행 후, 경과규정 미해당
_BEFORE = date(2026, 6, 15)   # 시행 전
_CUTOFF = date(2026, 6, 30)   # 경과규정 경계
_EFFECTIVE = date(2026, 7, 1)  # 규제 효력일
_REG = "GURI"                 # 6·30 규제지역


class Category(str, Enum):
    SCOPE = "SCOPE"
    BASELINE = "BASELINE"
    EXCEPTION = "EXCEPTION"
    BOUNDARY = "BOUNDARY"
    GRANDFATHERING = "GRANDFATHERING"
    CONFLICT = "CONFLICT"


@dataclass(frozen=True)
class GeneratedCase:
    """생성된 회귀 테스트케이스 1건."""
    case_id: str
    category: Category
    description: str
    app: MortgageApplication
    expected: ExpectedOutcome
    spec_note: Optional[str] = None   # 알려진 명세 모호성·주의사항(있으면)


def _app(**kw) -> MortgageApplication:
    base = dict(region_code=_REG, evaluation_date=_AFTER)
    base.update(kw)
    return MortgageApplication(**base)


def _case(
    case_id: str,
    category: Category,
    description: str,
    app: MortgageApplication,
    spec_note: Optional[str] = None,
) -> GeneratedCase:
    """오라클이 기대값을 채우도록 케이스를 조립한다(정답은 명세 오라클에서만 온다)."""
    return GeneratedCase(
        case_id=case_id,
        category=category,
        description=description,
        app=app,
        expected=expected_outcome(app),
        spec_note=spec_note,
    )


# ---------------------------------------------------------------------------
# 카테고리별 생성기
# ---------------------------------------------------------------------------
def scope_cases() -> list[GeneratedCase]:
    return [
        _case("SCOPE-01", Category.SCOPE,
              "주택구입목적 아님 → OUT_OF_SCOPE",
              _app(loan_purpose=LoanPurpose.OTHER)),
        _case("SCOPE-02", Category.SCOPE,
              "정책대출 → Discovery (다른 조건 무시)",
              _app(policy_mortgage_flag=True, first_home_buyer=True, house_count=0)),
        _case("SCOPE-03", Category.SCOPE,
              "정책대출 + 다주택 → 여전히 Discovery",
              _app(policy_mortgage_flag=True, house_count=3)),
    ]


def baseline_cases() -> list[GeneratedCase]:
    return [
        _case("BASE-01", Category.BASELINE,
              "시행 전(6.15) 규제지역 코드 → 아직 非규제, 무주택 70%",
              _app(evaluation_date=_BEFORE, house_count=0)),
        _case("BASE-02", Category.BASELINE,
              "미등록 지역 → 非규제 기준선 70%",
              _app(region_code="SEOUL_GANGNAM", house_count=0)),
        _case("BASE-03", Category.BASELINE,
              "非규제 비처분 1주택 → 기준값 부재 → NEEDS_HUMAN_REVIEW",
              _app(region_code="SEOUL_GANGNAM", house_count=1),
              spec_note="Q10 잔여 미결: FAQ Q2 非규제(수도권) 열은 주1) 무주택 기준이라 "
                        "비처분 1주택 값이 없다. 추정 금지(LOCKED §4) → escalation."),
        _case("BASE-04", Category.BASELINE,
              "수도권 다주택 · 시행 전(非규제) → 0% (규제 여부 무관 규칙)",
              _app(evaluation_date=_BEFORE, house_count=2),
              spec_note="FSC p2 / FAQ Q1 ※ '다주택자는 수도권 內 주택구입시 규제지역 여부와 "
                        "무관하게 LTV 0% 적용'. 旣 마련된 규정이라 시행 전에도 동일."),
        _case("BASE-05", Category.BASELINE,
              "비수도권 다주택 · 非규제 → 기준값 부재 → NEEDS_HUMAN_REVIEW",
              _app(region_code="CHEONGJU", house_count=2),
              spec_note="수도권 0% 규칙은 수도권 限. 비수도권 非규제 다주택 값은 원문에 없다."),
    ]


def exception_cases() -> list[GeneratedCase]:
    return [
        _case("EXC-01", Category.EXCEPTION,
              "규제지역 무주택 일반 → 40%",
              _app(house_count=0)),
        _case("EXC-02", Category.EXCEPTION,
              "규제지역 생애최초 → 70%",
              _app(house_count=0, first_home_buyer=True)),
        _case("EXC-03", Category.EXCEPTION,
              "규제지역 서민·실수요 → 60%",
              _app(house_count=0, real_demand_flag=True)),
        _case("EXC-04", Category.EXCEPTION,
              "처분조건부 1주택 = 무주택 기준 → 40%",
              _app(house_count=1, disposal_condition_flag=True)),
        _case("EXC-05", Category.EXCEPTION,
              "처분조건부 1주택 + 생애최초 → 70%",
              _app(house_count=1, disposal_condition_flag=True, first_home_buyer=True)),
    ]


def boundary_cases() -> list[GeneratedCase]:
    """경계값: 효력일·경과규정 컷오프의 ±1일, house_count 0/1/2."""
    cases: list[GeneratedCase] = []

    # 효력일 경계: 6.30(전일) 非규제 vs 7.1(효력일) 규제
    cases.append(_case(
        "BND-EFF-01", Category.BOUNDARY,
        "효력일 전일(6.30) 평가 → 아직 非규제 70%",
        _app(evaluation_date=_CUTOFF, house_count=0)))
    cases.append(_case(
        "BND-EFF-02", Category.BOUNDARY,
        "효력일 당일(7.1) 평가 → 규제 40%",
        _app(evaluation_date=_EFFECTIVE, house_count=0)))

    # 경과규정 접수일(G1) 컷오프 ±1일 — 판정이 갈리는 지점
    for label, d in (("cutoff", _CUTOFF),
                     ("cutoff-1", _CUTOFF - timedelta(days=1)),
                     ("cutoff+1", _CUTOFF + timedelta(days=1))):
        cases.append(_case(
            f"BND-G1-{label}", Category.BOUNDARY,
            f"전산 접수일 {d.isoformat()} ({label}) → 경과규정 경계",
            _app(house_count=0, application_accepted_at=d)))

    # house_count 경계 0/1/2 (규제지역, 비처분)
    for hc in (0, 1, 2):
        cases.append(_case(
            f"BND-HC-{hc}", Category.BOUNDARY,
            f"규제지역 house_count={hc} (비처분) 경계",
            _app(house_count=hc)))

    return cases


def grandfathering_cases() -> list[GeneratedCase]:
    return [
        _case("GF-G1-01", Category.GRANDFATHERING,
              "G1 전산 접수 6.30 → 종전규정 70%",
              _app(house_count=0, application_accepted_at=_CUTOFF)),
        _case("GF-G1-02", Category.GRANDFATHERING,
              "G1 전산 접수 7.1 → 신규규정 40%",
              _app(house_count=0, application_accepted_at=_EFFECTIVE)),
        _case("GF-G2-01", Category.GRANDFATHERING,
              "G2 계약 6.29 + 계약금 → 종전규정 (접수 7.1이어도)",
              _app(house_count=0, contract_signed_at=date(2026, 6, 29),
                   downpayment_paid_at=date(2026, 6, 29),
                   application_accepted_at=_EFFECTIVE)),
        _case("GF-G2-02", Category.GRANDFATHERING,
              "G2 계약만 있고 계약금 미납 → 경과규정 불인정 40%",
              _app(house_count=0, contract_signed_at=date(2026, 6, 29))),
        _case("GF-G3-01", Category.GRANDFATHERING,
              "G3 토허제 신청 6.30 → 이후 계약해도 종전규정",
              _app(house_count=0, land_permit_target=True,
                   land_permit_applied_at=_CUTOFF,
                   contract_signed_at=date(2026, 7, 10))),
        _case("GF-G3-02", Category.GRANDFATHERING,
              "G3 토허제 대상 아님 → 신청일 있어도 경과규정 불인정",
              _app(house_count=0, land_permit_target=False,
                   land_permit_applied_at=_CUTOFF)),
        _case("GF-MULTI-01", Category.GRANDFATHERING,
              "수도권 다주택 + 경과규정 해당 → 여전히 0% (보호할 변화가 없음)",
              _app(house_count=2, application_accepted_at=_CUTOFF),
              spec_note="경과규정은 6·30 지정으로 바뀐 것으로부터 보호하는 장치인데, 수도권 "
                        "다주택은 지정 전후 모두 0%라 되돌릴 값이 없다. 이 케이스가 P0c의 "
                        "우선순위 위치(경과규정보다 앞)를 고정한다 — 뒤로 옮기면 실패."),
        _case("GF-OWNER-01", Category.GRANDFATHERING,
              "비처분 1주택 + 경과규정 해당 → 종전값 부재로 NEEDS_HUMAN_REVIEW",
              _app(house_count=1, application_accepted_at=_CUTOFF),
              spec_note="Q10 잔여 미결 — 경과규정이 되돌릴 '종전 非규제 수도권 유주택' 값이 없다."),
    ]


def conflict_cases() -> list[GeneratedCase]:
    """동시 충족·우선순위 충돌·escalation. 정답은 §H 우선순위(엔진 구현 기준)로 정한다."""
    return [
        _case("CFL-01", Category.CONFLICT,
              "생애최초 + 서민실수요 동시 → 상위(P5) 생애최초 70%",
              _app(house_count=0, first_home_buyer=True, real_demand_flag=True)),
        _case("CFL-02", Category.CONFLICT,
              "경과규정 + 생애최초 동시 → 경과규정(P1) 우선, 종전 70%로 수렴",
              _app(house_count=0, first_home_buyer=True,
                   application_accepted_at=_CUTOFF)),
        _case("CFL-03", Category.CONFLICT,
              "경과규정 + 유주택(다주택) → 종전 유주택 기준값 부재 → escalation",
              _app(house_count=2, application_accepted_at=date(2026, 6, 20))),
        _case(
            "CFL-04", Category.CONFLICT,
            "유주택(비처분 1주택) + 생애최초: §H(P4) short-circuit → 0%",
            _app(house_count=1, disposal_condition_flag=False, first_home_buyer=True),
            spec_note=(
                "알려진 명세 모호성: §E 주석은 '유주택+생애최초=논리상 불가, 데이터 충돌 시 "
                "NEEDS_HUMAN_REVIEW'라 하나, §H(엔진 구현 기준) 의사코드는 P4에서 0%로 "
                "short-circuit 한다. 여기서는 권위 기준(§H)을 채택. 03_OPEN_QUESTIONS 참조."),
        ),
        _case("CFL-05", Category.CONFLICT,
              "다주택 + 서민실수요 → 다주택(P3)이 우선 0%",
              _app(house_count=2, real_demand_flag=True)),
    ]


# ---------------------------------------------------------------------------
# 통합 생성
# ---------------------------------------------------------------------------
def generate_all() -> list[GeneratedCase]:
    """전 카테고리 회귀 케이스를 생성한다. case_id 는 안정적(재현 가능)."""
    cases: list[GeneratedCase] = []
    cases += scope_cases()
    cases += baseline_cases()
    cases += exception_cases()
    cases += boundary_cases()
    cases += grandfathering_cases()
    cases += conflict_cases()

    # case_id 유일성 보장 (전사 오류 방지)
    seen: set[str] = set()
    for c in cases:
        if c.case_id in seen:
            raise ValueError(f"중복 case_id: {c.case_id}")
        seen.add(c.case_id)
    return cases
