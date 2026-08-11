"""Validation Report 렌더러 — E2E 산출물을 사람이 읽는 Markdown 보고서로.

브리프 §18 마지막 노드. 검증보고서(Phase 3에서 15~20쪽으로 확장)의 **stub**:
각 노드 산출물을 한 문서로 잇고, 한계와 사람검토 게이트를 명시한다.
"""
from __future__ import annotations

from .pipeline import ValidationReport


def _ltv(v) -> str:
    return "—" if v is None else f"{v:.0%}"


def render_markdown(rep: ValidationReport) -> str:
    L: list[str] = []
    ok = "✅ 관통 성공" if rep.e2e_ok else "❌ 관통 실패"
    llm = "실제 LLM" if rep.used_live_llm else "오프라인 stub(API 키 없이 관통)"

    L.append("# RegImpact — Validation Report (Walking Skeleton)")
    L.append("")
    L.append(f"- **시나리오:** {rep.scenario}")
    L.append(f"- **정책 시점:** before `{rep.before_date}` → after `{rep.after_date}`")
    L.append(f"- **추출 경로:** {llm}")
    L.append(f"- **E2E 상태:** {ok}")
    L.append("")
    L.append("> 브리프 §18 코어라인: Source → Policy Version → Before/After → Impact Matrix "
             "→ Rule Proposal → Test Cases → Rule Regression → Assurance → Human Review → Report. "
             "각 노드가 실제 산출물을 냈는지 한 문서로 관통 확인.")
    L.append("")

    # 1. Source Snapshot
    L.append("## 1. Source Snapshot (원문 무결성)")
    L.append("")
    L.append("| doc_id | chars | raw_sha256 (앞 16) |")
    L.append("|---|---:|---|")
    for s in rep.snapshots:
        L.append(f"| {s.doc_id} | {s.n_chars} | `{s.raw_sha256[:16]}…` |")
    L.append("")
    L.append("> raw_sha256 = extractor가 실제 소비한 추출 텍스트의 지문. "
             "원본(PDF/HWP) 해시는 `docs/sources/SOURCES.md`.")
    L.append("")

    # 2. Policy Version Resolution
    L.append("## 2. Policy Version Resolution (지역 규제상태 전환)")
    L.append("")
    L.append("| region | before | after | 신규규제 |")
    L.append("|---|---|---|:---:|")
    for t in rep.transitions:
        mark = "🔺" if t.newly_regulated else ""
        L.append(f"| {t.region_code} | {t.before_status} | {t.after_status} | {mark} |")
    L.append("")

    # 3. Before/After (RegChange)
    L.append("## 3. Before/After — RegChange 추출")
    L.append("")
    ex = rep.extraction
    L.append(f"- policy_id: `{ex.policy_id}`  ·  effective_from: `{ex.effective_from}`  "
             f"·  target_regions: {', '.join(ex.target_regions)}")
    L.append("")
    L.append("| category | 변경 | before | after |")
    L.append("|---|---|---|---|")
    for c in ex.changes:
        L.append(f"| {c.category} | {c.summary} | {c.before or '—'} | {c.after or '—'} |")
    L.append("")

    # 4. Impact Matrix
    m = rep.matrix
    L.append("## 4. Impact Matrix (Before/After · 룰엔진 실측)")
    L.append("")
    L.append(f"포트폴리오 n={m.n} · 변경영향 {m.n_changed}({m.affected_rate:.0%}) · "
             f"강화 {m.n_tightened} · 경과규정보호 {m.n_grandfathered} · **고임팩트 {m.n_high_impact}**")
    L.append("")
    L.append("| 세그먼트 | n | 변화 | before | after | Δ | 고위험 |")
    L.append("|---|---:|---:|---:|---:|---:|---:|")
    for s in m.segments:
        L.append(
            f"| {s.segment.label()} | {s.n} | {s.n_changed} | "
            f"{_ltv(s.avg_ltv_before)} | {_ltv(s.avg_ltv_after)} | "
            f"{_ltv(s.avg_ltv_delta)} | {s.n_high_impact} |"
        )
    L.append("")

    # 5. Structured Rule Change Proposal
    p = rep.proposal
    L.append("## 5. Structured Rule Change Proposal (승인 대기)")
    L.append("")
    L.append(f"- 상태: **{p.approval_status}** (§4 AI초안→사람확정)")
    L.append(f"- 경과규정: {p.grandfathering}")
    L.append("")
    L.append("| 차주 유형 | before LTV | after LTV | rule_id | 비고 |")
    L.append("|---|---:|---:|---|---|")
    for ln in p.ltv_lines:
        L.append(f"| {ln.borrower} | {_ltv(ln.before_ltv)} | {_ltv(ln.after_ltv)} | "
                 f"`{ln.rule_id}` | {ln.note} |")
    L.append("")

    # 6. Rule Regression
    reg = rep.regression
    L.append("## 6. Deterministic Rule Regression (엔진 ⟷ 명세 오라클)")
    L.append("")
    L.append(f"- Rule-regression Pass Rate: **{reg.passed}/{reg.total} = {reg.pass_rate:.0%}**")
    L.append("")
    L.append("| 카테고리 | 통과/전체 |")
    L.append("|---|---:|")
    for cat, (pp, nn, _rate) in reg.pass_rate_by_category().items():
        L.append(f"| {cat} | {pp}/{nn} |")
    L.append("")
    if reg.failures:
        L.append("⚠ 실패 케이스:")
        for f in reg.failures:
            L.append(f"- {f.case.case_id}: {'; '.join(f.mismatches)}")
        L.append("")

    # 7. Assurance
    g = rep.grounding
    L.append("## 7. Assurance (Citation Grounding + Gold)")
    L.append("")
    L.append(f"- Citation Correctness: **{g.citation_correctness:.0%}** "
             f"({g.grounded}/{g.total})  ·  Unsupported Claim Rate: {g.unsupported_claim_rate:.0%}")
    if rep.gold:
        gd = rep.gold
        L.append(f"- Change Completeness: **{gd.change_completeness:.0%}**  ·  "
                 f"Exception Recall: **{gd.exception_recall:.0%}**  ·  "
                 f"Effective-date: {'✅' if gd.effective_date_correct else '❌'}  ·  "
                 f"Regions: {'✅' if gd.regions_correct else '❌'}")
        if gd.missed_changes or gd.missed_exceptions:
            L.append(f"- 놓침: 변경={gd.missed_changes or '없음'} / 예외={gd.missed_exceptions or '없음'}")
    if g.ungrounded:
        L.append("- ⚠ 미검증 인용:")
        for u in g.ungrounded:
            L.append(f"  - [{u.category}] {u.summary}")
    L.append("")

    # 8. Human Review gate
    L.append("## 8. Human Review 게이트")
    L.append("")
    if rep.review_items:
        L.append(f"자동판정으로 종결하지 않고 **사람 검토로 넘기는 {len(rep.review_items)}건**:")
        L.append("")
        L.append("| 출처 | 대상 | 사유 |")
        L.append("|---|---|---|")
        for it in rep.review_items:
            L.append(f"| {it.source} | {it.ref} | {it.reason} |")
    else:
        L.append("사람 검토 필요 항목 없음.")
    L.append("")

    # 9. 한계
    L.append("## 9. 한계 (정직한 명시)")
    L.append("")
    L.append("- **Walking Skeleton stub.** 각 노드는 관통 확인용 최소 구현. 포트폴리오는 소규모 대표 표본.")
    if not rep.used_live_llm:
        L.append("- 추출은 오프라인 stub(환각 없음). 실제 LLM 추출 시 Assurance 수치가 첫 실측 지표가 됨.")
    L.append("- 룰엔진 LTV 값은 확정 명세(FAQ Q2)에서만 옴(LOCKED §4). 이 보고서는 값을 만들지 않음.")
    L.append("- 규칙 변경안은 **승인 대기** 상태 — 사람 확정 전에는 운영 반영 금지(§4).")
    L.append("")
    L.append(f"---\n\n_E2E 상태: {ok} · 생성: RegImpact report node (stub)_")
    return "\n".join(L)
