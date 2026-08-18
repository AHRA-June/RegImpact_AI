"""고객·포트폴리오 영향 분석 (브리프 §10 '고객·포트폴리오 영향 분석' 행, §18 Customer Impact).

Before/After를 **같은 결정론 엔진**으로 두 번 돌려 차이를 집계한다. LLM은 여기 개입하지 않는다.
    Before = 2026-06-30 시점 규정 (시행 전날)
    After  = 2026-07-02 시점 규정 (시행 후, 경과규정 성립 건은 종전규정으로 재판정됨)

집계가 정직하려면 세 가지를 구분해야 한다:
    ① LTV가 실제로 바뀐 건            → 영향(impacted)
    ② 경과규정으로 종전규정이 유지된 건 → 유예(grandfathered), 시행일 전후 처리가 갈리는 실무의 핵심
    ③ 판정이 사람에게 넘어간 건        → escalation. **이 건들은 '변화 없음'이 아니다.**
       숫자를 지어내지 않은 대가로 생긴 미결이므로 분모에서 지우지 않고 따로 센다.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field, replace
from typing import Iterable, Optional

from ..models import EvaluationStatus, LtvDecision
from ..rule_engine import evaluate
from .portfolio import AFTER_AS_OF, BEFORE_AS_OF, PortfolioRow, build_portfolio


@dataclass(frozen=True)
class RowImpact:
    """1건의 Before/After 판정과 그 차이.

    `after_no_gf` 는 반사실(counterfactual)이다 — 경과규정 이벤트를 지우고 시행 후 규정을 그대로
    적용했다면 어떤 판정이었을지. 경과규정이 '실제로 무엇을 막아줬는지'는 이 값과의 차이로만 말할 수 있다.
    """
    row: PortfolioRow
    before: LtvDecision
    after: LtvDecision
    after_no_gf: LtvDecision

    @property
    def ltv_before(self) -> Optional[float]:
        return self.before.max_ltv

    @property
    def ltv_after(self) -> Optional[float]:
        return self.after.max_ltv

    @property
    def decided_both(self) -> bool:
        return self.before.max_ltv is not None and self.after.max_ltv is not None

    @property
    def ltv_delta(self) -> Optional[float]:
        return None if not self.decided_both else self.after.max_ltv - self.before.max_ltv

    @property
    def limit_delta_eok(self) -> Optional[float]:
        """한도 변화(억) = 가격 × LTV 차이. LTV만 반영한 참고값(DTI·차주한도 미반영)."""
        d = self.ltv_delta
        return None if d is None else round(self.row.price_eok * d, 4)

    @property
    def impacted(self) -> bool:
        return bool(self.ltv_delta)          # 0.0 과 None 은 모두 False

    @property
    def grandfathered(self) -> bool:
        return self.after.grandfathering_applied

    @property
    def escalated(self) -> bool:
        return (self.before.status is EvaluationStatus.NEEDS_HUMAN_REVIEW
                or self.after.status is EvaluationStatus.NEEDS_HUMAN_REVIEW)

    @property
    def protected_by_grandfathering(self) -> bool:
        """경과규정이 실제로 판정을 바꿔준 건 (유예가 없었다면 결과가 달랐을 건)."""
        if not self.grandfathered:
            return False
        return (self.after.max_ltv != self.after_no_gf.max_ltv
                or self.after.status is not self.after_no_gf.status)

    @property
    def transition(self) -> str:
        """rule_id 전이 — Rule Change Proposal 의 원재료."""
        b = self.before.applicable_rule_id or self.before.status.value
        a = self.after.applicable_rule_id or self.after.status.value
        return f"{b} → {a}"


@dataclass
class SegmentImpact:
    """세그먼트(지역군 × 차주유형) 집계."""
    region_group: str
    borrower_label: str
    n: float = 0.0
    impacted: float = 0.0
    grandfathered: float = 0.0
    escalated: float = 0.0
    ltv_before_sum: float = 0.0
    ltv_after_sum: float = 0.0
    ltv_decided_n: float = 0.0
    limit_delta_sum_eok: float = 0.0
    transitions: dict[str, float] = field(default_factory=lambda: defaultdict(float))

    @property
    def impacted_rate(self) -> float:
        return self.impacted / self.n if self.n else 0.0

    @property
    def escalation_rate(self) -> float:
        return self.escalated / self.n if self.n else 0.0

    @property
    def avg_ltv_before(self) -> Optional[float]:
        if not self.ltv_decided_n:
            return None
        return round(self.ltv_before_sum / self.ltv_decided_n, 6)

    @property
    def avg_ltv_after(self) -> Optional[float]:
        if not self.ltv_decided_n:
            return None
        return round(self.ltv_after_sum / self.ltv_decided_n, 6)

    @property
    def avg_ltv_delta(self) -> Optional[float]:
        if not self.ltv_decided_n:
            return None
        return round(self.avg_ltv_after - self.avg_ltv_before, 6)

    @property
    def top_transition(self) -> Optional[str]:
        return max(self.transitions, key=self.transitions.get) if self.transitions else None


@dataclass
class StratumImpact:
    """한 축(지역군/이벤트/차주유형)으로 자른 층 집계."""
    label: str
    n: float = 0.0
    impacted: float = 0.0
    grandfathered: float = 0.0
    protected: float = 0.0
    escalated: float = 0.0
    limit_delta_sum_eok: float = 0.0

    @property
    def impacted_rate(self) -> float:
        return self.impacted / self.n if self.n else 0.0

    @property
    def escalation_rate(self) -> float:
        return self.escalated / self.n if self.n else 0.0


@dataclass
class CustomerImpactReport:
    rows: list[RowImpact]
    segments: list[SegmentImpact]

    # --- 전체 지표 (가중치 반영) ---
    @property
    def total(self) -> float:
        return sum(r.row.weight for r in self.rows)

    @property
    def impacted(self) -> float:
        return sum(r.row.weight for r in self.rows if r.impacted)

    @property
    def grandfathered(self) -> float:
        return sum(r.row.weight for r in self.rows if r.grandfathered)

    @property
    def escalated(self) -> float:
        return sum(r.row.weight for r in self.rows if r.escalated)

    @property
    def impacted_rate(self) -> float:
        return self.impacted / self.total if self.total else 0.0

    @property
    def escalation_rate(self) -> float:
        """자동 판정을 거부한 비율. Assurance 지표이자 운영 부하 지표."""
        return self.escalated / self.total if self.total else 0.0

    @property
    def limit_delta_sum_eok(self) -> float:
        return round(sum(r.row.weight * (r.limit_delta_eok or 0.0) for r in self.rows), 4)

    def tightened(self) -> float:
        return sum(r.row.weight for r in self.rows if (r.ltv_delta or 0) < 0)

    def loosened(self) -> float:
        return sum(r.row.weight for r in self.rows if (r.ltv_delta or 0) > 0)

    def rule_transitions(self) -> dict[str, float]:
        """실제로 발생한 rule_id 전이와 그 건수 — 구조화 Rule Change Proposal 의 근거."""
        out: dict[str, float] = defaultdict(float)
        for r in self.rows:
            if r.impacted:
                out[r.transition] += r.row.weight
        return dict(sorted(out.items(), key=lambda kv: -kv[1]))

    @property
    def protected_by_grandfathering(self) -> float:
        return sum(r.row.weight for r in self.rows if r.protected_by_grandfathering)

    # --- 층별 집계 (혼합 비율 하나로 말하지 않기 위한 분해) ---
    def by_region_group(self) -> dict[str, "StratumImpact"]:
        return self._stratify(lambda r: r.row.region_group)

    def by_event(self) -> dict[str, "StratumImpact"]:
        return self._stratify(lambda r: r.row.event.label)

    def by_borrower(self) -> dict[str, "StratumImpact"]:
        return self._stratify(lambda r: r.row.borrower.label)

    def no_event_only(self) -> "CustomerImpactReport":
        """경과규정 이벤트가 없는 층만.

        헤드라인 영향률과 **세그먼트 평균 LTV는 이 층에서 읽어야 한다.** 전체 격자로 평균을 내면
        경과규정 건(전체의 3/4)이 섞여 "70% → 63%" 같은 값이 나오는데, 그건 규제 변경의 크기가
        아니라 격자 설계의 부산물이다. 실제 변경은 "70% → 40%"다.
        """
        rows = [r for r in self.rows if r.row.event.key == "none"]
        return CustomerImpactReport(rows=rows, segments=build_segments(rows))

    def _stratify(self, keyfn) -> dict[str, "StratumImpact"]:
        out: dict[str, StratumImpact] = {}
        for r in self.rows:
            st = out.setdefault(keyfn(r), StratumImpact(label=keyfn(r)))
            w = r.row.weight
            st.n += w
            if r.impacted:
                st.impacted += w
            if r.grandfathered:
                st.grandfathered += w
            if r.protected_by_grandfathering:
                st.protected += w
            if r.escalated:
                st.escalated += w
            if r.decided_both:
                st.limit_delta_sum_eok += w * (r.limit_delta_eok or 0.0)
        return out

    def escalation_reasons(self) -> dict[str, float]:
        out: dict[str, float] = defaultdict(float)
        for r in self.rows:
            if not r.escalated:
                continue
            for code in set(r.before.reason_codes) | set(r.after.reason_codes):
                if code.endswith("UNKNOWN") or code == "OWNER_BASELINE_UNKNOWN":
                    out[code] += r.row.weight
        return dict(sorted(out.items(), key=lambda kv: -kv[1]))


def analyze_customer_impact(
    portfolio: Optional[Iterable[PortfolioRow]] = None,
) -> CustomerImpactReport:
    """포트폴리오 전체를 Before/After 두 번 판정해 세그먼트별로 집계한다."""
    rows_in = list(portfolio) if portfolio is not None else build_portfolio()

    impacts = []
    for r in rows_in:
        after_app = r.as_of(AFTER_AS_OF)
        # 반사실: 경과규정 이벤트를 모두 지운 동일 신청건
        no_gf_app = replace(
            after_app, application_accepted_at=None, contract_signed_at=None,
            downpayment_paid_at=None, land_permit_target=False, land_permit_applied_at=None,
        )
        impacts.append(RowImpact(
            row=r,
            before=evaluate(r.as_of(BEFORE_AS_OF)),
            after=evaluate(after_app),
            after_no_gf=evaluate(no_gf_app),
        ))

    return CustomerImpactReport(rows=impacts, segments=build_segments(impacts))


def build_segments(impacts: list[RowImpact]) -> list[SegmentImpact]:
    """지역군 × 차주유형으로 집계."""
    buckets: dict[tuple[str, str], SegmentImpact] = {}
    for imp in impacts:
        key = (imp.row.region_group, imp.row.borrower.label)
        seg = buckets.setdefault(key, SegmentImpact(*key))
        w = imp.row.weight
        seg.n += w
        if imp.impacted:
            seg.impacted += w
            seg.transitions[imp.transition] += w
        if imp.grandfathered:
            seg.grandfathered += w
        if imp.escalated:
            seg.escalated += w
        if imp.decided_both:
            seg.ltv_decided_n += w
            seg.ltv_before_sum += w * imp.ltv_before
            seg.ltv_after_sum += w * imp.ltv_after
            seg.limit_delta_sum_eok += w * (imp.limit_delta_eok or 0.0)
    return list(buckets.values())
