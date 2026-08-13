"""Impact Matrix — 규제 변경의 고객 세그먼트별 before/after 영향을 산출한다.

브리프 §18 / 04_PLAN Phase 1: "Impact Matrix(1~2행)". 각 행은
(세그먼트 × 지역)에 대해 시행 전(before)과 시행 후(after)를 **동일 룰엔진**으로
평가하고 그 차이(delta)를 낸다. 값이 아니라 '차이의 방향·크기·escalation 여부'가
영향분석의 핵심 산출물이다.

LOCKED §4: before/after LTV는 전부 deterministic 룰엔진(evaluate)이 낸 값이다.
LLM이 영향 수치를 만들지 않는다 → Impact Matrix는 auditable하다.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from ..models import EvaluationStatus, LtvDecision
from ..rule_engine import evaluate
from .personas import SIX_THIRTY_PERSONAS, Persona

# 6·30 시나리오 시점 앵커
BEFORE_DATE = date(2026, 6, 30)   # 효력 발생일 전일 → 아직 非규제(수도권)
AFTER_DATE = date(2026, 7, 2)     # 시행 후 → 규제지역
SIX_THIRTY_REGIONS = ("GURI", "YONGIN_GIHEUNG", "HWASEONG_DONGTAN")

# 고영향(high-impact) 판정 임계 — metrics_spec high-risk 후보와 정렬(초안, 사용자 확정 대기).
# LTV가 20%p 이상 변하거나 escalation 상태로 전이하면 사람 검토 우선순위가 높다.
HIGH_IMPACT_LTV_DELTA = 0.20

_ESCALATION_STATUSES = {EvaluationStatus.NEEDS_HUMAN_REVIEW, EvaluationStatus.DISCOVERY}


@dataclass(frozen=True)
class ImpactRow:
    """Impact Matrix 한 행 — 한 세그먼트가 한 지역에서 받는 영향."""
    persona_id: str
    segment_label: str
    region_code: str
    before: LtvDecision
    after: LtvDecision

    @property
    def before_ltv(self) -> Optional[float]:
        return self.before.max_ltv

    @property
    def after_ltv(self) -> Optional[float]:
        return self.after.max_ltv

    @property
    def delta_ltv(self) -> Optional[float]:
        """양 시점이 모두 LTV로 확정된 경우에만 차이가 정의된다.

        한쪽이라도 escalation(NEEDS_HUMAN_REVIEW/DISCOVERY)이면 delta는 None
        (= '기계적으로 비교 불가, 사람 검토 필요'라는 정직한 신호)."""
        if self.before.max_ltv is None or self.after.max_ltv is None:
            return None
        return round(self.after.max_ltv - self.before.max_ltv, 4)

    @property
    def escalated(self) -> bool:
        """어느 한 시점이라도 사람 검토·Discovery로 빠지는가."""
        return (
            self.before.status in _ESCALATION_STATUSES
            or self.after.status in _ESCALATION_STATUSES
        )

    @property
    def status_changed(self) -> bool:
        return self.before.status != self.after.status

    @property
    def high_impact(self) -> bool:
        """고영향 행: 큰 LTV 하락/상승 또는 escalation 전이.

        정의는 초안(HIGH_IMPACT_LTV_DELTA)이며 metrics_spec high-risk 확정 시 정렬한다."""
        if self.escalated:
            return True
        d = self.delta_ltv
        return d is not None and abs(d) >= HIGH_IMPACT_LTV_DELTA


def build_impact_matrix(
    regions: Optional[list[str] | tuple[str, ...]] = None,
    personas: Optional[list[Persona]] = None,
    before_date: date = BEFORE_DATE,
    after_date: date = AFTER_DATE,
) -> list[ImpactRow]:
    """세그먼트 × 지역을 before/after 두 시점으로 평가한 Impact Matrix를 만든다.

    regions/personas 미지정 시 6·30 기본값을 쓴다. 지역 목록은 보통
    RegChange 추출의 target_regions에서 온다(pipeline.run_e2e 참조).
    """
    regions = list(regions) if regions else list(SIX_THIRTY_REGIONS)
    personas = personas if personas is not None else SIX_THIRTY_PERSONAS

    rows: list[ImpactRow] = []
    for region in regions:
        for p in personas:
            before = evaluate(p.application(region, before_date))
            after = evaluate(p.application(region, after_date))
            rows.append(
                ImpactRow(
                    persona_id=p.persona_id,
                    segment_label=p.label,
                    region_code=region,
                    before=before,
                    after=after,
                )
            )
    return rows
