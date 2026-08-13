"""골드셋 채점 — 전부 결정적 (LOCKED §4 금지선: LLM이 LLM 채점 금지).

두 축:
1) scenario 채점: `scenario_input`을 가진 아이템은 MortgageApplication으로 만들어
   **룰엔진(deterministic)** 에 넣고 기대 LTV/status/escalation과 대조한다.
   룰엔진은 tc_generator 오라클로 이미 검증됐고, 골드는 사람이 원문에서 확정한 값이므로
   이 대조는 '엔진이 사람 확정 사실과 일치하는가'의 수용 테스트다(순환 아님).
2) grounding 채점: `source_quote`를 가진 아이템은 그 인용이 원문에 verbatim 존재하는지
   확인한다(골드셋 자체의 근거 무결성 게이트). extractor.evaluate와 동일 정규화.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from ..models import EvaluationStatus, LoanPurpose, MortgageApplication
from ..rule_engine import evaluate
from .schema import GoldCategory, GoldItem

_ESCALATION_STATUSES = {EvaluationStatus.NEEDS_HUMAN_REVIEW, EvaluationStatus.DISCOVERY}

_DATE_FIELDS = (
    "evaluation_date", "application_accepted_at", "contract_signed_at",
    "downpayment_paid_at", "land_permit_applied_at",
)


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def build_application(scenario_input: dict) -> MortgageApplication:
    """scenario_input dict → MortgageApplication (날짜 문자열/enum 파싱)."""
    kw = dict(scenario_input)
    for f in _DATE_FIELDS:
        if kw.get(f):
            kw[f] = date.fromisoformat(kw[f])
    if "loan_purpose" in kw and kw["loan_purpose"] is not None:
        kw["loan_purpose"] = LoanPurpose(kw["loan_purpose"])
    return MortgageApplication(**kw)


@dataclass
class ItemResult:
    item: GoldItem
    passed: bool
    detail: str


@dataclass
class ScenarioScore:
    results: list[ItemResult] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def accuracy(self) -> float:
        return 1.0 if self.total == 0 else self.passed / self.total

    @property
    def failures(self) -> list[ItemResult]:
        return [r for r in self.results if not r.passed]

    def by_category(self) -> dict[str, tuple[int, int]]:
        out: dict[str, tuple[int, int]] = {}
        for cat in GoldCategory:
            subset = [r for r in self.results if r.item.category == cat]
            if not subset:
                continue
            out[cat.value] = (sum(1 for r in subset if r.passed), len(subset))
        return out

    def escalation_metrics(self) -> dict[str, float]:
        """Escalation Recall/Precision (metrics_spec §4) — scenario 아이템 기준.

        recall = 기대 escalation 중 엔진이 escalate한 비율
        precision = 엔진이 escalate한 것 중 실제 기대 escalation 비율
        """
        tp = fp = fn = 0
        for r in self.results:
            if r.item.scenario_input is None:
                continue
            actual = evaluate(build_application(r.item.scenario_input))
            actual_esc = actual.status in _ESCALATION_STATUSES
            expected_esc = r.item.expects_escalation
            if expected_esc and actual_esc:
                tp += 1
            elif not expected_esc and actual_esc:
                fp += 1
            elif expected_esc and not actual_esc:
                fn += 1
        recall = tp / (tp + fn) if (tp + fn) else 1.0
        precision = tp / (tp + fp) if (tp + fp) else 1.0
        return {"recall": recall, "precision": precision, "tp": tp, "fp": fp, "fn": fn}


def score_scenario_items(items: list[GoldItem]) -> ScenarioScore:
    """scenario_input을 가진 아이템을 룰엔진으로 결정적 채점한다."""
    results: list[ItemResult] = []
    for it in items:
        if it.scenario_input is None:
            continue
        actual = evaluate(build_application(it.scenario_input))
        actual_esc = actual.status in _ESCALATION_STATUSES

        mm: list[str] = []
        if it.expected_status is not None and actual.status.value != it.expected_status:
            mm.append(f"status {actual.status.value}≠{it.expected_status}")
        if it.expected_ltv is not None and actual.max_ltv != it.expected_ltv:
            mm.append(f"ltv {actual.max_ltv}≠{it.expected_ltv}")
        if actual_esc != it.expects_escalation:
            mm.append(f"escalation {actual_esc}≠{it.expects_escalation}")

        results.append(ItemResult(item=it, passed=not mm, detail="; ".join(mm) or "ok"))
    return ScenarioScore(results=results)


@dataclass
class GroundingResult:
    total: int
    grounded: int
    ungrounded: list[GoldItem]

    @property
    def rate(self) -> float:
        return 1.0 if self.total == 0 else self.grounded / self.total


def check_goldset_grounding(items: list[GoldItem], sources: dict[str, str]) -> GroundingResult:
    """source_quote를 가진 아이템의 인용이 원문에 verbatim 존재하는지 확인(근거 무결성)."""
    norm_sources = {k: _norm(v) for k, v in sources.items()}
    grounded = 0
    ungrounded: list[GoldItem] = []
    checkable = [it for it in items if it.source_quote and it.source_doc_id in norm_sources]
    for it in checkable:
        if _norm(it.source_quote) in norm_sources[it.source_doc_id]:
            grounded += 1
        else:
            ungrounded.append(it)
    return GroundingResult(total=len(checkable), grounded=grounded, ungrounded=ungrounded)
