"""RegChangeExtraction(LLM 추출) → RuleChangeProposal 결정적 조립.

거버넌스: LLM은 인용 근거가 붙은 사실(before/after 값·시행일·예외·경과규정)만 추출하고,
이 코드가 그 추출을 구조화 변경안으로 **deterministic하게** 조립한다. LLM이 변경안 전체를
자유서술로 생성하지 않으므로 hallucination 표면적이 줄고, 각 필드는 추출 인용으로 추적된다.
"""
from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Optional

from ..extractor.schema import RegChangeExtraction, RegChangeItem
from .schema import (
    ChangeType,
    Grandfathering,
    ProposalSource,
    ProposalStatus,
    RuleChangeProposal,
    RuleState,
)

DEFAULT_RULE_ID = "MORTGAGE_LTV_REGULATED_REGION"

# 예외 표현 → 표준 예외 코드 (룰엔진/reason_code 정렬).
_EXCEPTION_KEYWORDS = [
    ("FIRST_HOME_BUYER", ("생애최초",)),
    ("REAL_DEMAND", ("서민", "실수요")),
    ("POLICY_MORTGAGE", ("정책", "디딤돌", "보금자리")),
]

# LTV 항목 → 세그먼트. 정책 하나가 세그먼트별로 다른 LTV를 정하므로 스칼라 하나로는
# 담을 수 없다. 아래 어디에도 걸리지 않으면 STANDARD(규제지역·무주택 일반)로 본다.
_LTV_SEGMENTS = [
    ("FIRST_HOME_BUYER", ("생애최초",)),
    ("REAL_DEMAND", ("서민", "실수요")),
    ("MULTI_HOME", ("다주택",)),
    ("OWNER", ("유주택",)),
    ("POLICY_MORTGAGE", ("디딤돌", "보금자리", "정책모기지", "정책대출")),
]
STANDARD_SEGMENT = "STANDARD"

# 경과규정 표현 → 표준 조건 코드 (grandfathering.py 정렬).
_GRANDFATHERING_KEYWORDS = [
    ("APPLICATION_ACCEPTED", ("접수",)),
    ("CONTRACT_SIGNED_AND_DOWNPAYMENT_PROVEN", ("계약금", "계약")),
    ("LAND_PERMIT_APPLIED", ("토지거래", "허가")),
]


def parse_ltv(s: Optional[str]) -> Optional[float]:
    """'70%'·'0.70' 등을 소수 LTV(0.70)로 파싱. LTV가 아니면 None.

    **맨숫자는 받지 않는다.** 이전 판은 마지막 fallback으로 아무 정수나 집어
    100으로 나눴는데, 그 탓에 "최대한도 6억원 제한"이 LTV 0.06, "최대 만기 30년"이
    LTV 0.30이 되어 없는 값이 만들어졌다. 비율 표기(%)나 0~1 소수만 LTV로 본다.
    """
    if not s:
        return None
    m = re.search(r"(\d+(?:\.\d+)?)\s*%", s)
    if m:
        return round(float(m.group(1)) / 100, 4)
    m = re.fullmatch(r"\s*(0?\.\d+|1(?:\.0+)?)\s*", s)
    if m:
        return round(float(m.group(1)), 4)
    return None


def _year_of(iso: Optional[str]) -> Optional[int]:
    return int(iso[:4]) if iso and len(iso) >= 4 and iso[:4].isdigit() else None


def parse_kr_date(text: str, *, year_hint: Optional[int] = None) -> Optional[str]:
    """ISO / '2026년 6월 30일' / '2026.6.30' / '6.30' 을 ISO 문자열로. 실패 시 None.

    연도가 없는 '6.30일' 표기는 `year_hint`(보통 시행일의 연도)로 보정한다.
    공문이 연도를 생략하는 것은 같은 해를 뜻하므로 추정이 아니라 표기 복원이다.
    """
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", text)
    if m:
        return m.group(0)
    m = re.search(r"(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일", text)
    if m:
        y, mo, d = (int(g) for g in m.groups())
        return f"{y:04d}-{mo:02d}-{d:02d}"
    m = re.search(r"(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})", text)
    if m:
        y, mo, d = (int(g) for g in m.groups())
        return f"{y:04d}-{mo:02d}-{d:02d}"
    m = re.search(r"(?<!\d)(\d{1,2})\.\s*(\d{1,2})\s*일", text)
    if m and year_hint:
        mo, d = (int(g) for g in m.groups())
        return f"{year_hint:04d}-{mo:02d}-{d:02d}"
    return None


def _segment_of(text: str) -> str:
    for seg, keywords in _LTV_SEGMENTS:
        if any(k in text for k in keywords):
            return seg
    return STANDARD_SEGMENT


def _modal(values: list) -> tuple[Optional[float], bool]:
    """최빈값과 충돌 여부. 동률이면 (None, True) — 조용히 하나를 고르지 않는다."""
    if not values:
        return None, False
    counts: dict = {}
    for v in values:
        counts[v] = counts.get(v, 0) + 1
    top = max(counts.values())
    winners = [v for v, c in counts.items() if c == top]
    conflict = len(counts) > 1
    if len(winners) > 1:
        return None, True
    return winners[0], conflict


def _match_codes(text: str, table: list[tuple[str, tuple[str, ...]]]) -> list[str]:
    codes: list[str] = []
    for code, keywords in table:
        if any(k in text for k in keywords) and code not in codes:
            codes.append(code)
    return codes


def _source_from_item(field_name: str, policy_id: str, item: RegChangeItem) -> ProposalSource:
    return ProposalSource(
        field_name=field_name,
        policy_id=policy_id,
        source_doc_id=item.citation.source_doc_id,
        evidence_span=item.citation.quote,
    )


