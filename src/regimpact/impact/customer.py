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

from typing import Optional

from ..models import EvaluationStatus, LtvDecision
from ..rule_engine import evaluate
from .portfolio import AFTER_DATE, BEFORE_DATE, PortfolioCustomer


class Segment(str, Enum):
    """고객 영향 분류. 위에서부터 우선 적용(한 고객은 한 세그먼트).

    **심사 판정 가능 여부**와 **영향(변화량) 측정 가능 여부**는 다른 질문이다.
    규제지역 유주택자는 시행일 LTV가 0%로 확정되므로 **오늘 심사할 수 있다**. 다만 시행 전
    非규제 기준값이 명세에 없어서 "얼마나 줄었는가"만 계산되지 않는다(Q10). 이 둘을 한 통에
    담으면 "유주택 고객을 처리할 수 없다"는 잘못된 그림이 된다 → 분리한다.
    """
    OUT_OF_SCOPE = "적용 대상 아님"           # 주택구입목적 아님
    DISCOVERY = "Discovery(수동 검토)"        # 정책대출 등 코어 자동판정 제외
    NEEDS_HUMAN_REVIEW = "판정 불가(사람 검토)"  # 시행일 LTV 자체를 결정할 수 없음
    IMPACT_UNKNOWN = "판정됨·변화량 미상"       # 시행일 LTV는 확정, 시행 전 기준값만 부재
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
    def limit_before(self) -> Optional[int]:
        """시행 전 한도. LTV가 확정되지 않았으면 None (0원으로 세지 않는다)."""
        if self.before.max_ltv is None:
            return None
        return int(self.property_price * self.before.max_ltv)

    @property
    def limit_after(self) -> Optional[int]:
        if self.after.max_ltv is None:
            return None
        return int(self.property_price * self.after.max_ltv)

    @property
    def limit_delta(self) -> Optional[int]:
        """음수 = 한도 감소액. 양쪽 중 하나라도 미확정이면 None.

        미확정을 0으로 대체하면 "한도가 늘었다" 같은 허구의 수치가 집계에 섞인다.
        """
        before, after = self.limit_before, self.limit_after
        if before is None or after is None:
            return None
        return after - before


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
    def undecidable_count(self) -> int:
        """시행일 LTV 자체를 결정할 수 없는 건 — 오늘 심사가 막히는 진짜 escalation."""
        return self.segment_counts[Segment.NEEDS_HUMAN_REVIEW.value]

    @property
    def impact_unknown_count(self) -> int:
        """심사는 되지만 시행 전 기준값 부재로 변화량만 계산되지 않는 건 (Q10)."""
        return self.segment_counts[Segment.IMPACT_UNKNOWN.value]

    @property
    def decision_coverage(self) -> float:
        """**심사 판정 커버리지** — 시행일 LTV가 확정된 비율.

        Discovery·Out-of-scope는 애초에 코어 자동판정 대상이 아니므로 분모에서 뺀다
        (자동화율을 부풀리지 않으려면 분모를 '판정을 시도하는 모집단'으로 잡아야 한다).
        """
        target = [
            i for i in self.impacts
            if i.segment not in (Segment.OUT_OF_SCOPE, Segment.DISCOVERY)
        ]
        if not target:
            return 1.0
        decided = sum(1 for i in target if i.after.status == EvaluationStatus.DECIDED)
        return decided / len(target)

    @property
    def impact_coverage(self) -> float:
        """**영향 측정 커버리지** — before/after가 모두 확정되어 변화량을 계산할 수 있는 비율."""
        target = [
            i for i in self.impacts
            if i.segment not in (Segment.OUT_OF_SCOPE, Segment.DISCOVERY)
        ]
        if not target:
            return 1.0
        return sum(1 for i in target if i.limit_delta is not None) / len(target)

    @property
    def total_limit_reduction(self) -> int:
        """포트폴리오 전체 한도 감소액(원). 음수. 변화량이 확정된 건만 더한다."""
        return sum(i.limit_delta for i in self.reduced if i.limit_delta is not None)

    @property
    def avg_limit_reduction(self) -> int:
        r = self.reduced
        return int(self.total_limit_reduction / len(r)) if r else 0

    @property
    def worst_case(self) -> CustomerImpact | None:
        candidates = [i for i in self.reduced if i.limit_delta is not None]
        return min(candidates, key=lambda i: i.limit_delta, default=None)

    @property
    def grandfathered_count(self) -> int:
        return self.segment_counts[Segment.GRANDFATHERED.value]

    @property
    def human_review_count(self) -> int:
        """사람 개입이 필요한 전체 — 판정 불가 + 변화량 미상."""
        return self.undecidable_count + self.impact_unknown_count

    @property
    def escalation_reasons(self) -> dict[str, int]:
        """사람 개입이 필요한 건의 사유별 건수 (판정 불가 + 변화량 미상)."""
        c: Counter = Counter()
        for i in self.impacts:
            if i.segment not in (Segment.NEEDS_HUMAN_REVIEW, Segment.IMPACT_UNKNOWN):
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
    # 시행일 판정이 안 되면 이 고객은 오늘 심사할 수 없다 — 진짜 escalation.
    if after.status != EvaluationStatus.DECIDED:
        return Segment.NEEDS_HUMAN_REVIEW
    # 시행일 판정은 됐는데 시행 전 기준값이 없으면 심사는 가능, 변화량만 미상 (Q10).
    if before.status != EvaluationStatus.DECIDED:
        return Segment.IMPACT_UNKNOWN
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
