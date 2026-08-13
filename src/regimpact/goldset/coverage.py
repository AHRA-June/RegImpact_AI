"""골드셋 커버리지·진척 추적 — split × 카테고리 매트릭스, 확정 상태, 목표(115) 진척.

metrics_spec/브리프 §11: 성공 기준은 건수가 아니라 **실패모드 카테고리 커버리지**.
이 리포트가 "어떤 카테고리가 얇은지 / 무엇이 아직 AI_DRAFT인지"를 드러낸다.
"""
from __future__ import annotations

from collections import Counter

from .schema import CHALLENGE_WEIGHTED, GoldCategory, GoldItem, Split, Status

# 확정 split 목표 (docs/02_DECISION_LOG 2026-08-10, 총 ~115)
TARGET = {Split.DEV: 40, Split.LOCKED: 40, Split.CHALLENGE: 35}
TARGET_TOTAL = sum(TARGET.values())


def coverage(items: list[GoldItem]) -> dict:
    """split·카테고리·상태·escalation·scenario 분포를 집계한다."""
    by_split = Counter(it.split.value for it in items)
    by_category = Counter(it.category.value for it in items)
    by_status = Counter(it.status.value for it in items)
    split_category: dict[str, Counter] = {}
    for it in items:
        split_category.setdefault(it.split.value, Counter())[it.category.value] += 1
    return {
        "total": len(items),
        "target_total": TARGET_TOTAL,
        "by_split": dict(by_split),
        "by_category": dict(by_category),
        "by_status": dict(by_status),
        "split_category": {k: dict(v) for k, v in split_category.items()},
        "scenario_items": sum(1 for it in items if it.is_scenario),
        "escalation_items": sum(1 for it in items if it.expects_escalation),
        "confirmed": sum(1 for it in items if it.status == Status.HUMAN_CONFIRMED),
    }


def format_coverage(items: list[GoldItem]) -> str:
    cov = coverage(items)
    L: list[str] = []
    L.append("=" * 60)
    L.append("RegImpact — 골드셋 커버리지 / 진척")
    L.append("=" * 60)
    L.append(f"총 문항          : {cov['total']} / 목표 {cov['target_total']} "
             f"({cov['total'] / cov['target_total']:.0%})")
    L.append(f"확정(사람)       : {cov['confirmed']} / {cov['total']}  "
             f"(나머지 AI_DRAFT — LOCKED §4 사람확정 대기)")
    L.append(f"scenario(결정채점): {cov['scenario_items']}   escalation 기대: {cov['escalation_items']}")
    L.append("")
    L.append("Split 진척:")
    for sp in Split:
        have = cov["by_split"].get(sp.value, 0)
        L.append(f"  {sp.value:<10} {have:>3} / {TARGET[sp]:<3} ({have / TARGET[sp]:.0%})")
    L.append("")
    L.append("카테고리 분포 (★=CHALLENGE 가중):")
    for cat in GoldCategory:
        n = cov["by_category"].get(cat.value, 0)
        star = " ★" if cat in CHALLENGE_WEIGHTED else ""
        L.append(f"  {cat.value:<15} {n:>3}{star}")
    L.append("=" * 60)
    return "\n".join(L)