def build_proposal_from_extraction(
    extraction: RegChangeExtraction,
    *,
    rule_id: str = DEFAULT_RULE_ID,
    change_type: ChangeType = ChangeType.MODIFY,
) -> RuleChangeProposal:
    """추출 결과를 구조화 변경안으로 조립한다(status=DRAFT).

    카테고리별 매핑:
      LTV           → before/after.max_ltv
      REGION        → after.target_regions + region_status 전환
      EFFECTIVE_DATE→ after.effective_from
      EXCEPTION     → exceptions[]
      GRANDFATHERING→ grandfathering{cutoff, conditions}
    각 매핑은 해당 추출 항목의 citation을 sources[]에 근거로 남긴다.
    """
    before = RuleState(region_status="NON_REGULATED")
    after = RuleState(
        region_status="REGULATED",
        target_regions=list(extraction.target_regions),
        effective_from=extraction.effective_from,
    )
    exceptions: list[str] = []
    grandfathering: Optional[Grandfathering] = None
    sources: list[ProposalSource] = []
    summary_bits: list[str] = []
    conflicts: list[str] = []
    unmapped: list[str] = []

    # 세그먼트별로 관측된 (before, after) 를 모은다. 정책 하나가 세그먼트마다 다른 LTV를
    # 정하므로, 항목을 순회하며 스칼라 하나에 덮어쓰면 마지막 항목이 이겨버린다.
    seg_before: dict[str, list[float]] = {}
    seg_after: dict[str, list[float]] = {}
    gf_texts: list[str] = []
    gf_conditions: list[str] = []

    for item in extraction.changes:
        cat = item.category
        text = f"{item.summary} {item.before or ''} {item.after or ''}"
        if cat == "LTV":
            b, a = parse_ltv(item.before), parse_ltv(item.after)
            if b is None and a is None:
                # 'LTV'로 분류됐지만 비율이 없는 항목(전입의무·만기·한도 제한 등).
                # 조용히 버리면 변경안이 원문보다 작아진다 → 사람이 보도록 남긴다.
                unmapped.append(item.summary)
                continue
            seg = _segment_of(text)
            if b is not None:
                seg_before.setdefault(seg, []).append(b)
            if a is not None:
                seg_after.setdefault(seg, []).append(a)
            sources.append(_source_from_item(f"ltv_by_segment.{seg}", extraction.policy_id, item))
            if seg == STANDARD_SEGMENT:
                summary_bits.append(item.summary)
        elif cat == "REGION":
            if not after.target_regions and extraction.target_regions:
                after.target_regions = list(extraction.target_regions)
            sources.append(_source_from_item("after.target_regions", extraction.policy_id, item))
        elif cat == "EFFECTIVE_DATE":
            iso = parse_kr_date(item.after or "", year_hint=_year_of(extraction.effective_from))
            if iso:
                after.effective_from = iso
            sources.append(_source_from_item("after.effective_from", extraction.policy_id, item))
        elif cat == "EXCEPTION":
            for code in _match_codes(text, _EXCEPTION_KEYWORDS):
                if code not in exceptions:
                    exceptions.append(code)
            sources.append(_source_from_item("exceptions", extraction.policy_id, item))
        elif cat == "GRANDFATHERING":
            gf_texts.append(text)
            for code in _match_codes(text, _GRANDFATHERING_KEYWORDS):
                if code not in gf_conditions:
                    gf_conditions.append(code)
            sources.append(_source_from_item("grandfathering", extraction.policy_id, item))
        # SCOPE_LIMIT 등 Discovery 항목은 변경안 코어에 넣지 않는다(브리프 §5.2).

    # --- 세그먼트별 LTV 확정 + 충돌 기록 ---
    for seg in sorted(set(seg_before) | set(seg_after)):
        b_val, b_conf = _modal(seg_before.get(seg, []))
        a_val, a_conf = _modal(seg_after.get(seg, []))
        if a_val is not None:
            after.ltv_by_segment[seg] = a_val
        if b_val is not None:
            before.ltv_by_segment[seg] = b_val
        if b_conf:
            conflicts.append(
                f"{seg} before 값 불일치: {sorted(set(seg_before[seg]))} → 최빈값 {b_val} 채택"
            )
        if a_conf:
            conflicts.append(
                f"{seg} after 값 불일치: {sorted(set(seg_after[seg]))} → 최빈값 {a_val} 채택"
            )
    before.max_ltv = before.ltv_by_segment.get(STANDARD_SEGMENT)
    after.max_ltv = after.ltv_by_segment.get(STANDARD_SEGMENT)

    # --- 경과규정 컷오프 ---
    if gf_texts:
        cutoff = None
        for t in gf_texts:
            cutoff = parse_kr_date(t, year_hint=_year_of(after.effective_from))
            if cutoff:
                break
        if cutoff is None and after.effective_from and any(
            k in " ".join(gf_texts) for k in ("전일", "직전", "이전")
        ):
            # 원문이 "효력발생일 전일"이라고 말하면서 날짜를 안 적은 경우.
            # 값을 지어내는 것이 아니라 원문이 정의한 관계를 계산하는 것이다.
            cutoff = (date.fromisoformat(after.effective_from) - timedelta(days=1)).isoformat()
        grandfathering = Grandfathering(cutoff_date=cutoff, conditions=gf_conditions)

    summary = "; ".join(summary_bits) or f"{rule_id} {change_type.value}"
    return RuleChangeProposal(
        rule_id=rule_id,
        change_type=change_type,
        before=before,
        after=after,
        exceptions=exceptions,
        grandfathering=grandfathering,
        sources=sources,
        status=ProposalStatus.DRAFT,
        summary=summary,
        conflicts=conflicts,
        unmapped=unmapped,
    )
