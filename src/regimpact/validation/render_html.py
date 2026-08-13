"""Validation Report → 정식 HTML 보고서 (self-contained, 데이터바인딩).

`format_report_md`(마크다운)의 HTML 판. 파이프라인 각 노드의 실제 산출을 디자인 시스템
(DESIGN.md: Institutional Navy·Noto Sans·JetBrains Mono·상태색)으로 렌더한 검증보고서.
모든 값은 ValidationReport에서만 온다(하드코딩 없음). 외부 스크립트 의존 없음.

브리프 §18의 '정식 15~20쪽 검증보고서'의 프레젠테이션 골격 — 실데이터 조립 + 정직성 섹션.
"""
from __future__ import annotations

import html
from typing import Optional

from ..impact.matrix import EvaluationStatus, ImpactDirection
from ..models import LtvDecision
from ..proposal.schema import ApprovalStatus
from .report import ValidationReport

# 파이프라인 노드 라벨(순서 유지)
_NODE_LABELS = [
    ("extraction", "[2] RegChange Extractor"),
    ("impact_matrix", "[3] Impact Matrix"),
    ("rule_proposal", "[4] Rule Change Proposal"),
    ("rule_regression", "[5] TC / Rule-Regression"),
    ("assurance", "[6] Assurance"),
]

_DIRECTION = {
    ImpactDirection.TIGHTENED: ("강화", "badge-error"),
    ImpactDirection.LOOSENED: ("완화", "badge-info"),
    ImpactDirection.UNCHANGED: ("동일", "badge-neutral"),
    ImpactDirection.REVIEW: ("검토", "badge-warn"),
}

_APPROVAL_BADGE = {
    ApprovalStatus.APPROVED: "badge-ok",
    ApprovalStatus.PENDING_REVIEW: "badge-warn",
    ApprovalStatus.REJECTED: "badge-error",
    ApprovalStatus.CHANGES_REQUESTED: "badge-warn",
}

