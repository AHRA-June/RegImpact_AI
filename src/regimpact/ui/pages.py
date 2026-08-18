"""화면 5개 — 전부 **엔진·추출기·회귀의 실제 출력**에서 렌더된다.

Stitch 1차 산출물(2026-08-10)은 디자인은 훌륭했으나 데이터를 환각했다(지역을 세종·부산·강남으로,
LTV 60→50 등). 그래서 디자인은 `theme.py`로 보존하고, 화면에 찍히는 값은 여기서 전부
실제 객체에서 뽑는다. 리터럴 도메인 수치를 이 파일에 적지 않는 것이 규칙이며,
`tests/test_ui.py`가 그것을 강제한다(UI grounding).
"""
from __future__ import annotations

from ..extractor.evaluate import GoldReport, GroundingReport
from ..extractor.schema import RegChangeExtraction
from ..grandfathering import CUTOFF
from ..impact.builder import derive_rule_diff
from ..impact.customer import CustomerImpactReport, Segment
from ..impact.schema import ImpactMatrix, Phase
from ..tc_generator.regression import RegressionReport
from .theme import (
    bar,
    card,
    chip,
    esc,
    icon,
    page,
    page_title,
    stat,
    table,
)

SCENARIO = "2026-06-30 규제지역 추가 지정"


def _pct(v) -> str:
    return "기준없음" if v is None else f"{v:.0%}"


def _won(amount: int) -> str:
    sign = "-" if amount < 0 else ""
    a = abs(amount)
    if a >= 10_000_000_000:
        return f"{sign}{a / 100_000_000:,.0f}억원"
    if a >= 100_000_000:
        return f"{sign}{a / 100_000_000:.2f}억원"
    return f"{sign}{a:,}원"


def _grounded_set(grounding: GroundingReport | None) -> set:
    if grounding is None:
        return set()
    return {(u.citation.source_doc_id, u.citation.quote) for u in grounding.ungrounded}


# ------------------------------------------------------------------ 1. 규제 변경 분석

def regchange_page(
    extraction: RegChangeExtraction, grounding: GroundingReport, scored: GoldReport
) -> str:
    ungrounded = _grounded_set(grounding)

    stats = (
        '<div class="grid grid-cols-4 gap-4">'
        + stat("추출된 변경", f"{len(extraction.changes)}건",
               sub=f"시행일 {extraction.effective_from}")
        + stat("Citation Correctness", f"{grounding.citation_correctness:.0%}",
               tone="good" if grounding.citation_correctness == 1.0 else "warn",
               sub=f"{grounding.grounded}/{grounding.total} 원문 verbatim 확인")
        + stat("Unsupported Claim Rate", f"{grounding.unsupported_claim_rate:.0%}",
               tone="good" if grounding.unsupported_claim_rate == 0 else "bad",
               sub="원문에 없는 인용 = 환각 신호")
        + stat("신규 규제지역", f"{len(extraction.target_regions)}곳",
               sub=", ".join(extraction.target_regions))
        + "</div>"
    )

    rows = []
    for c in extraction.changes:
        key = (c.citation.source_doc_id, c.citation.quote)
        ok = key not in ungrounded
        ba = (
            f'{chip(c.before or "—", mono=True)} <span class="text-on-surface-variant">→</span> '
            f'{chip(c.after or "—", tone="primary", mono=True)}'
            if (c.before or c.after) else '<span class="text-on-surface-variant">—</span>'
        )
        quote = " ".join(c.citation.quote.split())
        rows.append([
            chip(c.category, tone="primary", mono=True),
            f'<div class="font-medium">{esc(c.summary)}</div>',
            ba,
            f'<div class="flex flex-col gap-1">'
            f'{chip(c.citation.source_doc_id, mono=True)}'
            f'<div class="text-body-sm text-on-surface-variant max-w-md">'
            f'{"✓" if ok else "⚠"} “{esc(quote[:110])}{"…" if len(quote) > 110 else ""}”</div></div>',
            chip(f"{c.confidence:.2f}", tone="good" if c.confidence >= 0.9 else "warn", mono=True),
        ])

    gold_rows = [
        ["Change Completeness", f"{scored.change_completeness:.0%}",
         ", ".join(scored.missed_changes) or "—"],
        ["Exception Recall", f"{scored.exception_recall:.0%}",
         ", ".join(scored.missed_exceptions) or "—"],
        ["Effective-date", "OK" if scored.effective_date_correct else "MISS", "—"],
        ["Regions", "OK" if scored.regions_correct else "MISS", "—"],
    ]

    body = (
        page_title(
            "규제 변경 분석",
            "공문 원문에서 추출한 Before/After 변경사항과 그 근거 인용. "
            "모든 인용은 원문 verbatim 대조를 거쳤고, 대조에 실패한 인용은 ⚠로 표시된다.",
        )
        + stats
        + card(
            "추출된 변경사항",
            table(["카테고리", "변경 내용", "Before → After", "근거 (원문 인용)", "신뢰도"], rows),
            note="근거 열의 ✓ = 원문에서 그대로 확인됨 / ⚠ = 원문 미확인",
        )
        + card(
            "골드 정답지 대조",
            table(
                ["지표", "값", "놓친 항목"],
                [[esc(a), chip(b, tone="good" if b in ("OK", "100%") else "warn"), esc(c)]
                 for a, b, c in gold_rows],
            ),
            note="사람이 확정한 골드 정답지(docs/eval/regchange_gold_6_30.json) 기준",
        )
    )
    return page(title="규제 변경 분석", active="regchange.html", scenario=SCENARIO,
                status="검토 필요", body=body)


