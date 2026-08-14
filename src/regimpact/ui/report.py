"""검증 보고서 화면 (data-path=audit-trail) — ValidationReport E2E 렌더.

브리프 §18 '코어 완성의 정의'인 End-to-End 파이프라인을 하나의 감사추적 화면으로 렌더한다:
Source → Policy Version → RegChange → Impact Matrix → Rule Change Proposal → Test/Regression →
Assurance → Human Review. 값은 실제 산출물에서 유도되며 미측정은 지어내지 않고 표기한다.
"""
from __future__ import annotations

from ..report import ValidationReport, build_validation_report
from .chrome import esc, mono_chip, page, provenance_strip, title_block

_STEP_TONE = {
    "OK": ("bg-secondary-container text-on-secondary", "check_circle"),
    "MEASURED": ("bg-secondary-container text-on-secondary", "verified"),
    "REVIEW": ("bg-tertiary-fixed text-on-tertiary-fixed-variant", "fact_check"),
    "PENDING": ("bg-tertiary-fixed text-on-tertiary-fixed-variant", "schedule"),
}


def _status_badge(status: str) -> str:
    tone = ("bg-tertiary-fixed text-on-tertiary-fixed-variant"
            if status == "REVIEW_REQUIRED" else "bg-secondary-container text-on-secondary")
    label = "검토 필요" if status == "REVIEW_REQUIRED" else "OK"
    return (
        f'<span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full {tone} '
        f'font-mono-label text-mono-label"><span class="w-2 h-2 rounded-full bg-current"></span>{esc(label)}</span>'
    )


def _pipeline(report: ValidationReport) -> str:
    steps = []
    for st in report.steps:
        tone, icon = _STEP_TONE.get(st.status, ("bg-surface-variant text-on-surface-variant", "circle"))
        steps.append(
            '<div class="flex items-start gap-3">'
            f'<div class="shrink-0 w-8 h-8 rounded-full {tone} flex items-center justify-center">'
            f'<span class="material-symbols-outlined text-[18px]">{icon}</span></div>'
            '<div class="flex-1 pb-4 border-b border-outline-variant/20">'
            '<div class="flex items-center gap-2">'
            f'<span class="font-body-md font-semibold">{st.order}. {esc(st.name)}</span>'
            f'<span class="font-mono-label text-mono-label text-on-surface-variant">[{esc(st.status)}]</span></div>'
            f'<div class="font-body-sm text-body-sm text-on-surface-variant mt-0.5">{esc(st.detail)}</div></div></div>'
        )
    return (
        '<div class="bg-surface-container-lowest rounded-xl border border-outline-variant/30 p-6">'
        '<div class="flex items-center gap-2 mb-4"><span class="material-symbols-outlined text-secondary">account_tree</span>'
        '<h3 class="font-h3 text-h3">파이프라인 (End-to-End)</h3></div>'
        f'<div class="flex flex-col gap-3">{"".join(steps)}</div></div>'
    )


def _sources(report: ValidationReport) -> str:
    items = "".join(
        '<li class="flex items-center gap-2 flex-wrap">'
        '<span class="material-symbols-outlined text-[16px] text-secondary">description</span>'
        f'<span class="font-body-sm">{esc(s["org"])} · {esc(s["published"])}</span>'
        f'{mono_chip(s["doc_id"])}'
        f'<span class="font-mono-label text-mono-label text-outline">#{esc(s["hash"])}</span></li>'
        for s in report.sources
    )
    return (
        '<div class="bg-surface-container-lowest rounded-xl border border-outline-variant/30 p-6">'
        '<div class="flex items-center gap-2 mb-3"><span class="material-symbols-outlined text-secondary">inventory_2</span>'
        '<h4 class="font-h3 text-h3">1. Source Snapshot</h4></div>'
        f'<ul class="flex flex-col gap-2">{items}</ul></div>'
    )


def _proposal_card(report: ValidationReport) -> str:
    p = report.proposal
    rows = "".join(
        '<tr class="hover:bg-surface-container-low/50">'
        f'<td class="p-2 font-semibold whitespace-nowrap">{esc(pc.tier)}</td>'
        f'<td class="p-2 text-right font-mono-data text-mono-data">{esc(pc.before_label)}</td>'
        f'<td class="p-2 text-right font-mono-data text-mono-data font-semibold">{esc(pc.after_label)}</td>'
        f'<td class="p-2">{mono_chip(pc.reason_code)}</td></tr>'
        for pc in p.parameter_changes
    )
    return (
        '<div class="bg-surface-container-lowest rounded-xl border border-outline-variant/30 p-6">'
        '<div class="flex items-center gap-2 mb-3"><span class="material-symbols-outlined text-secondary">edit_document</span>'
        f'<h4 class="font-h3 text-h3">5. Rule Change Proposal</h4></div>'
        f'<div class="font-mono-label text-mono-label text-on-surface-variant mb-3">{esc(p.rule_id)} · '
        f'승인상태 {esc(p.approval_status.value)}</div>'
        '<table class="w-full text-left border-collapse font-body-sm text-body-sm">'
        '<thead class="text-on-surface-variant"><tr><th class="p-2">계층</th><th class="p-2 text-right">종전</th>'
        '<th class="p-2 text-right">변경</th><th class="p-2">근거</th></tr></thead>'
        f'<tbody class="divide-y divide-outline-variant/30">{rows}</tbody></table></div>'
    )