_CSS = """
:root{
  --surface:#fcf8ff; --surface-container-lowest:#ffffff; --surface-container-low:#f5f2ff;
  --surface-container-high:#e8e5ff; --surface-variant:#e2e0fc;
  --on-surface:#1a1a2e; --on-surface-variant:#43474e; --outline:#74777f; --outline-variant:#c4c6cf;
  --primary:#022448; --on-primary:#ffffff; --primary-container:#1e3a5f;
  --secondary:#0051d5; --on-secondary:#ffffff; --secondary-container:#316bf3; --on-secondary-container:#fefcff;
  --error:#ba1a1a; --error-container:#ffdad6; --on-error-container:#93000a;
  --ok:#0f7b3f; --ok-container:#c8f2d6; --on-ok-container:#00391a;
  --tertiary-fixed:#ffddb2; --on-tertiary-fixed-variant:#60410c;
  --background:#fcf8ff;
}
*{box-sizing:border-box;}
body{margin:0;background:var(--background);color:var(--on-surface);
  font-family:"Noto Sans","Apple SD Gothic Neo","Malgun Gothic",system-ui,sans-serif;font-size:14px;line-height:20px;}
.mono{font-family:"JetBrains Mono",ui-monospace,SFMono-Regular,Menlo,monospace;}
.wrap{max-width:1080px;margin:0 auto;padding:32px 24px 56px;}
.topbar{display:flex;align-items:center;justify-content:space-between;gap:16px;
  padding-bottom:16px;border-bottom:2px solid var(--primary);margin-bottom:24px;}
.brand{display:flex;align-items:center;gap:10px;font-weight:700;color:var(--primary);font-size:20px;}
.scenario{display:inline-flex;align-items:center;gap:8px;background:var(--surface-container-low);
  border:1px solid var(--outline-variant);border-radius:8px;padding:6px 12px;font-size:12px;font-weight:600;}
h1{font-size:28px;line-height:36px;letter-spacing:-.02em;font-weight:700;color:var(--primary);margin:0 0 6px;}
.meta{color:var(--on-surface-variant);font-size:13px;margin-bottom:20px;}
h2{font-size:18px;font-weight:600;color:var(--on-surface);margin:28px 0 12px;
  padding-bottom:6px;border-bottom:1px solid var(--outline-variant);}
.verdict{display:inline-flex;align-items:center;gap:8px;border-radius:9999px;padding:6px 16px;
  font-weight:700;font-size:14px;margin:4px 0 8px;}
.verdict.complete{background:var(--ok-container);color:var(--on-ok-container);}
.verdict.partial{background:var(--tertiary-fixed);color:var(--on-tertiary-fixed-variant);}
.nodes{display:flex;flex-wrap:wrap;gap:8px;margin:8px 0 4px;}
.node{display:inline-flex;align-items:center;gap:6px;border-radius:8px;padding:6px 12px;
  font-size:12px;font-weight:600;border:1px solid var(--outline-variant);background:var(--surface-container-lowest);}
.node.on{border-color:var(--ok);color:var(--on-ok-container);background:var(--ok-container);}
.node.off{color:var(--outline);}
.panel{background:var(--surface-container-lowest);border:1px solid var(--outline-variant);
  border-radius:8px;overflow:hidden;box-shadow:0 1px 2px rgba(0,0,0,.04);}
table{width:100%;border-collapse:collapse;}
thead th{background:var(--surface-container-low);color:var(--on-surface-variant);text-align:left;
  font-size:12px;font-weight:600;padding:10px 14px;border-bottom:1px solid var(--outline-variant);white-space:nowrap;}
tbody td{padding:10px 14px;border-bottom:1px solid rgba(196,198,207,.4);vertical-align:middle;}
tbody tr:last-child td{border-bottom:none;}
tbody tr:hover{background:var(--surface-container-low);}
.seg{font-weight:600;color:var(--secondary);}
.ltv{font-family:"JetBrains Mono",monospace;font-weight:500;}
.delta-down{color:var(--error);font-weight:600;} .delta-up{color:var(--secondary);font-weight:600;}
.delta-flat,.na{color:var(--on-surface-variant);}
.na{color:var(--outline);}
.badge{display:inline-flex;align-items:center;gap:5px;border-radius:9999px;padding:2px 9px;
  font-family:"JetBrains Mono",monospace;font-size:11px;font-weight:500;white-space:nowrap;}
.badge-error{background:var(--error-container);color:var(--on-error-container);}
.badge-warn{background:var(--tertiary-fixed);color:var(--on-tertiary-fixed-variant);}
.badge-neutral{background:var(--surface-variant);color:var(--on-surface-variant);}
.badge-info{background:var(--secondary-container);color:var(--on-secondary-container);}
.badge-ok{background:var(--ok-container);color:var(--on-ok-container);}
.reason{font-family:"JetBrains Mono",monospace;font-size:11px;background:var(--surface-variant);
  color:var(--on-surface-variant);padding:1px 7px;border-radius:4px;}
.cite{font-family:"JetBrains Mono",monospace;font-size:11px;color:var(--on-surface-variant);}
.tiles{display:flex;flex-wrap:wrap;gap:12px;margin:4px 0;}
.tile{flex:1 1 150px;background:var(--surface-container-lowest);border:1px solid var(--outline-variant);
  border-radius:8px;padding:12px 14px;}
.tile .k{font-size:12px;color:var(--on-surface-variant);}
.tile .v{font-size:20px;font-weight:700;font-family:"JetBrains Mono",monospace;margin-top:2px;}
.tile .v.good{color:var(--ok);} .tile .v.warn{color:var(--on-tertiary-fixed-variant);}
ul.changes{margin:6px 0;padding-left:0;list-style:none;}
ul.changes li{padding:8px 0;border-bottom:1px solid rgba(196,198,207,.35);}
ul.changes li:last-child{border-bottom:none;}
.limits{background:var(--surface-container-high);border:1px dashed var(--outline-variant);
  border-radius:8px;padding:16px 18px;margin-top:16px;}
.limits h2{border:none;margin-top:0;}
.limits li{margin-bottom:6px;color:var(--on-surface-variant);}
.footnote{margin-top:22px;color:var(--outline);font-size:12px;}
"""


def _esc(x) -> str:
    return html.escape(str(x)) if x is not None else ""


def _ltv(v: Optional[float]) -> str:
    return f'<span class="ltv">{v:.0%}</span>' if v is not None else '<span class="na">—</span>'


def _ltv_dec(dec: LtvDecision) -> str:
    if dec.status == EvaluationStatus.DECIDED and dec.max_ltv is not None:
        return f'<span class="ltv">{dec.max_ltv:.0%}</span>'
    return f'<span class="na">{_esc(dec.status.value)}</span>'


def _delta(v: Optional[float]) -> str:
    if v is None:
        return '<span class="na">—</span>'
    pp = v * 100
    if pp < 0:
        return f'<span class="delta-down">{pp:.0f}pp</span>'
    if pp > 0:
        return f'<span class="delta-up">+{pp:.0f}pp</span>'
    return '<span class="delta-flat">0pp</span>'


