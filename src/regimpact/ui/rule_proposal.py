"""Rule 변경안 화면 (data-path=rule-amendments) — 구조화 RuleChangeProposal 렌더.

Stitch 목업(rule)의 환각(대상지역 "세종/부산 해운대", 경과규정 부등호 반대, 가상 "약 1,240건",
실명 검토자)을 구조화 제안 객체(`regimpact.proposal.RuleChangeProposal`)로 대체한다. 제안은
룰엔진 상수·regions·경과규정·Impact Matrix에서 유도되며 화면에서 값을 지어내지 않는다.

거버넌스: LLM은 실행 코드를 직접 수정하지 않는다. 이 화면은 '제안(diff)'이며 사람 승인 후
deterministic rule registry에 반영된다.
"""
from __future__ import annotations

from ..proposal import RuleChangeProposal, build_rule_change_proposal, render_rule_dsl
from .chrome import esc, mono_chip, page, provenance_strip, title_block


def _code_block(title: str, lines: list[str], tone: str, icon: str) -> str:
    numbered = "".join(
        f'<div class="flex"><span class="w-8 shrink-0 text-outline text-right pr-3 select-none">{i}</span>'
        f'<span class="whitespace-pre-wrap">{esc(line)}</span></div>'
        for i, line in enumerate(lines, 1)
    )
    return (
        f'<div class="rounded-lg border border-outline-variant/30 overflow-hidden">'
        f'<div class="flex items-center gap-2 px-4 py-2 {tone} font-mono-label text-mono-label">'
        f'<span class="material-symbols-outlined text-[16px]">{icon}</span>{esc(title)}</div>'
        f'<div class="bg-surface-container-lowest p-4 font-mono-data text-mono-data text-on-surface">{numbered}</div>'
        f"</div>"
    )


def _diff_section(proposal: RuleChangeProposal) -> str:
    before, after = render_rule_dsl(proposal)
    return (
        '<div class="grid grid-cols-1 lg:grid-cols-2 gap-4">'
        + _code_block("BEFORE (비규제 기준선)", before,
                      "bg-error-container/40 text-on-error-container", "remove_circle")
        + _code_block(f"AFTER (Proposed · {proposal.rule_id})", after,
                      "bg-secondary-container text-on-secondary", "add_circle")
        + "</div>"
    )


def _parameter_table(proposal: RuleChangeProposal) -> str:
    rows = []
    for pc in proposal.parameter_changes:
        badge = (
            '<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-error-container '
            'text-on-error-container font-mono-label text-mono-label">변경</span>'
            if pc.changed else
            '<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-surface-variant '
            'text-on-surface-variant font-mono-label text-mono-label">유지</span>'
        )
        before = (f'<span class="font-mono-data text-mono-data">{pc.before_label}</span>'
                  if pc.before is not None else
                  '<span class="font-body-sm text-body-sm italic text-outline">명세부재</span>')
        rows.append(
            '<tr class="hover:bg-surface-container-low/50">'
            f'<td class="p-3 font-semibold whitespace-nowrap">{esc(pc.tier)}</td>'
            f'<td class="p-3 text-right">{before}</td>'
            f'<td class="p-3 text-right font-mono-data text-mono-data font-semibold">{esc(pc.after_label)}</td>'
            f'<td class="p-3 text-center">{badge}</td>'
            f'<td class="p-3">{mono_chip(pc.reason_code)}</td>'
            f'<td class="p-3 font-body-sm text-body-sm text-on-surface-variant">{esc(pc.note)}</td></tr>'
        )
    return (
        '<div class="w-full overflow-x-auto bg-surface-container-lowest rounded-xl border border-outline-variant/30">'
        '<table class="w-full text-left border-collapse">'
        '<thead class="bg-surface-container-low font-body-sm text-body-sm text-on-surface-variant">'
        '<tr><th class="p-3 font-semibold">차주 계층</th><th class="p-3 font-semibold text-right">종전</th>'
        '<th class="p-3 font-semibold text-right">변경</th><th class="p-3 font-semibold text-center">상태</th>'
        '<th class="p-3 font-semibold">근거코드</th><th class="p-3 font-semibold">비고</th></tr></thead>'
        f'<tbody class="divide-y divide-outline-variant/30 font-body-md text-body-md">{"".join(rows)}</tbody>'
        "</table></div>"
    )


