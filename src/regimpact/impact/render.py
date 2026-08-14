"""Impact Matrix → HTML 렌더러 (UI를 엔진 출력의 '빌드 산출물'로 만든다).

목적: 임팩트 매트릭스 화면의 하드코딩(일부 환각) 값을 rule_engine 실제 출력으로 대체.
디자인 시스템(Stitch DESIGN.md)은 `templates/chrome_*.html`(기존 export에서 추출)로 그대로
보존하고, 표 본문·요약·Discovery 섹션만 `ImpactMatrix`에서 생성한다.

→ 값을 손으로 적지 않으므로 환각이 재발할 수 없다. 엔진이 단일 진실(single source of truth).
"""
from __future__ import annotations

import html
from datetime import date
from pathlib import Path

from ..models import EvaluationStatus
from .matrix import ImpactDirection, ImpactMatrix, ImpactRow, build_impact_matrix

_TPL_DIR = Path(__file__).resolve().parent / "templates"


def _chrome() -> tuple[str, str]:
    head = (_TPL_DIR / "chrome_head.html").read_text(encoding="utf-8")
    foot = (_TPL_DIR / "chrome_foot.html").read_text(encoding="utf-8")
    return head, foot


# 방향 → (라벨, badge Tailwind 클래스, dot 클래스). 디자인 상태색 팔레트 사용.
_DIRECTION_BADGE: dict[ImpactDirection, tuple[str, str, str]] = {
    ImpactDirection.DOWNGRADE: ("하향", "bg-error-container text-on-error-container", "bg-on-error-container"),
    ImpactDirection.NEW_RESTRICTION: ("신규 제한", "bg-error text-on-error", "bg-on-error"),
    ImpactDirection.UNCHANGED: ("유지", "bg-surface-variant text-on-surface-variant", "bg-on-surface-variant"),
    ImpactDirection.UPGRADE: ("상향", "bg-secondary-container text-on-secondary", "bg-on-secondary"),
    ImpactDirection.REVIEW: ("검토 필요", "bg-tertiary-fixed text-on-tertiary-fixed-variant", "bg-on-tertiary-fixed-variant"),
    ImpactDirection.DISCOVERY: ("Discovery", "bg-surface-variant text-on-surface-variant", "bg-on-surface-variant"),
}


def _esc(s: object) -> str:
    return html.escape(str(s))


def _direction_badge(direction: ImpactDirection) -> str:
    label, cls, dot = _DIRECTION_BADGE[direction]
    return (
        f'<span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full '
        f'{cls} font-mono-label text-mono-label">'
        f'<span class="w-1.5 h-1.5 rounded-full {dot}"></span>{_esc(label)}</span>'
    )


def _ltv_before(row: ImpactRow) -> str:
    if row.before_ltv is not None:
        return f'<span class="font-mono-data text-mono-data">{row.before_ltv:.0%}</span>'
    # 명세부재(정직 처리) — 지어내지 않음
    return (
        '<span class="font-body-sm text-body-sm italic text-outline" '
        'title="원문에 기준선 없음 → 사람 검토">명세부재</span>'
    )


def _ltv_after(row: ImpactRow) -> str:
    if row.after_ltv is None:
        word = {
            EvaluationStatus.DISCOVERY: "Discovery",
            EvaluationStatus.OUT_OF_SCOPE: "범위외",
            EvaluationStatus.NEEDS_HUMAN_REVIEW: "검토",
        }.get(row.after.status, "—")
        return f'<span class="font-body-sm text-body-sm text-on-surface-variant">{_esc(word)}</span>'

    main = f'<span class="font-mono-data text-mono-data font-semibold">{row.after_ltv:.0%}</span>'
    if row.counterfactual_ltv is not None:
        # 경과규정으로 종전규정 유지 — 보호가 없었다면 적용됐을 값을 함께 노출(거버넌스)
        main += (
            ' <span class="font-mono-label text-mono-label px-1.5 py-0.5 rounded '
            'bg-tertiary-fixed/40 text-on-tertiary-fixed-variant">종전유지</span>'
            f'<div class="font-body-sm text-body-sm text-outline mt-0.5">'
            f'미보호 시 {row.counterfactual_ltv:.0%}</div>'
        )
    return main


