"""추출(RegChange) → Impact Matrix 연결 (E2E: 공문 → 추출 → 임팩트).

이 다리(bridge)는 LLM이 추출한 정책 메타데이터를 deterministic 임팩트 분석의 입력으로 흘려보낸다:
  - policy_id           → 매트릭스 식별자
  - effective_from      → before(시행 전)/after(시행 후) 시점 유도
  - target_regions(한글명) → 정규화(regions.normalize_regions) → 영향 지역 code
  - 각 지역 × 대표 고객 유형(archetype) → 세그먼트 → 룰엔진 before/after 차등

LOCKED §4: 임팩트 판정은 여전히 deterministic 룰엔진에서만 나온다. LLM은 '어느 정책·어느 지역·
언제부터'라는 **좌표**만 제공하고, 그 좌표에서의 LTV 판정은 사람 확정 룰이 한다.
추출 target_regions는 한글명 그대로 보존하고(원문 충실), 코드 정규화는 이 다리에서만 수행한다.

의존성 주의: 이 모듈은 extractor를 런타임 import하지 않는다(레이어 독립). extraction 객체는
`.policy_id / .effective_from / .target_regions` 속성만 있으면 되는 duck typing.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Optional

from ..regions import normalize_regions
from .matrix import ImpactMatrix, analyze_impact
from .segments import DEFAULT_ARCHETYPES, SegmentArchetype, segments_for_region


def _parse_iso(s: str) -> date:
    y, m, d = s.split("-")
    return date(int(y), int(m), int(d))


@dataclass
class PolicyImpact:
    """추출 → Impact Matrix 연결 결과 + provenance(어디서 왔는지)."""
    matrix: ImpactMatrix
    regions: list[str]                       # 정규화된 대상지역 code
    unmapped_regions: list[str]              # 코드 매핑 실패(표면화, 조용한 누락 금지)
    effective_from: date
    before_date: date
    after_date: date


def impact_from_extraction(
    extraction: Any,
    archetypes: Optional[list[SegmentArchetype]] = None,
    before_margin: int = 1,
    after_margin: int = 1,
) -> PolicyImpact:
    """RegChange 추출을 Impact Matrix 로 변환한다 (E2E 진입점).

    - before = effective_from - before_margin일 (시행 전, 규제 효력 발생 전)
    - after  = effective_from + after_margin일  (시행 후)
    - 세그먼트 = 정규화된 각 지역 × archetype (여러 지역이면 라벨에 지역 표기)
    """
    archetypes = archetypes if archetypes is not None else DEFAULT_ARCHETYPES

    raw_regions = list(getattr(extraction, "target_regions", []) or [])
    codes, unmapped = normalize_regions(raw_regions)

    eff_raw = getattr(extraction, "effective_from", None)
    if not eff_raw:
        raise ValueError("effective_from이 없어 before/after 시점을 유도할 수 없습니다.")
    eff = _parse_iso(eff_raw)
    before = eff - timedelta(days=before_margin)
    after = eff + timedelta(days=after_margin)

    multi = len(codes) > 1
    segments = [
        s
        for code in codes
        for s in segments_for_region(code, archetypes, label_region=multi)
    ]

    matrix = analyze_impact(
        segments,
        policy_id=getattr(extraction, "policy_id", "(unknown)"),
        before_date=before,
        after_date=after,
    )
    matrix.regions = codes
    matrix.unmapped_regions = unmapped

    return PolicyImpact(
        matrix=matrix,
        regions=codes,
        unmapped_regions=unmapped,
        effective_from=eff,
        before_date=before,
        after_date=after,
    )
