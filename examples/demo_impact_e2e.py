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
from regimpact.audit import Action, AuditLog  # noqa: E402
from regimpact.impact.builder import derive_rule_diff  # noqa: E402
from regimpact.impact.portfolio import DEFAULT_SEED, DEFAULT_SIZE  # noqa: E402
from regimpact.proposal import (  # noqa: E402
    apply_consistency_status,
    build_proposal_from_extraction,
    check_proposal_consistency,
)
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

    audit = AuditLog()

    # 1 — Source Snapshot
    head("Source Snapshot — 공문 원문 로드")
    sources = load_sources()
    for doc_id, text in sources.items():
        print(f"  {doc_id}: {len(text):,}자")
        audit.record(Action.SOURCE_INGESTED, doc_id, {"chars": len(text)})

    # 2 — Before/After 추출 (LLM) + Citation Assurance
    head(f"RegChange 추출 (provider={a.provider})")
    kwargs = {"run_path": a.run} if a.provider == "replay" else {}
    complete = resolve_completion(a.provider, model=a.model, **kwargs)
    extraction = extract_regchange(sources, complete=complete)
    print(f"  변경 {len(extraction.changes)}건 · 시행일 {extraction.effective_from}")
    audit.record(Action.EXTRACTION, extraction.policy_id,
                 {"provider": a.provider, "changes": len(extraction.changes),
                  "effective_from": extraction.effective_from})

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
    audit.record(Action.IMPACT_ANALYZED, extraction.policy_id,
                 {"portfolio": a.size, "seed": a.seed,
                  "decision_coverage": round(impact.decision_coverage, 4),
                  "impact_coverage": round(impact.impact_coverage, 4)})
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
    audit.record(Action.REGRESSION_RUN, "tc_generator",
                 {"total": regression.total, "pass_rate": regression.pass_rate,
                  "failures": len(regression.failures)})

    # 7 — Rule Change Proposal (LLM 추출 → 구조화 변경안 → 엔진 교차검증)
    head("Rule Change Proposal — 구조화 변경안 + 엔진 일치 검증")
    proposal = build_proposal_from_extraction(extraction)
    consistency = check_proposal_consistency(proposal, rule_diff=derive_rule_diff())
    proposal = apply_consistency_status(proposal, consistency)
    print(f"  세그먼트별 LTV(after): {proposal.after.ltv_by_segment}")
    print(f"  신규지정 {len(proposal.after.target_regions)}곳 · 시행 {proposal.after.effective_from}"
          f" · 경과규정 컷오프 {proposal.grandfathering.cutoff_date if proposal.grandfathering else '—'}")
    print(f"  근거 인용 {len(proposal.sources)}건")
    print(f"  엔진 대조 {consistency.summary()['passed']}/{consistency.summary()['total']} 통과")
    for c in consistency.failed:
        if isinstance(c.actual, list):
            continue          # 아래 ⤷ 목록에서 항목별로 보여준다
        print(f"    ⚠ {c.name} — 기대 {c.expected} / 실제 {c.actual}")
    for x in proposal.conflicts:
        print(f"    ⤷ 충돌: {x}")
    for x in proposal.unmapped:
        print(f"    ⤷ LTV 아님(별도 룰 필요): {x}")
    audit.record(Action.PROPOSAL_CREATED, proposal.rule_id,
                 {"status": proposal.status.value,
                  "consistency": consistency.summary(),
                  "conflicts": len(proposal.conflicts),
                  "unmapped": len(proposal.unmapped)})
    print(f"  승인 상태: {proposal.status.value}"
          + ("  ← 사람 검토 후 registry 반영" if proposal.status.value != "APPROVED" else ""))

    # 8 — Impact Matrix 조립
    head("Impact Matrix 조립 (§10)")
    matrix = build_impact_matrix(
        extraction, impact, grounding=grounding, regression=regression
    )
    print(format_matrix_text(matrix))

    # 9 — Assurance 종합
    head("Assurance Evaluation")
    print(f"  Citation Correctness   {grounding.citation_correctness:.0%}")
    print(f"  Unsupported Claim Rate {grounding.unsupported_claim_rate:.0%}")
    print(f"  Change Completeness    {scored.change_completeness:.0%}")
    print(f"  Exception Recall       {scored.exception_recall:.0%}"
          + (f"   (놓친 예외: {scored.missed_exceptions})" if scored.missed_exceptions else ""))
    print(f"  Effective-date         {'OK' if scored.effective_date_correct else 'MISS'}")
    print(f"  Regions                {'OK' if scored.regions_correct else 'MISS'}")
    print(f"  Rule Regression        {regression.pass_rate:.0%}")
    print(f"  Proposal Consistency   {consistency.summary()['passed']}/{consistency.summary()['total']}"
          f"  (변경안 {proposal.status.value})")
    print(f"  자동처리 가능 비율      {matrix.automation_rate:.0%} "
          f"(Human Review {len(matrix.human_review_rows)}행)")

    # 10 — E2E 관통 확인
    head("E2E 관통 확인 (브리프 §18 코어 완성의 정의)")
    checks = [
        ("Source Snapshot", bool(sources)),
        ("Policy Version Resolution", bool(norm.mapping) and not norm.unmapped),
        ("Before/After 추출", bool(extraction.changes)),
        ("Impact Matrix", bool(matrix.rows)),
        ("Customer Impact", bool(impact.impacts)),
        ("Structured Rule Proposal", bool(proposal.sources) and proposal.after.max_ltv is not None),
        ("Proposal ↔ Engine Consistency", bool(consistency.checks)),
        ("Test Cases", regression.total > 0),
        ("Deterministic Rule Regression", regression.pass_rate == 1.0),
        ("Assurance Evaluation", grounding.total > 0),
        ("Human Review 표시", bool(matrix.human_review_rows)),
    ]
    for name, ok in checks:
        print(f"  {'✅' if ok else '❌'} {name}")
    print(f"\n  → {'관통 성공' if all(ok for _, ok in checks) else '미관통 — 위 ❌ 항목 확인'}")

    # 11 — Audit Trail
    audit.record(Action.ASSURANCE_SCORED, extraction.policy_id, {
        "citation_correctness": grounding.citation_correctness,
        "change_completeness": scored.change_completeness,
        "exception_recall": scored.exception_recall,
        "automation_rate": round(matrix.automation_rate, 4),
    })
    head("Audit Trail — 해시 체인 감사로그")
    verdict = audit.verify()
    for e in audit.events:
        print(f"  #{e.seq} {e.action:<18} {e.target:<32} {e.entry_hash[:12]}…")
    print(f"\n  체인 무결성: {'OK' if verdict.ok else 'BROKEN'} · {len(audit)}건")
    print(f"  head 해시: {audit.head_hash}")
    print("  ⤷ 이 해시를 로그 바깥(커밋·리포트)에 남겨야 끝에서 잘라낸 것도 잡힌다.")
    if a.write:
        out = REPO / "docs" / "eval" / "audit_6_30.jsonl"
        audit.write_jsonl(out)
        print(f"  기록: {out.relative_to(REPO)}")

    if a.write:
        OUT_MD.write_text(format_matrix_markdown(matrix), encoding="utf-8")
        print(f"\n매트릭스 저장: {OUT_MD.relative_to(REPO)}")


if __name__ == "__main__":
    main()
