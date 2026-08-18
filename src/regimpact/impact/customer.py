"""고객·포트폴리오 영향 분석 — 임팩트 매트릭스에서 가장 값이 무거운 행(§10).

방법: 합성 포트폴리오의 **같은 신청건을 시행 전일(6.30)과 시행일(7.1) 두 시점으로**
deterministic 룰엔진에 태우고 차이를 집계한다. LLM은 여기 관여하지 않는다 —
"누가 얼마나 영향받는가"는 추정이 아니라 확정 규칙의 계산 결과여야 한다.

경과규정 대상은 7.1에 평가해도 종전규정(70%)이 나오므로 자연스럽게 "보호됨"으로 분리된다.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from enum import Enum

from ..models import EvaluationStatus, LtvDecision
from ..rule_engine import evaluate
from .portfolio import AFTER_DATE, BEFORE_DATE, PortfolioCustomer


class Segment(str, Enum):
    """고객 영향 분류. 위에서부터 우선 적용(한 고객은 한 세그먼트)."""
    OUT_OF_SCOPE = "적용 대상 아님"           # 주택구입목적 아님
    DISCOVERY = "Discovery(수동 검토)"        # 정책대출 등 코어 자동판정 제외
    NEEDS_HUMAN_REVIEW = "사람 검토 필요"      # 기준 부재·모호
    GRANDFATHERED = "경과규정 보호"            # 종전규정 유지
    REDUCED = "한도 감소"                      # LTV 하락
    UNAFFECTED = "영향 없음"


@dataclass(frozen=True)
class CustomerImpact:
    customer_id: str
    region_code: str
    property_price: int
    before: LtvDecision
    after: LtvDecision
    segment: Segment

    @property
    def limit_before(self) -> int:
        return int(self.property_price * (self.before.max_ltv or 0.0))

    @property
    def limit_after(self) -> int:
        return int(self.property_price * (self.after.max_ltv or 0.0))

    @property
    def limit_delta(self) -> int:
        """음수 = 한도 감소액."""
        return self.limit_after - self.limit_before


@dataclass
class CustomerImpactReport:
    impacts: list[CustomerImpact] = field(default_factory=list)
    portfolio_size: int = 0
    seed: int = 0
    before_date: str = BEFORE_DATE.isoformat()
    after_date: str = AFTER_DATE.isoformat()

    # ---- 집계 ----
    @property
    def segment_counts(self) -> dict[str, int]:
        c = Counter(i.segment.value for i in self.impacts)
        return {s.value: c.get(s.value, 0) for s in Segment}

    @property
    def reduced(self) -> list[CustomerImpact]:
        return [i for i in self.impacts if i.segment == Segment.REDUCED]

    @property
    def affected_rate(self) -> float:
        """한도가 실제로 줄어든 고객 비율."""
        return len(self.reduced) / len(self.impacts) if self.impacts else 0.0

    @property
    def total_limit_reduction(self) -> int:
        """포트폴리오 전체 한도 감소액(원). 음수."""
        return sum(i.limit_delta for i in self.reduced)

    @property
    def avg_limit_reduction(self) -> int:
        r = self.reduced
        return int(self.total_limit_reduction / len(r)) if r else 0

    @property
    def worst_case(self) -> CustomerImpact | None:
        return min(self.reduced, key=lambda i: i.limit_delta, default=None)

    @property
    def grandfathered_count(self) -> int:
        return self.segment_counts[Segment.GRANDFATHERED.value]

    @property
    def human_review_count(self) -> int:
        return self.segment_counts[Segment.NEEDS_HUMAN_REVIEW.value]

    @property
    def escalation_reasons(self) -> dict[str, int]:
        """사람 검토로 넘어간 사유별 건수 — 자동화가 어디서 멈추는지의 실체."""
        c: Counter = Counter()
        for i in self.impacts:
            if i.segment != Segment.NEEDS_HUMAN_REVIEW:
                continue
            codes = set(i.before.reason_codes) | set(i.after.reason_codes)
            for code in sorted(codes):
                c[code] += 1
        return dict(sorted(c.items(), key=lambda kv: -kv[1]))

    @property
    def ltv_transitions(self) -> dict[str, int]:
        """LTV before → after 전이표. 매트릭스 "예상 한도 변화"의 근거."""
        c: Counter = Counter()
        for i in self.impacts:
            b = "—" if i.before.max_ltv is None else f"{i.before.max_ltv:.0%}"
            a = "—" if i.after.max_ltv is None else f"{i.after.max_ltv:.0%}"
            c[f"{b} → {a}"] += 1
        return dict(sorted(c.items(), key=lambda kv: -kv[1]))


def _classify(before: LtvDecision, after: LtvDecision) -> Segment:
    if after.status == EvaluationStatus.OUT_OF_SCOPE:
        return Segment.OUT_OF_SCOPE
    if after.status == EvaluationStatus.DISCOVERY:
        return Segment.DISCOVERY
    if EvaluationStatus.NEEDS_HUMAN_REVIEW in (before.status, after.status):
        return Segment.NEEDS_HUMAN_REVIEW
    if after.grandfathering_applied:
        return Segment.GRANDFATHERED
    if (after.max_ltv or 0.0) < (before.max_ltv or 0.0):
        return Segment.REDUCED
    return Segment.UNAFFECTED


def analyze_portfolio(
    portfolio: list[PortfolioCustomer], *, seed: int = 0
) -> CustomerImpactReport:
    """포트폴리오를 시행 전/후 두 시점으로 평가해 영향을 집계한다."""
    impacts = []
    for cust in portfolio:
        before = evaluate(cust.as_of(BEFORE_DATE))
        after = evaluate(cust.as_of(AFTER_DATE))
        impacts.append(
            CustomerImpact(
                customer_id=cust.customer_id,
                region_code=cust.application.region_code,
                property_price=cust.property_price,
                before=before,
                after=after,
                segment=_classify(before, after),
            )
        )
    return CustomerImpactReport(
        impacts=impacts, portfolio_size=len(portfolio), seed=seed
    )