def _section_nodes(report: ValidationReport) -> str:
    chips = []
    for key, label in _NODE_LABELS:
        on = report.node_status().get(key, False)
        cls = "node on" if on else "node off"
        mark = "✅" if on else "⬜"
        chips.append(f'<span class="{cls}">{mark} {_esc(label)}</span>')
    complete = report.is_pipeline_complete
    vcls = "verdict complete" if complete else "verdict partial"
    vtxt = "관통 (핵심 노드 완결)" if complete else "부분 관통"
    return (f'<h2>1. 파이프라인 관통 현황</h2><div class="{vcls}">{"✔" if complete else "◐"} {vtxt}</div>'
            f'<div class="nodes">{"".join(chips)}</div>')


def _section_extraction(report: ValidationReport) -> str:
    if report.extraction is None:
        return ""
    changes = getattr(report.extraction, "changes", []) or []
    items = []
    for c in changes:
        cat = _esc(getattr(c, "category", ""))
        summ = _esc(getattr(c, "summary", ""))
        cit = getattr(c, "citation", None)
        cite = ""
        if cit is not None:
            cite = (f'<div class="cite">⤷ {_esc(cit.source_doc_id)}: '
                    f'&ldquo;{_esc((cit.quote or "")[:70])}…&rdquo;</div>')
        items.append(f'<li><span class="reason">{cat}</span> {summ}{cite}</li>')
    return (f'<h2>2. 규제 변경 요약 (원문 추출)</h2>'
            f'<div class="meta">추출 변경 항목 {len(changes)}건 (인용 = 원문 verbatim)</div>'
            f'<ul class="changes">{"".join(items)}</ul>')


def _section_matrix(report: ValidationReport) -> str:
    m = report.matrix
    if m is None:
        return ""
    rows = []
    for r in m.rows:
        label, cls = _DIRECTION[r.direction]
        rows.append(
            f"<tr><td class='seg'>{_esc(r.segment.label)}</td>"
            f"<td>{_ltv_dec(r.before)}</td><td>{_ltv_dec(r.after)}</td>"
            f"<td>{_delta(r.delta_ltv)}</td>"
            f"<td><span class='badge {cls}'>{label}</span></td></tr>"
        )
    s = m.summary()
    return (f'<h2>3. 시행 전/후 영향 매트릭스</h2>'
            f'<div class="meta">지역 <span class="mono">{_esc(m.region_code)}</span> · '
            f'전 <span class="mono">{m.before_date.isoformat()}</span> → '
            f'후 <span class="mono">{m.after_date.isoformat()}</span> · '
            f'강화 {s["TIGHTENED"]} · 완화 {s["LOOSENED"]} · 동일 {s["UNCHANGED"]} · 검토 {s["REVIEW"]}</div>'
            f'<div class="panel"><table><thead><tr>'
            f'<th>세그먼트</th><th>시행 전</th><th>시행 후</th><th>Δ</th><th>방향</th>'
            f'</tr></thead><tbody>{"".join(rows)}</tbody></table></div>')


def _section_proposal(report: ValidationReport) -> str:
    p = report.proposal
    if p is None:
        return ""
    ap = p.approval
    badge = _APPROVAL_BADGE.get(ap.status, "badge-neutral")
    reviewer = f' · 검토자 {_esc(ap.reviewer)}' if ap.reviewer else ""
    note = f'<div class="meta">검토 노트: {_esc(ap.note)}</div>' if ap.note else ""
    rows = []
    for ln in p.lines:
        rc = " ".join(f'<span class="reason">{_esc(c)}</span>' for c in ln.reason_codes) or "—"
        flag = '<span class="badge badge-warn">검토</span>' if ln.needs_review else ""
        rows.append(
            f"<tr><td class='seg'>{_esc(ln.segment_label)}</td>"
            f"<td class='mono'>{_esc(ln.rule_id or '—')}</td>"
            f"<td>{_ltv(ln.before_ltv)} → {_ltv(ln.after_ltv)}</td>"
            f"<td>{rc}</td><td>{flag}</td></tr>"
        )
    return (f'<h2>4. 룰 변경 제안 <span class="badge {badge}">{_esc(ap.status.value)}</span></h2>'
            f'<div class="meta">제안 ID <span class="mono">{_esc(p.proposal_id)}</span>{reviewer} · '
            f'제안 행 {len(p.lines)}건 (사람 검토 필요 {len(p.review_required_lines)}건) · '
            f'AI초안→사람확정(LOCKED §4)</div>{note}'
            f'<div class="panel"><table><thead><tr>'
            f'<th>세그먼트</th><th>rule_id</th><th>전→후</th><th>근거</th><th>검토</th>'
            f'</tr></thead><tbody>{"".join(rows)}</tbody></table></div>')