def _regression_card(report: ValidationReport) -> str:
    reg = report.regression
    bars = "".join(
        '<div class="flex items-center justify-between font-body-sm text-body-sm">'
        f'<span>{esc(cat)}</span><span class="font-mono-data text-mono-data">{passed}/{total} ({rate:.0%})</span></div>'
        for cat, (passed, total, rate) in reg["by_category"].items()
    )
    return (
        '<div class="bg-surface-container-lowest rounded-xl border border-outline-variant/30 p-6">'
        '<div class="flex items-center gap-2 mb-3"><span class="material-symbols-outlined text-secondary">rule</span>'
        f'<h4 class="font-h3 text-h3">6. Rule Regression</h4></div>'
        f'<div class="font-h2 text-h2 text-secondary mb-2">{reg["pass_rate"]:.0%}</div>'
        f'<div class="font-mono-label text-mono-label text-on-surface-variant mb-3">'
        f'{reg["passed"]}/{reg["total"]} · 독립 오라클 차등 검증</div>'
        f'<div class="flex flex-col gap-1">{bars}</div></div>'
    )


def _gold_set_card(report: ValidationReport) -> str:
    gs = report.gold_set
    dev = gs["dev"]
    rows = "".join(
        '<div class="flex items-center justify-between font-body-sm text-body-sm">'
        f'<span>{esc(cat)}</span><span class="font-mono-data text-mono-data">{p}/{t}</span></div>'
        for cat, (p, t, _r) in sorted(dev["by_category"].items())
    )
    if gs.get("opened"):
        headline = (
            f'<div class="font-h2 text-h2 text-secondary mb-1">최종 {gs["overall"]["pass_rate"]:.0%}</div>'
            f'<div class="font-mono-label text-mono-label text-on-surface-variant mb-2">'
            f'{gs["overall"]["passed"]}/{gs["overall"]["total"]} · 개봉 {esc(gs["opened_date"])}</div>'
        )
        badges = (
            '<div class="flex items-center gap-2">'
            f'<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-secondary-container '
            f'text-on-secondary font-mono-label text-mono-label">'
            f'<span class="material-symbols-outlined text-[14px]">lock_open</span>'
            f'LOCKED {gs["locked"]["passed"]}/{gs["locked"]["total"]}</span>'
            f'<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-secondary-container '
            f'text-on-secondary font-mono-label text-mono-label">'
            f'<span class="material-symbols-outlined text-[14px]">lock_open</span>'
            f'CHALLENGE {gs["challenge"]["passed"]}/{gs["challenge"]["total"]}</span></div>'
        )
        note = '<div class="font-body-sm text-body-sm text-on-surface-variant mt-2">최초·최종 개봉(§12). 재튜닝·재보고 금지.</div>'
        rv = gs.get("review")
        if rv:
            rs = rv["summary"]
            note += (
                '<div class="mt-2 flex items-center gap-1 flex-wrap">'
                f'<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-secondary-container '
                f'text-on-secondary font-mono-label text-mono-label">'
                f'<span class="material-symbols-outlined text-[14px]">verified</span>'
                f'도메인 검수 {esc(rv["version"])} · {rs["total"]}문항 확정</span>'
                '<span class="font-mono-label text-mono-label text-on-surface-variant">'
                f'직접 {rs["CONFIRMED"]}·escalation {rs["CONFIRMED_ESCALATION"]}·precedence {rs["CONFIRMED_PRECEDENCE"]} '
                '(사람 확정)</span></div>'
            )
    else:
        headline = (
            f'<div class="font-h2 text-h2 text-secondary mb-1">DEV {dev["pass_rate"]:.0%}</div>'
            f'<div class="font-mono-label text-mono-label text-on-surface-variant mb-2">{dev["passed"]}/{dev["total"]} · 상시 회귀</div>'
        )
        badges = (
            '<div class="flex items-center gap-2">'
            f'<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-tertiary-fixed '
            f'text-on-tertiary-fixed-variant font-mono-label text-mono-label">'
            f'<span class="material-symbols-outlined text-[14px]">lock</span>LOCKED {gs["locked_sealed"]} sealed</span>'
            f'<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-tertiary-fixed '
            f'text-on-tertiary-fixed-variant font-mono-label text-mono-label">'
            f'<span class="material-symbols-outlined text-[14px]">lock</span>CHALLENGE {gs["challenge_sealed"]} sealed</span></div>'
        )
        note = '<div class="font-body-sm text-body-sm text-on-surface-variant mt-2">누수 방지(§12): sealed는 Phase 3 최종 1회.</div>'
    return (
        '<div class="bg-surface-container-lowest rounded-xl border border-outline-variant/30 p-6">'
        '<div class="flex items-center gap-2 mb-3"><span class="material-symbols-outlined text-secondary">dataset</span>'
        f'<h4 class="font-h3 text-h3">6b. Gold Set ({esc(gs["version"])} · {gs["total"]}문항)</h4></div>'
        f'{headline}<div class="flex flex-col gap-1 mb-3">{rows}</div>{badges}{note}</div>'
    )


