"""Impact Analyzer — 규제 변경의 Before/After 임팩트를 포트폴리오 단위로 산출.

브리프 코어 완성선(§18)의 중심 노드: Source→Policy→**Before/After→Impact Matrix**→…→Report.
`04_PLAN.md` Phase 1 Walking Skeleton의 "Impact Matrix(1~2행)"를 실제 엔진 출력으로 구현한다.

설계 (반증 가능한 정직한 counterfactual):
    한 고객 프로필을 **두 정책 시점**에 각각 룰엔진으로 평가한다.
      - before = 변경 전 규제세계 (as_of=before_date). 지역이 아직 非규제 → 종전 기준선.
      - after  = 변경 후 규제세계 (as_of=after_date). 지역 규제 전환 + 경과규정 반영.
    룰엔진이 이미 시점 해석(regions.resolve_region_status)을 하므로, 6·30 변경은
    "같은 프로필을 두 날짜에 평가"하는 것으로 자연스럽게 표현된다.

    LOCKED §4 준수: 임팩트는 룰엔진(확정 명세의 구현)이 낸 판정의 '차이'일 뿐,
    이 파일은 새로운 규칙값을 만들지 않는다. before/after 모두 동일 엔진을 쓴다.

경과규정의 의미가 여기서 드러난다: 경과규정 대상 고객은 after에서도 종전규정(70%)을
유지 → before와 같음 → UNCHANGED. 즉 "경과규정 = 임팩트 없음"이 매트릭스에 정직하게 나타난다.
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from datetime import date
from enum import Enum

from ..models import EvaluationStatus, LtvDecision, MortgageApplication, RegionStatus
from ..regions import resolve_region_status
from ..rule_engine import evaluate

# 6·30 시나리오 기본 정책 시점 (변경 전/후). 다른 규제 변경엔 인자로 교체.
DEFAULT_BEFORE_DATE = date(2026, 6, 15)   # 시행 전
DEFAULT_AFTER_DATE = date(2026, 7, 2)     # 시행 후, 경과규정 미해당 기준 시점

# 고임팩트 임계 (metrics_spec high-risk 후보 기반).
HIGH_IMPACT_LTV_DROP = 0.30               # LTV가 30%p 이상 하락 = 고임팩트


class ImpactDirection(str, Enum):
    """before→after 판정 변화 방향."""
    TIGHTENED = "TIGHTENED"          # 규제 강화 (LTV 하락 또는 자동판정→0%/검토필요)
    LOOSENED = "LOOSENED"            # 규제 완화 (LTV 상승)
    UNCHANGED = "UNCHANGED"          # 변화 없음 (경과규정 보호 포함)
    STATUS_ONLY = "STATUS_ONLY"      # LTV 수치 비교 불가하나 상태(status)가 바뀜


def _before_view(app: MortgageApplication, before_date: date) -> MortgageApplication:
    """변경 '전' 세계의 프로필. 경과규정은 '변경'의 산물이므로 before에선 무의미 → 제거.

    이렇게 하면 before는 순수 종전 기준선이 되어, after의 경과규정 보호 효과가
    임팩트(UNCHANGED)로 정확히 드러난다.
    """
    return dataclasses.replace(
        app,
        evaluation_date=before_date,
        application_accepted_at=None,
        contract_signed_at=None,
        downpayment_paid_at=None,
        land_permit_target=False,
        land_permit_applied_at=None,
    )


def _is_denial(dec: LtvDecision) -> bool:
    """LTV 0% = 사실상 대출 거절(가장 강한 규제). 방향/고임팩트 판정의 핵심."""
    return dec.max_ltv == 0.0


def _direction(before: LtvDecision, after: LtvDecision) -> ImpactDirection:
    b, a = before.max_ltv, after.max_ltv
    if b is not None and a is not None:
        if a < b:
            return ImpactDirection.TIGHTENED
        if a > b:
            return ImpactDirection.LOOSENED
        return ImpactDirection.UNCHANGED
    # 한쪽만 수치가 있음: 0%(거절)로의 이동은 방향을 결정할 수 있다.
    # (before가 NEEDS_HUMAN_REVIEW/불명이어도 after 0%는 '강화된 거절'로 읽는다.)
    if _is_denial(after) and not _is_denial(before):
        return ImpactDirection.TIGHTENED
    if _is_denial(before) and not _is_denial(after):
        return ImpactDirection.LOOSENED
    # 그 외(불명↔양수 LTV): 정직하게 '수치 비교 불가, 상태만 변함'으로 둔다.
    if before.status == after.status:
        return ImpactDirection.UNCHANGED
    return ImpactDirection.STATUS_ONLY


@dataclass(frozen=True)
class ImpactRow:
    """고객 1건의 before/after 임팩트."""
    app: MortgageApplication
    before: LtvDecision
    after: LtvDecision
    direction: ImpactDirection

    @property
    def customer_id(self) -> str | None:
        return self.app.customer_id

    @property
    def ltv_delta(self) -> float | None:
        """after - before (둘 다 수치일 때만). 음수 = 강화."""
        if self.before.max_ltv is None or self.after.max_ltv is None:
            return None
        return round(self.after.max_ltv - self.before.max_ltv, 4)

    @property
    def grandfathered(self) -> bool:
        return self.after.grandfathering_applied

    @property
    def changed(self) -> bool:
        return self.direction in (
            ImpactDirection.TIGHTENED,
            ImpactDirection.LOOSENED,
            ImpactDirection.STATUS_ONLY,
        )

    @property
    def high_impact(self) -> bool:
        """고임팩트 (metrics_spec high-risk 후보 기반):
        ① LTV 30%p 이상 하락, ② 신규 대출거절(after 0%, before는 비거절),
        ③ 자동판정(DECIDED)에서 사람검토/판정불가로 전환.
        """
        d = self.ltv_delta
        if d is not None and d <= -HIGH_IMPACT_LTV_DROP:
            return True
        if _is_denial(self.after) and not _is_denial(self.before):
            return True
        if (
            self.before.status == EvaluationStatus.DECIDED
            and self.after.status in (
                EvaluationStatus.NEEDS_HUMAN_REVIEW,
                EvaluationStatus.DISCOVERY,
            )
        ):
            return True
        return False


def analyze_row(
    app: MortgageApplication,
    before_date: date = DEFAULT_BEFORE_DATE,
    after_date: date = DEFAULT_AFTER_DATE,
) -> ImpactRow:
    """한 고객 프로필의 규제 변경 임팩트를 산출한다."""
    before = evaluate(_before_view(app, before_date))
    after = evaluate(dataclasses.replace(app, evaluation_date=after_date))
    return ImpactRow(app=app, before=before, after=after, direction=_direction(before, after))


# ---------------------------------------------------------------------------
# 세그먼트 (Impact Matrix의 행)
# ---------------------------------------------------------------------------
def _housing_bucket(app: MortgageApplication) -> str:
    if app.house_count >= 2:
        return "MULTI_HOME"
    if app.house_count == 1:
        return "DISPOSAL_1HOME" if app.disposal_condition_flag else "OWNER_1HOME"
    return "NO_HOME"


def _exception_bucket(app: MortgageApplication) -> str:
    if app.first_home_buyer:
        return "FIRST_HOME"
    if app.real_demand_flag:
        return "REAL_DEMAND"
    return "GENERAL"


@dataclass(frozen=True)
class Segment:
    """포트폴리오 세그먼트 키 (사람이 읽는 임팩트 매트릭스 행 라벨)."""
    region_transition: str   # NEWLY_REGULATED / STAYED_REGULATED / NON_REGULATED
    housing: str
    exception: str

    def label(self) -> str:
        return f"{self.region_transition} · {self.housing} · {self.exception}"


def segment_of(row: ImpactRow) -> Segment:
    """임팩트 행을 세그먼트로 분류. 지역 전환은 시점별 지역상태(regions)로 판정."""
    app = row.app
    before_status, _ = resolve_region_status(app.region_code, DEFAULT_BEFORE_DATE)
    after_status, _ = resolve_region_status(app.region_code, DEFAULT_AFTER_DATE)
    if before_status == RegionStatus.REGULATED and after_status == RegionStatus.REGULATED:
        transition = "STAYED_REGULATED"
    elif after_status == RegionStatus.REGULATED:
        transition = "NEWLY_REGULATED"
    else:
        transition = "NON_REGULATED"
    return Segment(
        region_transition=transition,
        housing=_housing_bucket(app),
        exception=_exception_bucket(app),
    )


@dataclass
class SegmentImpact:
    """세그먼트 1개의 집계 임팩트 (매트릭스 셀)."""
    segment: Segment
    rows: list[ImpactRow] = field(default_factory=list)

    @property
    def n(self) -> int:
        return len(self.rows)

    @property
    def n_changed(self) -> int:
        return sum(1 for r in self.rows if r.changed)

    @property
    def n_tightened(self) -> int:
        return sum(1 for r in self.rows if r.direction == ImpactDirection.TIGHTENED)

    @property
    def n_grandfathered(self) -> int:
        return sum(1 for r in self.rows if r.grandfathered)

    @property
    def n_high_impact(self) -> int:
        return sum(1 for r in self.rows if r.high_impact)

    def _avg_ltv(self, which: str) -> float | None:
        vals = [
            getattr(r, which).max_ltv
            for r in self.rows
            if getattr(r, which).max_ltv is not None
        ]
        return round(sum(vals) / len(vals), 4) if vals else None

    @property
    def avg_ltv_before(self) -> float | None:
        return self._avg_ltv("before")

    @property
    def avg_ltv_after(self) -> float | None:
        return self._avg_ltv("after")

    @property
    def avg_ltv_delta(self) -> float | None:
        deltas = [r.ltv_delta for r in self.rows if r.ltv_delta is not None]
        return round(sum(deltas) / len(deltas), 4) if deltas else None


@dataclass
class ImpactMatrix:
    """포트폴리오 전체 임팩트 매트릭스."""
    rows: list[ImpactRow]
    before_date: date
    after_date: date

    @property
    def segments(self) -> list[SegmentImpact]:
        """세그먼트별 집계. 정렬: 고임팩트 → 강화건수 → n 내림차순."""
        buckets: dict[Segment, SegmentImpact] = {}
        for r in self.rows:
            seg = segment_of(r)
            buckets.setdefault(seg, SegmentImpact(segment=seg)).rows.append(r)
        return sorted(
            buckets.values(),
            key=lambda s: (s.n_high_impact, s.n_tightened, s.n),
            reverse=True,
        )

    @property
    def n(self) -> int:
        return len(self.rows)

    @property
    def n_changed(self) -> int:
        return sum(1 for r in self.rows if r.changed)

    @property
    def n_tightened(self) -> int:
        return sum(1 for r in self.rows if r.direction == ImpactDirection.TIGHTENED)

    @property
    def n_grandfathered(self) -> int:
        return sum(1 for r in self.rows if r.grandfathered)

    @property
    def n_high_impact(self) -> int:
        return sum(1 for r in self.rows if r.high_impact)

    @property
    def affected_rate(self) -> float:
        """변경 영향 비율 = 변화 건 / 전체 (분모 0이면 0.0)."""
        return 0.0 if self.n == 0 else self.n_changed / self.n


def analyze_portfolio(
    apps: list[MortgageApplication],
    before_date: date = DEFAULT_BEFORE_DATE,
    after_date: date = DEFAULT_AFTER_DATE,
) -> ImpactMatrix:
    """포트폴리오를 before/after로 평가해 Impact Matrix를 만든다."""
    rows = [analyze_row(a, before_date, after_date) for a in apps]
    return ImpactMatrix(rows=rows, before_date=before_date, after_date=after_date)


def _fmt_ltv(v: float | None) -> str:
    return "  —  " if v is None else f"{v:5.0%}"


def format_matrix(matrix: ImpactMatrix) -> str:
    """사람이 읽는 Impact Matrix 요약 (데모·리포트·UI 대체값)."""
    lines: list[str] = []
    lines.append("=" * 78)
    lines.append("RegImpact — Impact Matrix (Before/After · 룰엔진 실측)")
    lines.append("=" * 78)
    lines.append(
        f"정책 시점: before={matrix.before_date.isoformat()}  "
        f"after={matrix.after_date.isoformat()}"
    )
    lines.append(
        f"포트폴리오 n={matrix.n}  변경영향={matrix.n_changed}"
        f"({matrix.affected_rate:.0%})  강화={matrix.n_tightened}  "
        f"경과규정보호={matrix.n_grandfathered}  고임팩트={matrix.n_high_impact}"
    )
    lines.append("-" * 78)
    header = (
        f"{'세그먼트':<44} {'n':>3} {'변화':>4} "
        f"{'before':>7} {'after':>7} {'Δ':>7} {'고위험':>5}"
    )
    lines.append(header)
    lines.append("-" * 78)
    for s in matrix.segments:
        lines.append(
            f"{s.segment.label():<44} {s.n:>3} {s.n_changed:>4} "
            f"{_fmt_ltv(s.avg_ltv_before):>7} {_fmt_ltv(s.avg_ltv_after):>7} "
            f"{_fmt_ltv(s.avg_ltv_delta):>7} {s.n_high_impact:>5}"
        )
    lines.append("=" * 78)
    if matrix.n_high_impact:
        lines.append(
            f"⚠ 고임팩트 {matrix.n_high_impact}건 — LTV 30%p↑ 하락 / 신규 대출거절(0%) / "
            "자동판정→검토필요 전환."
        )
    lines.append(
        "주: before/after 모두 동일 룰엔진(확정 명세 구현)으로 평가. "
        "경과규정 대상은 after에서도 종전규정 유지 → UNCHANGED로 표기됨."
    )
    return "\n".join(lines)
