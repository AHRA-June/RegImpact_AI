"""Impact Matrix 산출 — 룰엔진 before/after 차등 실행.

핵심: 각 세그먼트를 시행 전(before)·후(after) 두 시점에 deterministic 룰엔진으로
실행하고 그 델타를 구조화한다. 이 매트릭스의 모든 LTV 값은 **엔진 실제 출력**이며,
하드코딩이 아니다(UI/Stitch 목업의 하드코딩값을 이 출력으로 교체하는 것이 목표).

축(axis) 정의:
- before(기존) = 시행 전일(2026-06-30) + 경과규정 이벤트 제거 → 구규제 기준선.
- after(변경)  = 시행 후(2026-07-02) + 모든 속성/이벤트 → 신규제 적용값.

정직성(브리프 §5, LOCKED §4): 유주택/다주택의 '기존 LTV'는 명세에 기준선이 없어
엔진이 NEEDS_HUMAN_REVIEW를 반환한다. 이를 임의로 70%로 채우지 않고 그대로 노출한다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional

from ..models import EvaluationStatus, LtvDecision
from ..rule_engine import evaluate
from .segments import Segment, SIX_THIRTY_SEGMENTS

# 6·30 before/after 기준 시점 (regions.REG_EFFECTIVE = 2026-07-01).
BEFORE_DATE = date(2026, 6, 30)   # 규제 효력 발생 전일 = 구규제 기준선
AFTER_DATE = date(2026, 7, 2)     # 규제 효력 발생 후 = 신규제 적용
POLICY_ID = "SIX_THIRTY_2026"


class ImpactDirection(str, Enum):
    """before→after LTV 변화 방향."""
    TIGHTENED = "TIGHTENED"        # 하향(규제강화): after < before
    EASED = "EASED"                # 상향(완화): after > before
    UNCHANGED = "UNCHANGED"        # 동일 (예외/경과규정 등으로 유지 포함)
    BASELINE_GAP = "BASELINE_GAP"  # before 기준부재(검토필요) → 델타 계산 불가
    NON_CORE = "NON_CORE"          # Discovery / Out-of-scope (자동판정 제외)


_DIRECTION_LABEL = {
    ImpactDirection.TIGHTENED: "규제강화(하향)",
    ImpactDirection.EASED: "완화(상향)",
    ImpactDirection.UNCHANGED: "동일",
    ImpactDirection.BASELINE_GAP: "기준부재→검토",
    ImpactDirection.NON_CORE: "코어 외(Discovery)",
}

# 코어 자동판정으로 볼 수 없는 상태 (매트릭스에는 표시하되 델타 산출 제외).
_NON_CORE_STATUSES = {EvaluationStatus.DISCOVERY, EvaluationStatus.OUT_OF_SCOPE}


def _ltv_display(d: LtvDecision) -> str:
    """LtvDecision을 표 셀 문자열로."""
    if d.status == EvaluationStatus.DECIDED and d.max_ltv is not None:
        return f"{d.max_ltv:.0%}"
    if d.status == EvaluationStatus.NEEDS_HUMAN_REVIEW:
        return "검토필요(기준부재)"
    if d.status == EvaluationStatus.DISCOVERY:
        return "Discovery"
    if d.status == EvaluationStatus.OUT_OF_SCOPE:
        return "대상외"
    return d.status.value


@dataclass
class ImpactRow:
    """매트릭스 한 행 = 한 세그먼트의 before/after 룰엔진 판정과 그 델타."""

    segment: Segment
    before: LtvDecision
    after: LtvDecision

    # ── 표시용 파생값 ──
    @property
    def region_label(self) -> str:
        return self.segment.region_label

    @property
    def borrower_type(self) -> str:
        return self.segment.borrower_type

    @property
    def ltv_before(self) -> Optional[float]:
        return self.before.max_ltv if self.before.status == EvaluationStatus.DECIDED else None

    @property
    def ltv_after(self) -> Optional[float]:
        return self.after.max_ltv if self.after.status == EvaluationStatus.DECIDED else None

    @property
    def before_display(self) -> str:
        return _ltv_display(self.before)

    @property
    def after_display(self) -> str:
        return _ltv_display(self.after)

    @property
    def grandfathering(self) -> bool:
        return bool(self.after.grandfathering_applied)

    @property
    def review_required(self) -> bool:
        """after가 사람 검토를 요구하는가(코어 자동판정 불가)."""
        return self.after.status == EvaluationStatus.NEEDS_HUMAN_REVIEW

    @property
    def is_core(self) -> bool:
        """코어 자동판정 대상인가(Discovery/대상외 아님)."""
        return self.after.status not in _NON_CORE_STATUSES

    @property
    def reason_codes(self) -> list[str]:
        return list(self.after.reason_codes)

    @property
    def applicable_rule_id(self) -> Optional[str]:
        return self.after.applicable_rule_id

    @property
    def delta_pp(self) -> Optional[float]:
        """LTV 변화폭(percentage point). 양측 모두 수치일 때만."""
        b, a = self.ltv_before, self.ltv_after
        if b is None or a is None:
            return None
        return round((a - b) * 100, 1)

    @property
    def direction(self) -> ImpactDirection:
        if self.after.status in _NON_CORE_STATUSES:
            return ImpactDirection.NON_CORE
        b, a = self.ltv_before, self.ltv_after
        if a is None:
            # after가 검토필요 등 → 방향 미정, 사실상 기준부재로 분류
            return ImpactDirection.BASELINE_GAP
        if b is None:
            # before 기준부재(유주택 등) 인데 after는 확정 → 델타 계산 불가
            return ImpactDirection.BASELINE_GAP
        if a < b:
            return ImpactDirection.TIGHTENED
        if a > b:
            return ImpactDirection.EASED
        return ImpactDirection.UNCHANGED

    @property
    def changed(self) -> bool:
        """실질 변화가 있는가(동일/코어외가 아님)."""
        return self.direction in (
            ImpactDirection.TIGHTENED,
            ImpactDirection.EASED,
            ImpactDirection.BASELINE_GAP,
        )

    @property
    def high_impact(self) -> bool:
        """고영향 행 — LTV가 0%로 떨어지거나(대출불가) 15%p 이상 하향, 또는 기준부재.

        metrics_spec 'high-risk failure 정의'와 정렬: 경과규정·시행일·예외 오판이
        regime을 뒤바꾸는 케이스가 위험하며, 그 결과가 드러나는 행을 표시한다.
        """
        if self.direction == ImpactDirection.BASELINE_GAP:
            return True
        if self.ltv_after == 0.0 and self.direction == ImpactDirection.TIGHTENED:
            return True
        dpp = self.delta_pp
        return dpp is not None and dpp <= -15.0

    def to_dict(self) -> dict:
        return {
            "segment_id": self.segment.segment_id,
            "region_code": self.segment.region_code,
            "region_label": self.region_label,
            "borrower_type": self.borrower_type,
            "ltv_before": self.ltv_before,
            "ltv_after": self.ltv_after,
            "before_display": self.before_display,
            "after_display": self.after_display,
            "delta_pp": self.delta_pp,
            "direction": self.direction.value,
            "direction_label": _DIRECTION_LABEL[self.direction],
            "changed": self.changed,
            "grandfathering": self.grandfathering,
            "review_required": self.review_required,
            "is_core": self.is_core,
            "high_impact": self.high_impact,
            "applicable_rule_id": self.applicable_rule_id,
            "reason_codes": self.reason_codes,
            "source_policy_ids": list(self.after.source_policy_ids),
            "note": self.segment.note,
        }


@dataclass
class ImpactMatrix:
    """6·30 규제 변경의 세그먼트별 영향 매트릭스."""

    policy_id: str
    before_date: date
    after_date: date
    rows: list[ImpactRow] = field(default_factory=list)

    @property
    def core_rows(self) -> list[ImpactRow]:
        return [r for r in self.rows if r.is_core]

    @property
    def discovery_rows(self) -> list[ImpactRow]:
        return [r for r in self.rows if not r.is_core]

    def summary(self) -> dict:
        core = self.core_rows
        return {
            "policy_id": self.policy_id,
            "before_date": self.before_date.isoformat(),
            "after_date": self.after_date.isoformat(),
            "total_segments": len(self.rows),
            "core_segments": len(core),
            "discovery_segments": len(self.discovery_rows),
            "changed": sum(1 for r in core if r.changed),
            "tightened": sum(1 for r in core if r.direction == ImpactDirection.TIGHTENED),
            "unchanged": sum(1 for r in core if r.direction == ImpactDirection.UNCHANGED),
            "grandfathered": sum(1 for r in core if r.grandfathering),
            "review_required": sum(1 for r in core if r.review_required),
            "baseline_gap": sum(1 for r in core if r.direction == ImpactDirection.BASELINE_GAP),
            "high_impact": sum(1 for r in core if r.high_impact),
        }

    def to_dict(self) -> dict:
        return {
            "summary": self.summary(),
            "rows": [r.to_dict() for r in self.rows],
        }


def build_impact_matrix(
    segments: Optional[list[Segment]] = None,
    *,
    before_date: date = BEFORE_DATE,
    after_date: date = AFTER_DATE,
    policy_id: str = POLICY_ID,
) -> ImpactMatrix:
    """세그먼트 목록을 룰엔진 before/after 차등 실행으로 매트릭스화한다.

    before는 경과규정 이벤트를 제거해 구규제 기준선을 순수 평가하고,
    after는 모든 속성/이벤트를 반영해 신규제 적용값을 얻는다.
    """
    if segments is None:
        segments = SIX_THIRTY_SEGMENTS
    rows: list[ImpactRow] = []
    for seg in segments:
        before = evaluate(seg.application(before_date, drop_transition_events=True))
        after = evaluate(seg.application(after_date))
        rows.append(ImpactRow(segment=seg, before=before, after=after))
    return ImpactMatrix(
        policy_id=policy_id,
        before_date=before_date,
        after_date=after_date,
        rows=rows,
    )


def format_report(matrix: ImpactMatrix) -> str:
    """매트릭스를 사람이 읽는 표 리포트로 렌더링."""
    s = matrix.summary()
    lines: list[str] = []
    lines.append(
        f"Impact Matrix — {matrix.policy_id}  "
        f"(before {matrix.before_date.isoformat()} → after {matrix.after_date.isoformat()})"
    )
    lines.append(
        f"세그먼트 {s['total_segments']}개 (코어 {s['core_segments']} / Discovery {s['discovery_segments']}) · "
        f"변화 {s['changed']} · 규제강화 {s['tightened']} · 경과규정 {s['grandfathered']} · "
        f"검토필요 {s['review_required']} · 고영향 {s['high_impact']}"
    )
    lines.append("")
    header = f"{'지역':<8} {'차주유형':<20} {'기존':<16} {'변경':<16} {'경과':<5} {'방향':<14} reason_code"
    lines.append(header)
    lines.append("-" * len(header))
    for r in matrix.rows:
        gf = "해당" if r.grandfathering else "-"
        flag = " ★" if r.high_impact else ""
        lines.append(
            f"{r.region_label:<8} {r.borrower_type:<20} "
            f"{r.before_display:<16} {r.after_display:<16} {gf:<5} "
            f"{_DIRECTION_LABEL[r.direction]:<14} {','.join(r.reason_codes) or '-'}{flag}"
        )
    lines.append("")
    lines.append("★ = 고영향(대출불가 0% / 15%p+ 하향 / 기준부재)")
    return "\n".join(lines)
