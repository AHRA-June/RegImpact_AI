"""비중/가격 민감도·견고성 분석 (sensitivity & robustness) — 04_PLAN Phase 2.

목적:
  임팩트/여력의 **헤드라인 결론**(여력 축소·강화 과반·감소율 28.6% 등)은 전부 **문서화된 가정**
  (아키타입 비중·지역 mix·담보가격 분포/수준) 위에 서 있다. Model Risk 검증의 첫 질문은
  "그 가정이 범위 안에서 틀리면 결론이 얼마나 움직이나?"이다. 이 모듈이 그 답을 낸다:
    1. OAT 토네이도 — 어떤 가정이 헤드라인을 가장 크게 좌우하는가(driver).
    2. 몬테카를로 밴드 — 가정을 그럴듯한 범위에서 흔들 때 헤드라인의 P5/P50/P95 밴드 + 결론 견고성.
    3. 가격 불변성 — 감소율(%)은 담보가격 수준에 불변, 절대 금액만 비례 이동함을 드러낸다.

⚠️ **정직성 고지(반드시 유지):**
  - 이것은 **문서화된 가정 입력에 대한 민감도**이지 **실세계 불확실성의 정량화가 아니다**(실측 없음).
  - **룰엔진·LTV 로직·시행일·경과규정은 절대 흔들지 않는다** — 그건 사람이 확정한 사실이지 가정이 아니다.
    민감도는 오직 예시적(illustrative) 모집단·가격 구성에만 가한다("확정 규칙 고정, 가정 입력만 스트레스").
  - 섭동 범위(±50%, ±30%, Dirichlet 집중도)와 표본분포도 **문서화된 가정**이다.
  - 목적은 과잉확신(false precision)을 막는 것: 점추정이 아니라 밴드로, 그리고 결론의 견고성으로 말한다.

성능: (아키타입×지역) 응답표(before/after LTV)는 weight·price와 무관하므로 **엔진 평가는 1회만**
  수행하고, 이후 모든 섭동은 순수 가중 산술로 처리한다(수천 표본도 즉시).
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from ..models import EvaluationStatus
from .exposure import PRICE_BANDS, PriceBand, mean_property_price
from .matrix import (
    AFTER_DATE,
    BEFORE_DATE,
    CustomerSegment,
    ImpactDirection,
    analyze_segment,
)
from .population import ARCHETYPE_SHARE, REGION_MIX
from .segments import DEFAULT_ARCHETYPES

# --- 섭동 범위 (문서화된 가정) ---
DEFAULT_CONCENTRATION = 40.0   # Dirichlet 집중도: 높을수록 base 주변으로 좁게(작을수록 넓게)
PRICE_LEVEL_JITTER = 0.20      # 담보가격 수준 로그정규 σ (≈ ±20%)
ARCH_OAT_DELTA = 0.5           # OAT: 각 아키타입 비중 ±50%(상대) 후 재정규화
PRICE_LEVEL_OAT = 0.3          # OAT: 담보가격 수준 ±30%
PRICE_SKEW_STRENGTH = 0.6      # OAT: 담보가격 mix 저가↔고가 편중 강도


@dataclass
class HeadlineMetrics:
    """가정 1세트에서 나온 헤드라인 지표 묶음."""
    tightened_share: float          # 강화 방향 가중 비중
    review_share: float             # 사람검토 필요 가중 비중(escalation∪NEEDS_REVIEW)
    mean_delta_pp: float            # 수치비교 가능분 가중평균 LTV Δ (pp, 음수)
    exposure_pct_reduction: float   # 판정가능 여력 감소율(양수 = 축소)
    per_unit_delta_eok: float       # 1인당 평균 여력 Δ (억, 음수)
    undetermined_share: float       # 금액 산정불가 가중 비중


@dataclass(frozen=True)
class _Cell:
    """(아키타입×지역) 응답 셀 — 엔진 판정의 불변 primitive."""
    arch: str
    region: str
    b_ltv: Optional[float]
    a_ltv: Optional[float]
    direction: str
    ltv_delta: Optional[float]
    is_review: bool
    determinable: bool


def build_response_table(
    before_date: date = BEFORE_DATE,
    after_date: date = AFTER_DATE,
) -> list[_Cell]:
    """아키타입×지역 응답표를 엔진으로 1회 산출(이후 섭동은 가중 산술만).

    LTV before/after·방향·검토여부는 weight·price와 무관하므로 여기서 고정된다.
    """
    cells: list[_Cell] = []
    for a in DEFAULT_ARCHETYPES:
        for region in REGION_MIX:
            seg = CustomerSegment(
                label=a.label,
                attrs={**a.attrs, "region_code": region},
                weight=1.0,
            )
            imp = analyze_segment(seg, before_date, after_date)
            b = imp.before.max_ltv if imp.before.status == EvaluationStatus.DECIDED else None
            a_ltv = imp.after.max_ltv if imp.after.status == EvaluationStatus.DECIDED else None
            cells.append(_Cell(
                arch=a.label,
                region=region,
                b_ltv=b,
                a_ltv=a_ltv,
                direction=imp.direction.value,
                ltv_delta=imp.ltv_delta,
                is_review=imp.escalation_required or imp.direction == ImpactDirection.NEEDS_REVIEW,
                determinable=(b is not None and a_ltv is not None),
            ))
    return cells


def compute_headline(
    table: list[_Cell],
    archetype_share: dict[str, float] = ARCHETYPE_SHARE,
    region_mix: dict[str, float] = REGION_MIX,
    bands: list[PriceBand] = PRICE_BANDS,
) -> HeadlineMetrics:
    """주어진 가정(비중·지역·밴드)에서 헤드라인 지표를 순수 산술로 산출.

    담보가격이 세그먼트와 독립(모든 세그먼트 동일 밴드분포)이므로 여력은 가중평균 담보가격 mp로 환산.
    이 함수의 base 결과는 analyze_impact/compute_exposure와 일치한다(테스트로 교차확인).
    """
    mp = mean_property_price(bands)
    tw = tight = review = 0.0
    dnum = dden = 0.0
    det_w = und_w = 0.0
    cap_b = cap_a = 0.0
    for c in table:
        w = archetype_share.get(c.arch, 0.0) * region_mix.get(c.region, 0.0)
        if w == 0:
            continue
        tw += w
        if c.direction == ImpactDirection.TIGHTENED.value:
            tight += w
        if c.is_review:
            review += w
        if c.ltv_delta is not None:
            dnum += w * c.ltv_delta
            dden += w
        if c.determinable:
            det_w += w
            cap_b += w * mp * c.b_ltv       # type: ignore[operator]
            cap_a += w * mp * c.a_ltv       # type: ignore[operator]
        else:
            und_w += w
    return HeadlineMetrics(
        tightened_share=tight / tw if tw else 0.0,
        review_share=review / tw if tw else 0.0,
        mean_delta_pp=(dnum / dden * 100) if dden else 0.0,
        exposure_pct_reduction=(-(cap_a - cap_b) / cap_b) if cap_b else 0.0,
        per_unit_delta_eok=((cap_a - cap_b) / det_w) if det_w else 0.0,
        undetermined_share=und_w / tw if tw else 0.0,
    )


# --------------------------------------------------------------------------- #
# 섭동 유틸
# --------------------------------------------------------------------------- #

def _renorm(d: dict[str, float]) -> dict[str, float]:
    s = sum(d.values())
    return {k: v / s for k, v in d.items()} if s else dict(d)


def _scale_one(base: dict[str, float], key: str, factor: float) -> dict[str, float]:
    """한 항목만 factor배 후 전체 재정규화(합=1 유지, 나머지는 비례 축소/확대)."""
    d = dict(base)
    d[key] = d[key] * factor
    return _renorm(d)


def _dirichlet(rng: random.Random, base: dict[str, float], concentration: float) -> dict[str, float]:
    """base를 평균으로 하는 Dirichlet 표본(gammavariate로 구성, numpy 불필요)."""
    gammas = {k: rng.gammavariate(max(concentration * v, 1e-6), 1.0) for k, v in base.items()}
    s = sum(gammas.values())
    return {k: g / s for k, g in gammas.items()} if s else _renorm(base)


def _skew_bands(direction: int, strength: float = PRICE_SKEW_STRENGTH) -> list[PriceBand]:
    """담보가격 밴드 share를 저가(-1)↔고가(+1)로 기울인다(대표가격은 불변)."""
    n = len(PRICE_BANDS)
    tilt = []
    for i, b in enumerate(PRICE_BANDS):
        r = (i / (n - 1)) * 2 - 1 if n > 1 else 0.0   # 저가 -1 … 고가 +1
        tilt.append(b.share * math.exp(direction * strength * r))
    s = sum(tilt)
    return [PriceBand(b.label, b.representative_price, t / s) for b, t in zip(PRICE_BANDS, tilt)]


# --------------------------------------------------------------------------- #
# 1) OAT 토네이도
# --------------------------------------------------------------------------- #

@dataclass
class TornadoBar:
    assumption: str
    low: HeadlineMetrics
    high: HeadlineMetrics

    def swing(self, metric: str) -> float:
        return abs(getattr(self.high, metric) - getattr(self.low, metric))


def oat_tornado(
    table: Optional[list[_Cell]] = None,
    arch_delta: float = ARCH_OAT_DELTA,
    price_delta: float = PRICE_LEVEL_OAT,
) -> tuple[HeadlineMetrics, list[TornadoBar]]:
    """가정을 한 번에 하나씩(low/high) 흔들어 헤드라인 스윙을 만든다."""
    table = table if table is not None else build_response_table()
    base = compute_headline(table)
    bars: list[TornadoBar] = []

    for label in ARCHETYPE_SHARE:
        lo = compute_headline(table, archetype_share=_scale_one(ARCHETYPE_SHARE, label, 1 - arch_delta))
        hi = compute_headline(table, archetype_share=_scale_one(ARCHETYPE_SHARE, label, 1 + arch_delta))
        bars.append(TornadoBar(f"비중:{label}", lo, hi))

    uniform = {k: 1.0 / len(REGION_MIX) for k in REGION_MIX}
    bars.append(TornadoBar("지역 mix(균등화)", compute_headline(table, region_mix=uniform), base))

    lo_bands = [PriceBand(b.label, b.representative_price * (1 - price_delta), b.share) for b in PRICE_BANDS]
    hi_bands = [PriceBand(b.label, b.representative_price * (1 + price_delta), b.share) for b in PRICE_BANDS]
    bars.append(TornadoBar(f"담보가격 수준 ±{int(price_delta*100)}%",
                           compute_headline(table, bands=lo_bands),
                           compute_headline(table, bands=hi_bands)))

    bars.append(TornadoBar("담보가격 mix(저가↔고가)",
                           compute_headline(table, bands=_skew_bands(-1)),
                           compute_headline(table, bands=_skew_bands(+1))))
    return base, bars


# --------------------------------------------------------------------------- #
# 2) 몬테카를로 밴드 + 견고성
# --------------------------------------------------------------------------- #

@dataclass
class SensitivityBands:
    n: int
    base: HeadlineMetrics
    bands: dict[str, tuple[float, float, float]] = field(default_factory=dict)   # metric → (P5,P50,P95)
    robustness: dict[str, float] = field(default_factory=dict)                   # 결론 → 성립 표본 비율


def _pct(sorted_vals: list[float], p: float) -> float:
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    k = (len(sorted_vals) - 1) * p / 100.0
    f, c = math.floor(k), math.ceil(k)
    if f == c:
        return sorted_vals[int(k)]
    return sorted_vals[f] * (c - k) + sorted_vals[c] * (k - f)


_METRIC_FIELDS = [
    "tightened_share", "review_share", "mean_delta_pp",
    "exposure_pct_reduction", "per_unit_delta_eok", "undetermined_share",
]


def monte_carlo(
    table: Optional[list[_Cell]] = None,
    n: int = 2000,
    seed: int = 42,
    concentration: float = DEFAULT_CONCENTRATION,
    price_level_jitter: float = PRICE_LEVEL_JITTER,
) -> list[HeadlineMetrics]:
    """가정(아키타입 비중·지역 mix·밴드 share·가격 수준)을 그럴듯한 범위에서 표본추출."""
    table = table if table is not None else build_response_table()
    rng = random.Random(seed)
    band_base = {b.label: b.share for b in PRICE_BANDS}
    price_by_label = {b.label: b.representative_price for b in PRICE_BANDS}
    out: list[HeadlineMetrics] = []
    for _ in range(n):
        ashare = _dirichlet(rng, ARCHETYPE_SHARE, concentration)
        rmix = _dirichlet(rng, REGION_MIX, concentration)
        bshares = _dirichlet(rng, band_base, concentration)
        level = math.exp(rng.gauss(0.0, price_level_jitter))
        bands = [PriceBand(lbl, price_by_label[lbl] * level, bshares[lbl]) for lbl in band_base]
        out.append(compute_headline(table, ashare, rmix, bands))
    return out


def sensitivity_bands(
    table: Optional[list[_Cell]] = None,
    n: int = 2000,
    seed: int = 42,
    concentration: float = DEFAULT_CONCENTRATION,
    price_level_jitter: float = PRICE_LEVEL_JITTER,
) -> SensitivityBands:
    """몬테카를로 표본에서 지표별 P5/P50/P95 밴드 + 헤드라인 결론의 견고성 비율."""
    table = table if table is not None else build_response_table()
    base = compute_headline(table)
    samples = monte_carlo(table, n=n, seed=seed,
                          concentration=concentration, price_level_jitter=price_level_jitter)
    bands: dict[str, tuple[float, float, float]] = {}
    for f in _METRIC_FIELDS:
        vals = sorted(getattr(s, f) for s in samples)
        bands[f] = (_pct(vals, 5), _pct(vals, 50), _pct(vals, 95))
    robustness = {
        "여력 축소(감소율>0)": sum(1 for s in samples if s.exposure_pct_reduction > 0) / n,
        "1인당 여력 감소(Δ<0)": sum(1 for s in samples if s.per_unit_delta_eok < 0) / n,
        "강화 과반(강화>50%)": sum(1 for s in samples if s.tightened_share > 0.5) / n,
    }
    return SensitivityBands(n=n, base=base, bands=bands, robustness=robustness)


# --------------------------------------------------------------------------- #
# 리포트 포매터
# --------------------------------------------------------------------------- #

_METRIC_META = {
    "tightened_share": ("강화 비중", "pct"),
    "review_share": ("사람검토 비중", "pct"),
    "mean_delta_pp": ("가중평균 Δ", "pp"),
    "exposure_pct_reduction": ("여력 감소율", "pct"),
    "per_unit_delta_eok": ("1인당 Δ여력", "eok"),
    "undetermined_share": ("산정불가 비중", "pct"),
}


def _fmt(value: float, unit: str) -> str:
    if unit == "pct":
        return f"{value:.1%}"
    if unit == "pp":
        return f"{value:+.1f}pp"
    if unit == "eok":
        return f"{value:+.2f}억"
    return f"{value:.3f}"


def format_tornado(base: HeadlineMetrics, bars: list[TornadoBar], metric: str = "exposure_pct_reduction") -> str:
    name, unit = _METRIC_META[metric]
    ranked = sorted(bars, key=lambda b: b.swing(metric), reverse=True)
    lines = [f"토네이도 — 출력지표: {name} (base {_fmt(getattr(base, metric), unit)})",
             "가정을 한 번에 하나씩 흔든 스윙(큰 것이 driver):"]
    width = max((len(b.assumption) for b in ranked), default=10)
    for b in ranked:
        lo, hi = getattr(b.low, metric), getattr(b.high, metric)
        lines.append(
            f"  {b.assumption:<{width}}  "
            f"[{_fmt(min(lo, hi), unit):>8} … {_fmt(max(lo, hi), unit):>8}]  "
            f"스윙 {_fmt(b.swing(metric), unit)}"
        )
    return "\n".join(lines)


def format_bands(sb: SensitivityBands) -> str:
    lines = [f"몬테카를로 민감도 밴드 (n={sb.n}, 가정 섭동만·규칙 고정)"]
    lines.append("정직성: 문서화된 가정에 대한 민감도이지 실세계 불확실성 정량화가 아님(실측 없음).")
    lines.append("")
    hdr = f"{'지표':<14} {'base':>9} {'P5':>9} {'P50':>9} {'P95':>9}"
    lines.append(hdr)
    lines.append("-" * len(hdr))
    for f in _METRIC_FIELDS:
        name, unit = _METRIC_META[f]
        p5, p50, p95 = sb.bands[f]
        lines.append(
            f"{name:<14} {_fmt(getattr(sb.base, f), unit):>9} "
            f"{_fmt(p5, unit):>9} {_fmt(p50, unit):>9} {_fmt(p95, unit):>9}"
        )
    lines.append("-" * len(hdr))
    lines.append("결론 견고성(가정 범위에서 성립한 표본 비율):")
    for k, v in sb.robustness.items():
        mark = "✓" if v >= 0.999 else ("~" if v >= 0.9 else "✗")
        lines.append(f"  {mark} {k}: {v:.1%}")
    return "\n".join(lines)