def _reason_chips(row: ImpactRow) -> str:
    if not row.reason_codes:
        return '<span class="text-outline">-</span>'
    chips = [
        f'<span class="font-mono-data text-mono-data bg-surface-variant '
        f'text-on-surface-variant px-2 py-1 rounded">{_esc(rc)}</span>'
        for rc in row.reason_codes
    ]
    return '<div class="flex flex-wrap gap-1.5">' + "".join(chips) + "</div>"


def _gf_cell(row: ImpactRow) -> str:
    if row.grandfathering_applied:
        return (
            '<span class="inline-flex items-center gap-1 font-mono-label text-mono-label '
            'text-on-tertiary-fixed-variant"><span class="material-symbols-outlined '
            'text-[16px]">history</span>해당</span>'
        )
    return '<span class="text-outline">미해당</span>'


def _core_row_html(row: ImpactRow) -> str:
    highlight = " bg-error/5" if row.direction == ImpactDirection.NEW_RESTRICTION else ""
    return (
        f'<tr class="hover:bg-surface-container-low/50 transition-colors{highlight}">'
        f'<td class="p-4 font-semibold text-secondary whitespace-nowrap">{_esc(row.region_label)}</td>'
        f'<td class="p-4 whitespace-nowrap">{_esc(row.borrower_type)}</td>'
        f'<td class="p-4 text-right">{_ltv_before(row)}</td>'
        f'<td class="p-4 text-right">{_ltv_after(row)}</td>'
        f'<td class="p-4 text-center">{_direction_badge(row.direction)}</td>'
        f'<td class="p-4 text-center">{_gf_cell(row)}</td>'
        f'<td class="p-4">{_reason_chips(row)}</td>'
        f"</tr>"
    )


def _summary_cards(matrix: ImpactMatrix) -> str:
    s = matrix.summary
    cards = [
        ("총 세그먼트", s["TOTAL"], "text-on-surface", "grid_view"),
        ("하향", s["DOWNGRADE"], "text-error", "trending_down"),
        ("신규 제한", s["NEW_RESTRICTION"], "text-error", "block"),
        ("경과규정 보호", s["GRANDFATHERED"], "text-on-tertiary-fixed-variant", "history"),
        ("Discovery", s["DISCOVERY"], "text-on-surface-variant", "search_insights"),
    ]
    out = ['<div class="grid grid-cols-2 md:grid-cols-5 gap-4">']
    for label, value, color, icon in cards:
        out.append(
            '<div class="bg-surface-container-lowest p-4 rounded-xl border border-outline-variant/30">'
            f'<div class="flex items-center gap-2 text-on-surface-variant mb-2">'
            f'<span class="material-symbols-outlined text-[18px]">{icon}</span>'
            f'<span class="font-body-sm text-body-sm">{_esc(label)}</span></div>'
            f'<div class="font-h2 text-h2 {color}">{value}</div></div>'
        )
    out.append("</div>")
    return "".join(out)


def _provenance(matrix: ImpactMatrix) -> str:
    """엔진 산출 근거 스트립 — '실제 엔진 출력'임을 시각적으로 못박는다."""
    return (
        '<div class="flex flex-wrap items-center gap-x-4 gap-y-1 font-mono-label text-mono-label '
        'text-on-surface-variant bg-surface-container-low px-4 py-2 rounded-lg '
        'border border-outline-variant/30">'
        '<span class="flex items-center gap-1.5 text-secondary">'
        '<span class="material-symbols-outlined text-[16px]">bolt</span>'
        'rule_engine v1 (deterministic)</span>'
        f'<span>before={matrix.before_date.isoformat()}</span>'
        f'<span>after={matrix.after_date.isoformat()}</span>'
        f'<span>rows={len(matrix.rows)}</span>'
        '<span class="text-outline">· 값은 손으로 적지 않고 엔진이 생성 (LOCKED §4)</span>'
        "</div>"
    )