def _impact_summary(proposal: RuleChangeProposal) -> str:
    s = proposal.impact_summary
    regions = ", ".join(proposal.target_region_labels)
    items = [
        f'신규 규제지역 {len(proposal.target_regions)}곳({regions}) · 시행일 {proposal.effective_date.isoformat()}',
        f'경과규정 컷오프 {proposal.grandfathering_cutoff.isoformat()}까지 접수/계약 → 종전규정 유지',
        f'영향 세그먼트: 하향 {s["DOWNGRADE"]} + 신규 제한 {s["NEW_RESTRICTION"]} = {proposal.impacted_segment_count}건 '
        f'(경과규정 보호 {s["GRANDFATHERED"]}건, Discovery {s["DISCOVERY"]}건 별도)',
        f'근거 정책: {", ".join(proposal.source_policy_ids)}',
    ]
    lis = "".join(
        '<li class="flex items-start gap-2">'
        '<span class="material-symbols-outlined text-[18px] text-secondary">chevron_right</span>'
        f"<span>{esc(x)}</span></li>"
        for x in items
    )
    return (
        '<div class="bg-surface-container-lowest rounded-xl border border-outline-variant/30 p-6">'
        '<div class="flex items-center gap-2 mb-3">'
        '<span class="material-symbols-outlined text-secondary">insights</span>'
        '<h3 class="font-h3 text-h3">영향 분석 요약 (Impact Matrix 실측)</h3></div>'
        f'<ul class="flex flex-col gap-2 font-body-md text-body-md text-on-surface">{lis}</ul></div>'
    )


def _governance(proposal: RuleChangeProposal) -> str:
    esc_cards = "".join(
        '<div class="flex items-center gap-2 mb-2">'
        + mono_chip(e.reason_code, "bg-error-container text-on-error-container")
        + f'</div><div class="font-body-sm text-body-sm text-on-surface-variant mb-3">{esc(e.description)}</div>'
        for e in proposal.escalations
    ) or '<div class="font-body-sm text-body-sm text-on-surface-variant">escalation 없음</div>'
    return (
        '<div class="grid grid-cols-1 md:grid-cols-2 gap-4">'
        '<div class="bg-surface-container-lowest rounded-xl border border-outline-variant/30 p-6">'
        '<div class="flex items-center gap-2 mb-4"><span class="material-symbols-outlined text-secondary">fact_check</span>'
        '<h3 class="font-h3 text-h3">Human Review</h3></div>'
        '<div class="flex items-center gap-3 mb-3">'
        '<span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-secondary-container '
        'text-on-secondary font-mono-label text-mono-label"><span class="material-symbols-outlined text-[16px]">check</span>Draft Generated</span>'
        f'<span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-tertiary-fixed '
        f'text-on-tertiary-fixed-variant font-mono-label text-mono-label">{esc(proposal.approval_status.value)}</span></div>'
        f'<div class="font-body-sm text-body-sm text-on-surface-variant">생성: {esc(proposal.generator)} · '
        'LLM은 실행 코드를 직접 수정하지 않으며, 승인 후에만 deterministic rule registry에 반영된다.</div></div>'
        '<div class="bg-surface-container-lowest rounded-xl border border-outline-variant/30 p-6">'
        '<div class="flex items-center gap-2 mb-4"><span class="material-symbols-outlined text-error">gavel</span>'
        f'<h3 class="font-h3 text-h3">Escalation</h3></div>{esc_cards}</div>'
        "</div>"
    )


def _main(proposal: RuleChangeProposal) -> str:
    subtitle = (
        f'<b>{esc(proposal.policy_event)}</b>에 따른 <span class="font-mono-label">{proposal.rule_id}</span> '
        '변경 제안. 구조화 제안 객체(파라미터 변경·대상·경과규정·근거·영향·escalation)는 룰엔진 상수·'
        'regions·Impact Matrix 실측에서 유도되며, 화면에서 값을 지어내지 않는다.'
    )
    banner = (
        '<div class="flex items-start gap-3 bg-secondary-container/30 border border-secondary/30 '
        'rounded-lg p-4 font-body-sm text-body-sm text-on-surface">'
        '<span class="material-symbols-outlined text-secondary">info</span>'
        '<span><b>LLM은 실행 코드를 직접 수정하지 않습니다.</b> 제안된 변경은 검토 후 결정론적 규칙 '
        '레지스트리에 안전하게 반영되며, 완전한 감사 추적을 유지합니다.</span></div>'
    )
    prov = provenance_strip([
        f"rule_id={proposal.rule_id}",
        f"params={len(proposal.parameter_changes)}",
        f"cutoff={proposal.grandfathering_cutoff.isoformat()}",
        f"status={proposal.approval_status.value}",
    ], engine_label="RuleChangeProposal (엔진 유도)")
    return (
        title_block("Rule 변경안", subtitle)
        + banner + prov
        + _diff_section(proposal)
        + '<div class="flex items-center gap-2 mt-2 mb-1">'
          '<span class="material-symbols-outlined text-secondary">tune</span>'
          '<h3 class="font-h3 text-h3">파라미터 변경 (LTV 계층별)</h3></div>'
        + _parameter_table(proposal)
        + _impact_summary(proposal)
        + _governance(proposal)
    )


def render(proposal: RuleChangeProposal | None = None) -> str:
    proposal = proposal if proposal is not None else build_rule_change_proposal()
    return page("rule-amendments", _main(proposal))
