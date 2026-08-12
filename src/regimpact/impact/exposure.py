"""대출 여력 영향 금액 집계 (loanable-capacity exposure) — 04_PLAN Phase 2.

목적:
  Impact Matrix가 산출하는 **LTV %p 변화**를, 문서화된 **담보가격 밴드**와 결합해
  차주 1인당·포트폴리오 전체의 **대출 여력(loanable capacity) 변화 금액**으로 환산한다.
  여력 = 담보가격 × 적용 LTV. before/after 두 시점의 여력 차이가 6·30 규제의 금액 영향이다.

⚠️ **정직성 고지 4가지 (반드시 리포트에 노출, 조용한 누락 금지):**
  1. 이것은 **여력(한도) 변화**이지 **실행액(originations)이 아니다.** 실제 실행은 수요·DSR·
     차주 선택에 좌우된다. 여기서는 "규제가 허용하는 최대 담보대출 한도"만 비교한다.
  2. **LTV 규칙만** 반영한다. 가격대별 **대출 최대한도 상한(6억/4억/2억)**은 여기서 적용하지 않는다
     (별도 Discovery 항목). 상한을 적용하면 고가 밴드의 여력은 더 줄어든다 → 본 산정은 상한 미적용
     기준의 **상한(upper bound)** 성격.
  3. 담보가격 분포(PRICE_BANDS)와 대표가격은 **문서화된 시나리오 가정**이지 실측 데이터가 아니다.
     실측이 확보되면 이 표만 교체한다(집계 코드는 불변).
  4. before/after 어느 시점이라도 **자동판정 불가(명세 여백 등, 예: 비규제 유주택 시행 전 기준선)**
     이면 여력 금액을 **산정 불가**로 분리 집계한다(undetermined). 0으로 뭉개지 않는다.

두 경로(같은 분포):
  - PRICE_BANDS와 세그먼트 weight의 곱으로 **정확 가중** 집계(compute_exposure).
  - sample_portfolio 표본에 담보가격을 몬테카를로로 부여해도 같은 분포에 수렴(attach_sampled_prices).
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from ..models import EvaluationStatus, LtvDecision
from .matrix import (
    AFTER_DATE,
    BEFORE_DATE,
    CustomerSegment,
    analyze_segment,
)

# --------------------------------------------------------------------------- #
# 담보가격 밴드 (문서화된 가정, 실측 아님) — 수도권 신규 규제지역 시나리오
# representative_price: 밴드 대표 담보가격(억원). share: 모집단 내 밴드 점유율(합=1.00).
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class PriceBand:
    label: str
    representative_price: float   # 억원
    share: float                  # 모집단 점유율(가정)


PRICE_BANDS: list[PriceBand] = [
    PriceBand("6억 이하", 4.5, 0.30),
    PriceBand("6~9억", 7.5, 0.28),
    PriceBand("9~15억", 12.0, 0.25),
    PriceBand("15~25억", 19.0, 0.13),
    PriceBand("25억 초과", 30.0, 0.04),
]


def price_model_note() -> str:
    total = sum(b.share for b in PRICE_BANDS)
    mean = mean_property_price()
    return (
        "담보가격 밴드(문서화된 가정, 실측 아님): "
        + ", ".join(f"{b.label} {b.share:.0%}@{b.representative_price:g}억" for b in PRICE_BANDS)
        + f" | 밴드합 {total:.2f} · 가중평균 담보가격 {mean:.2f}억"
    )


def mean_property_price(bands: list[PriceBand] = PRICE_BANDS) -> float:
    """밴드 점유율 가중 평균 담보가격(억원)."""
    tw = sum(b.share for b in bands)
    if tw == 0:
        return 0.0
    return sum(b.representative_price * b.share for b in bands) / tw


# --------------------------------------------------------------------------- #
# 집계 결과 스키마
# --------------------------------------------------------------------------- #

@dataclass
class BandExposure:
    """담보가격 밴드 1개의 여력 변화(자동판정 가능분 기준)."""
    label: str
    weight: float               # 이 밴드에 배분된 가중치(판정가능분)
    before_capacity: float      # Σ w·price·before_ltv  (억원·가중)
    after_capacity: float       # Σ w·price·after_ltv
    undetermined_weight: float  # 이 밴드에 배분된 산정불가 가중치

    @property
    def delta_capacity(self) -> float:
        return self.after_capacity - self.before_capacity


@dataclass
class SegmentExposure:
    """세그먼트(아키타입) 1개의 여력 변화."""
    label: str
    weight: float               # 세그먼트 총 가중(모든 밴드 합)
    determinable: bool          # before·after 모두 자동판정(DECIDED) 여부
    before_ltv: Optional[float]
    after_ltv: Optional[float]
    before_capacity: float      # 판정가능 시 Σ w·price·before_ltv, 아니면 0
    after_capacity: float
    note: str = ""

    @property
    def delta_capacity(self) -> float:
        return self.after_capacity - self.before_capacity


@dataclass
class ExposureReport:
    """대출 여력 영향 금액 집계 결과 (감사 가능)."""
    policy_id: str
    before_date: date
    after_date: date
    total_weight: float
    determinable_weight: float       # before·after 모두 DECIDED 인 가중 합
    undetermined_weight: float       # 어느 시점이라도 자동판정 불가한 가중 합
    before_capacity: float           # Σ(판정가능) w·price·before_ltv (억원·가중)
    after_capacity: float
    by_band: list[BandExposure] = field(default_factory=list)
    by_segment: list[SegmentExposure] = field(default_factory=list)

    @property
    def delta_capacity(self) -> float:
        """여력 변화 금액(억원·가중). 음수 = 여력 축소."""
        return self.after_capacity - self.before_capacity

    @property
    def pct_reduction(self) -> Optional[float]:
        """판정가능분 대비 여력 감소율(음수 delta면 양수 %). before=0이면 None."""
        if self.before_capacity == 0:
            return None
        return -self.delta_capacity / self.before_capacity

    @property
    def undetermined_share(self) -> float:
        """전체 가중 대비 산정불가(명세 여백) 비중."""
        if self.total_weight == 0:
            return 0.0
        return self.undetermined_weight / self.total_weight

    def per_unit_before(self) -> Optional[float]:
        """판정가능분 1인당 평균 여력(시행 전, 억원). 분모=판정가능 가중."""
        if self.determinable_weight == 0:
            return None
        return self.before_capacity / self.determinable_weight

    def per_unit_after(self) -> Optional[float]:
        if self.determinable_weight == 0:
            return None
        return self.after_capacity / self.determinable_weight

    def per_unit_delta(self) -> Optional[float]:
        if self.determinable_weight == 0:
            return None
        return self.delta_capacity / self.determinable_weight


# --------------------------------------------------------------------------- #
# 집계 로직
# --------------------------------------------------------------------------- #

def _decided_ltv(d: LtvDecision) -> Optional[float]:
    if d.status == EvaluationStatus.DECIDED and d.max_ltv is not None:
        return d.max_ltv
    return None


def compute_exposure(
    segments: list[CustomerSegment],
    policy_id: str = "6_30_2026",
    before_date: date = BEFORE_DATE,
    after_date: date = AFTER_DATE,
    bands: list[PriceBand] = PRICE_BANDS,
) -> ExposureReport:
    """세그먼트 목록 × 담보가격 밴드로 대출 여력 변화 금액을 집계한다.

    핵심: before/after LTV는 담보가격과 무관하므로 세그먼트당 1회만 평가하고,
    밴드는 (weight × share × price) 곱으로 금액을 배분한다. 판정 불가 세그먼트의
    가중치는 undetermined 로 분리(산정 불가) — 0으로 합산하지 않는다.
    """
    band_before = {b.label: 0.0 for b in bands}
    band_after = {b.label: 0.0 for b in bands}
    band_weight = {b.label: 0.0 for b in bands}
    band_undet = {b.label: 0.0 for b in bands}

    seg_rows: list[SegmentExposure] = []
    total_weight = 0.0
    determinable_weight = 0.0
    undetermined_weight = 0.0
    total_before = 0.0
    total_after = 0.0

    for seg in segments:
        imp = analyze_segment(seg, before_date, after_date)
        b_ltv = _decided_ltv(imp.before)
        a_ltv = _decided_ltv(imp.after)
        determinable = b_ltv is not None and a_ltv is not None

        total_weight += seg.weight
        seg_before = 0.0
        seg_after = 0.0

        for band in bands:
            w = seg.weight * band.share
            if determinable:
                bc = w * band.representative_price * b_ltv  # type: ignore[operator]
                ac = w * band.representative_price * a_ltv  # type: ignore[operator]
                band_before[band.label] += bc
                band_after[band.label] += ac
                band_weight[band.label] += w
                seg_before += bc
                seg_after += ac
            else:
                band_undet[band.label] += w

        if determinable:
            determinable_weight += seg.weight
            total_before += seg_before
            total_after += seg_after
        else:
            undetermined_weight += seg.weight

        seg_rows.append(SegmentExposure(
            label=seg.label,
            weight=seg.weight,
            determinable=determinable,
            before_ltv=b_ltv,
            after_ltv=a_ltv,
            before_capacity=seg_before,
            after_capacity=seg_after,
            note=seg.note,
        ))

    by_band = [
        BandExposure(
            label=b.label,
            weight=band_weight[b.label],
            before_capacity=band_before[b.label],
            after_capacity=band_after[b.label],
            undetermined_weight=band_undet[b.label],
        )
        for b in bands
    ]

    return ExposureReport(
        policy_id=policy_id,
        before_date=before_date,
        after_date=after_date,
        total_weight=total_weight,
        determinable_weight=determinable_weight,
        undetermined_weight=undetermined_weight,
        before_capacity=total_before,
        after_capacity=total_after,
        by_band=by_band,
        by_segment=seg_rows,
    )


def attach_sampled_prices(
    segments: list[CustomerSegment],
    seed: int = 42,
    bands: list[PriceBand] = PRICE_BANDS,
) -> list[CustomerSegment]:
    """표본 세그먼트에 담보가격을 밴드 분포로 몬테카를로 부여(결정적 seed).

    각 세그먼트에 밴드 1개를 뽑아 대표가격을 property_price로 설정한 **복제본**을 돌려준다
    (원본 불변). 큰 표본이면 밴드 분포가 PRICE_BANDS.share 에 수렴 → compute_exposure와 동일 결론.
    """
    rng = random.Random(seed)
    labels = [b.label for b in bands]
    shares = [b.share for b in bands]
    price_by_label = {b.label: b.representative_price for b in bands}
    out: list[CustomerSegment] = []
    for seg in segments:
        chosen = rng.choices(labels, weights=shares, k=1)[0]
        out.append(CustomerSegment(
            label=seg.label,
            attrs=dict(seg.attrs),
            weight=seg.weight,
            note=seg.note,
            property_price=price_by_label[chosen],
        ))
    return out


# --------------------------------------------------------------------------- #
# 리포트 포매터 (텍스트)
# --------------------------------------------------------------------------- #

def _won(eok: float) -> str:
    """억원 → 사람이 읽는 금액 문자열."""
    sign = "-" if eok < 0 else ""
    v = abs(eok)
    if v >= 10000:
        return f"{sign}{v / 10000:.2f}조원"
    return f"{sign}{v:.1f}억"


def format_exposure(report: ExposureReport) -> str:
    lines: list[str] = []
    lines.append(
        f"대출 여력 영향 금액 — policy={report.policy_id}  "
        f"before={report.before_date}  after={report.after_date}"
    )
    lines.append(price_model_note())
    lines.append("")
    lines.append("정직성 고지: (1) 여력(한도) 변화 — 실행액 아님  "
                 "(2) LTV 규칙만 — 최대한도 상한(6/4/2억) 미적용(상한 성격)")
    lines.append("            (3) 담보가격 분포는 문서화된 가정(실측 아님)  "
                 "(4) 자동판정 불가분은 '산정 불가'로 분리")
    lines.append("")

    # 밴드별
    bh = f"{'담보가격 밴드':<12} {'판정가중':>8} {'여력 전':>10} {'여력 후':>10} {'Δ':>10}"
    lines.append(bh)
    lines.append("-" * max(len(bh), 60))
    for b in report.by_band:
        lines.append(
            f"{b.label:<12} {b.weight:>8.2f} "
            f"{_won(b.before_capacity):>10} {_won(b.after_capacity):>10} "
            f"{_won(b.delta_capacity):>10}"
        )
    lines.append("-" * max(len(bh), 60))

    # 세그먼트별 (산정 불가 표시)
    lines.append("")
    sh = f"{'세그먼트':<22} {'가중':>6} {'전LTV':>6} {'후LTV':>6} {'Δ여력':>10}"
    lines.append(sh)
    lines.append("-" * max(len(sh), 60))
    for s in report.by_segment:
        if s.determinable:
            b_ltv = f"{s.before_ltv:.0%}"
            a_ltv = f"{s.after_ltv:.0%}"
            dcap = _won(s.delta_capacity)
        else:
            b_ltv = "—" if s.before_ltv is None else f"{s.before_ltv:.0%}"
            a_ltv = "—" if s.after_ltv is None else f"{s.after_ltv:.0%}"
            dcap = "산정불가"
        lines.append(f"{s.label:<22} {s.weight:>6.2f} {b_ltv:>6} {a_ltv:>6} {dcap:>10}")
    lines.append("-" * max(len(sh), 60))

    # 집계
    pu_b = report.per_unit_before()
    pu_a = report.per_unit_after()
    pu_d = report.per_unit_delta()
    pct = report.pct_reduction
    lines.append(
        f"판정가능 여력  전 {_won(report.before_capacity)} → 후 {_won(report.after_capacity)}  "
        f"(Δ {_won(report.delta_capacity)}"
        + (f", 감소율 {pct:.1%})" if pct is not None else ")")
    )
    if pu_b is not None:
        lines.append(
            f"1인당 평균 여력  전 {pu_b:.2f}억 → 후 {pu_a:.2f}억  (Δ {pu_d:+.2f}억)"
        )
    lines.append(
        f"가중 분모  전체 {report.total_weight:.2f} · 판정가능 {report.determinable_weight:.2f} · "
        f"산정불가 {report.undetermined_weight:.2f} (비중 {report.undetermined_share:.1%})"
    )
    if report.undetermined_weight > 0:
        lines.append(
            "  주: 산정불가분은 시행 전/후 어느 시점이 자동판정 불가(명세 여백, 예: 비규제 유주택 "
            "시행 전 기준선)라 금액을 매기지 않고 분리 표기함(조용한 누락 금지)."
        )
    return "\n".join(lines)
