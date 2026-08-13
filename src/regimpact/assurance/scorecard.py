"""Assurance 스코어카드 — 4 dimension 지표를 확정 임계값으로 판정·집계.

원시 지표(metrics.compute_metrics) × 확정 임계값(thresholds.THRESHOLDS) → PASS/WARN/FAIL.
차원별·전체 종합 판정(고위험 FAIL → 전체 FAIL). validation 보고서에 요약을 넘길 수 있다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .metrics import compute_metrics
from .thresholds import (
    DIMENSION_NAMES,
    THRESHOLDS,
    MetricSpec,
    Status,
    overall_status,
)


@dataclass(frozen=True)
class MetricResult:
    spec: MetricSpec
    value: float
    status: Status

    @property
    def high_risk(self) -> bool:
        return self.spec.high_risk


@dataclass
class DimensionResult:
    dimension: int
    name: str
    metrics: list[MetricResult] = field(default_factory=list)

    @property
    def status(self) -> Status:
        return overall_status([(m.status, m.high_risk) for m in self.metrics])


@dataclass
class AssuranceScorecard:
    dimensions: list[DimensionResult] = field(default_factory=list)

    @property
    def all_metrics(self) -> list[MetricResult]:
        return [m for d in self.dimensions for m in d.metrics]

    @property
    def overall(self) -> Status:
        return overall_status([(m.status, m.high_risk) for m in self.all_metrics])

    @property
    def failed(self) -> list[MetricResult]:
        return [m for m in self.all_metrics if m.status == Status.FAIL]

    def summary(self) -> dict[str, str]:
        """validation 보고서 assurance dict용. '지표: 값 (STATUS)'."""
        out = {m.spec.label: f"{m.value:.0%} ({m.status.value})" for m in self.all_metrics}
        out["Overall"] = self.overall.value
        return out

    def dimension_summary(self) -> dict[str, str]:
        """차원별 요약(간결) — validation 보고서 타일용. '① 이름: STATUS'."""
        circ = {1: "①", 2: "②", 3: "③", 4: "④"}
        out = {f"{circ[d.dimension]} {d.name}": d.status.value
               for d in self.dimensions if d.metrics}
        out["Overall"] = self.overall.value
        return out


def build_scorecard(extraction, sources, gold, regression=None) -> AssuranceScorecard:
    """원시 지표를 계산하고 확정 임계값으로 판정한 스코어카드를 만든다."""
    values = compute_metrics(extraction, sources, gold, regression)
    dims: dict[int, DimensionResult] = {
        d: DimensionResult(dimension=d, name=name) for d, name in DIMENSION_NAMES.items()
    }
    for key, value in values.items():
        spec = THRESHOLDS[key]
        dims[spec.dimension].metrics.append(
            MetricResult(spec=spec, value=value, status=spec.evaluate(value))
        )
    return AssuranceScorecard(dimensions=[dims[d] for d in sorted(dims)])


_MARK = {Status.PASS: "✅", Status.WARN: "⚠️", Status.FAIL: "❌"}


def format_scorecard_md(sc: AssuranceScorecard) -> str:
    """스코어카드를 마크다운으로 렌더."""
    L = ["# Assurance Scorecard (4 dimension, 확정 임계값 Strict)", ""]
    L.append(f"**종합 판정: {_MARK[sc.overall]} {sc.overall.value}**"
             " — 고위험(★) 지표 FAIL 시 전체 FAIL.")
    L.append("")
    for d in sc.dimensions:
        if not d.metrics:
            continue
        L.append(f"## Dimension {d.dimension}. {d.name} — {_MARK[d.status]} {d.status.value}")
        L.append("| 지표 | 값 | 임계(Strict) | 고위험 | 판정 |")
        L.append("|---|---|---|---|---|")
        for m in d.metrics:
            direction = "≥" if m.spec.direction == "higher" else "≤"
            thr = f"{direction}{m.spec.pass_at:.0%}"
            hr = "★" if m.high_risk else ""
            L.append(f"| {m.spec.label} | {m.value:.0%} | {thr} | {hr} | {_MARK[m.status]} {m.status.value} |")
        L.append("")
    if sc.failed:
        L.append("## FAIL 지표")
        for m in sc.failed:
            L.append(f"- {m.spec.label}: {m.value:.0%} (임계 {m.spec.pass_at:.0%})")
        L.append("")
    L.append("> 임계값 출처: `src/regimpact/assurance/thresholds.py`(확정 2026-08-13, Strict).")
    L.append("> 지표는 6·30 단일 앵커 기준(n=1 문서셋). 오라클은 challenger(제3자 벤치마크 아님).")
    return "\n".join(L)