# ------------------------------------------------------------------ 2. 임팩트 매트릭스

_PHASE_ID = {Phase.D_MINUS: "d-minus", Phase.POST: "post", Phase.SEPARATE_TRIGGER: "trigger"}
_PRIORITY_TONE = {"필수": "bad", "회귀": "warn", "검토": "neutral"}


def impact_matrix_page(matrix: ImpactMatrix) -> str:
    stats = (
        '<div class="grid grid-cols-4 gap-4">'
        + stat("매트릭스 행", f"{len(matrix.rows)}행",
               sub=f"D-day 전 필수 {len(matrix.d_minus_required)}건")
        + stat("자동처리 가능", f"{matrix.automation_rate:.0%}",
               tone="good", sub=f"Human Review {len(matrix.human_review_rows)}행")
        + stat("시행일", f"{matrix.effective_from}", sub="이 날짜 전에 D-day 전 행이 끝나야 한다")
        + stat("대상 지역", f"{len(matrix.target_regions)}곳", sub=", ".join(matrix.target_regions))
        + "</div>"
    )

    tabs, panels = [], []
    for i, phase in enumerate(Phase):
        rows = matrix.by_phase(phase)
        if not rows:
            continue
        pid = _PHASE_ID[phase]
        active = "bg-primary text-on-primary shadow-sm" if i == 0 else \
                 "bg-surface-container-high text-on-surface-variant hover:bg-surface-container-highest"
        tabs.append(
            f'<button data-phase="{pid}" class="phase-tab px-6 py-2 rounded-full '
            f'font-body-md text-body-md font-semibold transition-all {active}">'
            f"{esc(phase.value)} ({len(rows)})</button>"
        )

        core = [r for r in rows if not r.area.startswith("[Discovery]")]
        disc = [r for r in rows if r.area.startswith("[Discovery]")]
        panel = table(
            ["업무영역", "변경 내용", "근거", "영향 대상", "산출물", "우선순위", "담당", "승인상태", "자동"],
            [_matrix_row(r) for r in core],
            align_center=(5, 6, 7, 8),
        )
        if disc:
            panel += (
                '<div class="mt-6 border-t border-outline-variant/40 pt-6">'
                '<div class="flex items-center gap-2 mb-3">'
                + icon("travel_explore", 18)
                + '<span class="font-h3 text-h3 text-on-background">Discovery Scope</span>'
                '<span class="text-body-sm text-on-surface-variant">'
                "영향은 표시하되 코어 룰엔진에서 자동판정하지 않는다 (브리프 §24-12)</span></div>"
                + table(["항목", "변경 내용", "근거", "영향 대상", "처리"],
                        [_discovery_row(r) for r in disc])
                + "</div>"
            )
        panels.append(
            f'<div class="phase-panel flex flex-col gap-4" data-phase="{pid}"'
            f'{"" if i == 0 else " hidden"}>{panel}</div>'
        )

    hr_list = "".join(
        f'<li class="flex gap-3 py-2 border-b border-outline-variant/30 last:border-0">'
        f'{chip(r.area, tone="warn")}'
        f'<span class="text-body-sm text-on-surface-variant">{esc(r.human_review_reason)}</span></li>'
        for r in matrix.human_review_rows
    )

    body = (
        page_title(
            "임팩트 매트릭스",
            "규제 변경을 업무영역별로 전개한다. 시간축(Phase)이 이 매트릭스의 핵심 — "
            "일은 시행일 전 / 시행 후 / 별도 트리거 세 물결로 온다.",
        )
        + stats
        + '<div class="flex gap-4">' + "".join(tabs) + "</div>"
        + "".join(panels)
        + card(
            f"Human Review 필요 ({len(matrix.human_review_rows)}행)",
            f'<ul class="flex flex-col">{hr_list}</ul>',
            note="자동처리 불가 행은 사유가 반드시 명시된다",
        )
        + f'<div class="text-body-sm text-on-surface-variant font-mono-label text-mono-label">'
          f"generated_from: {esc(matrix.generated_from)}</div>"
    )
    script = (
        "<script>document.querySelectorAll('.phase-tab').forEach(function(t){"
        "t.addEventListener('click',function(){"
        "document.querySelectorAll('.phase-tab').forEach(function(x){"
        "x.className=x.className.replace('bg-primary text-on-primary shadow-sm',"
        "'bg-surface-container-high text-on-surface-variant hover:bg-surface-container-highest');});"
        "t.className=t.className.replace('bg-surface-container-high text-on-surface-variant "
        "hover:bg-surface-container-highest','bg-primary text-on-primary shadow-sm');"
        "document.querySelectorAll('.phase-panel').forEach(function(p){"
        "p.hidden=(p.dataset.phase!==t.dataset.phase);});});});</script>"
    )
    return page(title="임팩트 매트릭스", active="impact_matrix.html", scenario=SCENARIO,
                status="검토 필요", body=body, extra_script=script)


