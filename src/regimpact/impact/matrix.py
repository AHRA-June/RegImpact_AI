"""Impact Matrix 빌더 — 룰엔진을 Before/After 두 시점에 실행해 '차이'를 계산한다.

핵심: 규칙을 새로 만들지 않는다. 동일한 차주 프로파일을 두 evaluation_date에 넣어
rule_engine.evaluate 를 두 번 호출하고, 두 판정의 델타를 구조화할 뿐이다. 지역의
규제상태(시점 버전)와 경과규정은 엔진이 날짜로 스스로 해석한다.

정직성 원칙(브리프 §5.2, LOCKED §4):
- 非규제 유주택 기준선은 원문에 없다 → 엔진이 NEEDS_HUMAN_REVIEW로 escalate.
  Impact Matrix는 이 'before 미정의'를 숨기지 않고 NEW_RESTRICTION으로 정직하게 표기한다.
- 정책대출·비주택구입목적은 자동판정하지 않고 Discovery Scope로 분리한다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any, Optional

from ..models import EvaluationStatus, LtvDecision, MortgageApplication
from ..rule_engine import evaluate
from .segments import SIX_THIRTY_SEGMENTS, Segment

# 6·30 시나리오의 Before/After 앵커 시점.
# Before = 시행 전일(규제 효력 발생 직전), After = 시행 후.
BEFORE_DATE = date(2026, 6, 30)
AFTER_DATE = date(2026, 7, 2)

# profile dict 에서 date 로 변환할 필드 (문자열 "YYYY-MM-DD" 허용)
_DATE_FIELDS = (
    "application_accepted_at",
    "contract_signed_at",
    "downpayment_paid_at",
    "land_permit_applied_at",
)


class ImpactDirection(str, Enum):
    """세그먼트의 변경 방향(정성 요약)."""
    DOWNGRADE = "DOWNGRADE"            # LTV 하향 (after < before)
    UPGRADE = "UPGRADE"               # LTV 상향 (after > before)
    UNCHANGED = "UNCHANGED"           # 동일 (경과규정 유지 포함)
    NEW_RESTRICTION = "NEW_RESTRICTION"  # before가 명세부재/검토, after는 확정 제한
    REVIEW = "REVIEW"                 # after가 사람 검토 필요
    DISCOVERY = "DISCOVERY"           # 자동판정 제외(정책대출·비주택구입목적)


@dataclass
class ImpactRow:
    """Impact Matrix 한 행 — 한 세그먼트의 Before/After 판정과 델타."""
    key: str
    region_code: str
    region_label: str
    borrower_type: str
    before: LtvDecision
    after: LtvDecision
    direction: ImpactDirection
    grandfathering_applied: bool
    counterfactual_ltv: Optional[float] = None  # 경과규정 없었다면 적용됐을 LTV
    reason_codes: list[str] = field(default_factory=list)  # after 근거
    note: str = ""

    @property
    def before_ltv(self) -> Optional[float]:
        return self.before.max_ltv

    @property
    def after_ltv(self) -> Optional[float]:
        return self.after.max_ltv

    @property
    def is_discovery(self) -> bool:
        return self.direction == ImpactDirection.DISCOVERY

    @property
    def delta(self) -> Optional[float]:
        """after - before (둘 다 수치일 때만)."""
        if self.before.max_ltv is None or self.after.max_ltv is None:
            return None
        return round(self.after.max_ltv - self.before.max_ltv, 4)


@dataclass
class ImpactMatrix:
    """전체 영향분석 결과 = Core 판정 행 + Discovery 분리 행 + 요약."""
    policy_event: str
    before_date: date
    after_date: date
    rows: list[ImpactRow]

    @property
    def core_rows(self) -> list[ImpactRow]:
        """자동판정 대상(주택구입목적·비정책대출)."""
        return [r for r in self.rows if not r.is_discovery]

    @property
    def discovery_rows(self) -> list[ImpactRow]:
        """영향 가능성만 탐지, 수동 정책검토 대상."""
        return [r for r in self.rows if r.is_discovery]

    @property
    def summary(self) -> dict[str, int]:
        """방향별 카운트(요약 지표). UI 상단 카드/차트에 사용."""
        counts = {d.value: 0 for d in ImpactDirection}
        grandfathered = 0
        for r in self.rows:
            counts[r.direction.value] += 1
            if r.grandfathering_applied:
                grandfathered += 1
        counts["TOTAL"] = len(self.rows)
        counts["GRANDFATHERED"] = grandfathered
        counts["CORE"] = len(self.core_rows)
        return counts


def _build_application_from_profile(
    profile: dict[str, Any], region_code: str, as_of: date, customer_id: str | None = None
) -> MortgageApplication:
    """프로파일 dict + 지역 + 시점 → MortgageApplication. 문자열 날짜는 date로 정규화."""
    kwargs: dict[str, Any] = dict(profile)
    for f in _DATE_FIELDS:
        v = kwargs.get(f)
        if isinstance(v, str):
            kwargs[f] = date.fromisoformat(v)
    return MortgageApplication(
        region_code=region_code,
        evaluation_date=as_of,
        customer_id=customer_id,
        **kwargs,
    )


def _build_application(segment: Segment, as_of: date) -> MortgageApplication:
    """세그먼트 프로파일 + 시점 → MortgageApplication."""
    return _build_application_from_profile(
        segment.profile, segment.region_code, as_of, customer_id=segment.key
    )


def classify_direction(before: LtvDecision, after: LtvDecision) -> ImpactDirection:
    """Before/After 판정 → 변경 방향."""
    if after.status in (EvaluationStatus.DISCOVERY, EvaluationStatus.OUT_OF_SCOPE):
        return ImpactDirection.DISCOVERY
    if after.status == EvaluationStatus.NEEDS_HUMAN_REVIEW:
        return ImpactDirection.REVIEW

    # after 는 DECIDED (수치 확정)
    if before.status != EvaluationStatus.DECIDED or before.max_ltv is None:
        # before 가 명세부재/검토였는데 after 는 확정 제한 → 신규 제한 도입
        return ImpactDirection.NEW_RESTRICTION

    if after.max_ltv < before.max_ltv:
        return ImpactDirection.DOWNGRADE
    if after.max_ltv > before.max_ltv:
        return ImpactDirection.UPGRADE
    return ImpactDirection.UNCHANGED


def _counterfactual_ltv(segment: Segment, as_of: date) -> Optional[float]:
    """경과규정 이벤트를 제거하고 after 시점에 재평가 → '보호 없었다면' LTV."""
    stripped = dict(segment.profile)
    for f in _DATE_FIELDS + ("land_permit_target",):
        stripped.pop(f, None)
    cf_segment = Segment(
        key=segment.key,
        borrower_type=segment.borrower_type,
        region_code=segment.region_code,
        profile=stripped,
    )
    return evaluate(_build_application(cf_segment, as_of)).max_ltv


def build_impact_matrix(
    segments: Optional[list[Segment]] = None,
    before_date: date = BEFORE_DATE,
    after_date: date = AFTER_DATE,
    policy_event: str = "2026-06-30 규제지역 추가 지정",
) -> ImpactMatrix:
    """세그먼트들을 Before/After 두 시점에 룰엔진으로 관통시켜 Impact Matrix 생성."""
    segments = segments if segments is not None else SIX_THIRTY_SEGMENTS
    rows: list[ImpactRow] = []
    for seg in segments:
        before = evaluate(_build_application(seg, before_date))
        after = evaluate(_build_application(seg, after_date))
        direction = classify_direction(before, after)

        counterfactual = None
        if after.grandfathering_applied:
            cf = _counterfactual_ltv(seg, after_date)
            # 보호가 실제로 값을 바꿨을 때만(달랐을 때만) 의미가 있음
            if cf is not None and cf != after.max_ltv:
                counterfactual = cf

        rows.append(
            ImpactRow(
                key=seg.key,
                region_code=seg.region_code,
                region_label=seg.region_label,
                borrower_type=seg.borrower_type,
                before=before,
                after=after,
                direction=direction,
                grandfathering_applied=after.grandfathering_applied,
                counterfactual_ltv=counterfactual,
                reason_codes=list(after.reason_codes),
                note=seg.note,
            )
        )
    return ImpactMatrix(
        policy_event=policy_event,
        before_date=before_date,
        after_date=after_date,
        rows=rows,
    )


def _fmt_ltv(v: Optional[float], status: EvaluationStatus) -> str:
    if v is not None:
        return f"{v:.0%}"
    return {
        EvaluationStatus.DISCOVERY: "Discovery",
        EvaluationStatus.OUT_OF_SCOPE: "범위외",
        EvaluationStatus.NEEDS_HUMAN_REVIEW: "검토",
    }.get(status, "—")


def format_matrix(matrix: ImpactMatrix) -> str:
    """사람이 읽는 텍스트 표 (데모/리포트 stub)."""
    lines: list[str] = []
    lines.append(f"■ Impact Matrix — {matrix.policy_event}")
    lines.append(f"  Before {matrix.before_date} → After {matrix.after_date}")
    lines.append("")
    header = f"{'지역':<8} {'차주유형':<22} {'기존':>6} {'변경':>8} {'방향':<15} {'경과':<5} 근거"
    lines.append(header)
    lines.append("-" * len(header))

    def _row_line(r: ImpactRow) -> str:
        before_s = _fmt_ltv(r.before_ltv, r.before.status)
        after_s = _fmt_ltv(r.after_ltv, r.after.status)
        if r.counterfactual_ltv is not None:
            after_s = f"{after_s}*"  # 경과규정으로 보호됨
        gf = "GF" if r.grandfathering_applied else "-"
        return (
            f"{r.region_label:<8} {r.borrower_type:<22} {before_s:>6} {after_s:>8} "
            f"{r.direction.value:<15} {gf:<5} {','.join(r.reason_codes) or '-'}"
        )

    for r in matrix.core_rows:
        lines.append(_row_line(r))
    if matrix.discovery_rows:
        lines.append("")
        lines.append("── Discovery Scope (자동판정 제외 · 수동 정책검토) ──")
        for r in matrix.discovery_rows:
            lines.append(_row_line(r))

    s = matrix.summary
    lines.append("")
    lines.append(
        f"요약: 총 {s['TOTAL']}건 (Core {s['CORE']}) · "
        f"하향 {s['DOWNGRADE']} · 신규제한 {s['NEW_RESTRICTION']} · "
        f"유지 {s['UNCHANGED']} · 검토 {s['REVIEW']} · Discovery {s['DISCOVERY']} · "
        f"경과규정보호 {s['GRANDFATHERED']}"
    )
    if any(r.counterfactual_ltv is not None for r in matrix.rows):
        lines.append("  * 경과규정으로 종전규정 유지(경과규정 없었다면 하향됐을 행).")
    return "\n".join(lines)
