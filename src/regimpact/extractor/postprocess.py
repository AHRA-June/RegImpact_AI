"""추출 결과 후처리 — LLM 자연어 출력을 룰엔진 어휘로 결정적으로 변환한다.

왜 LLM에게 맡기지 않는가: 룰엔진은 지역 **코드**(GURI …)로 동작하고 공문은 **한글
지역명**(구리시 …)을 쓴다. 이 매핑을 프롬프트로 넘기면 코드 어휘 자체가 정답 힌트가
되어 평가가 오염된다. 그래서 경계 변환은 별칭 테이블 기반 결정적 코드로 처리하고,
매핑 실패는 조용히 버리지 않고 **escalation 목록**으로 표면화한다(브리프: 실패의 명시적 통제).
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Optional

from ..regions import normalize_region_name
from .schema import RegChangeExtraction


@dataclass
class RegionNormalizationReport:
    normalized: RegChangeExtraction
    mapping: dict[str, str]        # 원문 표기 -> 코드
    unmapped: list[str]            # 코드를 찾지 못한 표기 (사람 확인 필요)

    @property
    def measured(self) -> bool:
        """정규화할 지역이 하나라도 있었는가."""
        return bool(self.mapping or self.unmapped)

    @property
    def coverage(self) -> Optional[float]:
        """매핑 성공률. **지역이 없으면 None** — 0건 중 0건은 100% 가 아니다.

        2026-08-21 발견: 2025 10·15 대책은 규제지역 지정이 없는 대책(DSR·스트레스금리·
        전세대출)이라 target_regions 가 비었는데, coverage 가 1.0 으로 나왔다. "완벽히
        매핑됨"과 "매핑할 것이 없었음"은 다른 사실이고, 전자로 보고하면 나중에 아무도
        구분하지 못한다.
        """
        total = len(self.mapping) + len(self.unmapped)
        return len(self.mapping) / total if total else None


def normalize_regions(extraction: RegChangeExtraction) -> RegionNormalizationReport:
    """target_regions의 한글 표기를 룰엔진 지역코드로 변환한다.

    변환된 코드만 정규화 결과에 담고, 실패한 표기는 원문 그대로 유지해 이후 단계에서
    "미확인 지역"으로 드러나게 한다(누락 은폐 방지).
    """
    mapping: dict[str, str] = {}
    unmapped: list[str] = []
    out: list[str] = []
    for name in extraction.target_regions:
        code = normalize_region_name(name)
        if code:
            mapping[name] = code
            if code not in out:
                out.append(code)
        else:
            unmapped.append(name)
            if name not in out:
                out.append(name)
    return RegionNormalizationReport(
        normalized=replace(extraction, target_regions=out),
        mapping=mapping,
        unmapped=unmapped,
    )