def _assurance_card(report: ValidationReport) -> str:
    items = []
    for d in report.assurance_dimensions:
        if d.measured:
            val = f'<span class="font-mono-data text-mono-data text-secondary font-semibold">{esc(d.value)}</span>'
            badge = '<span class="material-symbols-outlined text-[16px] text-secondary">check_circle</span>'
        else:
            val = '<span class="font-body-sm text-body-sm text-outline">미측정</span>'
            badge = ('<span class="inline-flex px-1.5 py-0.5 rounded-full bg-tertiary-fixed '
                     'text-on-tertiary-fixed-variant font-mono-label text-mono-label">실측 대기</span>')
        items.append(
            '<div class="flex items-center justify-between gap-2 font-body-sm text-body-sm py-1">'
            f'<span>{esc(d.label)}</span><span class="flex items-center gap-2">{val}{badge}</span></div>'
        )
    return (
        '<div class="bg-surface-container-lowest rounded-xl border border-outline-variant/30 p-6">'
        '<div class="flex items-center gap-2 mb-3"><span class="material-symbols-outlined text-secondary">verified_user</span>'
        '<h4 class="font-h3 text-h3">7. Assurance (4 DEEP)</h4></div>'
        f'<div class="flex flex-col divide-y divide-outline-variant/20">{"".join(items)}</div></div>'
    )


def _human_review(report: ValidationReport) -> str:
    escs = "".join(
        '<div class="flex items-start gap-2 mb-2">'
        f'{mono_chip(e.reason_code, "bg-error-container text-on-error-container")}'
        f'<span class="font-body-sm text-body-sm text-on-surface-variant">{esc(e.description)}</span></div>'
        for e in report.escalations
    ) or '<div class="font-body-sm text-body-sm text-on-surface-variant">escalation 없음</div>'
    return (
        '<div class="bg-surface-container-lowest rounded-xl border border-outline-variant/30 p-6">'
        '<div class="flex items-center gap-2 mb-3"><span class="material-symbols-outlined text-error">gavel</span>'
        f'<h4 class="font-h3 text-h3">8. Human Review</h4></div>'
        f'<div class="font-mono-label text-mono-label text-on-surface-variant mb-3">승인상태 '
        f'{esc(report.approval_status.value)}</div>{escs}</div>'
    )


def _main(report: ValidationReport) -> str:
    subtitle = (
        '6·30 시나리오가 Source Snapshot → Policy Version → RegChange → Impact Matrix → '
        'Rule Change Proposal → Test/Regression → Assurance → Human Review 로 End-to-End 완결된 '
        '감사추적 보고서. 값은 gold·엔진·회귀 실제 산출물에서 유도.'
    )
    prov = provenance_strip([
        f"steps={len(report.steps)}",
        f"overall={report.overall_status}",
        f"regression={report.regression['passed']}/{report.regression['total']}",
        f"escalations={len(report.escalations)}",
    ], engine_label="ValidationReport (E2E)")
    header = (
        '<div class="flex items-center gap-3 mb-2">'
        f'<span class="font-body-md text-on-surface-variant">전체 판정</span>{_status_badge(report.overall_status)}</div>'
    )
    grid = (
        '<div class="grid grid-cols-1 md:grid-cols-2 gap-4">'
        + _sources(report) + _proposal_card(report)
        + _regression_card(report) + _gold_set_card(report)
        + _assurance_card(report)
        + "</div>"
    )
    return (
        title_block("검증 보고서 (Validation Report)", subtitle)
        + header + prov
        + _pipeline(report)
        + grid
        + _human_review(report)
    )


def render(report: ValidationReport | None = None) -> str:
    report = report if report is not None else build_validation_report()
    return page("audit-trail", _main(report))
