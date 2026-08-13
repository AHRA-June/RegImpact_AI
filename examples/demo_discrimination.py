"""데모: 판별력(negative control) — 하니스가 '틀린 것'을 실제로 <100%로 잡는가?

배경: 정상 데이터에서 지표가 계속 100%면 "하니스에 이빨이 없다"는 의심이 정당하다.
이 데모는 **의도적으로 오류를 주입**하고, 각 Assurance 지표가 100%에서 떨어지는지 실측한다.
지표가 정상 데이터에 100%, 오염 데이터에 <100%면 → **동적 범위(discrimination)가 있다**는 증거다.

실행:
    python examples/demo_discrimination.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from regimpact import rule_engine  # noqa: E402
from regimpact.extractor import (  # noqa: E402
    check_citation_grounding,
    load_sources,
    score_against_gold,
)
from regimpact.extractor.schema import Citation, RegChangeExtraction, RegChangeItem  # noqa: E402
from regimpact.goldset import (  # noqa: E402
    Split,
    check_goldset_grounding,
    load_goldset,
    score_scenario_items,
)
from regimpact.impact import anchor_extraction, load_gold, run_e2e  # noqa: E402


def _bad_extraction() -> RegChangeExtraction:
    """현실적인 LLM 오류를 심은 '나쁜 추출'.

    - LTV 인용을 원문에 없는 문장으로(환각) → grounding 하락
    - 경과규정·예외(생애최초/서민) 항목 누락 → completeness/recall 하락
    - effective_from 틀림(7.15) → effective-date 오류
    - target_regions에서 화성동탄 누락 → regions 오류
    """
    return RegChangeExtraction(
        policy_id="FSC_20260630",
        effective_from="2026-07-15",                       # WRONG (정답 7-01)
        target_regions=["GURI", "YONGIN_GIHEUNG"],          # 화성동탄 누락
        changes=[
            RegChangeItem(
                category="LTV",
                summary="규제지역 LTV 강화 (비규제 70% → 규제 40%)",   # 값은 맞지만…
                before="70%", after="40%",
                citation=Citation("FAQ_20260630", "규제지역 LTV를 90%에서 20%로 인하한다"),  # 환각 인용
                confidence=0.9,
            ),
            RegChangeItem(
                category="REGION",
                summary="규제지역 추가 지정 (투기과열지구·조정대상지역)",
                before=None, after="규제지역",
                citation=Citation("FSC_PRESS_20260630",
                                  "동탄구, 기흥구, 구리시의 규제지역(투기과열지역, 조정대상지역) 지정에"),
                confidence=0.95,
            ),
            RegChangeItem(
                category="EXCEPTION",
                summary="다주택자 수도권 주택구입 LTV 0%",
                before=None, after="0%",
                citation=Citation("FAQ_20260630",
                                  "다주택자는 수도권 內 주택구입시 규제지역 여부와 무관하게 LTV 0% 적용"),
                confidence=0.9,
            ),
            # 누락(의도적): EFFECTIVE_DATE 항목, GRANDFATHERING 항목, 생애최초/서민 EXCEPTION 항목
        ],
    )


def _pct(x: float) -> str:
    return f"{x:.0%}"


def main() -> None:
    sources = load_sources()
    gold = load_gold()

    print("=" * 68)
    print("판별력 실측: 정상 데이터(100%) vs 오류 주입 데이터(<100%여야 함)")
    print("=" * 68)

    # --- 1) Extractor Assurance ---
    good = anchor_extraction()
    bad = _bad_extraction()
    gg, bg = check_citation_grounding(good, sources), check_citation_grounding(bad, sources)
    gs = score_against_gold(good, gold)
    bs = score_against_gold(bad, gold)

    rows = [
        ("Citation Correctness", gg.citation_correctness, bg.citation_correctness),
        ("Change Completeness", gs.change_completeness, bs.change_completeness),
        ("Exception Recall", gs.exception_recall, bs.exception_recall),
        ("Effective-date OK", float(gs.effective_date_correct), float(bs.effective_date_correct)),
        ("Regions OK", float(gs.regions_correct), float(bs.regions_correct)),
    ]
    print("\n[Extractor Assurance]  지표            정상 → 오류주입")
    for name, g, b in rows:
        flag = "  ✓ 하락 감지" if b < g else "  ✗ 미감지(문제!)"
        print(f"    {name:<22} {_pct(g):>4} → {_pct(b):>4}{flag}")

    # --- 2) E2E 종합 판정 ---
    good_e2e = run_e2e()
    bad_e2e = run_e2e(extraction=bad)
    print("\n[E2E 종합 판정]")
    print(f"    정상 추출   → e2e_ok = {good_e2e.e2e_ok}")
    print(f"    오류 추출   → e2e_ok = {bad_e2e.e2e_ok}   "
          f"{'✓ 관통 실패로 잡음' if not bad_e2e.e2e_ok else '✗ 잡지 못함(문제!)'}")

    # --- 3) 골드셋 scenario: 엔진 변조 시 정확도 하락 ---
    items = load_goldset(splits=[Split.DEV, Split.LOCKED, Split.CHALLENGE])
    good_acc = score_scenario_items(items).accuracy
    saved = rule_engine.LTV_REGULATED_STANDARD
    try:
        rule_engine.LTV_REGULATED_STANDARD = 0.50   # 40%→50% 버그 주입
        bad_acc = score_scenario_items(items).accuracy
    finally:
        rule_engine.LTV_REGULATED_STANDARD = saved

    print("\n[골드셋 scenario 채점] (엔진 상수 40%→50% 변조)")
    print(f"    정상 엔진   → {_pct(good_acc)}")
    print(f"    변조 엔진   → {_pct(bad_acc)}   "
          f"{'✓ 골드가 오류를 잡음' if bad_acc < good_acc else '✗ 못 잡음(문제!)'}")

    # --- 4) 골드셋 grounding: 인용 오염 시 하락 ---
    good_g = check_goldset_grounding(items, sources).rate
    corrupted = load_goldset(splits=[Split.DEV])
    hit = next(it for it in corrupted if it.source_quote)
    hit.source_quote = "이 문장은 원문에 존재하지 않는다"
    bad_g = check_goldset_grounding(corrupted, sources).rate
    print("\n[골드셋 근거 grounding] (인용 1건 오염)")
    print(f"    정상        → {_pct(good_g)}")
    print(f"    오염        → {_pct(bad_g)}   "
          f"{'✓ 환각 인용을 잡음' if bad_g < good_g else '✗ 못 잡음(문제!)'}")

    print("\n" + "=" * 68)
    print("결론: 모든 지표가 정상=100%, 오류주입=<100% → 하니스에 '이빨'이 있다.")
    print("(100%는 '오류 없음'을 뜻하지, '검증 능력 없음'을 뜻하지 않는다.)")
    print("=" * 68)


if __name__ == "__main__":
    main()
