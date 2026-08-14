"""RegImpact AI — 평가셋(Gold Set) 로더·회귀 (브리프 §11~12).

100~120문항 골드 평가셋을 DEV / LOCKED TEST / CHALLENGE 로 분리(freeze)해 관리한다.
- DEV: 개발 중 상시 회귀(튜닝 가능).
- LOCKED / CHALLENGE: **개봉 규율** — 코어 완성 후 1회만 실행(Phase 3). 기본 sealed.
정답은 rule_engine 이 아니라 **독립 명세 오라클**(tc_generator.oracle)에서 유도 → 순환 아님.
"""
from .gold_set import (
    GOLD_DIR,
    SEALED_SPLITS,
    SPLITS,
    GoldEvalReport,
    GoldItem,
    evaluate_items,
    load_manifest,
    load_split,
    run_gold_regression,
)

__all__ = [
    "GoldItem",
    "GoldEvalReport",
    "load_split",
    "load_manifest",
    "evaluate_items",
    "run_gold_regression",
    "SPLITS",
    "SEALED_SPLITS",
    "GOLD_DIR",
]
