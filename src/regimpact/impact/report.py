"""임팩트 매트릭스 렌더링 — 사람이 읽고 검토·승인하는 산출물 형태로 출력.

두 가지 형태:
  - `format_matrix_markdown()` — 검증보고서·PR에 붙이는 표 (Phase별 그룹)
  - `format_matrix_text()`     — 터미널 요약
Phase별로 묶는 이유: 이 매트릭스의 요점이 "시행일 전에 뭘 끝내야 하는가"이기 때문이다(LOCKED §0-7).
"""
from __future__ import annotations

from .schema import ImpactMatrix, ImpactRow, Phase

_AUTO = {True: "🤖 자동", False: "🖐 사람"}


def _evidence_cell(row: ImpactRow) -> str:
    if not row.evidence:
        return "—"
    return "<br>".join(e.short(60).replace("|", "\\|") for e in row.evidence)


def _esc(s: str) -> str:
    return s.replace("|", "\\|")


def format_matrix_markdown(matrix: ImpactMatrix) -> str:
    """§10 공통 열을 그대로 가진 마크다운 표 (Phase별 섹션)."""
    L: list[str] = []
    L.append(f"# 임팩트 매트릭스 — {matrix.policy_id}")
    L.append("")
    L.append(f"- 시행일: **{matrix.effective_from}**")
    L.append(f"- 대상 지역: {', '.join(matrix.target_regions) or '—'}")
    L.append(f"- 총 {len(matrix.rows)}행 · 자동처리 가능 {matrix.automation_rate:.0%} "
             f"· D-day 전 필수 {len(matrix.d_minus_required)}건")
    L.append(f"- 생성 근거: {matrix.generated_from}")
    L.append("")
    L.append("> 자동처리 불가 행은 **Human Review 사유**를 반드시 명시한다. "
             "이 매트릭스는 자동화율을 자랑하는 문서가 아니라 "
             "**어디까지 자동이고 어디부터 사람인지 경계를 고정하는 문서**다.")
    L.append("")

    for phase in Phase:
        rows = matrix.by_phase(phase)
        if not rows:
            continue
        L.append(f"## Phase: {phase.value} ({len(rows)}행)")
        L.append("")
        L.append("| 업무영역 | 변경 내용 | 근거 문서 | 영향 대상 | 산출물 | 우선순위 | 담당 | 승인 상태 | 자동 | Human Review 사유 |")
        L.append("|---|---|---|---|---|---|---|---|---|---|")
        for r in rows:
            L.append(
                f"| **{_esc(r.area)}** | {_esc(r.change)} | {_evidence_cell(r)} "
                f"| {_esc(r.affected)} | {_esc(r.deliverable)} | {r.priority.value} "
                f"| {r.owner.value} | {r.approval_status.value} | {_AUTO[r.automatable]} "
                f"| {_esc(r.human_review_reason or '—')} |"
            )
        L.append("")

    hr = matrix.human_review_rows
    L.append(f"## Human Review 필요 ({len(hr)}행)")
    L.append("")
    for r in hr:
        L.append(f"- **{r.area}** — {r.human_review_reason}")
    L.append("")
    return "\n".join(L)


def format_matrix_text(matrix: ImpactMatrix) -> str:
    """터미널용 요약."""
    L: list[str] = []
    L.append(f"임팩트 매트릭스 — {matrix.policy_id} (시행 {matrix.effective_from})")
    L.append(f"대상 지역: {', '.join(matrix.target_regions)}")
    L.append(f"{len(matrix.rows)}행 · 자동처리 {matrix.automation_rate:.0%} "
             f"· D-day 전 필수 {len(matrix.d_minus_required)}건")
    for phase in Phase:
        rows = matrix.by_phase(phase)
        if not rows:
            continue
        L.append("")
        L.append(f"[{phase.value}] {len(rows)}행")
        for r in rows:
            L.append(f"  {_AUTO[r.automatable]} {r.priority.value:<3} {r.area}")
            L.append(f"      {r.change}")
            if r.human_review_reason:
                L.append(f"      ⤷ 사람 검토: {r.human_review_reason}")
    return "\n".join(L)