def _evidence_html(row) -> str:
    if not row.evidence:
        return '<span class="text-on-surface-variant">—</span>'
    parts = []
    for e in row.evidence[:2]:
        flat = " ".join(e.quote.split())
        mark = "" if e.grounded is None else ("✓ " if e.grounded else "⚠ ")
        parts.append(
            f'<div class="flex flex-col gap-1 mb-2">{chip(e.source_doc_id, mono=True)}'
            f'<span class="text-body-sm text-on-surface-variant max-w-xs">'
            f'{mark}“{esc(flat[:70])}{"…" if len(flat) > 70 else ""}”</span></div>'
        )
    return "".join(parts)


def _matrix_row(r) -> list[str]:
    return [
        f'<div class="font-semibold text-secondary">{esc(r.area)}</div>',
        f'<div class="max-w-md">{esc(r.change)}</div>',
        _evidence_html(r),
        f'<div class="text-body-sm max-w-xs">{esc(r.affected)}</div>',
        f'<div class="text-body-sm max-w-xs">{esc(r.deliverable)}</div>',
        chip(r.priority.value, tone=_PRIORITY_TONE.get(r.priority.value, "neutral")),
        chip(r.owner.value),
        chip(r.approval_status.value, tone="warn"),
        chip("🤖 자동" if r.automatable else "🖐 사람",
             tone="good" if r.automatable else "warn"),
    ]


