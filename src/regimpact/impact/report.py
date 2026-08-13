"""E2EReport의 사람이 읽는 검증보고서 렌더링 (데모·CI 로그·UI 텍스트용)."""
from __future__ import annotations

from .matrix import ImpactRow
from .pipeline import E2EReport
from .proposal import ApprovalStatus


def _ltv(v) -> str:
    return "-" if v is None else f"{v:.0%}"


def _row_line(r: ImpactRow) -> str:
    before = _ltv(r.before_ltv) if r.before.max_ltv is not None else r.before.status.value
    after = _ltv(r.after_ltv) if r.after.max_ltv is not None else r.after.status.value
    delta = "" if r.delta_ltv is None else f"{r.delta_ltv:+.0%}"
    flags = []
    if r.high_impact:
        flags.append("고영향")
    if r.escalated:
        flags.append("escalation")
    flag_s = f"  [{'/'.join(flags)}]" if flags else ""
    return f"  {r.segment_label:<14} {r.region_code:<18} {before:>8} → {after:>8}  {delta:>6}{flag_s}"


def format_e2e_report(report: E2EReport) -> str:
    """6·30 E2E 검증보고서를 텍스트로 렌더링한다."""
    L: list[str] = []
    bar = "=" * 72
    L.append(bar)
    L.append(f"RegImpact — E2E Validation Report : {report.scenario}")
    L.append(bar)

    # 1. Source
    L.append("")
    L.append(f"[1] Source Snapshot   : {', '.join(report.sources_loaded) or '(없음)'}")

    # 2. RegChange 추출 (Before/After)
    e = report.extraction
    L.append("")
    L.append(f"[2] RegChange 추출    : policy={e.policy_id}  effective={e.effective_from}")
    L.append(f"    target_regions    : {', '.join(e.target_regions)}")
    L.append(f"    변경 항목({len(e.changes)}):")
    for it in e.changes:
        ba = ""
        if it.before or it.after:
            ba = f"  ({it.before or '-'} → {it.after or '-'})"
        L.append(f"      • [{it.category}] {it.summary}{ba}")

    # 3. Impact Matrix
    L.append("")
    L.append(f"[3] Impact Matrix     : {len(report.impact_matrix)}행 "
             f"(고영향 {len(report.high_impact_rows)} / escalation {len(report.escalated_rows)})")
    L.append(f"  {'세그먼트':<14} {'지역':<18} {'before':>8}   {'after':>6}  {'Δ':>6}")
    L.append("  " + "-" * 62)
    for r in report.impact_matrix:
        L.append(_row_line(r))

    # 4. Rule Change Proposal
    p = report.proposal
    status_mark = "🟢 확정" if p.approval_status == ApprovalStatus.HUMAN_CONFIRMED else "🟡 AI초안(사람확정 대기)"
    L.append("")
    L.append(f"[4] Rule Change Proposal : {p.proposal_id}  상태={status_mark}")
    L.append(f"    서술 변경 {len(p.narrative_changes)} · 세그먼트 영향 {len(p.segment_impacts)}")

    # 5. Test Cases + Rule Regression
    reg = report.regression
    L.append("")
    L.append(f"[5] Rule Regression   : Pass Rate {reg.passed}/{reg.total} = {reg.pass_rate:.0%} "
             "(engine ⟷ 독립 명세 오라클)")
    for cat, (pc, n, rate) in reg.pass_rate_by_category().items():
        L.append(f"      {cat:<15} {pc:>2}/{n:<2} {rate:.0%}")
    if reg.failures:
        L.append(f"      ✗ 실패 {len(reg.failures)}건:")
        for f in reg.failures:
            L.append(f"         - {f.case.case_id} {f.mismatches}")

    # 6. Assurance
    g, gd = report.grounding, report.gold
    L.append("")
    L.append("[6] Assurance (검증)")
    L.append(f"    ① Citation Correctness : {g.citation_correctness:.0%} "
             f"(grounded {g.grounded}/{g.total}, unsupported {len(g.ungrounded)})")
    L.append(f"    ② Change Completeness  : {gd.change_completeness:.0%}"
             + (f"  (miss: {gd.missed_changes})" if gd.missed_changes else ""))
    L.append(f"    ③ Exception Recall     : {gd.exception_recall:.0%}"
             + (f"  (miss: {gd.missed_exceptions})" if gd.missed_exceptions else ""))
    L.append(f"    ③ Effective-date/Region: date={'✓' if gd.effective_date_correct else '✗'} "
             f"region={'✓' if gd.regions_correct else '✗'}")

    # 7. 종합
    L.append("")
    verdict = "✅ E2E 관통 성공" if report.e2e_ok else "⚠️ E2E 점검 필요"
    L.append(f"[7] 종합 판정         : {verdict}")
    L.append("    (회귀 100% + 인용 환각 0 + 추출·매트릭스 산출 = 배관 관통 확인)")
    L.append(bar)
    return "\n".join(L)
