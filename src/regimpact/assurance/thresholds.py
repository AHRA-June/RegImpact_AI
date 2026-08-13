"""Assurance 임계값 확정 (2026-08-13, Strict / Model Risk 보수).

사용자 확정(03_OPEN_QUESTIONS Q2 잔여 마감):
    - 프로파일: **Strict** — 고위험 지표 PASS 기준을 높게.
    - 종합 판정: **고위험(★) 지표가 FAIL이면 전체 FAIL**, 그 외 FAIL/WARN은 전체 WARN.

각 지표는 방향(higher/lower 좋음)과 pass/warn 경계를 가진다. metrics_spec.md §1~3의
high-risk 태그를 그대로 반영한다. 이 파일이 임계값의 단일 진실이다(LOCKED 성격).
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

DIMENSION_NAMES = {
    1: "Source Grounding & Citation",
    2: "Change & Exception Completeness",
    3: "Temporal / Policy-Version Consistency",
    4: "Rule Regression & Conflict",
}


class Status(str, Enum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


@dataclass(frozen=True)
class MetricSpec:
    key: str
    label: str
    dimension: int
    direction: str          # 'higher' = 값이 클수록 좋음, 'lower' = 작을수록 좋음
    pass_at: float
    warn_at: float
    high_risk: bool         # ★ 고위험(누락 시 LTV 오판·규제 전후 뒤바뀜 등)

    def evaluate(self, value: float) -> Status:
        if self.direction == "higher":
            if value >= self.pass_at:
                return Status.PASS
            if value >= self.warn_at:
                return Status.WARN
            return Status.FAIL
        # lower is better
        if value <= self.pass_at:
            return Status.PASS
        if value <= self.warn_at:
            return Status.WARN
        return Status.FAIL


# 확정 임계값 (Strict). exact=1.0 지표는 pass_at=warn_at=1.0 → 100% 아니면 FAIL(WARN 밴드 없음).
THRESHOLDS: dict[str, MetricSpec] = {
    # ① Source Grounding & Citation
    "citation_correctness": MetricSpec(
        "citation_correctness", "Citation Correctness", 1, "higher", 0.95, 0.90, False),
    "unsupported_claim_rate": MetricSpec(
        "unsupported_claim_rate", "Unsupported Claim Rate", 1, "lower", 0.05, 0.10, True),
    "source_contradiction_rate": MetricSpec(
        "source_contradiction_rate", "Source Contradiction Rate", 1, "lower", 0.0, 0.0, True),
    # ② Change & Exception Completeness
    "change_completeness": MetricSpec(
        "change_completeness", "Change Completeness", 2, "higher", 0.90, 0.80, True),
    "exception_recall": MetricSpec(
        "exception_recall", "Exception Recall", 2, "higher", 0.95, 0.90, True),
    "grandfathering_recall": MetricSpec(
        "grandfathering_recall", "Grandfathering Recall", 2, "higher", 0.95, 0.90, True),
    # ③ Temporal / Policy-Version Consistency
    "effective_date_accuracy": MetricSpec(
        "effective_date_accuracy", "Effective-date Accuracy", 3, "higher", 1.0, 1.0, True),
    "region_completeness": MetricSpec(
        "region_completeness", "Region Completeness", 3, "higher", 1.0, 1.0, True),
    "policy_version_consistency": MetricSpec(
        "policy_version_consistency", "Policy-version Consistency", 3, "higher", 1.0, 1.0, True),
    # ④ Rule Regression & Conflict
    "rule_regression_pass_rate": MetricSpec(
        "rule_regression_pass_rate", "Rule-regression Pass Rate", 4, "higher", 1.0, 1.0, True),
    "boundary_pass_rate": MetricSpec(
        "boundary_pass_rate", "Boundary-case Pass Rate", 4, "higher", 1.0, 1.0, False),
    "conflict_pass_rate": MetricSpec(
        "conflict_pass_rate", "Conflict-case Pass Rate", 4, "higher", 1.0, 1.0, True),
}


def overall_status(statuses: list[tuple[Status, bool]]) -> Status:
    """종합 판정. (status, high_risk) 목록에서: 고위험 FAIL→FAIL, 그 외 FAIL/WARN→WARN, else PASS."""
    if any(s == Status.FAIL and hr for s, hr in statuses):
        return Status.FAIL
    if any(s in (Status.FAIL, Status.WARN) for s, _ in statuses):
        return Status.WARN
    return Status.PASS
