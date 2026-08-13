"""Impact Matrix → HTML 렌더 (데이터바인딩, 하드코딩 없음).

Stitch 목업(`docs/ui/stitch_export/_1`)의 하드코딩·환각값(예: "60%→50%")을 **룰엔진 실제
산출(`ImpactMatrix`)** 로 교체하기 위한 렌더러. 화면의 모든 수치·지역·시점·근거는
`analyze_impact(...)` 결과에서만 온다 → UI가 엔진과 항상 일치(single source of truth).

디자인 토큰은 `docs/ui/stitch_export/regimpact_ai/DESIGN.md`(Institutional Navy, Noto Sans,
JetBrains Mono, 상태색)를 CSS 변수로 인라인. 외부 스크립트 의존 없음(self-contained) —
브라우저에서 바로 열리고, 폰트는 실패해도 시스템 폰트로 우아하게 저하된다.
"""
from __future__ import annotations

import html
from datetime import date
from typing import Optional

from ..models import EvaluationStatus, LtvDecision
from .matrix import ImpactDirection, ImpactMatrix, ImpactRow

# 방향 → (라벨, 배지 CSS 클래스)
_DIRECTION_BADGE = {
    ImpactDirection.TIGHTENED: ("강화", "badge-error"),
    ImpactDirection.LOOSENED: ("완화", "badge-info"),
    ImpactDirection.UNCHANGED: ("동일", "badge-neutral"),
    ImpactDirection.REVIEW: ("검토 필요", "badge-warn"),
}

_STATUS_LABEL_KO = {
    EvaluationStatus.DECIDED: "확정",
    EvaluationStatus.OUT_OF_SCOPE: "범위 밖",
    EvaluationStatus.DISCOVERY: "Discovery(수동)",
    EvaluationStatus.NEEDS_HUMAN_REVIEW: "검토 필요",
}

_CSS = """
:root{
  --surface:#fcf8ff; --surface-container-lowest:#ffffff; --surface-container-low:#f5f2ff;
  --surface-container:#efecff; --surface-container-high:#e8e5ff; --surface-container-highest:#e2e0fc;
  --surface-variant:#e2e0fc; --on-surface:#1a1a2e; --on-surface-variant:#43474e;
  --outline:#74777f; --outline-variant:#c4c6cf;
  --primary:#022448; --on-primary:#ffffff; --primary-container:#1e3a5f; --on-primary-container:#8aa4cf;
  --secondary:#0051d5; --on-secondary:#ffffff; --secondary-container:#316bf3; --on-secondary-container:#fefcff;
  --error:#ba1a1a; --error-container:#ffdad6; --on-error-container:#93000a;
  --tertiary-fixed:#ffddb2; --on-tertiary-fixed-variant:#60410c; --tertiary-fixed-dim:#edbf7f;
  --background:#fcf8ff; --on-background:#1a1a2e;
}
*{box-sizing:border-box;}
body{margin:0;background:var(--background);color:var(--on-surface);
  font-family:"Noto Sans","Apple SD Gothic Neo","Malgun Gothic",system-ui,sans-serif;font-size:14px;line-height:20px;}
.mono{font-family:"JetBrains Mono",ui-monospace,SFMono-Regular,Menlo,monospace;}
.wrap{max-width:1200px;margin:0 auto;padding:32px 24px;}
.topbar{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:24px;
  padding-bottom:16px;border-bottom:1px solid var(--outline-variant);}
.brand{display:flex;align-items:center;gap:10px;font-weight:700;color:var(--primary);font-size:20px;}
.scenario{display:inline-flex;align-items:center;gap:8px;background:var(--surface-container-low);
  border:1px solid var(--outline-variant);border-radius:8px;padding:6px 12px;font-size:12px;font-weight:600;}
h1{font-size:30px;line-height:38px;letter-spacing:-.02em;font-weight:700;color:var(--on-background);margin:0 0 8px;}
.sub{color:var(--on-surface-variant);max-width:56rem;margin-bottom:8px;}
.meta{color:var(--on-surface-variant);font-size:13px;margin-bottom:20px;}
.summary{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:20px;}
.chip{display:inline-flex;align-items:center;gap:6px;border-radius:9999px;padding:5px 12px;
  font-size:12px;font-weight:600;border:1px solid var(--outline-variant);background:var(--surface-container-lowest);}
.dot{width:8px;height:8px;border-radius:9999px;}
.panel{background:var(--surface-container-lowest);border:1px solid var(--outline-variant);
  border-radius:8px;overflow:hidden;box-shadow:0 1px 2px rgba(0,0,0,.04);}
table{width:100%;border-collapse:collapse;}
thead th{background:var(--surface-container-low);color:var(--on-surface-variant);text-align:left;
  font-size:12px;font-weight:600;padding:12px 16px;border-bottom:1px solid var(--outline-variant);white-space:nowrap;}
tbody td{padding:12px 16px;border-bottom:1px solid rgba(196,198,207,.4);vertical-align:middle;}
tbody tr:last-child td{border-bottom:none;}
tbody tr:hover{background:var(--surface-container-low);}
.seg{font-weight:600;color:var(--secondary);}
.ltv{font-family:"JetBrains Mono",monospace;font-size:14px;font-weight:500;}
.delta-down{color:var(--error);font-weight:600;}
.delta-flat{color:var(--on-surface-variant);}
.delta-up{color:var(--secondary);font-weight:600;}
.na{color:var(--outline);}
.badge{display:inline-flex;align-items:center;gap:6px;border-radius:9999px;padding:3px 10px;
  font-family:"JetBrains Mono",monospace;font-size:12px;font-weight:500;white-space:nowrap;}
.badge-error{background:var(--error-container);color:var(--on-error-container);}
.badge-warn{background:var(--tertiary-fixed);color:var(--on-tertiary-fixed-variant);}
.badge-neutral{background:var(--surface-variant);color:var(--on-surface-variant);}
.badge-info{background:var(--secondary-container);color:var(--on-secondary-container);}
.reason{font-family:"JetBrains Mono",monospace;font-size:12px;background:var(--surface-variant);
  color:var(--on-surface-variant);padding:2px 8px;border-radius:4px;}
.cite{font-family:"JetBrains Mono",monospace;font-size:11px;color:var(--on-surface-variant);}
.review{margin-top:24px;background:var(--surface-container-high);border:1px dashed var(--outline-variant);
  border-radius:8px;padding:20px;}
.review h3{margin:0 0 12px;font-size:16px;color:var(--on-surface-variant);}
.review li{margin-bottom:6px;}
.footnote{margin-top:24px;color:var(--outline);font-size:12px;}
"""