def _section_regression(report: ValidationReport) -> str:
    reg = report.regression
    if reg is None:
        return ""
    pr = getattr(reg, "pass_rate", None)
    passed = getattr(reg, "passed", None)
    total = getattr(reg, "total", None)
    tiles = [(f"{passed}/{total}", f"Pass Rate {pr:.0%}" if pr is not None else "Pass Rate")]
    by = getattr(reg, "pass_rate_by_category", None)
    cat_rows = ""
    if callable(by):
        for cat, (p_, n_, rate) in by().items():
            cat_rows += f"<tr><td>{_esc(cat)}</td><td class='mono'>{p_}/{n_}</td><td class='mono'>{rate:.0%}</td></tr>"
    tile_html = "".join(
        f'<div class="tile"><div class="k">{_esc(k)}</div><div class="v good">{_esc(v)}</div></div>'
        for v, k in tiles)
    table = (f'<div class="panel" style="margin-top:12px"><table><thead><tr>'
             f'<th>카테고리</th><th>통과</th><th>비율</th></tr></thead>'
             f'<tbody>{cat_rows}</tbody></table></div>') if cat_rows else ""
    return (f'<h2>5. 룰 회귀 검증 (엔진 ⟷ 독립 오라클)</h2>'
            f'<div class="tiles">{tile_html}</div>{table}')


def _section_assurance(report: ValidationReport) -> str:
    a = report.assurance
    if not a:
        return ""
    tiles = []
    for k, v in a.items():
        vs = str(v).strip()
        if "FAIL" in vs:
            cls = "warn"
        elif "WARN" in vs:
            cls = "warn"
        elif "PASS" in vs or vs.startswith(("100", "OK")) or vs == "0%":
            cls = "good"
        else:
            cls = "warn"
        tiles.append(f'<div class="tile"><div class="k">{_esc(k)}</div>'
                     f'<div class="v {cls}">{_esc(v)}</div></div>')
    return (f'<h2>6. Assurance (실측)</h2>'
            f'<div class="tiles">{"".join(tiles)}</div>')


def _section_limits(report: ValidationReport) -> str:
    items = ["<li>이 보고서는 6·30 단일 앵커 기준이다(정식 15~20쪽 분석 서사는 Phase 3).</li>"]
    if report.review_required_count:
        items.append(f"<li>사람 검토 필요 세그먼트 {report.review_required_count}건 — 자동 확정 보류(escalation).</li>")
    if report.assurance is None:
        items.append("<li>Assurance 정량 지표는 부분(Citation grounding 위주). 4 dimension 완성은 Phase 3.</li>")
    if (report.proposal is not None
            and report.proposal.approval.status == ApprovalStatus.PENDING_REVIEW):
        items.append("<li>룰 변경 제안은 <strong>초안</strong>이며 사람 승인 전이다(LOCKED §4).</li>")
    items.append("<li>룰 회귀의 오라클은 challenger(제3자 벤치마크 아님) — 100%는 '엔진=명세' 일치를 뜻한다.</li>")
    return f'<div class="limits"><h2>7. 한계 (정직성)</h2><ul>{"".join(items)}</ul></div>'


def render_report_html(report: ValidationReport) -> str:
    """ValidationReport(파이프라인 실제 산출)를 self-contained HTML 검증보고서로 렌더한다."""
    regions = ", ".join(f'<span class="mono">{_esc(r)}</span>' for r in report.target_regions) or "—"
    return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>검증보고서 — {_esc(report.scenario_title)}</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans:wght@400;500;600;700&amp;family=JetBrains+Mono:wght@400;500&amp;display=swap" rel="stylesheet"/>
<style>{_CSS}</style></head>
<body><div class="wrap">
<div class="topbar">
  <div class="brand">🛡 RegImpact AI</div>
  <div class="scenario">🎯 검증보고서 (Validation Report)</div>
</div>
<h1>{_esc(report.scenario_title)}</h1>
<div class="meta">정책 <span class="mono">{_esc(report.policy_id or '—')}</span> ·
  시행일 <span class="mono">{_esc(report.effective_from or '—')}</span> · 대상지역 {regions}</div>
{_section_nodes(report)}
{_section_extraction(report)}
{_section_matrix(report)}
{_section_proposal(report)}
{_section_regression(report)}
{_section_assurance(report)}
{_section_limits(report)}
<div class="footnote">이 보고서는 <span class="mono">regimpact.validation.render_report_html</span>로
파이프라인 실제 산출(Extractor·Impact Matrix·Rule Proposal·Rule-Regression·Assurance)에서 생성됨 —
하드코딩 없음. LOCKED §4: 규칙값은 확정 명세→엔진에서만.</div>
</div></body></html>"""
