"""RegChange Extractor — 공문에서 Before/After 변경을 구조화 추출(E) + 검증(A)."""
from .extractor import anthropic_completion, extract_regchange
from .backends import ollama_completion, openai_compatible_completion
from .evaluate import (
    GoldReport,
    GroundingReport,
    check_citation_grounding,
    score_against_gold,
)
from .schema import Citation, RegChangeExtraction, RegChangeItem
from .sources import load_sources

__all__ = [
    "extract_regchange",
    "anthropic_completion",
    "ollama_completion",
    "openai_compatible_completion",
    "check_citation_grounding",
    "score_against_gold",
    "GroundingReport",
    "GoldReport",
    "RegChangeExtraction",
    "RegChangeItem",
    "Citation",
    "load_sources",
]
