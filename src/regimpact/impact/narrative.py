"""고객용 내러티브 — reason_code 를 사람 말로 옮기고 "그래서 나는?"에 답한다.

대상은 일반 고객이다. 질문 흐름은 "뭐가 바뀌었지 → 왜 → 그래서 나는 뭘 해야 하지".
시스템 용어(reason_code·status)를 그대로 노출하지 않되 **근거는 남긴다** — 사람 말로 옮기는 것과
근거를 버리는 것은 다르다.

과대약속 금지: 자동 판정 결과는 "정확한 확정"이 아니라 **검증 가능한 초안 + 사람 확인이
필요한 지점의 명시**다. 사람 검토 대상이면 그 사실을 문장에 반드시 남긴다.

번역이 빠진 코드는 테스트가 잡는다 — 번역 없는 코드는 고객 화면에 영문 상수로 새어나간다.
"""
from __future__ import annotations

from typing import Optional

from ..models import EvaluationStatus, ReasonCode
from .customer import CustomerImpact, Segment

# reason_code → 고객이 이해할 한 줄. **모든 ReasonCode 에 항목이 있어야 한다.**
REASON_KO: dict[str, str] = {
    ReasonCode.LTV_REGULATED_40: "규제지역 무주택 기준이 적용됩니다.",
    ReasonCode.EXCEPTION_FIRST_HOME: "생애최초 구입 예외로 종전 한도가 유지됩니다.",
    ReasonCode.EXCEPTION_REAL_DEMAND: "서민·실수요자 예외가 적용됩니다.",
    ReasonCode.LTV_OWNER_0: "규제지역에서 주택을 보유한 경우 주택구입 목적 대출이 제한됩니다.",
    ReasonCode.LTV_MULTI_HOME_0: "다주택자는 수도권 주택구입 목적 대출이 제한됩니다.",
    ReasonCode.LTV_BASELINE_70: "비규제 기준이 적용됩니다.",
    ReasonCode.GRANDFATHERED_ACCEPTED_OR_CONTRACT:
        "시행 전에 이미 접수·계약을 마쳐 종전 규정이 적용됩니다.",
    ReasonCode.GRANDFATHERED_LAND_PERMIT:
        "시행 전에 토지거래허가를 신청해 종전 규정이 적용됩니다.",
    ReasonCode.OWNER_BASELINE_UNKNOWN:
        "이 경우의 종전 기준값이 공식 원문에 없어 담당자 확인이 필요합니다.",
    ReasonCode.MULTI_HOME_BASELINE_UNKNOWN:
        "이 경우의 종전 기준값이 공식 원문에 없어 담당자 확인이 필요합니다.",
    ReasonCode.REGION_UNKNOWN:
        "해당 지역의 규제 상태를 확인할 수 없어 담당자 확인이 필요합니다.",
    ReasonCode.OUT_OF_SCOPE_PRODUCT: "주택구입 목적 대출이 아니어서 이 판정 대상이 아닙니다.",
    ReasonCode.DISCOVERY_POLICY_LOAN:
        "정책대출(디딤돌·보금자리 등)은 별도 기준이라 담당 창구 확인이 필요합니다.",
}

# 세그먼트 → 헤드라인. **모든 Segment 에 항목이 있어야 한다.**
HEADLINE_KO: dict[Segment, str] = {
    Segment.REDUCED: "대출 한도가 줄어듭니다.",
    Segment.UNAFFECTED: "이번 규제로 한도가 달라지지 않습니다.",
    Segment.GRANDFATHERED: "경과규정으로 종전 한도가 그대로 유지됩니다.",
    Segment.IMPACT_UNKNOWN: "이 조건으로는 주택구입 목적 대출이 제한됩니다.",
    Segment.NEEDS_HUMAN_REVIEW: "자동 판정만으로 결론 내기 어려워 담당자 확인이 필요합니다.",
    Segment.DISCOVERY: "별도 기준이 적용되어 담당 창구 확인이 필요합니다.",
    Segment.OUT_OF_SCOPE: "이 규제의 자동 판정 대상이 아닙니다.",
}

# 세그먼트 → 다음 행동
ACTION_KO: dict[Segment, str] = {
    Segment.REDUCED: "필요 자기자금이 늘어납니다. 생애최초·서민실수요 예외 해당 여부를 확인해 보세요.",
    Segment.UNAFFECTED: "별도 조치는 필요하지 않습니다.",
    Segment.GRANDFATHERED: "종전 규정 적용을 위해 접수·계약 증빙을 보관하세요.",
    Segment.IMPACT_UNKNOWN: "기존 주택 처분(처분조건부) 등 요건 변경이 가능한지 확인해 보세요.",
    Segment.NEEDS_HUMAN_REVIEW: "지점·상담 창구에 문의하세요. 자동 결과는 참고용입니다.",
    Segment.DISCOVERY: "정책대출 담당 창구에 별도 문의하세요.",
    Segment.OUT_OF_SCOPE: "해당 없음.",
}

DRAFT_NOTICE = "⚠ 이 결과는 자동 초안입니다. 최종 판단은 담당자가 확인합니다."


def _pct(v: Optional[float]) -> str:
    return "—" if v is None else f"{v:.0%}"


def _won(v: Optional[int]) -> str:
    return "—" if v is None else f"{v:,}원"


# "영향 없음"은 두 가지를 함께 담는다 — 70%→70%(문제 없음)와 0%→0%(애초에 못 빌린다).
# 후자에게 "달라지지 않습니다"만 말하면 빌릴 수 있다는 오해를 준다. 실제로 돌려보고 발견했다.
_ALREADY_INELIGIBLE = "이번 규제로 달라지는 것은 없지만, 이 조건으로는 주택구입 목적 대출이 어렵습니다."


def _headline(impact: CustomerImpact) -> str:
    if impact.segment is Segment.UNAFFECTED and impact.after.max_ltv == 0:
        return _ALREADY_INELIGIBLE
    return HEADLINE_KO[impact.segment]


def explain(impact: CustomerImpact) -> str:
    """고객용 설명 문단 — 헤드라인 · 무엇이 · 왜 · 그래서."""
    seg = impact.segment
    lines = [_headline(impact)]

    before, after = impact.before.max_ltv, impact.after.max_ltv
    if before is not None and after is not None:
        lines.append(
            f"· 최대 LTV: {_pct(before)} → {_pct(after)}"
            if before != after else f"· 최대 LTV: {_pct(after)} (변동 없음)")
    elif after is not None:
        # 시행 전 기준값이 없는 경우 — "0원에서 시작했다"고 오해하지 않도록 말로 적는다.
        lines.append(f"· 시행 후 최대 LTV: {_pct(after)} (시행 전 기준값은 원문에 없습니다)")

    if impact.limit_before is not None and impact.limit_after is not None:
        delta = impact.limit_delta
        lines.append(f"· 대출 한도: {_won(impact.limit_before)} → {_won(impact.limit_after)}"
                     + (f" ({delta:+,}원)" if delta else ""))

    reasons = [REASON_KO[rc] for rc in impact.after.reason_codes if rc in REASON_KO]
    if reasons:
        lines.append("· 이유: " + " ".join(dict.fromkeys(reasons)))

    action = ACTION_KO[seg]
    if seg is Segment.UNAFFECTED and impact.after.max_ltv == 0:
        action = "이 규제와 무관한 사유이므로, 조건 변경 가능 여부를 창구에서 확인해 보세요."
    lines.append("· 다음 단계: " + action)

    if impact.after.status is EvaluationStatus.NEEDS_HUMAN_REVIEW:
        lines.append("· " + DRAFT_NOTICE)
    return "\n".join(lines)
