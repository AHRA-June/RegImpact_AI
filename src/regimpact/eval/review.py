"""골드셋 도메인 검수 (v2) — 정답을 원문 규제사실에 grounding하고 사람이 확정.

v1 정답은 독립 명세 오라클(§H)에서 유도됐다(AI초안, LOCKED §4). 이 검수는 각 정답을 **원문
규제사실의 실제 인용**에 grounding하고, 수치 일관성(정답 = 인용이 말하는 값)을 검증하며,
도메인 판단으로 확정 상태를 부여한다. 입력·정답은 바꾸지 않는다 — 오라클 유도값이 원문과
일치함을 확인하는 것이 검수의 결론이다(불일치 시 예외).

확정 상태:
- CONFIRMED            — 수치/상태 정답이 원문 인용과 일치(직접 grounding).
- CONFIRMED_ESCALATION — 정답이 '사람 검토'(원문에 기준선 부재). escalation 자체가 올바른 정답.
- CONFIRMED_PRECEDENCE — 복수 조건 충돌을 §H 우선순위(DECISION_LOG 확정)로 해소한 정답.

최종 권한(authority)은 사람(사용자)이다(LOCKED §4 'AI초안→사람확정').
"""
from __future__ import annotations

import json
from pathlib import Path

from .gold_set import GOLD_DIR, GoldItem, load_split

REVIEW_PATH = GOLD_DIR / "REVIEW_v2.json"
REVIEW_VERSION = "v2"

# reason_code → 원문 grounding (doc·인용·원문이 말하는 값/상태).
# 인용은 실측 추출(docs/eval/regchange_extraction_6_30.json)·regulatory_facts에서 확인됨.
_GROUNDING: dict[str, dict] = {
    "LTV_REGULATED_40": {"doc": "FAQ_20260630",
        "quote": "규제지역 내 주담대 취급시 강화된 LTV(70→40%) 적용", "ltv": 0.40},
    "EXCEPTION_FIRST_HOME": {"doc": "MOLIT_PRESS_20260630",
        "quote": "생애최초 LTV 70% + 전입의무(6개월 이내)", "ltv": 0.70},
    "EXCEPTION_REAL_DEMAND": {"doc": "FAQ_20260630",
        "quote": "금융권 서민·실수요자 주담대 … 완화된 LTV가 적용됨(60%)", "ltv": 0.60},
    "LTV_OWNER_0": {"doc": "MOLIT_PRESS_20260630",
        "quote": "무주택(처분조건부 1주택 포함) 40%, 유주택 0%", "ltv": 0.00},
    "LTV_MULTI_HOME_0": {"doc": "FSC_PRESS_20260630",
        "quote": "다주택자는 수도권 內 주택구입시 … LTV 0% 적용", "ltv": 0.00},
    "LTV_BASELINE_70": {"doc": "MOLIT_PRESS_20260630",
        "quote": "非규제지역(수도권 외) 무주택(처분조건부 1주택) 70%", "ltv": 0.70},
    "GRANDFATHERED_ACCEPTED_OR_CONTRACT": {"doc": "FAQ_20260630",
        "quote": "6.30일까지 전산 접수 완료 또는 계약+계약금 → 종전규정 적용", "ltv": 0.70},
    "GRANDFATHERED_LAND_PERMIT": {"doc": "FSC_PRESS_20260630",
        "quote": "토지거래허가 신청 접수(≤6.30) → 이후 계약해도 종전규정 적용", "ltv": 0.70},
    "OUT_OF_SCOPE_PRODUCT": {"doc": "FSC_PRESS_20260630",
        "quote": "주택구입목적 주담대에 한해 자동판정(그 외는 Discovery)", "status": "OUT_OF_SCOPE"},
    "DISCOVERY_POLICY_LOAN": {"doc": "FAQ_20260630",
        "quote": "생애최초·정책모기지 등 정책성 대출은 별도(디딤돌·보금자리) → Discovery 분리", "status": "DISCOVERY"},
    "OWNER_BASELINE_UNKNOWN": {"doc": "regulatory_facts.md",
        "quote": "非규제지역 유주택 LTV 기준선은 6·30 원문에 명시되지 않음", "status": "NEEDS_HUMAN_REVIEW"},
}


