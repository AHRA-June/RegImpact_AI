"""Impact Matrix — 규제 변경의 before/after 차등 임팩트 산출.

핵심 아이디어(LOCKED §4 준수):
    이 모듈은 **새로운 규칙을 만들지 않는다.** deterministic 룰엔진(evaluate)을
    같은 고객 세그먼트에 대해 **두 시점**(시행 전/후)으로 돌려, 그 차이를 표로 정리할 뿐이다.
    6·30 건의 경우 지역 규제상태가 2026-07-01부터 바뀌므로(regions.py),
    같은 세그먼트를 before=2026-06-30, after=2026-07-02 로 평가하면 정책 효과가 그대로 드러난다.

출력(ImpactMatrix)은 감사 가능하도록 각 행에 before/after의 status·reason_codes·
source_policy_ids를 모두 보존한다(브리프 §16 audit trail).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional

from ..models import EvaluationStatus, LtvDecision, MortgageApplication
from ..rule_engine import evaluate

# 6·30 표준 관측 시점 (경계 자정 포함 규칙 → 하루 여유를 두고 관측)
BEFORE_DATE = date(2026, 6, 30)   # 시행 전 (규제 효력 발생 전일)
AFTER_DATE = date(2026, 7, 2)     # 시행 후

# high-impact 임계: 수치 delta 절대값이 이 이상이면 중대 영향으로 표시
HIGH_IMPACT_DELTA = 0.30


class ImpactDirection(str, Enum):
    """세그먼트가 규제 변경으로 받은 영향의 방향."""
    TIGHTENED = "TIGHTENED"      # LTV 하락 (규제 강화)
    LOOSENED = "LOOSENED"        # LTV 상승 (완화)
    UNCHANGED = "UNCHANGED"      # 변화 없음 (예외/경과규정으로 보호되거나 원래 동일)
    NEEDS_REVIEW = "NEEDS_REVIEW"  # 어느 한 시점이라도 자동판정 불가 → 수치 delta 산출 불가


@dataclass
class CustomerSegment:
    """임팩트 분석 대상 고객 세그먼트.

    `attrs`는 MortgageApplication 생성 kwargs에서 **evaluation_date를 제외한** 것.
    evaluation_date는 임팩트의 축(시행 전/후)이므로 분석기가 주입한다.
    weight는 포트폴리오 내 상대 비중(집계 영향 산출용, 예시값 — 실측 아님).
    """
    label: str
    attrs: dict = field(default_factory=dict)
    weight: float = 1.0
    note: str = ""

    def application(self, evaluation_date: date) -> MortgageApplication:
        return MortgageApplication(evaluation_date=evaluation_date, **self.attrs)


@dataclass
class SegmentImpact:
    """한 세그먼트의 before/after 판정과 그 차이."""
    segment: CustomerSegment
    before: LtvDecision
    after: LtvDecision
    direction: ImpactDirection
    ltv_delta: Optional[float]      # after.max_ltv - before.max_ltv (둘 다 DECIDED일 때만)
    escalation_required: bool       # after가 사람검토/Discovery 로 귀결
    high_impact: bool               # 중대 영향(대폭 delta 또는 어느 쪽이든 검토 필요)

    @property
    def label(self) -> str:
        return self.segment.label


@dataclass
class ImpactMatrix:
    """정책 1건에 대한 세그먼트별 임팩트 집합 + 집계."""
    policy_id: str
    before_date: date
    after_date: date
    rows: list[SegmentImpact] = field(default_factory=list)

    # --- 집계 (분모/분자 명확히) ---
    def count_by_direction(self) -> dict[str, int]:
        out: dict[str, int] = {d.value: 0 for d in ImpactDirection}
        for r in self.rows:
            out[r.direction.value] += 1
        return out

    @property
    def escalation_count(self) -> int:
        return sum(1 for r in self.rows if r.escalation_required)

    @property
    def high_impact_count(self) -> int:
        return sum(1 for r in self.rows if r.high_impact)

    def weighted_mean_delta(self) -> Optional[float]:
        """수치 비교 가능한(둘 다 DECIDED) 행에 한해 가중 평균 LTV delta.

        분모 = 그 행들의 weight 합. 비교 불가 행(NEEDS_REVIEW)은 제외하고,
        제외 사실은 report에 명시한다(조용한 누락 금지).
        """
        num = 0.0
        den = 0.0
        for r in self.rows:
            if r.ltv_delta is None:
                continue
            num += r.ltv_delta * r.segment.weight
            den += r.segment.weight
        if den == 0:
            return None
        return num / den

    @property
    def comparable_count(self) -> int:
        return sum(1 for r in self.rows if r.ltv_delta is not None)


def _classify(before: LtvDecision, after: LtvDecision) -> tuple[ImpactDirection, Optional[float]]:
    b_decided = before.status == EvaluationStatus.DECIDED and before.max_ltv is not None
    a_decided = after.status == EvaluationStatus.DECIDED and after.max_ltv is not None

    if b_decided and a_decided:
        delta = round(after.max_ltv - before.max_ltv, 6)  # type: ignore[operator]
        if delta < 0:
            return ImpactDirection.TIGHTENED, delta
        if delta > 0:
            return ImpactDirection.LOOSENED, delta
        return ImpactDirection.UNCHANGED, delta

    # 양쪽 상태가 같은 비자동판정(예: Discovery→Discovery, 범위외→범위외):
    # 규제 변경이 이 세그먼트를 움직이지 않음 → 변화 없음.
    if before.status == after.status:
        return ImpactDirection.UNCHANGED, None

    # 상태가 서로 다른데 한쪽이 자동판정 불가 → 수치 delta 산출 불가 (정직한 표기)
    return ImpactDirection.NEEDS_REVIEW, None


def analyze_segment(
    segment: CustomerSegment,
    before_date: date = BEFORE_DATE,
    after_date: date = AFTER_DATE,
) -> SegmentImpact:
    """세그먼트 하나를 두 시점으로 평가해 임팩트를 산출."""
    before = evaluate(segment.application(before_date))
    after = evaluate(segment.application(after_date))
    direction, delta = _classify(before, after)

    escalation_required = after.status != EvaluationStatus.DECIDED
    # 중대영향 = 대폭 수치 변동이거나, 자동판정 가능/불가 상태가 뒤바뀐 실질 전이(NEEDS_REVIEW).
    # 양쪽 동일 비자동상태(변화 없음)는 중대영향이 아니다.
    if delta is not None:
        high_impact = abs(delta) >= HIGH_IMPACT_DELTA
    else:
        high_impact = direction == ImpactDirection.NEEDS_REVIEW

    return SegmentImpact(
        segment=segment,
        before=before,
        after=after,
        direction=direction,
        ltv_delta=delta,
        escalation_required=escalation_required,
        high_impact=high_impact,
    )


def analyze_impact(
    segments: list[CustomerSegment],
    policy_id: str = "6_30_2026",
    before_date: date = BEFORE_DATE,
    after_date: date = AFTER_DATE,
) -> ImpactMatrix:
    """세그먼트 목록에 대한 Impact Matrix 를 산출한다 (E2E 진입점)."""
    rows = [analyze_segment(s, before_date, after_date) for s in segments]
    return ImpactMatrix(
        policy_id=policy_id,
        before_date=before_date,
        after_date=after_date,
        rows=rows,
    )


# --------------------------------------------------------------------------- #
# 리포트 포매터 (텍스트 표) — UI 연동 전까지 CLI/데모 출력에 사용
# --------------------------------------------------------------------------- #

def _fmt_ltv(d: LtvDecision) -> str:
    if d.status != EvaluationStatus.DECIDED or d.max_ltv is None:
        # 자동판정 불가: 상태 축약 표기
        return {
            EvaluationStatus.NEEDS_HUMAN_REVIEW: "검토",
            EvaluationStatus.DISCOVERY: "Disc",
            EvaluationStatus.OUT_OF_SCOPE: "범위외",
        }.get(d.status, d.status.value)
    return f"{d.max_ltv:.0%}"


def _fmt_delta(imp: SegmentImpact) -> str:
    if imp.ltv_delta is None:
        return "—"
    pp = imp.ltv_delta * 100
    sign = "+" if pp > 0 else ""
    return f"{sign}{pp:.0f}pp"


_DIRECTION_MARK = {
    ImpactDirection.TIGHTENED: "▼ 강화",
    ImpactDirection.LOOSENED: "▲ 완화",
    ImpactDirection.UNCHANGED: "= 유지",
    ImpactDirection.NEEDS_REVIEW: "? 검토",
}


def format_report(matrix: ImpactMatrix) -> str:
    """Impact Matrix 를 사람이 읽는 텍스트 표로 렌더링."""
    lines: list[str] = []
    lines.append(
        f"Impact Matrix — policy={matrix.policy_id}  "
        f"before={matrix.before_date}  after={matrix.after_date}"
    )
    header = (
        f"{'세그먼트':<22} {'before':>6} {'after':>6} {'Δ':>7}  "
        f"{'방향':<7} {'중대':^4} {'reason(after)'}"
    )
    lines.append(header)
    lines.append("-" * max(len(header), 96))

    for r in matrix.rows:
        flag = "★" if r.high_impact else ""
        reason = ",".join(r.after.reason_codes) or "-"
        lines.append(
            f"{r.label:<22} {_fmt_ltv(r.before):>6} {_fmt_ltv(r.after):>6} "
            f"{_fmt_delta(r):>7}  {_DIRECTION_MARK[r.direction]:<7} {flag:^4} {reason}"
        )

    lines.append("-" * max(len(header), 96))
    counts = matrix.count_by_direction()
    wmd = matrix.weighted_mean_delta()
    wmd_s = "—" if wmd is None else f"{wmd * 100:+.1f}pp"
    lines.append(
        f"합계 {len(matrix.rows)}행 | "
        f"강화 {counts['TIGHTENED']} · 완화 {counts['LOOSENED']} · "
        f"유지 {counts['UNCHANGED']} · 검토 {counts['NEEDS_REVIEW']}"
    )
    lines.append(
        f"중대영향 {matrix.high_impact_count}행 · 사람검토 필요 {matrix.escalation_count}행 · "
        f"가중평균 Δ {wmd_s} (수치비교 가능 {matrix.comparable_count}/{len(matrix.rows)}행 기준)"
    )
    if matrix.comparable_count < len(matrix.rows):
        lines.append(
            f"  주: 수치비교 불가 {len(matrix.rows) - matrix.comparable_count}행은 "
            f"어느 시점이 자동판정 불가(검토/Discovery)라 수치 평균에서 제외됨."
        )
    return "\n".join(lines)
