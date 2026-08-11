"""RegChangeExtraction(LLM 추출) → RuleChangeProposal 결정적 조립.

거버넌스: LLM은 인용 근거가 붙은 사실(before/after 값·시행일·예외·경과규정)만 추출하고,
이 코드가 그 추출을 구조화 변경안으로 **deterministic하게** 조립한다. LLM이 변경안 전체를
자유서술로 생성하지 않으므로 hallucination 표면적이 줄고, 각 필드는 추출 인용으로 추적된다.
"""
from __future__ import annotations

import re
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

# 경과규정 표현 → 표준 조건 코드 (grandfathering.py 정렬).
_GRANDFATHERING_KEYWORDS = [
    ("APPLICATION_ACCEPTED", ("접수",)),
    ("CONTRACT_SIGNED_AND_DOWNPAYMENT_PROVEN", ("계약금", "계약")),
    ("LAND_PERMIT_APPLIED", ("토지거래", "허가")),
]


def parse_ltv(s: Optional[str]) -> Optional[float]:
    """'70%'·'70'·'0.70'·'0.7' 등을 소수 LTV(0.70)로 파싱. 실패 시 None."""
    if not s:
        return None
    m = re.search(r"(\d+(?:\.\d+)?)\s*%", s)
    if m:
        return round(float(m.group(1)) / 100, 4)
    m = re.search(r"(\d+(?:\.\d+)?)", s)
    if not m:
        return None
    val = float(m.group(1))
    return round(val, 4) if val <= 1.0 else round(val / 100, 4)


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

    for item in extraction.changes:
        cat = item.category
        if cat == "LTV":
            b, a = parse_ltv(item.before), parse_ltv(item.after)
            if b is not None:
                before.max_ltv = b
            if a is not None:
                after.max_ltv = a
            sources.append(_source_from_item("after.max_ltv", extraction.policy_id, item))
            summary_bits.append(item.summary)
        elif cat == "REGION":
            if not after.target_regions and extraction.target_regions:
                after.target_regions = list(extraction.target_regions)
            sources.append(_source_from_item("after.target_regions", extraction.policy_id, item))
        elif cat == "EFFECTIVE_DATE":
            if item.after:
                # 시행일이 항목에 명시되면 우선
                m = re.search(r"\d{4}-\d{2}-\d{2}", item.after)
                if m:
                    after.effective_from = m.group(0)
            sources.append(_source_from_item("after.effective_from", extraction.policy_id, item))
        elif cat == "EXCEPTION":
            for code in _match_codes(item.summary + " " + (item.after or ""), _EXCEPTION_KEYWORDS):
                if code not in exceptions:
                    exceptions.append(code)
            sources.append(_source_from_item("exceptions", extraction.policy_id, item))
        elif cat == "GRANDFATHERING":
            conds = _match_codes(item.summary + " " + (item.after or "") + " " + (item.before or ""),
                                 _GRANDFATHERING_KEYWORDS)
            cutoff = None
            m = re.search(r"\d{4}-\d{2}-\d{2}", (item.before or "") + " " + (item.after or "") + " " + item.summary)
            if m:
                cutoff = m.group(0)
            grandfathering = Grandfathering(cutoff_date=cutoff, conditions=conds)
            sources.append(_source_from_item("grandfathering", extraction.policy_id, item))
        # SCOPE_LIMIT 등 Discovery 항목은 변경안 코어에 넣지 않는다(브리프 §5.2).

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
    )
