"""데모: 골드 평가셋(DEV + CHALLENGE)을 로드해 커버리지 + 결정적 채점을 보인다.

실행:
    python examples/demo_goldset.py

산출:
    - 골드셋 커버리지(split×카테고리, 목표 115 진척, 확정 상태)
    - scenario 아이템 결정적 채점(룰엔진) — 카테고리별 정확도 + escalation recall/precision
    - 골드셋 근거 무결성(source_quote grounding)

메시지: 골드는 사람이 원문에서 확정한 '정답'이고, 채점은 결정적(LLM이 LLM 채점 금지, LOCKED §4).
현재 전 항목 AI_DRAFT(사람확정 대기) — 최종 성능 보고 전 사용자 도메인 검수 필요.
"""
from regimpact.extractor import load_sources
from regimpact.goldset import (
    Split,
    check_goldset_grounding,
    format_coverage,
    load_goldset,
    score_scenario_items,
)


def main() -> None:
    # 착수 단계이므로 DEV + CHALLENGE를 함께 본다(진척 확인용).
    items = load_goldset(splits=[Split.DEV, Split.CHALLENGE])
    print(format_coverage(items))
    print()

    score = score_scenario_items(items)
    print("=" * 60)
    print(f"scenario 결정적 채점 (룰엔진): {score.passed}/{score.total} = {score.accuracy:.0%}")
    print("=" * 60)
    for cat, (p, n) in score.by_category().items():
        print(f"  {cat:<15} {p:>2}/{n:<2}")
    esc = score.escalation_metrics()
    print(f"\nEscalation Recall/Precision: {esc['recall']:.0%} / {esc['precision']:.0%} "
          f"(tp={esc['tp']} fp={esc['fp']} fn={esc['fn']})")
    if score.failures:
        print(f"\n실패 {len(score.failures)}:")
        for r in score.failures:
            print(f"  ✗ {r.item.item_id} [{r.item.category.value}] {r.detail}")

    print("\n" + "=" * 60)
    g = check_goldset_grounding(items, load_sources())
    print(f"골드셋 근거 무결성(grounding): {g.grounded}/{g.total} = {g.rate:.0%}")
    for u in g.ungrounded:
        print(f"  ⚠ {u.item_id}: 원문 미확인 quote=\"{u.source_quote[:50]}\"")


if __name__ == "__main__":
    main()