def _discovery_row(r) -> list[str]:
    return [
        chip(r.area.replace("[Discovery] ", ""), tone="primary"),
        f'<div class="max-w-md">{esc(r.change)}</div>',
        _evidence_html(r),
        f'<div class="text-body-sm max-w-xs">{esc(r.affected)}</div>',
        f'<div class="text-body-sm text-on-surface-variant max-w-xs">{esc(r.human_review_reason)}</div>',
    ]


# ------------------------------------------------------------------ 3. Rule 변경안

def rule_page(extraction: RegChangeExtraction, regression: RegressionReport) -> str:
    diff = derive_rule_diff()
    changed = [d for d in diff if d["before"] != d["after"]]

    banner = (
        '<div class="flex items-start gap-3 bg-primary-fixed/60 border border-primary-fixed '
        'rounded-xl p-5">'
        + icon("gavel", 22)
        + '<div class="flex flex-col gap-1"><div class="font-h3 text-h3 text-on-primary-fixed">'
        "LLM은 실행 룰을 생성하지 않습니다</div>"
        '<div class="text-body-md text-on-primary-fixed-variant max-w-3xl">'
        "아래 변경안의 값은 사람이 확정한 규칙 명세(05_RULE_SPEC)의 구현인 deterministic "
        "룰엔진 상수에서 <b>읽어온 것</b>입니다. LLM은 공문에서 변경을 <b>탐지</b>할 뿐 "
        "규칙 로직을 만들지 않습니다 (LOCKED §4).</div></div></div>"
    )

    rows = []
    for d in diff:
        moved = d["before"] != d["after"]
        rows.append([
            chip(d["rule_id"], tone="primary", mono=True),
            esc(d["condition"]),
            chip(_pct(d["before"]), mono=True),
            chip(_pct(d["after"]), tone="bad" if moved else "neutral", mono=True),
            chip("변경" if moved else "좌동", tone="warn" if moved else "good"),
        ])

    regions = ", ".join(f'"{r}"' for r in extraction.target_regions)
    code = (
        "# 적용 시점: {eff} 부터\n"
        "REGULATED_REGIONS = [{regions}]\n"
        "GRANDFATHERING_CUTOFF = \"{cutoff}\"   # 이 날짜까지(<=) 접수·계약 → 종전규정\n\n"
        "def max_ltv(app):\n"
        "    if is_grandfathered(app, application_date <= GRANDFATHERING_CUTOFF):\n"
        "        return {baseline}          # 종전규정 유지\n"
        "    if region_status(app) != REGULATED:\n"
        "        return {baseline}\n"
        "    if app.house_count >= 2:       return {multi}   # 다주택\n"
        "    if app.is_owner:               return {owner}   # 유주택(비처분)\n"
        "    if app.first_home_buyer:       return {first}   # 생애최초 (좌동)\n"
        "    if app.real_demand:            return {real}    # 서민·실수요자\n"
        "    return {std}                   # 무주택 일반\n"
    ).format(
        eff=extraction.effective_from,
        regions=regions,
        cutoff=CUTOFF.isoformat(),
        baseline=f'{diff[0]["before"]:.2f}',
        multi=f'{[d for d in diff if d["rule_id"] == "MULTI_0"][0]["after"]:.2f}',
        owner=f'{[d for d in diff if d["rule_id"] == "REG_OWNER_0"][0]["after"]:.2f}',
        first=f'{[d for d in diff if d["rule_id"] == "REG_FIRSTHOME"][0]["after"]:.2f}',
        real=f'{[d for d in diff if d["rule_id"] == "REG_REALDEMAND"][0]["after"]:.2f}',
        std=f'{[d for d in diff if d["rule_id"] == "REG_STD"][0]["after"]:.2f}',
    )

    steps = ("AI 초안 생성", "정책부서 검토", "위원회 승인", "전산 반영")
    stepper = '<div class="flex items-center gap-2">'
    for i, s in enumerate(steps):
        done = i == 0
        stepper += (
            f'<div class="flex items-center gap-2">'
            f'<div class="w-7 h-7 rounded-full flex items-center justify-center text-body-sm '
            f'font-semibold {"bg-secondary text-on-secondary" if done else "bg-surface-container-high text-on-surface-variant"}">'
            f"{i + 1}</div>"
            f'<span class="text-body-sm {"font-semibold" if done else "text-on-surface-variant"}">{esc(s)}</span></div>'
        )
        if i < len(steps) - 1:
            stepper += '<div class="w-8 h-px bg-outline-variant"></div>'
    stepper += "</div>"

    body = (
        page_title(
            "Rule 변경안",
            "규제 변경을 여신 심사 룰의 구조화된 diff로 전개한다. "
            "값은 확정 명세의 구현(룰엔진 상수)에서 읽어오므로, 명세가 바뀌면 이 화면도 따라간다.",
        )
        + banner
        + '<div class="grid grid-cols-3 gap-4">'
        + stat("전체 룰", f"{len(diff)}건", sub="주택구입목적 LTV 경로")
        + stat("변경 룰", f"{len(changed)}건", tone="warn", sub="나머지는 좌동")
        + stat("회귀 검증", f"{regression.pass_rate:.0%}",
               tone="good" if regression.pass_rate == 1.0 else "bad",
               sub=f"{regression.total}케이스 · 실패 {len(regression.failures)}건")
        + "</div>"
        + card("Rule diff", table(["rule_id", "적용 조건", "Before", "After", ""], rows,
                                  align_center=(2, 3, 4)))
        + card(
            "적용 후 판정 로직 (AFTER)",
            '<pre class="bg-inverse-surface text-inverse-on-surface rounded-xl p-5 '
            'overflow-x-auto font-mono-data text-mono-data leading-6">'
            f"{esc(code)}</pre>",
            note="엔진 상수·지역코드·컷오프에서 생성됨 — 손으로 쓴 값 없음",
        )
        + card("승인 절차", stepper, note="현재 단계: AI 초안 생성 완료 → 사람 검토 대기")
    )
    return page(title="Rule 변경안", active="rule.html", scenario=SCENARIO,
                status="승인 대기", body=body)