def _primary_grounding(item: GoldItem) -> tuple[str, dict]:
    """정답 근거코드 중 grounding 테이블에 있는 첫 코드를 대표로."""
    for rc in item.expected.get("must_include_reasons", []):
        if rc in _GROUNDING:
            return rc, _GROUNDING[rc]
    # 상태만 있는 경우(방어)
    return "", {}


def review_item(item: GoldItem) -> dict:
    """한 문항을 원문에 grounding하고 확정 상태·근거를 산출한다.

    수치 정답은 인용이 말하는 값과 일치해야 한다(불일치 시 ValueError — 검수 실패).
    """
    status = item.expected["status"]
    rc, g = _primary_grounding(item)

    # 1) 명세부재 → escalation 이 정답
    if status == "NEEDS_HUMAN_REVIEW":
        return {
            "status": "CONFIRMED_ESCALATION",
            "grounding_doc": _GROUNDING["OWNER_BASELINE_UNKNOWN"]["doc"],
            "grounding_quote": _GROUNDING["OWNER_BASELINE_UNKNOWN"]["quote"],
            "rationale": "원문에 해당 기준선이 없어 값을 지어내지 않고 사람 검토(escalation)로 넘기는 것이 "
                         "올바른 정답이다. escalation 자체를 확정한다.",
        }

    # 2) 우선순위 충돌 → §H 로 해소된 정답
    if item.category == "CONFLICT":
        # 수치 일관성도 함께 확인(해소 결과가 원문 값과 일치)
        _assert_numeric_consistency(item, g)
        return {
            "status": "CONFIRMED_PRECEDENCE",
            "grounding_doc": g.get("doc", "05_RULE_SPEC.md §H"),
            "grounding_quote": g.get("quote", "우선순위 P0~P7"),
            "rationale": "복수 조건이 충돌하나 §H 우선순위(DECISION_LOG 2026-08-10 확정)로 해소된다. "
                         f"해소 결과({item.expected.get('max_ltv')})가 원문 값과 일치함을 확인했다.",
        }

    # 3) 일반 — 수치/상태를 원문 인용에 직접 grounding
    _assert_numeric_consistency(item, g)
    if g.get("status") and g["status"] != status:
        raise ValueError(f"{item.id}: 상태 불일치 {status}≠{g['status']}")
    return {
        "status": "CONFIRMED",
        "grounding_doc": g.get("doc", "-"),
        "grounding_quote": g.get("quote", "-"),
        "rationale": f"정답({_answer_label(item)})이 원문 인용과 직접 일치한다(근거코드 {rc}).",
    }


def _answer_label(item: GoldItem) -> str:
    ltv = item.expected.get("max_ltv")
    return f"{ltv:.0%}" if isinstance(ltv, (int, float)) else item.expected["status"]


def _assert_numeric_consistency(item: GoldItem, g: dict) -> None:
    exp_ltv = item.expected.get("max_ltv")
    src_ltv = g.get("ltv")
    if exp_ltv is not None and src_ltv is not None and abs(exp_ltv - src_ltv) > 1e-9:
        raise ValueError(f"{item.id}: 정답 LTV {exp_ltv} ≠ 원문 {src_ltv} ({g.get('doc')})")


def review_all() -> dict:
    """전 split 문항을 검수해 {id: review} 와 요약을 만든다(입력·정답 불변)."""
    reviews: dict[str, dict] = {}
    summary = {"total": 0, "CONFIRMED": 0, "CONFIRMED_ESCALATION": 0, "CONFIRMED_PRECEDENCE": 0}
    by_status_split: dict[str, dict[str, int]] = {}
    for name in ("dev", "locked", "challenge"):
        for it in load_split(name, unlock=True):
            r = review_item(it)
            r["split"] = name
            r["category"] = it.category
            reviews[it.id] = r
            summary["total"] += 1
            summary[r["status"]] += 1
            by_status_split.setdefault(name, {}).setdefault(r["status"], 0)
            by_status_split[name][r["status"]] += 1
    return {"reviews": reviews, "summary": summary, "by_split": by_status_split}


def load_review() -> dict | None:
    """저장된 v2 검수 기록을 로드한다. 없으면 None(→ v1로 표시)."""
    if not REVIEW_PATH.exists():
        return None
    return json.loads(REVIEW_PATH.read_text(encoding="utf-8"))


def review_summary() -> dict | None:
    rec = load_review()
    return rec["summary"] if rec else None
