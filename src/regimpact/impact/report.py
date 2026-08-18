"""검증보고서 렌더러 (브리프 §18 Validation Report).

E2E 결과를 사람이 읽는 마크다운으로 뽑는다. 규칙 하나: **안 돌린 단계를 돌린 것처럼 쓰지 않는다.**
`미실행` 단계와 `N/A` 지표는 그대로 노출한다.
"""
from __future__ import annotations

from .matrix import ApprovalStatus, ImpactMatrix, MatrixRow, Phase, Provenance
from .pipeline import E2EResult, StageStatus

_STATUS_MARK = {
    StageStatus.DONE: "✅",
    StageStatus.ATTENTION: "⚠️",
    StageStatus.MISSING: "⛔",
}


def _row_line(r: MatrixRow) -> str:
    ev = "<br>".join(e.render() for e in r.evidence) or "—"
    hr = r.human_review_reason or "—"
    return (f"| {r.area} | {r.change} | {ev} | {r.target} | {r.deliverable} | "
            f"{r.priority.value} | **{r.phase.value}** | {r.owner.value} | "
            f"{r.approval.value} | {r.automation.value} | {r.provenance.value} | {hr} |")


def render_matrix(matrix: ImpactMatrix) -> str:
    lines = [
        "| 업무영역 | 변경 내용 | 근거 / evidence | 영향 대상 | 산출물 | 우선순위 | 기한(Phase) "
        "| 담당 | 승인 상태 | 자동처리 | 근거 출처 | Human Review 사유 |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for phase in (Phase.BEFORE_DDAY, Phase.AFTER_EFFECTIVE, Phase.SEPARATE_TRIGGER):
        for r in matrix.by_phase(phase):
            lines.append(_row_line(r))
    return "\n".join(lines)


def render_report(result: E2EResult, *, title: str = "6·30 규제 변경 검증보고서") -> str:
    m = result.matrix
    impact = result.impact
    no_event = impact.no_event_only()
    out: list[str] = []

    out.append(f"# {title}")
    out.append("")
    out.append(f"- **정책 ID:** `{m.policy_id}` · **시행일:** {m.effective_from}")
    out.append(f"- **파이프라인 완결 여부:** "
               + ("전 단계 실행됨" if result.completed else
                  "⛔ **미실행 단계 있음** — 아래 단계표 참고. 이 보고서는 미완결 상태를 그대로 표시한다."))
    out.append("")
    out.append("> 이 보고서의 수치는 **합성 포트폴리오**(커버리지 격자)에서 나온 것이다. "
               "실제 고객 분포가 아니므로 '몇 명이 영향받는다'가 아니라 "
               "**'어떤 세그먼트가 어떻게 바뀌는가'** 로 읽어야 한다. (LOCKED §8 — 실제 고객데이터 미사용)")
    out.append("")

    # ── 1. 파이프라인 단계 ────────────────────────────────────────────────
    out.append("## 1. 파이프라인 단계 (브리프 §18 코어 완성의 정의)")
    out.append("")
    out.append("| | 단계 | 상태 | 내용 |")
    out.append("|---|---|---|---|")
    for i, s in enumerate(result.stages, 1):
        out.append(f"| {i} | {s.name} | {_STATUS_MARK[s.status]} {s.status.value} | {s.detail} |")
    out.append("")
    for s in result.stages:
        if not s.metrics:
            continue
        out.append(f"**{s.name}**")
        out.append("")
        for k, v in s.metrics.items():
            out.append(f"- {k}: `{v}`")
        out.append("")

    # ── 2. 임팩트 매트릭스 ────────────────────────────────────────────────
    out.append("## 2. 임팩트 매트릭스")
    out.append("")
    out.append("> **LOCKED §7 — 시간축(Phase)은 삭제하지 않는다.** 일은 두 물결로 온다: "
               "시행일 전 필수(룰·전산·테스트·공지)와 시행 후(전략·모니터링). "
               "대외보고 기준 변경은 **별도 트리거**로 나중에 도착한다.")
    out.append("")
    counts = {ph.value: len(m.by_phase(ph)) for ph in
              (Phase.BEFORE_DDAY, Phase.AFTER_EFFECTIVE, Phase.SEPARATE_TRIGGER)}
    out.append("Phase 분포: " + " · ".join(f"**{k}** {v}행" for k, v in counts.items()))
    out.append("")
    out.append(render_matrix(m))
    out.append("")

    # ── 3. 고객·포트폴리오 영향 ───────────────────────────────────────────
    out.append("## 3. 고객·포트폴리오 영향")
    out.append("")
    out.append(f"합성 포트폴리오 **{impact.total:,.0f}건** "
               f"(지역군 4 × 차주유형 6 × 경과규정 이벤트 4 × 가격구간 7, 등가중 완전요인).")
    out.append("")
    out.append("| 지역군 | 건수 | 영향률 | 경과규정 적용 | 유예로 판정이 달라진 건 | 자동판정 거부 | 한도 변화 |")
    out.append("|---|---:|---:|---:|---:|---:|---:|")
    for label, st in impact.by_region_group().items():
        out.append(f"| {label} | {st.n:,.0f} | {st.impacted_rate:.1%} | {st.grandfathered:,.0f} "
                   f"| {st.protected:,.0f} | {st.escalation_rate:.1%} "
                   f"| {st.limit_delta_sum_eok:,.1f}억 |")
    out.append("")
    out.append("| 차주 유형 | 건수 | 영향률 | 자동판정 거부 |")
    out.append("|---|---:|---:|---:|")
    for label, st in impact.by_borrower().items():
        out.append(f"| {label} | {st.n:,.0f} | {st.impacted_rate:.1%} | {st.escalation_rate:.1%} |")
    out.append("")
    out.append(f"**경과규정 미해당 층({no_event.total:,.0f}건) 기준 영향률 "
               f"{no_event.impacted_rate:.1%}, 한도 변화 {no_event.limit_delta_sum_eok:,.1f}억.** "
               "혼합 비율 하나로 말하지 않는 이유는 격자에서 경과규정 이벤트가 4분의 3을 차지하기 때문이다 "
               "— 그 비율은 현실이 아니라 설계다.")
    out.append("")

    # ── 4. Rule Change Proposal ──────────────────────────────────────────
    out.append("## 4. 구조화 Rule Change Proposal")
    out.append("")
    if not result.proposals:
        out.append("관측된 rule_id 전이 없음.")
    else:
        out.append("| 전이 | LTV | 관측 건수 | 근거 정책 | 승인 |")
        out.append("|---|---|---:|---|---|")
        for p in result.proposals:
            out.append(f"| `{p.rule_id_before}` → `{p.rule_id_after}` "
                       f"| {p.ltv_before:.0%} → {p.ltv_after:.0%} | {p.affected:,.0f} "
                       f"| {', '.join(p.source_policy_ids)} "
                       f"| {'사람 승인 필요' if p.requires_human_approval else '—'} |")
        out.append("")
        for p in result.proposals:
            out.append(f"- `{p.label}` 영향 세그먼트: " + "; ".join(p.segments))
    out.append("")
    out.append("> **LOCKED §4** — 룰 로직은 LLM이 생성하지 않는다. 위 제안은 확정 명세를 구현한 "
               "결정론 엔진이 Before/After를 실제로 판정해 관측한 전이이며, 반영은 사람이 승인한다.")
    out.append("")

    # ── 5. Human Review 큐 ───────────────────────────────────────────────
    out.append("## 5. Human Review 큐")
    out.append("")
    out.append(f"자동판정을 거부한 건 **{impact.escalated:,.0f}건 ({impact.escalation_rate:.1%})**. "
               "숫자를 지어내지 않은 대가이며, 명세 공백이 어디인지를 그대로 드러낸다.")
    out.append("")
    for code, n in impact.escalation_reasons().items():
        out.append(f"- `{code}` — {n:,.0f}건")
    out.append("")
    out.append("검토 필요 매트릭스 행:")
    out.append("")
    for r in m.needs_human_review():
        flag = " **[선행작업 대기]**" if r.approval is ApprovalStatus.BLOCKED else ""
        out.append(f"- **{r.area}**{flag} — {r.human_review_reason}")
    out.append("")

    # ── 6. 근거 출처 분포 ────────────────────────────────────────────────
    out.append("## 6. 근거 출처 분포 (추적 가능성)")
    out.append("")
    prov: dict[str, int] = {}
    for r in m.rows:
        prov[r.provenance.value] = prov.get(r.provenance.value, 0) + 1
    out.append("| 근거 출처 | 행 수 |")
    out.append("|---|---:|")
    for k, v in sorted(prov.items(), key=lambda kv: -kv[1]):
        out.append(f"| {k} | {v} |")
    out.append("")
    if result.extraction is None:
        out.append("> ⛔ **AI 추출 미실행.** 원문 인용이 필요한 행들은 사람 확정 골드(`docs/eval/`)를 "
                   "근거로 삼고 있으며, Citation Correctness·Change Completeness는 산출되지 않았다. "
                   "`ANTHROPIC_API_KEY`를 설정하고 다시 돌리면 이 행들의 출처가 "
                   f"`{Provenance.AI_EXTRACTION.value}`로 바뀌고 Assurance 수치가 채워진다.")
    out.append("")

    return "\n".join(out)
