"""Assurance 스코어카드 — 실측치를 임계와 대조해 dimension 별 판정을 낸다.

지표를 나열하는 것과 **통과했는지 판정하는 것**은 다르다. 판정이 없으면 숫자를 본 사람이
각자 기준으로 해석하게 되고, 그러면 검증 산출물이 아니다.

미측정은 **통과가 아니다.** 임계가 없거나 값이 없으면 `NOT_MEASURED` 로 표시하고,
dimension 판정에서도 통과로 세지 않는다 — 모르는 것을 통과로 처리하면 R-01 과 같은 실패다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from ..report.evidence import ValidationEvidence
from .thresholds import THRESHOLDS, Dimension, Threshold


class Verdict(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_MEASURED = "NOT_MEASURED"


@dataclass(frozen=True)
class MetricResult:
    threshold: Threshold
    value: Optional[float]
    evidence: str = ""              # 이 값이 어디서 나왔는지

    @property
    def verdict(self) -> Verdict:
        ok = self.threshold.passes(self.value)
        if ok is None:
            return Verdict.NOT_MEASURED
        return Verdict.PASS if ok else Verdict.FAIL

    @property
    def display(self) -> str:
        return "—" if self.value is None else f"{self.value:.0%}"


@dataclass
class DimensionResult:
    dimension: Dimension
    metrics: list[MetricResult] = field(default_factory=list)

    @property
    def verdict(self) -> Verdict:
        """하나라도 FAIL 이면 FAIL. 전부 미측정이면 NOT_MEASURED."""
        verdicts = [m.verdict for m in self.metrics]
        if Verdict.FAIL in verdicts:
            return Verdict.FAIL
        if all(v is Verdict.NOT_MEASURED for v in verdicts):
            return Verdict.NOT_MEASURED
        return Verdict.PASS

    @property
    def measured(self) -> int:
        return sum(1 for m in self.metrics if m.verdict is not Verdict.NOT_MEASURED)


@dataclass
class Scorecard:
    dimensions: list[DimensionResult]

    @property
    def all_metrics(self) -> list[MetricResult]:
        return [m for d in self.dimensions for m in d.metrics]

    @property
    def verdict(self) -> Verdict:
        vs = [d.verdict for d in self.dimensions]
        if Verdict.FAIL in vs:
            return Verdict.FAIL
        return Verdict.PASS if Verdict.PASS in vs else Verdict.NOT_MEASURED

    @property
    def failures(self) -> list[MetricResult]:
        return [m for m in self.all_metrics if m.verdict is Verdict.FAIL]

    @property
    def unmeasured(self) -> list[MetricResult]:
        return [m for m in self.all_metrics if m.verdict is Verdict.NOT_MEASURED]

    @property
    def high_risk_failures(self) -> list[MetricResult]:
        return [m for m in self.failures if m.threshold.high_risk]

    def summary(self) -> dict:
        return {
            "verdict": self.verdict.value,
            "total": len(self.all_metrics),
            "passed": sum(1 for m in self.all_metrics if m.verdict is Verdict.PASS),
            "failed": len(self.failures),
            "not_measured": len(self.unmeasured),
            "high_risk_failed": len(self.high_risk_failures),
        }


def _rate(passed: int, total: int) -> Optional[float]:
    return passed / total if total else None


def score(ev: ValidationEvidence, *, js_port_agreement: Optional[float] = None) -> Scorecard:
    """실측 evidence 를 임계와 대조한다.

    `js_port_agreement` 는 브라우저 포팅본 대조 결과(0~1). 대조를 돌리지 않았으면 None 이고,
    그러면 통과가 아니라 **미측정**으로 남는다.
    """
    g, s, r = ev.grounding, ev.gold_score, ev.regression
    by_cat = r.pass_rate_by_category()

    def cat_rate(name: str) -> Optional[float]:
        entry = by_cat.get(name)
        return entry[2] if entry else None

    values: dict[str, tuple[Optional[float], str]] = {
        "Citation Correctness": (
            g.citation_correctness, f"인용 {g.grounded}/{g.total} 이 원문에 verbatim 존재"),
        "Unsupported Claim Rate": (
            g.unsupported_claim_rate, f"근거 없는 주장 {g.ungrounded}/{g.total}"),
        "Change Completeness": (
            s.change_completeness,
            f"사람 확정 골드 필수 변경 {len(ev.gold.get('required_changes', []))}건 대조"),
        "Exception Recall": (
            s.exception_recall, f"골드 예외 {len(ev.gold.get('exceptions', []))}건 대조"),
        "Effective-date Accuracy": (
            1.0 if s.effective_date_correct else 0.0, f"추출 시행일 {ev.extraction.effective_from}"),
        "Region Accuracy": (
            1.0 if s.regions_correct else 0.0,
            f"지역 {len(ev.extraction.target_regions)}곳 · 미매핑 {len(ev.region_unmapped)}건"),
        "Policy Baseline Consistency": (
            1.0 if ev.drift.ok else 0.0,
            f"정책 {len(ev.registry.policies)}건 ↔ 지역 기준선 {ev.baseline_region_count}곳 양방향"),
        "Policy-version Consistency": (
            None, "시점 질의 골드(TEMPORAL 12문항)가 🤖 초안 — 사람 검수 후 측정 가동"),
        "Rule-regression Pass Rate": (
            r.pass_rate, f"독립 명세 오라클 대조 {r.passed}/{r.total}"),
        "Boundary-case Pass Rate": (
            cat_rate("BOUNDARY"), "컷오프·시행일 경계 케이스"),
        "Conflict-case Pass Rate": (
            cat_rate("CONFLICT"), "조건 충돌 케이스"),
        "JS Port Agreement": (
            js_port_agreement,
            "화면 JS 포팅본 ↔ Python 엔진 (tools/verify_js_port.mjs)"
            if js_port_agreement is not None else "대조를 실행하지 않았다"),
    }

    dims: dict[Dimension, DimensionResult] = {
        d: DimensionResult(dimension=d) for d in Dimension
    }
    for t in THRESHOLDS:
        value, evidence = values.get(t.metric, (None, "값 없음"))
        dims[t.dimension].metrics.append(
            MetricResult(threshold=t, value=value, evidence=evidence))

    return Scorecard(dimensions=list(dims.values()))