def _esc(x) -> str:
    return html.escape(str(x)) if x is not None else ""


def _ltv_cell(dec: LtvDecision) -> str:
    if dec.status == EvaluationStatus.DECIDED and dec.max_ltv is not None:
        return f'<span class="ltv">{dec.max_ltv:.0%}</span>'
    label = _STATUS_LABEL_KO.get(dec.status, dec.status.value)
    return f'<span class="na">{_esc(label)}</span>'


def _delta_cell(row: ImpactRow) -> str:
    if row.delta_ltv is None:
        return '<span class="na">–</span>'
    pp = row.delta_ltv * 100
    if pp < 0:
        return f'<span class="delta-down">{pp:.0f}pp</span>'
    if pp > 0:
        return f'<span class="delta-up">+{pp:.0f}pp</span>'
    return '<span class="delta-flat">0pp</span>'


def _reason_cell(row: ImpactRow) -> str:
    """근거 reason_code. 시행 후 판정 우선, 없으면 시행 전(escalation 사유)."""
    codes = row.after.reason_codes or row.before.reason_codes
    if not codes:
        return '<span class="na">–</span>'
    return " ".join(f'<span class="reason">{_esc(c)}</span>' for c in codes)


def _cite_cell(row: ImpactRow) -> str:
    ids = row.after.source_policy_ids or row.before.source_policy_ids
    if not ids:
        return '<span class="na">–</span>'
    return '<span class="cite">' + _esc(", ".join(ids)) + "</span>"


def _row_html(row: ImpactRow) -> str:
    label, cls = _DIRECTION_BADGE[row.direction]
    return (
        "<tr>"
        f'<td class="seg">{_esc(row.segment.label)}</td>'
        f"<td>{_ltv_cell(row.before)}</td>"
        f"<td>{_ltv_cell(row.after)}</td>"
        f"<td>{_delta_cell(row)}</td>"
        f'<td><span class="badge {cls}"><span class="dot" style="background:currentColor"></span>{label}</span></td>'
        f"<td>{_reason_cell(row)}</td>"
        f"<td>{_cite_cell(row)}</td>"
        "</tr>"
    )


