"""가중 합성 모집단 (weighted synthetic portfolio) — 04_PLAN Phase 2.

목적:
  1) **비중 실측화**: 임팩트 세그먼트의 weight(모집단 비중)를 illustrative 균일값이 아니라
     **문서화된 모집단 분포 모델**로 부여 → 가중 포트폴리오 통계(강화/유지/검토 비율, 가중 평균 Δ,
     사람검토 필요 비율)가 의미를 갖게 한다.
  2) **수천 건 확장**: 그 분포에서 **몬테카를로 표본**을 뽑아 수천 명 규모 합성 포트폴리오를 만든다
     (룰-회귀 분모 확대에도 활용).

⚠️ **정직성 고지:** 아래 비중은 실제 은행 포트폴리오 데이터가 아니라 **문서화된 시나리오 가정**이다
   (그럴듯한 범위에서 설정). 실측 데이터가 확보되면 이 표만 교체하면 된다(분석 코드는 불변).

두 생성 경로 — 같은 분포, 같은 가중 통계:
  - enumerate_weighted_profiles(): 아키타입×지역 정확 가중(24 프로파일, weight=결합확률).
  - sample_portfolio(n): 그 분포에서 n명 몬테카를로 추출(결정적 seed, weight=1).
"""
from __future__ import annotations

import random
from datetime import date
from typing import Optional

from .matrix import AFTER_DATE, CustomerSegment
from .segments import DEFAULT_ARCHETYPES, SegmentArchetype

# --- 비중 모델 (문서화된 가정, 실측 아님) ---
# 아키타입 모집단 비중: DEFAULT_ARCHETYPES.weight 를 '모집단 점유율'로 채택(합=1.00).
ARCHETYPE_SHARE: dict[str, float] = {a.label: a.weight for a in DEFAULT_ARCHETYPES}

# 6·30 신규 규제지역 3곳의 상대 비중(가정).
REGION_MIX: dict[str, float] = {
    "GURI": 0.35,
    "YONGIN_GIHEUNG": 0.35,
    "HWASEONG_DONGTAN": 0.30,
}

_ARCH_BY_LABEL: dict[str, SegmentArchetype] = {a.label: a for a in DEFAULT_ARCHETYPES}


def weight_model_note() -> str:
    return (
        "비중 모델(문서화된 가정, 실측 아님): 아키타입 모집단 점유율 = "
        + ", ".join(f"{k} {v:.0%}" for k, v in ARCHETYPE_SHARE.items())
        + " | 지역 mix = " + ", ".join(f"{k} {v:.0%}" for k, v in REGION_MIX.items())
    )


def enumerate_weighted_profiles() -> list[CustomerSegment]:
    """아키타입 × 지역의 정확 가중 프로파일(weight=결합확률, 합≈1). 결정적."""
    out: list[CustomerSegment] = []
    for a in DEFAULT_ARCHETYPES:
        for region, rw in REGION_MIX.items():
            out.append(CustomerSegment(
                label=f"{a.label}·{region}",
                attrs={**a.attrs, "region_code": region},
                weight=a.weight * rw,
                note=a.note,
            ))
    return out


def _pick(rng: random.Random, weights: dict[str, float]) -> str:
    items = list(weights.items())
    r = rng.random() * sum(w for _, w in items)
    acc = 0.0
    for name, w in items:
        acc += w
        if r <= acc:
            return name
    return items[-1][0]


def sample_portfolio(
    n: int = 5000,
    seed: int = 42,
    archetype_share: Optional[dict[str, float]] = None,
    region_mix: Optional[dict[str, float]] = None,
) -> list[CustomerSegment]:
    """비중 모델에서 n명을 몬테카를로 추출한 합성 포트폴리오(각 weight=1, 결정적 seed).

    각 차주 = (아키타입 추출) × (지역 추출). 표본이 크면 분포가 ARCHETYPE_SHARE/REGION_MIX 에 수렴.
    """
    ashare = archetype_share or ARCHETYPE_SHARE
    rmix = region_mix or REGION_MIX
    rng = random.Random(seed)
    out: list[CustomerSegment] = []
    for i in range(n):
        a = _ARCH_BY_LABEL[_pick(rng, ashare)]
        region = _pick(rng, rmix)
        out.append(CustomerSegment(
            label=f"{a.label}#{i}",
            attrs={**a.attrs, "region_code": region},
            weight=1.0,
            note=a.note,
        ))
    return out


def applications(segments: list[CustomerSegment], as_of: date = AFTER_DATE):
    """세그먼트를 특정 시점의 MortgageApplication 목록으로(룰-회귀/집계용)."""
    return [s.application(as_of) for s in segments]
