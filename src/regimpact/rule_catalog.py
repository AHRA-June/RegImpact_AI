"""내규 영향도 매핑 (Rule Catalog Impact) — "규제가 바뀌면 우리 규정 어디를 고쳐야 하나".

`rule_proposal.py`(룰엔진 *내부 파라미터* 대조)와 목적이 다르다. 이 모듈은 은행의 **여신 내규 대장
(규정 문서 목록)** 관점에서, 규제 변경이 **어느 규정을 건드리는지**를 짚어 수정 필요 지점을 초안한다.
= 브리프 슬로건 "규제가 바뀌면 무엇을 고쳐야 하는지 AI가 제안"의 가장 직접적 구현.

⚠️ **정직성 고지:**
  - 아래 내규 대장은 **모의(가짜) 규정**이다. 실제 회사 내규·고객 데이터가 아니다(LOCKED §8, 공개자료만).
    실제 도입 시 이 표를 진짜 내규 레지스트리로 교체하면 매핑 로직은 불변.
  - 규제 변경(공문)은 **실제**다. 매핑은 결정적 규칙(카테고리+키워드)으로 산출하며 LLM 판단이 아니다.
  - 모든 수정안은 **초안이며 승인 PENDING**이다(사람이 확정, LOCKED §4). 자동 반영 없음.
  - **무관 규정도 일부러 포함**한다(예금·카드) — 시스템이 무관한 규정을 과잉 플래그하지 않음을 보이기 위해.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Disposition(str, Enum):
    EDIT_REQUIRED = "EDIT_REQUIRED"     # 직접 대상 — 수정 필요
    NEEDS_REVIEW = "NEEDS_REVIEW"       # 연동 가능 — 사람 검토
    INDIRECT = "INDIRECT"               # 간접 영향 — 점검 권고
    UNAFFECTED = "UNAFFECTED"           # 무관


@dataclass(frozen=True)
class InternalRule:
    """모의 여신 내규 1건 (규정 대장의 레코드)."""
    rid: str
    title: str
    category: str                 # 표시용 분류(LTV/예외/경과/지역/시행일/범위/DTI/한도/수신/카드)
    current: str                  # 현재 규정 요지(모의)
    owner: str = ""               # 소관(모의)
    edit_cats: tuple[str, ...] = ()      # 이 추출 변경 카테고리면 '수정 필요'
    edit_keywords: tuple[str, ...] = ()  # (선택) summary 키워드로 드라이버 좁힘
    review_cats: tuple[str, ...] = ()    # '검토'
    indirect_cats: tuple[str, ...] = ()  # '간접 영향'
    note: str = ""


# --------------------------------------------------------------------------- #
# 모의 내규 대장 (문서화된 가정 — 실제 회사 문서 아님)
# --------------------------------------------------------------------------- #
DEFAULT_CATALOG: list[InternalRule] = [
    InternalRule("R-LTV-01", "규제지역 주택담보대출 LTV 표준", "LTV",
                 "규제지역 주담대 LTV 상한 70%", "여신정책부",
                 edit_cats=("LTV",), edit_keywords=("규제지역", "강화", "비율")),
    InternalRule("R-LTV-02", "다주택자 주택구입 LTV", "LTV",
                 "다주택자 규제지역 주택구입 LTV 미규정", "여신정책부",
                 edit_cats=("LTV",), edit_keywords=("다주택",)),
    InternalRule("R-EXC-03", "생애최초·서민실수요 예외 LTV", "예외",
                 "생애최초 70% / 서민·실수요 완화 적용", "여신정책부",
                 edit_cats=("EXCEPTION",)),
    InternalRule("R-GF-04", "경과규정(종전규정) 적용 기준", "경과규정",
                 "효력 발생 전 계약·접수분 종전규정", "여신심사부",
                 edit_cats=("GRANDFATHERING",)),
    InternalRule("R-REG-05", "규제지역 목록·판정 로직", "지역",
                 "규제지역 코드표 및 시점 판정", "여신정책부",
                 edit_cats=("REGION",)),
    InternalRule("R-EFF-06", "규제 시행일 관리", "시행일",
                 "규제 효력 발생일 파라미터", "여신정책부",
                 edit_cats=("EFFECTIVE_DATE",)),
    InternalRule("R-SCP-07", "전세대출 보유자 주택취득 제한", "범위",
                 "전세대출 보유 차주 취급 기준", "여신심사부",
                 edit_cats=("SCOPE_LIMIT",), edit_keywords=("전세",)),
    InternalRule("R-SCP-08", "신용대출 보유자 규제지역 주택구입 제한", "범위",
                 "신용대출 보유 차주 취급 기준", "여신심사부",
                 edit_cats=("SCOPE_LIMIT",), edit_keywords=("신용대출",)),
    InternalRule("R-BIZ-09", "사업자 주택구입목적 대출 제한", "범위",
                 "사업자대출 주택구입 목적 취급 기준", "기업여신부",
                 edit_cats=("SCOPE_LIMIT",), edit_keywords=("사업자",)),
    InternalRule("R-DTI-10", "DTI 한도(투기과열 40 / 조정 50)", "DTI",
                 "규제유형별 DTI 상한", "여신정책부",
                 review_cats=("REGION",),
                 note="규제지역 지정으로 DTI 체계 연동 가능 — 코어(LTV) 밖, 사람 확인"),
    InternalRule("R-LMT-11", "가격대별 대출 최대한도(6/4/2억)", "한도",
                 "주택가격 구간별 대출 최대한도", "여신정책부",
                 indirect_cats=("LTV", "REGION"),
                 note="여력 산정에서 미적용(상한 성격) — 규제 맥락상 점검 권고"),
    InternalRule("R-DEP-12", "예금(수신) 금리 정책", "수신",
                 "정기예금 기본금리 체계", "수신부"),
    InternalRule("R-CARD-13", "신용카드 발급 기준", "카드",
                 "신규 카드 발급 심사 기준", "카드사업부"),
]


# --------------------------------------------------------------------------- #
# 결과 스키마
# --------------------------------------------------------------------------- #
@dataclass
class RuleImpact:
    rule: InternalRule
    disposition: Disposition
    drivers: list[dict]           # 이 규정을 건드린 규제 변경들(요약+인용)
    suggested_edit: str           # 수정안 초안
    approval_status: str = "PENDING"


@dataclass
class CatalogImpact:
    items: list[RuleImpact] = field(default_factory=list)
    approval_status: str = "PENDING"

    def counts(self) -> dict[str, int]:
        c = Counter(i.disposition.value for i in self.items)
        for d in Disposition:
            c.setdefault(d.value, 0)
        return dict(c)

    def edits(self) -> list[RuleImpact]:
        return [i for i in self.items if i.disposition == Disposition.EDIT_REQUIRED]


# --------------------------------------------------------------------------- #
# 매핑 로직 (결정적 — 카테고리 + 키워드)
# --------------------------------------------------------------------------- #
def _match(changes: list[Any], cats: tuple[str, ...], keywords: tuple[str, ...]) -> list[Any]:
    if not cats:
        return []
    out = []
    for c in changes:
        if getattr(c, "category", "") in cats:
            summ = getattr(c, "summary", "") or ""
            if not keywords or any(k in summ for k in keywords):
                out.append(c)
    return out


def _driver(c: Any) -> dict:
    cit = getattr(c, "citation", None)
    return {
        "summary": getattr(c, "summary", ""),
        "before": getattr(c, "before", None),
        "after": getattr(c, "after", None),
        "doc_id": getattr(cit, "source_doc_id", "") if cit else "",
        "quote": ((getattr(cit, "quote", "") or "")[:100]) if cit else "",
    }


def _suggest(rule: InternalRule, drivers: list[Any]) -> str:
    c = drivers[0]
    b, a = getattr(c, "before", None), getattr(c, "after", None)
    ba = f" ({b or '—'} → {a or '—'})" if (b or a) else ""
    return f"규제 반영: {getattr(c, 'summary', '')}{ba} — 현재 규정 '{rule.current}' 수정 필요(초안)"


def map_catalog_impact(extraction: Any, catalog: list[InternalRule] = DEFAULT_CATALOG) -> CatalogImpact:
    """추출된 규제 변경을 모의 내규 대장에 매핑해 규정별 수정 필요 여부를 초안한다."""
    changes = list(getattr(extraction, "changes", []) or [])
    items: list[RuleImpact] = []
    for r in catalog:
        edits = _match(changes, r.edit_cats, r.edit_keywords)
        if edits:
            items.append(RuleImpact(r, Disposition.EDIT_REQUIRED,
                                    [_driver(c) for c in edits], _suggest(r, edits)))
            continue
        revs = _match(changes, r.review_cats, ())
        if revs:
            items.append(RuleImpact(r, Disposition.NEEDS_REVIEW, [_driver(c) for c in revs],
                                    (r.note or "규제 맥락 연동 — 사람 검토 필요") + "(초안)"))
            continue
        inds = _match(changes, r.indirect_cats, ())
        if inds:
            items.append(RuleImpact(r, Disposition.INDIRECT, [_driver(c) for c in inds],
                                    (r.note or "간접 영향 — 점검 권고") + "(초안)"))
            continue
        items.append(RuleImpact(r, Disposition.UNAFFECTED, [], "영향 없음"))
    return CatalogImpact(items=items)


# --------------------------------------------------------------------------- #
# 텍스트 포매터
# --------------------------------------------------------------------------- #
_DISP_KO = {
    Disposition.EDIT_REQUIRED: "수정필요",
    Disposition.NEEDS_REVIEW: "검토",
    Disposition.INDIRECT: "간접영향",
    Disposition.UNAFFECTED: "무관",
}


def format_catalog(ci: CatalogImpact) -> str:
    lines: list[str] = []
    lines.append("내규 영향도 맵 (모의 내규 대장 — 실제 회사 문서 아님, 승인 PENDING)")
    c = ci.counts()
    lines.append(f"수정필요 {c['EDIT_REQUIRED']} · 검토 {c['NEEDS_REVIEW']} · "
                 f"간접영향 {c['INDIRECT']} · 무관 {c['UNAFFECTED']} (총 {len(ci.items)})")
    lines.append("-" * 72)
    for i in ci.items:
        r = i.rule
        lines.append(f"[{_DISP_KO[i.disposition]:>4}] {r.rid} {r.title} ({r.category})")
        if i.drivers:
            d = i.drivers[0]
            more = f" 외 {len(i.drivers)-1}건" if len(i.drivers) > 1 else ""
            lines.append(f"        ← 규제변경: {d['summary']}{more}  [{d['doc_id']}]")
            lines.append(f"        ↳ {i.suggested_edit}")
    return "\n".join(lines)
