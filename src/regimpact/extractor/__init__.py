"""RegChange Extractor — 공문에서 Before/After 변경을 구조화 추출(E) + 검증(A)."""
from .extractor import anthropic_completion, extract_regchange
from .evaluate import (
    GOLD_PATH,
    GoldReport,
    GroundingReport,
    check_citation_grounding,
    load_gold,
    score_against_gold,
)
from .schema import Citation, RegChangeExtraction, RegChangeItem
from .sources import SOURCE_REGISTRY, load_sources

__all__ = [
    "extract_regchange",
    "anthropic_completion",
    "check_citation_grounding",
    "score_against_gold",
    "load_gold",
    "GOLD_PATH",
    "GroundingReport",
    "GoldReport",
    "RegChangeExtraction",
    "RegChangeItem",
    "Citation",
    "load_sources",
    "SOURCE_REGISTRY",
]
