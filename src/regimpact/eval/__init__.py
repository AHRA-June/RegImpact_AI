"""골드 평가셋 — 브리프 §11(문항 설계) · §12(누수 방지).

    load_split(Split.DEV)          # 튜닝에 쓰는 유일한 셋
    split_stats(Split.LOCKED)      # 정답을 보지 않고 구성만 확인 (봉인 유지)
    validate_items(items, sources) # 인용이 원문에 실제로 있는지 등 무결성 검사
"""
from .confirmation import ConfirmationStatus, check_confirmation, compute_digest
from .consistency import ConsistencyReport, check_gold_against_spec
from .goldset import (
    ACCESS_LOG,
    GOLD_DIR,
    SEALED,
    SealedSplitError,
    category_counts,
    coverage_report,
    load_split,
    save_split,
    split_path,
    split_stats,
)
from .qa import (
    QA_JSON_SCHEMA,
    QA_SYSTEM_PROMPT,
    QAReport,
    QAResponse,
    answer_questions,
    build_qa_prompt,
    fact_matches,
    format_qa_report,
    score_qa,
    validate_qa_response,
    QA_JSON_INSTRUCTION,
)
from .schema import (
    HIGH_RISK_CATEGORIES,
    Category,
    Citation,
    GoldItem,
    Split,
    ValidationReport,
)
from .validate import KNOWN_RULE_IDS, validate_items

__all__ = [
    "load_split", "split_stats", "save_split", "split_path",
    "category_counts", "coverage_report",
    "SealedSplitError", "SEALED", "GOLD_DIR", "ACCESS_LOG",
    "GoldItem", "Citation", "Category", "Split", "ValidationReport",
    "HIGH_RISK_CATEGORIES", "validate_items", "KNOWN_RULE_IDS",
    "check_gold_against_spec", "ConsistencyReport",
    "check_confirmation", "compute_digest", "ConfirmationStatus",
    "answer_questions", "score_qa", "format_qa_report", "build_qa_prompt",
    "QAReport", "QAResponse", "QA_SYSTEM_PROMPT", "QA_JSON_SCHEMA",
    "validate_qa_response", "QA_JSON_INSTRUCTION", "fact_matches",
]
