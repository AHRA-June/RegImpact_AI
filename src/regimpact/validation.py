"""입력 무결성 검증 (docs/05_RULE_SPEC.md §E — 복합 조건 처리).

## 왜 별도 게이트인가 (Q8 해소, 2026-08-18)

`05_RULE_SPEC` 의 두 서술이 오랫동안 상충하는 것처럼 보였다:

    §E-139  "유주택 AND 생애최초: 논리상 불가... 데이터 충돌 시 → NEEDS_HUMAN_REVIEW"
    §H      P4(유주택 비처분)에서 0%로 short-circuit → P5(생애최초)에 도달하지 않음

그런데 §E-138 이 "처분조건부 1주택 AND 생애최초"를 **유효한 조합**으로 명시한다. 즉 §E 가 말하는
"유주택"은 `grandfathering.is_owner()` 와 같은 의미(다주택 + 비처분 1주택)다. 그렇다면 §E-139 는
**우선순위 규칙이 아니라 입력 유효성 규칙**이다 — §H 는 "유효한 입력에 대해 어떤 LTV를 주는가"를 말하고,
§E-139 는 "그 입력이 애초에 성립하는가"를 말한다. 층위가 다르므로 **둘 다 참일 수 있다.**
§H 에 검증 게이트가 없었을 뿐이다.

## 왜 0% 자동판정이 아니라 escalation 인가

`house_count>=1 AND first_home_buyer` 는 **정상 신청건이 아니라 데이터 무결성 위반**이다.
여기서 0%를 자동으로 내주면 "정상 입력이고 답이 0%"와 "입력이 모순인데 우연히 0%가 나왔다"를
시스템이 구분하지 못한다. 게다가 0%는 무해한 답이 아니라 **대출 거절**이고, 만약 틀린 쪽이
`first_home_buyer` 플래그였다면(실제로는 무주택 생애최초) 정답은 70%다. 0%와 70% 사이 70%p 격차가
데이터 오류 하나 뒤에 숨는 구조는 그대로 두면 안 된다.

이 프로젝트는 이미 같은 원칙을 두 번 적용했다 — `OWNER_BASELINE_UNKNOWN`(기준값 부재),
`UNKNOWN_REGION`(미등록 지역). Q8 도 같은 부류다: **모르면 지어내지 않고 사람에게 넘긴다.**

## 넣지 않은 것 (Q12 잔여, 2026-08-18)

`downpayment_paid_at` 만 있고 `contract_signed_at` 이 없는 경우, 그리고 계약금 납부일이 계약 체결일보다
빠른 경우는 **모순으로 보지 않는다.** 실무에 **가계약금**(정식 계약 전 계약금 선납)이 실재하므로
기계적으로 막으면 정상 건을 사람 검토로 보낸다. 두 경우 모두 §F G2 가 "계약 체결 + 계약금 납부"를
쌍으로 요구하므로 **경과규정이 성립하지 않을 뿐**이고, 그건 이미 올바른 동작이다.
도메인 확인이 되면 그때 넣는다(`03_OPEN_QUESTIONS.md` Q12).

## 게이트의 위치

P0(스코프)·P0b(정책대출) **뒤**, P1(경과규정) **앞**.
- 뒤: 주택구입목적이 아니거나 정책대출이면 코어 자동판정 대상이 아니므로 모순을 따질 필요가 없다.
- 앞: 모순 입력에 경과규정 종전규정(70%)을 내주는 것도 0%를 내주는 것만큼 위험하다.
"""
from __future__ import annotations

from dataclasses import dataclass

from .grandfathering import is_owner
from .models import MortgageApplication, ReasonCode


@dataclass(frozen=True)
class InputContradiction:
    """입력 모순 1건. code 는 reason_code 로 그대로 실린다."""
    code: str
    detail: str


def validate_application(app: MortgageApplication) -> list[InputContradiction]:
    """입력의 논리적 모순을 찾는다. 빈 목록이면 판정을 진행해도 되는 입력.

    검사 대상은 **스키마·논리상 명백히 성립할 수 없는 조합**뿐이다(Q8·Q12 확정).
    실무 여지가 있는 것(가계약금 = 정식 계약 전 계약금 선납)은 넣지 않는다 — 기계적으로 막으면
    정상 건을 사람 검토로 보낸다. `docs/03_OPEN_QUESTIONS.md` Q12 잔여 항목 참고.
    """
    out: list[InputContradiction] = []

    # 자명한 무효값.
    if app.house_count < 0:
        out.append(InputContradiction(
            code=ReasonCode.INVALID_HOUSE_COUNT.value,
            detail=f"house_count={app.house_count} — 음수는 성립하지 않는다",
        ))

    # §E-139. 생애최초 = 세대원 전원 무주택 '이력'. 유주택과 동시에 성립할 수 없다.
    # (처분조건부 1주택은 §E-138 이 유효 조합으로 명시 → is_owner() 가 이미 제외한다.)
    if is_owner(app) and app.first_home_buyer:
        out.append(InputContradiction(
            code=ReasonCode.CONTRADICTION_OWNER_FIRST_HOME.value,
            detail=(f"house_count={app.house_count}"
                    f"{'(비처분)' if not app.disposal_condition_flag else ''} 이면서 "
                    "first_home_buyer=True — 생애최초는 세대원 전원 무주택 이력을 전제한다"),
        ))

    # Q12. 처분조건부 1주택 플래그는 §A 스키마가 "house_count==1과 함께"로 정의한다.
    #      보유 0채면 처분할 주택이 없고, 2채 이상이면 필드가 전제한 '1주택'이 아니다.
    #      둘 다 판정이 갈리는 지점이라(0채: 무주택 70% vs 실제는? / 2채: 다주택 0%) 사람이 봐야 한다.
    if app.disposal_condition_flag and app.house_count == 0:
        out.append(InputContradiction(
            code=ReasonCode.CONTRADICTION_DISPOSAL_WITHOUT_HOUSE.value,
            detail=("disposal_condition_flag=True 인데 house_count=0 — "
                    "처분할 주택이 없다 (§A: 처분조건부 1주택은 house_count==1과 함께)"),
        ))
    elif app.disposal_condition_flag and app.house_count >= 2:
        out.append(InputContradiction(
            code=ReasonCode.CONTRADICTION_DISPOSAL_MULTI_HOUSE.value,
            detail=(f"disposal_condition_flag=True 인데 house_count={app.house_count} — "
                    "이 필드는 '처분조건부 1주택'을 전제한다 (§A)"),
        ))

    return out
