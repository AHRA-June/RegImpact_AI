"""6·30 Walking Skeleton — E2E 관통 데모 (브리프 §18 "코어 완성의 정의").

    Source Snapshot → Policy Version Resolution → Before/After 추출
    → 지역코드 정규화 → Impact Matrix → Customer Impact → Rule Diff 제안
    → Test Cases → Deterministic Rule Regression → Assurance Evaluation
    → Human Review 표시 → 리포트

**기본은 비용 0원·LLM 호출 0회**다: 저장된 추출 실행 기록(`docs/eval/runs/`)을 재생한다.
추출부터 새로 돌리려면 `--provider cli`(구독 포함, 유료 키 불필요)를 준다.

    python examples/demo_impact_e2e.py                     # 저장본 재생 (기본)
    python examples/demo_impact_e2e.py --provider cli      # 추출부터 실제 LLM 실행
    python examples/demo_impact_e2e.py --write             # 매트릭스를 docs/eval/에 저장
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from regimpact.extractor import (  # noqa: E402
    check_citation_grounding,
    extract_regchange,
    load_sources,
    normalize_regions,
    resolve_completion,
    score_against_gold,
)
from regimpact.impact import (  # noqa: E402
    analyze_portfolio,
    build_impact_matrix,
    build_portfolio,
    composition,
    format_matrix_markdown,
    format_matrix_text,
)
from regimpact.impact.portfolio import DEFAULT_SEED, DEFAULT_SIZE  # noqa: E402
from regimpact.tc_generator import run_regression  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
DEFAULT_RUN = REPO / "docs" / "eval" / "runs" / "run_perdoc_sonnet5.json"
OUT_MD = REPO / "docs" / "eval" / "impact_matrix_6_30.md"


def _args():
    p = argparse.ArgumentParser(description="6·30 Impact Matrix E2E")
    p.add_argument("--provider", default="replay", help="replay(기본)|cli|gemini|manual|anthropic")
    p.add_argument("--run", default=str(DEFAULT_RUN), help="replay 시 재생할 run JSON")
    p.add_argument("--model", default=None)
    p.add_argument("--size", type=int, default=DEFAULT_SIZE, help="합성 포트폴리오 규모")
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p.add_argument("--write", action="store_true", help="매트릭스를 docs/eval/에 저장")
    return p.parse_args()


def main() -> None:
    a = _args()
    step = 0

    def head(title):
        nonlocal step
        step += 1
        print(f"\n{'=' * 72}\n[{step}] {title}\n{'=' * 72}")

    # 1 — Source Snapshot
    head("Source Snapshot — 공문 원문 로드")
    sources = load_sources()
    for doc_id, text in sources.items():
        print(f"  {doc_id}: {len(text):,}자")

    # 2 — Before/After 추출 (LLM) + Citation Assurance
    head(f"RegChange 추출 (provider={a.provider})")
    kwargs = {"run_path": a.run} if a.provider == "replay" else {}
    complete = resolve_completion(a.provider, model=a.model, **kwargs)
    extraction = extract_regchange(sources, complete=complete)
    print(f"  변경 {len(extraction.changes)}건 · 시행일 {extraction.effective_from}")

    grounding = check_citation_grounding(extraction, sources)
    gold_path = REPO / "docs" / "eval" / "regchange_gold_6_30.json"
    import json
    gold = json.loads(gold_path.read_text(encoding="utf-8"))

    # 3 — 지역코드 정규화 (경계 변환, 결정적)
    head("Policy Version Resolution — 지역명 → 룰엔진 지역코드")
    norm = normalize_regions(extraction)
    for name, code in norm.mapping.items():
        print(f"  {name} → {code}")
    for name in norm.unmapped:
        print(f"  ⚠ 코드 미확인: {name}")
    extraction = norm.normalized

    scored = score_against_gold(extraction, gold)

    # 4 — 합성 포트폴리오
    head(f"합성 포트폴리오 생성 (size={a.size:,}, seed={a.seed})")
    portfolio = build_portfolio(size=a.size, seed=a.seed)
    comp = composition(portfolio)
    print("  " + " · ".join(
        f"{k} {v:.0%}" if isinstance(v, float) else f"{k} {v:,}" for k, v in comp.items()
    ))

    # 5 — Customer Impact (룰엔진 before/after)
    head("Customer Impact — 시행 전(6.30) vs 시행일(7.1) 룰엔진 평가")
    impact = analyze_portfolio(portfolio, seed=a.seed)
    for seg, cnt in impact.segment_counts.items():
        if cnt:
            print(f"  {seg:<18} {cnt:>6,}건 ({cnt / len(impact.impacts):>5.1%})")
    print(f"  ── 총 한도 감소 {impact.total_limit_reduction / 1e8:,.0f}억원 "
          f"(건당 평균 {impact.avg_limit_reduction / 1e8:.2f}억원)")
    print("  LTV 전이:", impact.ltv_transitions)
    if impact.escalation_reasons:
        print("  자동판정 중단 사유:", impact.escalation_reasons)

    # 6 — Test Cases + Rule Regression
    head("Test Cases + Rule Regression — 독립 명세 오라클 차등 검증")
    regression = run_regression()
    print(f"  {regression.total}케이스 · Pass Rate {regression.pass_rate:.1%} "
          f"· 실패 {len(regression.failures)}건")
    for cat, (p, t, rate) in regression.pass_rate_by_category().items():
        print(f"    {cat:<16} {p}/{t} ({rate:.0%})")

    # 7 — Impact Matrix 조립
    head("Impact Matrix 조립 (§10)")
    matrix = build_impact_matrix(
        extraction, impact, grounding=grounding, regression=regression
    )
    print(format_matrix_text(matrix))

    # 8 — Assurance 종합
    head("Assurance Evaluation")
    print(f"  Citation Correctness   {grounding.citation_correctness:.0%}")
    print(f"  Unsupported Claim Rate {grounding.unsupported_claim_rate:.0%}")
    print(f"  Change Completeness    {scored.change_completeness:.0%}")
    print(f"  Exception Recall       {scored.exception_recall:.0%}"
          + (f"   (놓친 예외: {scored.missed_exceptions})" if scored.missed_exceptions else ""))
    print(f"  Effective-date         {'OK' if scored.effective_date_correct else 'MISS'}")
    print(f"  Regions                {'OK' if scored.regions_correct else 'MISS'}")
    print(f"  Rule Regression        {regression.pass_rate:.0%}")
    print(f"  자동처리 가능 비율      {matrix.automation_rate:.0%} "
          f"(Human Review {len(matrix.human_review_rows)}행)")

    # 9 — E2E 관통 확인
    head("E2E 관통 확인 (브리프 §18 코어 완성의 정의)")
    checks = [
        ("Source Snapshot", bool(sources)),
        ("Policy Version Resolution", bool(norm.mapping) and not norm.unmapped),
        ("Before/After 추출", bool(extraction.changes)),
        ("Impact Matrix", bool(matrix.rows)),
        ("Customer Impact", bool(impact.impacts)),
        ("Structured Rule Proposal", any(r.metrics.get("rule_diff") for r in matrix.rows)),
        ("Test Cases", regression.total > 0),
        ("Deterministic Rule Regression", regression.pass_rate == 1.0),
        ("Assurance Evaluation", grounding.total > 0),
        ("Human Review 표시", bool(matrix.human_review_rows)),
    ]
    for name, ok in checks:
        print(f"  {'✅' if ok else '❌'} {name}")
    print(f"\n  → {'관통 성공' if all(ok for _, ok in checks) else '미관통 — 위 ❌ 항목 확인'}")

    if a.write:
        OUT_MD.write_text(format_matrix_markdown(matrix), encoding="utf-8")
        print(f"\n매트릭스 저장: {OUT_MD.relative_to(REPO)}")


if __name__ == "__main__":
    main()
