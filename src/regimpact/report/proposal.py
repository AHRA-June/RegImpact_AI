"""Structured Rule Change Proposal — 추출된 RegChange를 '검토 가능한 규칙 변경안'으로 구조화.

브리프 코어라인의 노드: `… → Impact Matrix → Structured Rule Proposal → Test Cases → …`.
이 노드는 새 규칙값을 만들지 않는다(LOCKED §4). 확정 명세(rule_engine 상수)에서 값을 가져오고,
LLM 추출(RegChangeExtraction)에서 근거·시행일·대상지역을 가져와 **사람이 승인/반려할 초안**으로
조립한다. 승인 워크플로(§4 "AI초안→사람확정")의 대상 산출물.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ..extractor.schema import RegChangeExtraction
from ..rule_engine import (
    LTV_BASELINE,
    LTV_FIRST_HOME,
    LTV_MULTI,
    LTV_OWNER,
    LTV_REAL_DEMAND,
    LTV_REGULATED_STANDARD,
)


@dataclass(frozen=True)
class LtvRuleLine:
    """규칙 변경안 1행 (차주 유형별 before→after LTV)."""
    borrower: str
    before_ltv: Optional[float]   # 종전규정(非규제 수도권 무주택 기준선 등). None=명세 미정
    after_ltv: Optional[float]    # 신규규정. None=명세 미정(escalation)
    rule_id: str
    note: str = ""


@dataclass
class RuleChangeProposal:
    """구조화 규칙 변경안 (승인 대기 초안)."""
    policy_id: str
    effective_from: Optional[str]
    target_regions: list[str]
    ltv_lines: list[LtvRuleLine] = field(default_factory=list)
    grandfathering: str = ""
    citations: list[str] = field(default_factory=list)   # "doc_id: quote" 요약
    approval_status: str = "PENDING_HUMAN_APPROVAL"       # §4 워크플로


def build_proposal(extraction: RegChangeExtraction) -> RuleChangeProposal:
    """추출 결과 + 확정 명세값으로 규칙 변경안을 조립한다.

    LTV 값은 rule_engine 상수(확정 명세)에서만 온다. 추출은 '무엇이/언제/어디서 바뀌었나'의
    근거(citation)와 메타(시행일·대상지역)를 제공한다. 값과 근거의 출처를 분리 → 검증 가능.
    """
    # 확정 명세의 규제지역 LTV 표 (before=종전 무주택 기준선 70%)
    lines = [
        LtvRuleLine("무주택 일반 / 처분조건부 1주택", LTV_BASELINE, LTV_REGULATED_STANDARD,
                    "REG_STD"),
        LtvRuleLine("생애최초", LTV_BASELINE, LTV_FIRST_HOME, "REG_FIRSTHOME",
                    "예외 — 변동 없음(좌동)"),
        LtvRuleLine("서민·실수요자", LTV_BASELINE, LTV_REAL_DEMAND, "REG_REALDEMAND"),
        LtvRuleLine("유주택(비처분 1주택 이상)", LTV_BASELINE, LTV_OWNER, "REG_OWNER_0",
                    "사실상 대출 거절"),
        LtvRuleLine("다주택", LTV_BASELINE, LTV_MULTI, "MULTI_0", "사실상 대출 거절"),
    ]

    grandfathering = next(
        (c.summary for c in extraction.changes if c.category == "GRANDFATHERING"),
        "경과규정: 2026-06-30까지 접수/계약+계약금/토허제 신청 → 종전규정 적용",
    )
    citations = [
        f"{c.citation.source_doc_id}: {c.citation.quote[:60].strip()}…"
        for c in extraction.changes
        if c.citation and c.citation.quote
    ]

    return RuleChangeProposal(
        policy_id=extraction.policy_id,
        effective_from=extraction.effective_from,
        target_regions=list(extraction.target_regions),
        ltv_lines=lines,
        grandfathering=grandfathering,
        citations=citations,
    )
