"""RegChange Extractor — 공문에서 Before/After 변경을 구조화 추출(E) + 검증(A)."""
from .backends import (
    LLMBackendError,
    PROVIDERS,
    anthropic_completion,
    available_providers,
    cli_completion,
    coerce_json,
    gemini_completion,
    manual_completion,
    replay_completion,
    resolve_completion,
    validate_regchange,
)
from .extractor import extract_regchange
from .merge import MergeReport, extract_per_document, merge_cross_document
from .postprocess import RegionNormalizationReport, normalize_regions
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
    "extract_per_document",
    "MergeReport",
    "merge_cross_document",
    # 백엔드 (무과금 경로 우선)
    "resolve_completion",
    "available_providers",
    "cli_completion",
    "gemini_completion",
    "manual_completion",
    "replay_completion",
    "anthropic_completion",
    "coerce_json",
    "validate_regchange",
    "LLMBackendError",
    "PROVIDERS",
    # 평가
    "normalize_regions",
    "RegionNormalizationReport",
    "check_citation_grounding",
    "score_against_gold",
    "GroundingReport",
    "GoldReport",
    # 스키마·소스
    "RegChangeExtraction",
    "RegChangeItem",
    "Citation",
    "load_sources",
]
