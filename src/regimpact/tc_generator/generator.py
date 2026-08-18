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
    REGION         — 전국 지역 레지스트리(기존 규제지역·비규제·미등록 코드·지정일 경계)
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
_REG = "GYEONGGI_GURI"                    # 6·30 신규 지정 규제지역
_SEOUL_GANGNAM = "SEOUL_GANGNAM"          # 6·30 이전부터 이미 규제(투기과열 '17.8.3)
_SEOUL_NOWON = "SEOUL_NOWON"              # '25.10.16 지정
_NONREG = "ULSAN_NAM"                     # 비규제(비수도권)
_WIDE_2025 = date(2025, 10, 16)           # 서울 21구·경기 12곳 지정일


class Category(str, Enum):
    SCOPE = "SCOPE"
    BASELINE = "BASELINE"
    EXCEPTION = "EXCEPTION"
    BOUNDARY = "BOUNDARY"
    REGION = "REGION"
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
              "6·30 신규지정 지역, 시행 전(6.15) → 아직 非규제, 무주택 70%",
              _app(evaluation_date=_BEFORE, house_count=0)),
        _case("BASE-02", Category.BASELINE,
              "비규제 지역(울산 남구) 무주택 → 기준선 70%",
              _app(region_code=_NONREG, house_count=0)),
        _case("BASE-03", Category.BASELINE,
              "비규제 유주택 → 기준값 부재 → NEEDS_HUMAN_REVIEW",
              _app(region_code=_NONREG, house_count=1)),
    ]


def region_cases() -> list[GeneratedCase]:
    """전국 지역 레지스트리 회귀 — '미등록 → 조용히 非규제' 사고의 재발 방지선.

    2026-08-18 발견: 레지스트리에 3개 지역만 있고 나머지는 기본값 非규제였던 탓에,
    이미 투기과열지구인 서울 강남구가 비규제 기준선 70%로 판정됐다. 아래 케이스들이 그 회귀선이다.
    """
    return [
        _case("RGN-01", Category.REGION,
              "서울 강남구(투기과열 '17.8.3~) 무주택 → 규제 40%. 6·30 이전부터 이미 규제지역",
              _app(region_code=_SEOUL_GANGNAM, house_count=0)),
        _case("RGN-02", Category.REGION,
              "서울 강남구, 6·30 시행 전(6.15) 평가여도 이미 규제 → 40% (6·30과 무관)",
              _app(region_code=_SEOUL_GANGNAM, evaluation_date=_BEFORE, house_count=0)),
        _case("RGN-03", Category.REGION,
              "서울 중랑구('25.10.16 지정) 무주택 → 규제 40%",
              _app(region_code="SEOUL_JUNGNANG", house_count=0)),
        _case("RGN-04", Category.REGION,
              "서울 노원구, 지정 전일('25.10.15) → 아직 非규제 70%",
              _app(region_code=_SEOUL_NOWON,
                   evaluation_date=_WIDE_2025 - timedelta(days=1), house_count=0)),
        _case("RGN-05", Category.REGION,
              "서울 노원구, 지정 당일('25.10.16) → 규제 40%",
              _app(region_code=_SEOUL_NOWON, evaluation_date=_WIDE_2025, house_count=0)),
        _case("RGN-06", Category.REGION,
              "울산 남구(비수도권 비규제) 무주택 → 70%",
              _app(region_code=_NONREG, house_count=0)),
        _case("RGN-07", Category.REGION,
              "제주시(비규제) 생애최초 → 규제지역이 아니므로 기준선 70%",
              _app(region_code="JEJU_JEJU", house_count=0, first_home_buyer=True)),
        _case("RGN-08", Category.REGION,
              "인천 연수구(수도권 비규제) 무주택 → 70%",
              _app(region_code="INCHEON_YEONSU", house_count=0)),
        _case("RGN-09", Category.REGION,
              "레지스트리 미등록 코드 → 非규제로 넘겨짚지 않고 NEEDS_HUMAN_REVIEW",
              _app(region_code="ATLANTIS_XX", house_count=0)),
        _case("RGN-10", Category.REGION,
              "구(舊) 코드 'GURI' 별칭 → 현행 GYEONGGI_GURI 로 정규화되어 규제 40%",
              _app(region_code="GURI", house_count=0)),
        _case("RGN-11", Category.REGION,
              "경기 과천시('25.10.16 지정) 다주택 → 규제지역 0%",
              _app(region_code="GYEONGGI_GWACHEON", house_count=2)),
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
        _case(
            "CFL-06", Category.CONFLICT,
            "수도권 비규제(인천 연수) 다주택: §H는 escalation, 원문 C06은 0% — 미결",
            _app(region_code="INCHEON_YEONSU", house_count=2),
            spec_note=(
                "알려진 명세 상충: FSC 보도자료 p2 원문은 '다주택자는 수도권 內 주택구입시 규제지역 "
                "여부와 무관하게 LTV 0% 적용'이라 하고 05_RULE_SPEC §C-1b(R6)도 '다주택·수도권"
                "(규제 무관) 0%'로 적고 있으나, §H(엔진 구현 기준) 의사코드는 P3(다주택)를 P2 지역분기 "
                "**뒤**에 두어 비규제 경로에서는 도달하지 못한다. 전국 지역 레지스트리가 생기면서 "
                "비로소 도달 가능해진 경로다. 권위 기준(§H)을 채택해 현재는 escalation. "
                "03_OPEN_QUESTIONS Q10 참조."),
        ),
        _case(
            "CFL-07", Category.CONFLICT,
            "비수도권 비규제(울산) 유주택: §C-2에 기준값 없음 → escalation. 원문엔 60% 서술 — 미결",
            _app(region_code="ULSAN_NAM", house_count=1),
            spec_note=(
                "알려진 명세 공백: MOLIT 보도자료 참고1 표에 '非규제지역(수도권 外) 무주택(처분조건부 "
                "1주택) 70% / 유주택 60%'가 있으나, 05_RULE_SPEC §C-2는 무주택 70%만 확정했고 "
                "'수도권 外 유주택 60%는 다른 맥락이니 혼동 금지'라고 명시적으로 유보했다. "
                "LOCKED §4(규칙 값은 사람이 확정)에 따라 임의 채택하지 않고 escalation 유지. "
                "03_OPEN_QUESTIONS Q9 참조."),
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
    cases += region_cases()
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
