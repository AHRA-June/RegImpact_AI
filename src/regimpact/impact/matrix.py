"""Impact Matrix — 규제 변경의 '시행 전/후' 영향을 세그먼트별로 산출.

Walking Skeleton(docs/04_PLAN.md Phase 1)의 Before/After → Impact Matrix 노드.

핵심 아이디어:
    LTV 규제 변경의 '임팩트'는 **같은 고객 프로필을 시행 전 시점과 시행 후 시점으로
    각각 판정**했을 때의 차이다. 룰엔진(rule_engine.evaluate)은 이미 지역 규제상태를
    evaluation_date 로 시점 해석하므로(regions.resolve_region_status), 동일 프로필을
    before_date(시행 전) / after_date(시행 후)로 두 번 돌리면 Before/After 가 자연히 나온다.

    → Impact Matrix 는 룰엔진을 '차등 실행(temporal diff)' 하는 얇은 노드이며,
      규칙값을 자체 보유하지 않는다(LOCKED §4: 규칙은 확정 명세→엔진에서만).

정직성 원칙(브리프 §12, 가치제안):
    한쪽 시점에서라도 판정이 DECIDED 가 아니면(escalation/discovery/scope) 델타를
    억지로 계산하지 않고 REVIEW 로 표면화한다. 예: 非규제 수도권 유주택은 명세에
    기준값이 없어 시행 전이 NEEDS_HUMAN_REVIEW → 임팩트도 'REVIEW(검토필요)'로 노출.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum
from typing import Optional

from ..models import EvaluationStatus, LtvDecision, MortgageApplication
from ..rule_engine import evaluate


class ImpactDirection(str, Enum):
    """세그먼트가 규제 변경으로 받는 영향의 방향."""
    TIGHTENED = "TIGHTENED"    # LTV 하락 (규제 강화)
    LOOSENED = "LOOSENED"      # LTV 상승 (완화)
    UNCHANGED = "UNCHANGED"    # 변동 없음 (예외로 보호되는 경우 등)
    REVIEW = "REVIEW"          # 한쪽 이상 판정 불가 → 사람 검토 필요


# Impact Matrix 가 자연스러운 델타를 계산할 수 있는(=DECIDED + max_ltv 존재) 시점 상태.
def _is_numeric(dec: LtvDecision) -> bool:
    return dec.status == EvaluationStatus.DECIDED and dec.max_ltv is not None


@dataclass(frozen=True)
class Segment:
    """임팩트 분석 대상 고객 세그먼트(프로필 템플릿).

    profile 은 MortgageApplication 의 '비시점·비지역' 필드 kwargs (house_count,
    first_home_buyer, real_demand_flag, disposal_condition_flag, policy_mortgage_flag,
    loan_purpose 등). region_code / evaluation_date 는 분석기가 시점별로 채운다.
    """
    segment_id: str
    label: str
    profile: dict = field(default_factory=dict)

    def build(self, region_code: str, evaluation_date: date) -> MortgageApplication:
        """세그먼트 프로필을 특정 지역·시점의 룰엔진 입력으로 실체화한다."""
        return MortgageApplication(
            region_code=region_code,
            evaluation_date=evaluation_date,
            **self.profile,
        )


@dataclass(frozen=True)
class ImpactRow:
    """Impact Matrix 한 행: (세그먼트 × 지역)의 시행 전/후 판정과 그 차이."""
    segment: Segment
    region_code: str
    before: LtvDecision
    after: LtvDecision
    direction: ImpactDirection
    delta_ltv: Optional[float]   # after.max_ltv - before.max_ltv (양쪽 DECIDED일 때만)
    note: Optional[str] = None

    @property
    def before_ltv(self) -> Optional[float]:
        return self.before.max_ltv if _is_numeric(self.before) else None

    @property
    def after_ltv(self) -> Optional[float]:
        return self.after.max_ltv if _is_numeric(self.after) else None


@dataclass
class ImpactMatrix:
    """세그먼트별 Before/After 영향표 + 시점 메타."""
    region_code: str
    before_date: date
    after_date: date
    rows: list[ImpactRow] = field(default_factory=list)
    policy_id: Optional[str] = None   # 근거 정책(Extractor 연동 시)

    def by_direction(self, direction: ImpactDirection) -> list[ImpactRow]:
        return [r for r in self.rows if r.direction == direction]

    def summary(self) -> dict[str, int]:
        """방향별 세그먼트 수 요약."""
        out = {d.value: 0 for d in ImpactDirection}
        for r in self.rows:
            out[r.direction.value] += 1
        return out

    @property
    def review_required(self) -> list[ImpactRow]:
        """사람 검토가 필요한 행(정직한 escalation 노출)."""
        return self.by_direction(ImpactDirection.REVIEW)


def _classify(before: LtvDecision, after: LtvDecision) -> tuple[ImpactDirection, Optional[float]]:
    """시행 전/후 판정으로 영향 방향과 델타를 산정한다.

    양쪽 모두 수치 판정(DECIDED)일 때만 델타를 계산한다. 그 외에는 REVIEW.
    """
    if _is_numeric(before) and _is_numeric(after):
        # 부동소수 오차 방지 (0.70 - 0.40 = 0.29999... 방지)
        delta = round(after.max_ltv - before.max_ltv, 4)
        if delta < 0:
            return ImpactDirection.TIGHTENED, delta
        if delta > 0:
            return ImpactDirection.LOOSENED, delta
        return ImpactDirection.UNCHANGED, delta
    return ImpactDirection.REVIEW, None


def _review_note(before: LtvDecision, after: LtvDecision) -> Optional[str]:
    """REVIEW 사유를 사람이 읽을 수 있게 요약(있으면)."""
    parts: list[str] = []
    for when, dec in (("before", before), ("after", after)):
        if not _is_numeric(dec):
            rc = ",".join(dec.reason_codes) if dec.reason_codes else "-"
            parts.append(f"{when}={dec.status.value}({rc})")
    return "; ".join(parts) if parts else None


def analyze_impact(
    segments: list[Segment],
    region_code: str,
    before_date: date,
    after_date: date,
    policy_id: Optional[str] = None,
) -> ImpactMatrix:
    """세그먼트들을 시행 전/후 두 시점으로 판정해 Impact Matrix 를 만든다.

    Args:
        segments: 분석 대상 세그먼트 목록.
        region_code: 영향 지역(예: 6·30 신규지정 'GURI').
        before_date: 시행 전 평가 시점(예: 2026-06-30).
        after_date: 시행 후 평가 시점(예: 2026-07-02, 경과규정 미해당 기준).
        policy_id: 근거 정책 식별자(선택, Extractor 연동 시 추적용).
    """
    rows: list[ImpactRow] = []
    for seg in segments:
        before = evaluate(seg.build(region_code, before_date))
        after = evaluate(seg.build(region_code, after_date))
        direction, delta = _classify(before, after)
        note = _review_note(before, after) if direction == ImpactDirection.REVIEW else None
        rows.append(
            ImpactRow(
                segment=seg,
                region_code=region_code,
                before=before,
                after=after,
                direction=direction,
                delta_ltv=delta,
                note=note,
            )
        )
    return ImpactMatrix(
        region_code=region_code,
        before_date=before_date,
        after_date=after_date,
        rows=rows,
        policy_id=policy_id,
    )


def analyze_from_extraction(
    extraction,
    segments: list[Segment],
    region_code: str,
    after_gap_days: int = 2,
) -> ImpactMatrix:
    """RegChange Extractor 출력(effective_from)에서 시점을 유도해 Impact Matrix 생성.

    Walking Skeleton E2E 연결: Extractor(effective_from) → Impact Matrix.

    시행일(effective_from)이 규제 효력 시작일이므로:
        before_date = effective_from - 1일 (규제 전, 종전규정 구간)
        after_date  = effective_from + after_gap_days (규제 후, 경과규정 컷오프 여유)

    Args:
        extraction: RegChangeExtraction (extractor.schema). effective_from(ISO) 필요.
        segments: 분석 대상 세그먼트.
        region_code: 영향 지역 코드(추출된 target_regions 를 엔진 지역코드로 매핑한 값).
        after_gap_days: 시행일로부터 며칠 뒤를 '시행 후' 대표 시점으로 볼지.

    Raises:
        ValueError: extraction.effective_from 이 없거나 ISO date 로 파싱 불가할 때.
    """
    if not getattr(extraction, "effective_from", None):
        raise ValueError("extraction.effective_from 이 비어 있어 시점을 유도할 수 없습니다.")
    try:
        effective = date.fromisoformat(extraction.effective_from)
    except ValueError as exc:
        raise ValueError(
            f"effective_from='{extraction.effective_from}' 을 ISO date 로 파싱할 수 없습니다."
        ) from exc

    before_date = effective - timedelta(days=1)
    after_date = effective + timedelta(days=after_gap_days)
    return analyze_impact(
        segments=segments,
        region_code=region_code,
        before_date=before_date,
        after_date=after_date,
        policy_id=getattr(extraction, "policy_id", None),
    )
