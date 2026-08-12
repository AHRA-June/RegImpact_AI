"""Rule Change Proposal — 추출(RegChange) → 구조화 룰 변경안(초안) + 사람 확정 룰 대조.

파이프라인의 마지막 조각: 공문 → 추출 → **룰 변경안(초안)** → 사람 확정 룰과 대조.

핵심 원칙(LOCKED §4, 브리프 "AI 초안 → 사람 확정"):
  - LLM 추출은 **초안**이다. 이 모듈은 추출된 각 변경을 룰엔진의 실제 룰 표면
    (LTV 상수·지역 버전·경과규정 컷오프·시행일)에 **매핑**하고, **사람이 확정한 룰엔진의
    현재값과 교차 대조**한다.
  - 판정(룰의 값)을 새로 만들지 않는다. deterministic 룰엔진이 ground truth이고, 이 제안은
    "AI가 제안한 변경이 확정 명세와 일치하는가"를 각 항목에 대해 표시할 뿐이다.
  - **자동 확정 없음:** approval_status 는 항상 PENDING. 사람이 검토·승인한다(브리프 §16-17 감사추적).

각 변경의 disposition:
  MAPPED_CONSISTENT — 코어 룰 필드에 매핑되고, 추출 after 값이 엔진 현재값과 일치(반영됨).
  MAPPED_DIVERGENT  — 매핑되나 값이 엔진과 다름 → 사람 검토(엔진 갱신 or 추출 오류).
  OUT_OF_SCOPE      — 전세/신용/중도금/사업자·정책모기지 등 코어 자동판정 밖(Discovery).
  NEEDS_REVIEW      — 값 파싱 불가·매핑 불명 → 사람 검토.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any, Optional

from . import grandfathering, regions, rule_engine
from .regions import normalize_regions


class Disposition(str, Enum):
    MAPPED_CONSISTENT = "MAPPED_CONSISTENT"
    MAPPED_DIVERGENT = "MAPPED_DIVERGENT"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    NEEDS_REVIEW = "NEEDS_REVIEW"


@dataclass
class RuleDelta:
    """제안된 룰 변경 1건 + 엔진 대조 결과."""
    category: str
    summary: str
    target_field: Optional[str]        # 매핑된 룰엔진 필드(예: LTV_REGULATED_STANDARD)
    extracted_before: Optional[str]
    extracted_after: Optional[str]
    engine_current: Optional[str]      # 사람 확정 룰엔진의 현재값(표시용 문자열)
    disposition: Disposition
    citation_doc: str
    citation_quote: str
    confidence: float
    note: str = ""


@dataclass
class RuleChangeProposal:
    """정책 1건에 대한 구조화 룰 변경안(초안). 자동 확정 없음."""
    policy_id: str
    effective_from: Optional[str]
    deltas: list[RuleDelta] = field(default_factory=list)
    approval_status: str = "PENDING"   # LOCKED §4: 항상 사람 확정 대기
    generated_on: Optional[date] = None

    def counts(self) -> dict[str, int]:
        out = {d.value: 0 for d in Disposition}
        for x in self.deltas:
            out[x.disposition.value] += 1
        return out

    @property
    def consistent_count(self) -> int:
        return sum(1 for d in self.deltas if d.disposition == Disposition.MAPPED_CONSISTENT)

    @property
    def review_count(self) -> int:
        return sum(1 for d in self.deltas
                   if d.disposition in (Disposition.MAPPED_DIVERGENT, Disposition.NEEDS_REVIEW))


# --------------------------------------------------------------------------- #
# 값 파싱 · 매핑
# --------------------------------------------------------------------------- #
def _parse_pcts(s: Optional[str]) -> list[float]:
    """문자열에서 퍼센트를 모두 뽑아 소수로. '60~70%' → [0.60, 0.70]."""
    if not s:
        return []
    return [int(m) / 100 for m in re.findall(r"(\d{1,3})\s*%", s)]


def _pct(v: float) -> str:
    return f"{v:.0%}"


def _has(text: str, *subs: str) -> bool:
    return any(sub in text for sub in subs)


def _map_change(item: Any, effective_from: Optional[str],
                target_regions: list[str]) -> RuleDelta:
    """추출 change 1건을 룰엔진 필드에 매핑하고 현재값과 대조."""
    cat = item.category
    text = f"{item.summary} {item.before or ''} {item.after or ''}"
    afters = _parse_pcts(item.after)
    cite_doc = item.citation.source_doc_id
    cite_q = (item.citation.quote or "")[:140]

    def delta(target, engine_cur, disp, note=""):
        return RuleDelta(
            category=cat, summary=item.summary, target_field=target,
            extracted_before=item.before, extracted_after=item.after,
            engine_current=engine_cur, disposition=disp,
            citation_doc=cite_doc, citation_quote=cite_q,
            confidence=item.confidence, note=note,
        )

    # --- SCOPE_LIMIT: 전세/신용/중도금/사업자 → 코어 밖 ---
    if cat == "SCOPE_LIMIT":
        return delta(None, "Discovery(코어 밖)", Disposition.OUT_OF_SCOPE,
                     "전세/신용/중도금/사업자 제한은 자동판정 밖 — 사람 검토 라우팅")

    # --- EFFECTIVE_DATE: regions.REG_EFFECTIVE 와 대조 ---
    if cat == "EFFECTIVE_DATE":
        eng = regions.REG_EFFECTIVE.isoformat()
        got = (item.after or effective_from or "")
        disp = Disposition.MAPPED_CONSISTENT if eng in got else (
            Disposition.MAPPED_DIVERGENT if got else Disposition.NEEDS_REVIEW)
        return delta("REG_EFFECTIVE", eng, disp)

    # --- REGION: 정규화 후 KNOWN_REGION_CODES 와 대조 ---
    if cat == "REGION":
        codes, unmapped = normalize_regions(target_regions)
        eng = ", ".join(sorted(regions.KNOWN_REGION_CODES))
        if codes and set(codes) <= regions.KNOWN_REGION_CODES and not unmapped:
            return delta("REGION_VERSIONS", eng, Disposition.MAPPED_CONSISTENT,
                         f"정규화 {codes} ⊆ 엔진 등록 지역")
        return delta("REGION_VERSIONS", eng, Disposition.NEEDS_REVIEW,
                     f"미매핑 지역: {unmapped}" if unmapped else "지역 대조 필요")

    # --- GRANDFATHERING: grandfathering.CUTOFF 와 대조(규칙, 스칼라 아님) ---
    if cat == "GRANDFATHERING":
        eng = grandfathering.CUTOFF.isoformat()
        if _has(text, "6.30", "06-30", "6·30", "종전"):
            return delta("GRANDFATHERING_CUTOFF", eng, Disposition.MAPPED_CONSISTENT,
                         "종전규정 컷오프(6.30) 규칙 = 엔진 구현과 일치")
        return delta("GRANDFATHERING_CUTOFF", eng, Disposition.NEEDS_REVIEW)

    # --- EXCEPTION: 생애최초/서민실수요/정책모기지 ---
    if cat == "EXCEPTION":
        if _has(text, "정책모기지", "보금자리", "디딤돌"):
            return delta(None, "Discovery(코어 밖)", Disposition.OUT_OF_SCOPE,
                         "정책대출은 코어 자동판정 제외(Discovery)")
        if _has(text, "생애최초"):
            return _cmp_ltv(delta, "LTV_FIRST_HOME", rule_engine.LTV_FIRST_HOME, afters)
        if _has(text, "서민", "실수요"):
            return _cmp_ltv(delta, "LTV_REAL_DEMAND", rule_engine.LTV_REAL_DEMAND, afters)
        return delta(None, None, Disposition.NEEDS_REVIEW, "예외 대상 매핑 불명")

    # --- LTV: 다주택 0% / 유주택 0% / 표준 40% ---
    if cat == "LTV":
        if _has(text, "다주택"):
            return _cmp_ltv(delta, "LTV_MULTI", rule_engine.LTV_MULTI, afters)
        if _has(text, "유주택"):
            return _cmp_ltv(delta, "LTV_OWNER", rule_engine.LTV_OWNER, afters)
        return _cmp_ltv(delta, "LTV_REGULATED_STANDARD",
                        rule_engine.LTV_REGULATED_STANDARD, afters)

    return delta(None, None, Disposition.NEEDS_REVIEW, "카테고리 매핑 불명")


def _cmp_ltv(delta_fn, field_name: str, engine_val: float,
             afters: list[float]) -> RuleDelta:
    """추출 after 퍼센트와 엔진 LTV 값을 대조해 disposition 결정."""
    eng = _pct(engine_val)
    if not afters:
        return delta_fn(field_name, eng, Disposition.NEEDS_REVIEW, "after 값 파싱 불가")
    if engine_val in afters:
        return delta_fn(field_name, eng, Disposition.MAPPED_CONSISTENT,
                        "추출 after가 엔진 현재값과 일치(범위 포함)")
    got = "~".join(_pct(a) for a in afters)
    return delta_fn(field_name, eng, Disposition.MAPPED_DIVERGENT,
                    f"추출 after({got}) ≠ 엔진({eng}) → 검토")


def build_proposal(extraction: Any, generated_on: Optional[date] = None) -> RuleChangeProposal:
    """RegChange 추출을 구조화 룰 변경안(초안)으로 변환한다.

    extraction 은 `.policy_id / .effective_from / .target_regions / .changes` 속성만 있으면 됨
    (RegChangeExtraction 또는 duck typing).
    """
    tr = list(getattr(extraction, "target_regions", []) or [])
    eff = getattr(extraction, "effective_from", None)
    deltas = [_map_change(c, eff, tr) for c in getattr(extraction, "changes", [])]
    return RuleChangeProposal(
        policy_id=getattr(extraction, "policy_id", "(unknown)"),
        effective_from=eff,
        deltas=deltas,
        approval_status="PENDING",
        generated_on=generated_on,
    )


# --------------------------------------------------------------------------- #
# 텍스트 리포트
# --------------------------------------------------------------------------- #
_DISP_MARK = {
    Disposition.MAPPED_CONSISTENT: "✓ 반영됨",
    Disposition.MAPPED_DIVERGENT: "▲ 검토(불일치)",
    Disposition.OUT_OF_SCOPE: "◦ 코어밖",
    Disposition.NEEDS_REVIEW: "? 검토",
}


def format_proposal(p: RuleChangeProposal) -> str:
    lines: list[str] = []
    lines.append(f"Rule Change Proposal (초안) — policy={p.policy_id}  "
                 f"effective={p.effective_from}  승인상태={p.approval_status}")
    lines.append("-" * 92)
    for d in p.deltas:
        ba = f"{d.extracted_before or '—'} → {d.extracted_after or '—'}"
        tgt = d.target_field or "-"
        lines.append(f"[{d.category:<14}] {_DISP_MARK[d.disposition]:<14} {tgt:<24} {ba}")
        if d.engine_current and d.disposition != Disposition.OUT_OF_SCOPE:
            lines.append(f"      엔진 현재값: {d.engine_current}"
                         + (f"   · {d.note}" if d.note else ""))
        elif d.note:
            lines.append(f"      {d.note}")
    lines.append("-" * 92)
    c = p.counts()
    lines.append(
        f"합계 {len(p.deltas)}건 | 반영 {c['MAPPED_CONSISTENT']} · "
        f"검토(불일치) {c['MAPPED_DIVERGENT']} · 코어밖 {c['OUT_OF_SCOPE']} · "
        f"검토필요 {c['NEEDS_REVIEW']}"
    )
    lines.append("주: 이 변경안은 AI 초안이며, LTV 판정은 사람이 확정한 룰엔진 출력입니다. "
                 "승인 전까지 적용되지 않습니다(자동 확정 없음).")
    return "\n".join(lines)
