"""골드 평가셋 (브리프 §11~12) — DEV/LOCKED/CHALLENGE 분리, 결정적 채점.

핵심 진입점:
    load_goldset(splits?) -> [GoldItem]       (기본 DEV만; 누수 방지)
    score_scenario_items(items) -> ScenarioScore   (룰엔진 결정적 채점)
    check_goldset_grounding(items, sources) -> GroundingResult
    format_coverage(items) -> str             (split×카테고리 진척)

LOCKED §4 금지선: 채점은 결정적(LLM이 LLM 채점 금지). LOCKED §4 운영: 골드 정답은
사람이 원문 대조로 확정하기 전까지 AI_DRAFT(status로 통제).
"""
from .coverage import TARGET, TARGET_TOTAL, coverage, format_coverage
from .evaluate import (
    GroundingResult,
    ItemResult,
    ScenarioScore,
    build_application,
    check_goldset_grounding,
    score_scenario_items,
)
from .schema import (
    CHALLENGE_WEIGHTED,
    GoldCategory,
    GoldItem,
    Split,
    Status,
    load_goldset,
    load_split,
)

__all__ = [
    "GoldItem",
    "GoldCategory",
    "Split",
    "Status",
    "CHALLENGE_WEIGHTED",
    "load_goldset",
    "load_split",
    "score_scenario_items",
    "check_goldset_grounding",
    "build_application",
    "ScenarioScore",
    "ItemResult",
    "GroundingResult",
    "coverage",
    "format_coverage",
    "TARGET",
    "TARGET_TOTAL",
]
