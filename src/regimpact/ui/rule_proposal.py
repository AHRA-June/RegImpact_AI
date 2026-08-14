"""Rule 변경안 화면 (data-path=rule-amendments) — 구조화 Rule Change Proposal 렌더.

Stitch 목업(rule)의 환각(대상지역 "세종/부산 해운대", 경과규정 부등호 반대 `>=`, 가상
"약 1,240건", 특정 실명 검토자)을 룰엔진 상수·regions·grandfathering cutoff·Impact Matrix
실제 카운트로 대체한다. AFTER 코드는 엔진 로직에서 유도(값을 손으로 적지 않음).

거버넌스: LLM은 실행 코드를 직접 수정하지 않는다. 이 화면은 '제안(diff)'이며 사람 승인 후
deterministic rule registry에 반영된다(브리프 §6, LOCKED §4).
"""
from __future__ import annotations

from ..grandfathering import CUTOFF
from ..impact import ImpactDirection, build_impact_matrix
from ..impact.segments import REGION_LABELS
from ..regions import _SIX_THIRTY_REGIONS, REG_EFFECTIVE
from ..rule_engine import (
    LTV_BASELINE,
    LTV_FIRST_HOME,
    LTV_REAL_DEMAND,
    LTV_REGULATED_STANDARD,
)
from .chrome import esc, mono_chip, page, provenance_strip, title_block

RULE_ID = "MORTGAGE_LTV_REGULATED_REGION"


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


def _before_lines() -> list[str]:
    return [
        'rule "MORTGAGE_LTV" {',
        "  when {",
        "    loan.purpose == HOME_PURCHASE",
        "    region.status == NON_REGULATED",
        "  }",
        "  then {",
        f"    set max_ltv = {LTV_BASELINE:.2f}   // 무주택 기준선",
        "  }",
        "}",
    ]


def _after_lines() -> list[str]:
    region_list = ", ".join(f'"{r}"' for r in _SIX_THIRTY_REGIONS)
    return [
        f'rule "{RULE_ID}" {{',
        "  when {",
        "    loan.purpose == HOME_PURCHASE",
        "    region.status == REGULATED",
        f"    // 신규 규제지역: {region_list}",
        f'    // 경과규정: application_date <= "{CUTOFF.isoformat()}" → 종전규정(0.70)',
        "    grandfathering.applies == false",
        "  }",
        "  then {",
        f"    set max_ltv = {LTV_REGULATED_STANDARD:.2f}   // 무주택 표준",
        f"    // 예외: first_home={LTV_FIRST_HOME:.2f}, real_demand={LTV_REAL_DEMAND:.2f}, owner=0.00",
        "  }",
        "}",
    ]


def _diff_section() -> str:
    return (
        '<div class="grid grid-cols-1 lg:grid-cols-2 gap-4">'
        + _code_block(f"BEFORE (비규제 기준선, LTV {LTV_BASELINE:.0%})",
                      _before_lines(), "bg-error-container/40 text-on-error-container", "remove_circle")
        + _code_block(f"AFTER (Proposed, 규제지역 LTV {LTV_REGULATED_STANDARD:.0%})",
                      _after_lines(), "bg-secondary-container text-on-secondary", "add_circle")
        + "</div>"
    )