# ------------------------------------------------------------------ 4. 검증 (Assurance)

def assurance_page(
    grounding: GroundingReport,
    scored: GoldReport,
    regression: RegressionReport,
    matrix: ImpactMatrix,
    impact: CustomerImpactReport,
) -> str:
    cards = (
        '<div class="grid grid-cols-4 gap-4">'
        + stat("Citation Correctness", f"{grounding.citation_correctness:.0%}",
               tone="good" if grounding.citation_correctness == 1.0 else "warn",
               sub="인용의 원문 verbatim 일치율")
        + stat("Unsupported Claim Rate", f"{grounding.unsupported_claim_rate:.0%}",
               tone="good" if grounding.unsupported_claim_rate == 0 else "bad",
               sub="원문 근거 없는 주장 비율")
        + stat("Exception Recall", f"{scored.exception_recall:.0%}",
               tone="good" if scored.exception_recall == 1.0 else "bad",
               sub="★ high-risk — 예외 누락은 오판정으로 직결")
        + stat("Rule-regression", f"{regression.pass_rate:.0%}",
               tone="good" if regression.pass_rate == 1.0 else "bad",
               sub=f"{regression.total}케이스 · 독립 오라클 대조")
        + "</div>"
    )

    metric_rows = [
        ["Citation Correctness", f"{grounding.citation_correctness:.0%}", "TBD", "중",
         f"{grounding.grounded}/{grounding.total} 인용 원문 확인"],
        ["Unsupported Claim Rate", f"{grounding.unsupported_claim_rate:.0%}", "TBD", "중",
         f"미확인 인용 {len(grounding.ungrounded)}건"],
        ["Change Completeness", f"{scored.change_completeness:.0%}", "TBD", "놓침=위험",
         ", ".join(scored.missed_changes) or "놓친 변경 없음"],
        ["Exception Recall", f"{scored.exception_recall:.0%}", "TBD", "★ 높음",
         f"놓친 예외: {', '.join(scored.missed_exceptions) or '없음'}"],
        ["Effective-date Accuracy", "OK" if scored.effective_date_correct else "MISS",
         "TBD", "★ 높음", "골드 시행일과 일치" if scored.effective_date_correct else "불일치"],
        ["Rule-regression Pass Rate", f"{regression.pass_rate:.0%}", "100% 목표", "★ 높음",
         f"실패 {len(regression.failures)}건"],
    ]
    cat_rows = [
        [esc(cat), f"{p}/{t}", chip(f"{rate:.0%}", tone="good" if rate == 1.0 else "bad")]
        for cat, (p, t, rate) in regression.pass_rate_by_category().items()
    ]

    escalations = []
    for name in scored.missed_exceptions:
        escalations.append((
            "Exception Recall", f"골드 예외 '{name}' 미포착",
            "추출기가 문서 간 축약된 열거를 병합했다. 사람이 원문 대조로 보완해야 한다.",
        ))
    for u in grounding.ungrounded:
        escalations.append((
            "Citation", f"원문 미확인 인용 — {u.summary}",
            "인용문이 원문에 verbatim으로 존재하지 않는다(환각 가능). 원문 직접 확인 필요.",
        ))
    if impact.undecidable_count:
        escalations.append((
            "Rule Coverage",
            f"시행일 LTV 판정 불가 {impact.undecidable_count:,}건 "
            f"(심사 판정 커버리지 {impact.decision_coverage:.1%})",
            "경과규정 해당 유주택·비수도권 유주택 등 종전 기준값이 원문에 없는 구간. "
            "추정 금지(LOCKED §4) → 사람 판단 필요.",
        ))
    if impact.impact_unknown_count:
        escalations.append((
            "Impact Coverage",
            f"판정은 됐으나 변화량 미상 {impact.impact_unknown_count:,}건 "
            f"(영향 측정 커버리지 {impact.impact_coverage:.1%})",
            "시행일 LTV는 확정(예: 규제지역 유주택 0%)이라 심사는 가능하다. 시행 전 非규제 "
            "기준값이 없어 '얼마나 줄었는가'만 계산되지 않는다 (Q10).",
        ))

    esc_html = "".join(
        f'<div class="flex gap-4 py-3 border-b border-outline-variant/30 last:border-0">'
        f'<div class="w-40 shrink-0">{chip(k, tone="bad")}</div>'
        f'<div class="flex flex-col gap-1"><div class="font-medium">{esc(what)}</div>'
        f'<div class="text-body-sm text-on-surface-variant">{esc(why)}</div></div></div>'
        for k, what, why in escalations
    ) or '<div class="text-body-sm text-on-surface-variant">escalation 없음</div>'

    body = (
        page_title(
            "검증 (Assurance)",
            "AI 출력이 틀리지 않았음을 증명하는 층. 지표는 LLM 자기채점이 아니라 "
            "원문 verbatim 대조·사람 확정 골드·독립 명세 오라클로 산출된다.",
        )
        + cards
        + card(
            "지표 현황",
            table(["지표", "실측값", "임계", "high-risk", "비고"],
                  [[esc(a), chip(b, tone="good" if b in ("OK", "100%", "0%") else "warn"),
                    chip(c, tone="warn" if c == "TBD" else "neutral"), esc(d), esc(e)]
                   for a, b, c, d, e in metric_rows],
                  align_center=(1, 2, 3)),
            note="임계값 TBD = docs/metrics_spec.md 미확정 — 정직하게 비워 둔다",
        )
        + card("Rule-regression 카테고리별", table(["카테고리", "통과/전체", "비율"], cat_rows,
                                                align_center=(1, 2)))
        + card(f"Escalation ({len(escalations)}건)", esc_html,
               note="자동으로 넘기지 않고 사람에게 올린 항목")
        + card(
            "검증 기준 고정",
            '<div class="flex flex-wrap gap-3">'
            + chip("골드: docs/eval/regchange_gold_6_30.json (사람 확정)", tone="primary")
            + chip(f"회귀: 독립 명세 오라클 {regression.total}케이스", tone="primary")
            + chip(f"매트릭스 Human Review {len(matrix.human_review_rows)}행", tone="warn")
            + chip("LOCKED TEST / CHALLENGE 미개봉", tone="good")
            + "</div>",
            note="튜닝 종료 전까지 LOCKED/CHALLENGE 셋은 열지 않는다 (브리프 §12)",
        )
    )
    return page(title="검증 (Assurance)", active="assurance.html", scenario=SCENARIO,
                status="검토 필요", body=body)