def _summary_chips(matrix: ImpactMatrix) -> str:
    s = matrix.summary()
    order = [
        (ImpactDirection.TIGHTENED, "강화", "var(--error)"),
        (ImpactDirection.LOOSENED, "완화", "var(--secondary)"),
        (ImpactDirection.UNCHANGED, "동일", "var(--outline)"),
        (ImpactDirection.REVIEW, "검토", "var(--tertiary-fixed-dim)"),
    ]
    chips = []
    for d, ko, color in order:
        chips.append(
            f'<span class="chip"><span class="dot" style="background:{color}"></span>'
            f'{ko} <span class="mono">{s[d.value]}</span></span>'
        )
    return '<div class="summary">' + "".join(chips) + "</div>"


def _review_section(matrix: ImpactMatrix) -> str:
    rows = matrix.review_required
    if not rows:
        return ""
    items = "".join(
        f"<li><strong>{_esc(r.segment.label)}</strong> — "
        f'<span class="mono">{_esc(r.note or "판정 불가")}</span></li>'
        for r in rows
    )
    return (
        '<div class="review"><h3>⚠ 검토 필요 (사람 확정) — 자동판정 보류</h3>'
        "<p style='margin:0 0 10px;color:var(--on-surface-variant)'>"
        "명세에 기준값이 없어(예: 非규제 유주택) 델타를 자동 산출하지 않고 사람 검토로 escalation한 세그먼트."
        "</p><ul>" + items + "</ul></div>"
    )


def render_matrix_html(
    matrix: ImpactMatrix,
    scenario_title: str = "2026-06-30 규제지역 추가 지정",
) -> str:
    """`ImpactMatrix`(엔진 실제 산출)를 self-contained HTML 페이지로 렌더한다.

    페이지의 모든 값(지역·시점·LTV·델타·근거)은 matrix 에서만 온다. 하드코딩 없음.
    """
    pol = f" · policy <span class='mono'>{_esc(matrix.policy_id)}</span>" if matrix.policy_id else ""
    rows_html = "".join(_row_html(r) for r in matrix.rows)
    return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>임팩트 매트릭스 — RegImpact AI</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans:wght@400;500;600;700&amp;family=JetBrains+Mono:wght@400;500&amp;display=swap" rel="stylesheet"/>
<style>{_CSS}</style></head>
<body><div class="wrap">
<div class="topbar">
  <div class="brand">🛡 RegImpact AI</div>
  <div class="scenario">🎯 {_esc(scenario_title)}</div>
</div>
<h1>임팩트 매트릭스</h1>
<div class="sub">규제 변경의 <strong>시행 전/후</strong> 세그먼트별 LTV 영향. 모든 수치는 deterministic 룰엔진
(<span class="mono">rule_engine.evaluate</span>)을 두 시점으로 차등 실행한 실제 산출이다(하드코딩 없음).</div>
<div class="meta">지역 <span class="mono">{_esc(matrix.region_code)}</span> ·
  시행 전 <span class="mono">{matrix.before_date.isoformat()}</span> →
  시행 후 <span class="mono">{matrix.after_date.isoformat()}</span>{pol}</div>
{_summary_chips(matrix)}
<div class="panel"><table>
<thead><tr>
  <th>세그먼트</th><th>시행 전 LTV</th><th>시행 후 LTV</th><th>Δ</th>
  <th>방향</th><th>근거 (reason_code)</th><th>출처</th>
</tr></thead>
<tbody>{rows_html}</tbody>
</table></div>
{_review_section(matrix)}
<div class="footnote">이 페이지는 <span class="mono">regimpact.impact.render_matrix_html</span>로
<span class="mono">ImpactMatrix</span> 실제 산출에서 생성됨 — Stitch 목업의 하드코딩·환각값을 대체.
LOCKED §4: 규칙값은 확정 명세→엔진에서만.</div>
</div></body></html>"""


def render_6_30(as_of_before: Optional[date] = None) -> str:
    """6·30 표준 세그먼트로 Impact Matrix HTML 을 생성하는 편의 함수."""
    from .matrix import analyze_impact
    from .segments import DEFAULT_REGION, SIX_THIRTY_SEGMENTS

    matrix = analyze_impact(
        segments=SIX_THIRTY_SEGMENTS,
        region_code=DEFAULT_REGION,
        before_date=as_of_before or date(2026, 6, 30),
        after_date=date(2026, 7, 2),
        policy_id="FSC_MOLIT_20260630",
    )
    return render_matrix_html(matrix)