def _impact_summary() -> str:
    matrix = build_impact_matrix()
    s = matrix.summary
    impacted = s["DOWNGRADE"] + s["NEW_RESTRICTION"]
    regions = ", ".join(REGION_LABELS.get(r, r) for r in _SIX_THIRTY_REGIONS)
    items = [
        f'신규 규제지역 {len(_SIX_THIRTY_REGIONS)}곳({regions}) LTV {LTV_BASELINE:.0%} → {LTV_REGULATED_STANDARD:.0%} 하향',
        f'시행일 {REG_EFFECTIVE.isoformat()} · 경과규정 컷오프 {CUTOFF.isoformat()}까지 접수/계약 → 종전규정 유지',
        f'영향 세그먼트: 하향 {s["DOWNGRADE"]} + 신규 제한 {s["NEW_RESTRICTION"]} = {impacted}건 '
        f'(경과규정 보호 {s["GRANDFATHERED"]}건, Discovery {s["DISCOVERY"]}건 별도)',
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


def _governance() -> str:
    """사람 승인 스텝퍼 + 에스컬레이션 (실명 미기재, 역할 기반)."""
    return (
        '<div class="grid grid-cols-1 md:grid-cols-2 gap-4">'
        # review status
        '<div class="bg-surface-container-lowest rounded-xl border border-outline-variant/30 p-6">'
        '<div class="flex items-center gap-2 mb-4"><span class="material-symbols-outlined text-secondary">fact_check</span>'
        '<h3 class="font-h3 text-h3">Human Review</h3></div>'
        '<div class="flex items-center gap-3 mb-3">'
        '<span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-secondary-container '
        'text-on-secondary font-mono-label text-mono-label"><span class="material-symbols-outlined text-[16px]">check</span>Draft Generated</span>'
        '<span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-tertiary-fixed '
        'text-on-tertiary-fixed-variant font-mono-label text-mono-label">Review Required</span></div>'
        '<div class="font-body-sm text-body-sm text-on-surface-variant">배정: Compliance Dept. (역할 기반) · '
        'LLM은 실행 코드를 직접 수정하지 않으며, 승인 후에만 deterministic rule registry에 반영된다.</div></div>'
        # escalation (엔진 실제 escalation 사유)
        '<div class="bg-surface-container-lowest rounded-xl border border-outline-variant/30 p-6">'
        '<div class="flex items-center gap-2 mb-4"><span class="material-symbols-outlined text-error">gavel</span>'
        '<h3 class="font-h3 text-h3">Escalation</h3></div>'
        '<div class="flex items-center gap-2 mb-2">'
        + mono_chip("OWNER_BASELINE_UNKNOWN", "bg-error-container text-on-error-container")
        + '</div><div class="font-body-sm text-body-sm text-on-surface-variant">非규제 유주택 기준선이 원문에 '
        '정의되지 않아 룰엔진이 자동판정하지 않고 사람 검토로 escalate. (지어낸 값으로 채우지 않음)</div></div>'
        "</div>"
    )


def _main() -> str:
    subtitle = (
        f'<b>2026-06-30 규제지역 추가 지정</b>에 따른 <span class="font-mono-label">{RULE_ID}</span> '
        '변경 제안. BEFORE/AFTER 규칙과 영향 요약은 룰엔진 상수·regions·경과규정 cutoff·Impact Matrix '
        '실측에서 유도되며, 화면에서 지역·수치를 지어내지 않는다.'
    )
    banner = (
        '<div class="flex items-start gap-3 bg-secondary-container/30 border border-secondary/30 '
        'rounded-lg p-4 font-body-sm text-body-sm text-on-surface">'
        '<span class="material-symbols-outlined text-secondary">info</span>'
        '<span><b>LLM은 실행 코드를 직접 수정하지 않습니다.</b> 제안된 변경은 검토 후 결정론적 규칙 '
        '레지스트리에 안전하게 반영되며, 완전한 감사 추적을 유지합니다.</span></div>'
    )
    prov = provenance_strip([
        f"rule_id={RULE_ID}",
        f"before_ltv={LTV_BASELINE:.2f}",
        f"after_ltv={LTV_REGULATED_STANDARD:.2f}",
        f"cutoff={CUTOFF.isoformat()}",
    ], engine_label="rule_engine v1 상수")
    return (
        title_block("Rule 변경안", subtitle)
        + banner
        + prov
        + _diff_section()
        + _impact_summary()
        + _governance()
    )


def render() -> str:
    return page("rule-amendments", _main())