# ------------------------------------------------------------ 5. 고객·포트폴리오 영향

_SEGMENT_TONE = {
    Segment.REDUCED: "bad",
    Segment.NEEDS_HUMAN_REVIEW: "warn",
    Segment.IMPACT_UNKNOWN: "warn",
    Segment.GRANDFATHERED: "secondary",
    Segment.DISCOVERY: "muted",
    Segment.OUT_OF_SCOPE: "muted",
    Segment.UNAFFECTED: "primary",
}


def portfolio_page(impact: CustomerImpactReport) -> str:
    total = len(impact.impacts)
    worst = impact.worst_case

    cards = (
        '<div class="grid grid-cols-4 gap-4">'
        + stat("한도 감소 고객", f"{len(impact.reduced):,}건",
               tone="bad", sub=f"전체 {total:,}건 중 {impact.affected_rate:.1%}")
        + stat("총 한도 감소", _won(impact.total_limit_reduction),
               tone="bad", sub=f"건당 평균 {_won(impact.avg_limit_reduction)}")
        + stat("경과규정 보호", f"{impact.grandfathered_count:,}건",
               tone="good", sub="종전규정 유지 — 시행일 이후 신청해도 보호")
        + stat("심사 판정 커버리지", f"{impact.decision_coverage:.1%}",
               tone="good" if impact.decision_coverage >= 0.9 else "warn",
               sub=f"판정 불가 {impact.undecidable_count:,}건 — 유주택자도 코어 스코프 안")
        + "</div>"
    )

    seg_bars = "".join(
        bar(seg.value, impact.segment_counts[seg.value], total,
            tone=_SEGMENT_TONE[seg])
        for seg in Segment if impact.segment_counts[seg.value]
    )

    trans = impact.ltv_transitions
    max_t = max(trans.values()) if trans else 1
    trans_bars = "".join(
        bar(k, v, max_t, tone="bad" if "→ 0%" in k or "→ 40%" in k else "secondary")
        for k, v in trans.items()
    )

    esc_rows = [
        [chip(code, tone="warn", mono=True), f"{cnt:,}건",
         f"{cnt / impact.human_review_count:.0%}" if impact.human_review_count else "—"]
        for code, cnt in impact.escalation_reasons.items()
    ]

    # 대표 케이스: 세그먼트·판정근거 조합마다 실제 포트폴리오에서 1건씩
    seen, samples = set(), []
    for i in impact.impacts:
        key = (i.segment, tuple(i.after.reason_codes))
        if key in seen:
            continue
        seen.add(key)
        samples.append([
            chip(i.customer_id, mono=True),
            chip(i.region_code, tone="primary", mono=True),
            chip(i.segment.value, tone="bad" if i.segment == Segment.REDUCED else "neutral"),
            chip(_pct(i.before.max_ltv), mono=True),
            chip(_pct(i.after.max_ltv),
                 tone="bad" if (i.limit_delta or 0) < 0 else "neutral", mono=True),
            f'<span class="font-mono-data text-mono-data">'
            f'{"—(기준값 부재)" if i.limit_delta is None else _won(i.limit_delta)}</span>',
            " ".join(chip(rc, mono=True) for rc in i.after.reason_codes) or "—",
        ])
    samples = samples[:14]

    worst_html = (
        '<div class="text-body-md">해당 없음</div>' if worst is None else
        f'<div class="flex flex-wrap items-center gap-3">'
        f'{chip(worst.customer_id, mono=True)}{chip(worst.region_code, tone="primary", mono=True)}'
        f'<span>담보가액 {_won(worst.property_price)}</span>'
        f'<span>{_pct(worst.before.max_ltv)} → {_pct(worst.after.max_ltv)}</span>'
        f'{chip(_won(worst.limit_delta), tone="bad", mono=True)}</div>'
    )

    body = (
        page_title(
            "고객·포트폴리오 영향",
            f"합성 포트폴리오 {total:,}건을 시행 전일({impact.before_date})과 "
            f"시행일({impact.after_date}) 두 시점으로 deterministic 룰엔진에 태워 차이를 계산한 결과.",
        )
        + '<div class="flex items-start gap-3 bg-tertiary-fixed/30 border border-tertiary-fixed '
          'rounded-xl p-4">'
        + icon("science", 20)
        + '<div class="text-body-md text-on-tertiary-fixed-variant">'
          "이 포트폴리오는 <b>층화 합성 데이터</b>입니다(실 고객데이터 미사용 — 브리프 §0-8). "
          f"따라서 금액은 시장 추정치가 아니라 <b>이 조성에 확정 규칙을 적용한 계산 결과</b>이며, "
          f"seed={impact.seed} 로 완전히 재현됩니다.</div></div>"
        + cards
        + card(
            "커버리지 — 심사 판정 vs 영향 측정",
            '<div class="flex flex-col gap-3">'
            + bar("심사 판정 가능", int(round(impact.decision_coverage * 1000)), 1000,
                  tone="secondary", caption="시행일 LTV 확정")
            + bar("영향 측정 가능", int(round(impact.impact_coverage * 1000)), 1000,
                  tone="primary", caption="before/after 모두 확정")
            + "</div>",
            note=(
                f"둘의 차이 {impact.impact_unknown_count:,}건 = 심사는 되지만 시행 전 기준값이 "
                "없어 변화량만 계산되지 않는 구간 (Q10)"
            ),
        )
        + card("고객 세그먼트 분포", f'<div class="flex flex-col gap-3">{seg_bars}</div>')
        + card("LTV 전이 (Before → After)", f'<div class="flex flex-col gap-3">{trans_bars}</div>',
               note="“—” = 자동판정이 성립하지 않은 구간")
        + card("최대 영향 케이스", worst_html)
        + card(
            "자동판정 중단 사유",
            table(["reason_code", "건수", "비중"], esc_rows, align_center=(1, 2)),
            note="한 건이 여러 사유를 가질 수 있어 합계가 100%를 넘을 수 있다",
        )
        + card(
            "대표 케이스 (판정근거 조합별 실제 1건)",
            table(["고객", "지역", "세그먼트", "Before LTV", "After LTV", "한도 변화", "reason_codes"],
                  samples, align_center=(3, 4)),
            note="포트폴리오에서 실제로 뽑은 건 — 예시용으로 지어낸 행이 아니다",
        )
    )
    return page(title="고객·포트폴리오 영향", active="portfolio.html", scenario=SCENARIO,
                status="검토 필요", body=body)