def _discovery_section(matrix: ImpactMatrix) -> str:
    rows = matrix.discovery_rows
    if not rows:
        return ""
    cards = []
    for r in rows:
        cards.append(
            '<div class="bg-surface-container-lowest p-4 rounded-lg shadow-sm">'
            '<div class="flex justify-between items-start mb-2 gap-2">'
            f'<div class="font-body-lg text-body-lg font-semibold text-on-surface">{_esc(r.borrower_type)}</div>'
            f'{_reason_chips(r)}</div>'
            f'<div class="font-body-sm text-body-sm text-on-surface-variant">'
            f'{_esc(r.region_label)} · {_esc(r.note or "자동판정 제외 — 수동 정책검토 대상")}</div>'
            "</div>"
        )
    return (
        '<div class="mt-4 bg-surface-container-highest p-6 rounded-xl border border-dashed '
        'border-outline-variant">'
        '<div class="flex items-center gap-3 mb-2">'
        '<span class="material-symbols-outlined text-outline">search_insights</span>'
        '<h3 class="font-h3 text-h3 text-on-surface-variant">Discovery Scope — 자동판정 제외 · 수동 정책검토</h3></div>'
        '<p class="font-body-sm text-body-sm text-on-surface-variant mb-4 max-w-3xl">'
        '영향 범위는 넓게 발견하되, 자동판정은 신뢰 가능한 좁은 범위(Core)에서만 한다. '
        '아래 항목은 정책대출·비주택구입목적으로 deterministic 룰엔진이 판정하지 않는다.</p>'
        '<div class="grid grid-cols-1 md:grid-cols-2 gap-4">' + "".join(cards) + "</div></div>"
    )


def _main_content(matrix: ImpactMatrix) -> str:
    core_rows = "".join(_core_row_html(r) for r in matrix.core_rows)
    table = (
        '<div class="w-full overflow-x-auto bg-surface-container-lowest rounded-xl shadow-sm">'
        '<table class="w-full text-left border-collapse">'
        '<thead class="bg-surface-container-low font-body-md text-body-md text-on-surface-variant sticky top-0 z-10 shadow-sm">'
        "<tr>"
        '<th class="p-4 font-semibold whitespace-nowrap">지역</th>'
        '<th class="p-4 font-semibold whitespace-nowrap">차주 유형</th>'
        '<th class="p-4 font-semibold text-right whitespace-nowrap">기존 LTV</th>'
        '<th class="p-4 font-semibold text-right whitespace-nowrap">변경 LTV</th>'
        '<th class="p-4 font-semibold text-center">변화</th>'
        '<th class="p-4 font-semibold text-center whitespace-nowrap">경과규정</th>'
        '<th class="p-4 font-semibold">근거코드</th>'
        "</tr></thead>"
        f'<tbody class="font-body-md text-body-md text-on-surface divide-y divide-outline-variant/30">{core_rows}</tbody>'
        "</table></div>"
    )
    title = (
        '<div class="flex flex-col gap-3">'
        '<div class="font-h1 text-h1 text-on-background">임팩트 매트릭스</div>'
        '<div class="font-body-md text-body-md text-on-surface-variant max-w-3xl">'
        f'<b>{_esc(matrix.policy_event)}</b>에 따른 주택구입목적 주담대 LTV의 세그먼트별 '
        'Before/After 영향. 아래 표는 deterministic 룰엔진을 시행 전·후 두 시점에 실행해 산출한 '
        '실제 판정이며, 화면에 값을 하드코딩하지 않는다.</div></div>'
    )
    footer = (
        '<div class="font-body-sm text-body-sm text-on-surface-variant bg-surface-container-low '
        'px-4 py-3 rounded-lg border border-outline-variant/30">'
        '<b>정직성 원칙</b> · '
        '① 非규제 유주택 기준선은 원문에 없어 <span class="font-mono-label">명세부재→신규 제한</span>으로 표기(70→0 지어내지 않음) · '
        '② 정책대출·전세는 Discovery로 분리 · '
        '③ 경과규정은 종전규정 유지 + 미보호 시 값(counterfactual) 병기.</div>'
    )
    return (
        f'<div class="flex flex-col gap-3 mb-2">{title}</div>'
        f"{_provenance(matrix)}"
        f"{_summary_cards(matrix)}"
        f"{table}"
        f"{_discovery_section(matrix)}"
        f"{footer}"
    )


def render_impact_matrix_html(matrix: ImpactMatrix | None = None) -> str:
    """ImpactMatrix → 자기완결(self-contained) HTML 페이지 문자열."""
    matrix = matrix if matrix is not None else build_impact_matrix()
    head, foot = _chrome()
    return head + _main_content(matrix) + foot


def write_impact_matrix_html(path: str | Path, matrix: ImpactMatrix | None = None) -> Path:
    """렌더 결과를 파일로 저장하고 경로 반환."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_impact_matrix_html(matrix), encoding="utf-8")
    return out
