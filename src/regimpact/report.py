"""정적 HTML 리포트 생성기 — 파이프라인 실제 출력을 화면으로.

Stitch 목업이 도메인 데이터를 화면마다 환각한 문제(docs/ui/stitch_review.md)를 근본 해결한다:
이 리포트의 모든 값은 **엔진/추출 출력에서만** 온다 → 하드코딩·환각이 구조적으로 불가능.

입력:
  - PolicyImpact       (impact_from_extraction 결과) — 필수
  - RegChangeExtraction(선택) — "무엇이 달라졌나" 섹션(추출 변경 + 인용)
  - GroundingReport / GoldReport(선택) — Assurance 지표 타일

디자인: docs/ui/stitch_export/regimpact_ai/DESIGN.md (Institutional Navy, Noto Sans). 자체완결 HTML.
"""
from __future__ import annotations

import html
from datetime import date
from typing import Any, Optional

from .impact.matrix import EvaluationStatus, ImpactDirection, ImpactMatrix, SegmentImpact
from .regions import region_display_name
from .rule_proposal import Disposition, RuleChangeProposal

_DIR_LABEL = {
    ImpactDirection.TIGHTENED: ("▼ 강화", "t"),
    ImpactDirection.LOOSENED: ("▲ 완화", "l"),
    ImpactDirection.UNCHANGED: ("= 유지", "h"),
    ImpactDirection.NEEDS_REVIEW: ("? 검토", "r"),
}


def _esc(s: Any) -> str:
    return html.escape(str(s), quote=True)


def _ltv_cell(d) -> str:
    if d.status != EvaluationStatus.DECIDED or d.max_ltv is None:
        label = {
            EvaluationStatus.NEEDS_HUMAN_REVIEW: "검토",
            EvaluationStatus.DISCOVERY: "Discovery",
            EvaluationStatus.OUT_OF_SCOPE: "범위외",
        }.get(d.status, d.status.value)
        return f'<span class="muted">{_esc(label)}</span>'
    return f"{d.max_ltv:.0%}"


def _delta_cell(imp: SegmentImpact) -> str:
    if imp.ltv_delta is None:
        return '<span class="muted">—</span>'
    pp = imp.ltv_delta * 100
    if pp == 0:
        return '<span class="muted">0pp</span>'
    sign = "+" if pp > 0 else "−"
    cls = "neg" if pp < 0 else "pos"
    return f'<span class="delta {cls}">{sign}{abs(pp):.0f}pp</span>'


def _rows_by_region(matrix: ImpactMatrix) -> list[tuple[str, list[SegmentImpact]]]:
    """행을 region_code별로 그룹핑(순서 보존). region 없으면 단일 그룹."""
    groups: list[tuple[str, list[SegmentImpact]]] = []
    index: dict[str, list[SegmentImpact]] = {}
    for r in matrix.rows:
        code = r.segment.attrs.get("region_code", "")
        if code not in index:
            index[code] = []
            groups.append((code, index[code]))
        index[code].append(r)
    return groups


def _display_label(imp: SegmentImpact) -> str:
    # 다지역 라벨은 "서민·실수요·GURI" → 지역 접미(·CODE)만 제거. 유형명에도 '·'가 있으므로
    # split이 아니라 실제 region_code 접미를 정확히 벗겨낸다.
    code = imp.segment.attrs.get("region_code", "")
    label = imp.label
    suffix = f"·{code}"
    if code and label.endswith(suffix):
        return label[: -len(suffix)]
    return label


def _metric_tile(label: str, value: str, note: str, tone: str = "") -> str:
    return (
        f'<div class="tile {tone}">'
        f'<div class="t-label">{_esc(label)}</div>'
        f'<div class="t-val">{value}</div>'
        f'<div class="t-note">{_esc(note)}</div></div>'
    )


def _assurance_section(grounding, gold) -> str:
    if grounding is None and gold is None:
        return ""
    tiles: list[str] = []
    if grounding is not None:
        tiles.append(_metric_tile(
            "Citation 정확도", f"{grounding.citation_correctness:.0%}",
            f"{grounding.grounded}/{grounding.total} 인용 원문 실재", "good"))
        tiles.append(_metric_tile(
            "환각률", f"{grounding.unsupported_claim_rate:.0%}",
            "근거 없는 주장", "good" if grounding.unsupported_claim_rate == 0 else "warn"))
    if gold is not None:
        tiles.append(_metric_tile(
            "변경 완전성", f"{gold.change_completeness:.0%}",
            "필수 변경 포착", "good" if gold.change_completeness == 1 else "warn"))
        tiles.append(_metric_tile(
            "예외 재현율", f"{gold.exception_recall:.0%}",
            "예외 포착", "good" if gold.exception_recall == 1 else "warn"))
        tiles.append(_metric_tile(
            "지역 매칭", "OK" if gold.regions_correct else "MISS",
            "정규화 후 코드 대조", "good" if gold.regions_correct else "warn"))
    unmapped = ""
    if gold is not None and gold.unmapped_regions:
        unmapped = (f'<p class="foot-warn">⚠ 코드 매핑 실패(미상 지역): '
                    f'{_esc(", ".join(gold.unmapped_regions))}</p>')
    return (
        '<section class="panel"><h2>검증 (Assurance)</h2>'
        '<p class="lead">AI 추출의 신뢰를 숫자로. 인용이 원문에 실재하는지, 필수 변경·예외를 놓치지 않았는지.</p>'
        f'<div class="tiles">{"".join(tiles)}</div>{unmapped}</section>'
    )


_CAT_KO = {
    "LTV": "LTV", "EXCEPTION": "예외", "GRANDFATHERING": "경과규정",
    "EFFECTIVE_DATE": "시행일", "REGION": "규제지역", "SCOPE_LIMIT": "범위제한",
}


def _changes_section(extraction) -> str:
    if extraction is None or not getattr(extraction, "changes", None):
        return ""
    items: list[str] = []
    for c in extraction.changes:
        cat = _CAT_KO.get(c.category, c.category)
        ba = ""
        if c.before or c.after:
            b = _esc(c.before) if c.before else "—"
            a = _esc(c.after) if c.after else "—"
            ba = f'<span class="ba"><span class="b">{b}</span><span class="arr">→</span><span class="a">{a}</span></span>'
        quote = _esc((c.citation.quote or "")[:120])
        src = _esc(c.citation.source_doc_id)
        items.append(
            '<li class="change">'
            f'<div class="c-head"><span class="cat cat-{_esc(c.category)}">{_esc(cat)}</span>'
            f'<span class="c-sum">{_esc(c.summary)}</span>{ba}</div>'
            f'<div class="cite"><span class="q">“{quote}…”</span>'
            f'<span class="src">{src}</span></div>'
            '</li>'
        )
    return (
        '<section class="panel"><h2>무엇이 달라졌나</h2>'
        '<p class="lead">공문 원문에서 추출한 Before/After 변경. 각 항목은 원문 인용으로 뒷받침됩니다(검증 통과).</p>'
        f'<ul class="changes">{"".join(items)}</ul></section>'
    )


def _archetype_rows(matrix: ImpactMatrix):
    """지역 중복을 접어 대표 유형별 1행(첫 등장 기준). 차트용."""
    seen: dict[str, Any] = {}
    order: list[str] = []
    for r in matrix.rows:
        lbl = _display_label(r)
        if lbl not in seen:
            seen[lbl] = r
            order.append(lbl)
    return [seen[l] for l in order]


def _svg_impact(matrix: ImpactMatrix) -> str:
    """유형별 LTV Δ(pp) 수평 막대 — 길이=변화 크기, 색=방향(표와 동일 의미)."""
    rows = _archetype_rows(matrix)
    if not rows:
        return ""
    n = len(rows)
    row_h, label_w, x0, bar_max, top, pad_r = 30, 128, 138, 188, 30, 66
    W, H = x0 + bar_max + pad_r, top + n * row_h + 12
    max_pp = 30.0
    color = {ImpactDirection.TIGHTENED: "var(--tighten)",
             ImpactDirection.UNCHANGED: "var(--hold)",
             ImpactDirection.NEEDS_REVIEW: "var(--review)"}
    out = [f'<svg class="chart" viewBox="0 0 {W} {H}" role="img" '
           f'aria-label="유형별 LTV 변화 막대차트">']
    out.append(f'<text class="c-cap" x="{x0}" y="18">← LTV 축소 (pp) · 색=방향</text>')
    out.append(f'<line class="c-axis" x1="{x0}" y1="{top-4}" x2="{x0}" y2="{H-8}"/>')
    for i, r in enumerate(rows):
        y = top + i * row_h
        lbl = _esc(_display_label(r))
        out.append(f'<text class="c-lbl" x="{label_w}" y="{y+15}" text-anchor="end">{lbl}</text>')
        if r.ltv_delta is None:
            out.append(f'<text class="c-review" x="{x0+6}" y="{y+15}">검토 · 산정불가</text>')
            continue
        pp = r.ltv_delta * 100
        col = color.get(r.direction, "var(--hold)")
        if pp == 0:
            out.append(f'<circle cx="{x0+4}" cy="{y+11}" r="3.5" fill="{col}"/>')
            out.append(f'<text class="c-val" x="{x0+14}" y="{y+15}">0pp (유지)</text>')
        else:
            w = max(3.0, abs(pp) / max_pp * bar_max)
            out.append(f'<rect x="{x0}" y="{y+4}" width="{w:.1f}" height="14" rx="3" '
                       f'fill="{col}"><title>{lbl}: {pp:+.0f}pp</title></rect>')
            out.append(f'<text class="c-val" x="{x0+w+6:.1f}" y="{y+15}">'
                       f'{("%+.0f" % pp).replace("-", "−")}pp</text>')
    out.append("</svg>")
    return f'<div class="chart-wrap">{"".join(out)}</div>'


def _svg_exposure(exposure: Any) -> str:
    """밴드별 대출 여력 전/후 — 전(옅음) 위에 후(진함)를 겹쳐 감소분을 시각화."""
    bands = list(getattr(exposure, "by_band", []) or [])
    if not bands:
        return ""
    n = len(bands)
    row_h, label_w, x0, bar_max, top, pad_r = 34, 88, 96, 210, 34, 92
    W, H = x0 + bar_max + pad_r, top + n * row_h + 10
    max_cap = max((b.before_capacity for b in bands), default=1.0) or 1.0
    out = [f'<svg class="chart" viewBox="0 0 {W} {H}" role="img" '
           f'aria-label="담보가격 밴드별 대출 여력 전후 막대차트">']
    # 범례
    out.append(f'<rect x="{x0}" y="8" width="12" height="10" rx="2" fill="var(--outline)" opacity="0.5"/>')
    out.append(f'<text class="c-cap" x="{x0+16}" y="17">여력 전</text>')
    out.append(f'<rect x="{x0+58}" y="8" width="12" height="10" rx="2" fill="var(--secondary)"/>')
    out.append(f'<text class="c-cap" x="{x0+74}" y="17">여력 후 (억, 가중)</text>')
    for i, b in enumerate(bands):
        y = top + i * row_h
        out.append(f'<text class="c-lbl" x="{label_w}" y="{y+16}" text-anchor="end">{_esc(b.label)}</text>')
        wb = max(2.0, b.before_capacity / max_cap * bar_max)
        wa = max(1.0, b.after_capacity / max_cap * bar_max)
        out.append(f'<rect x="{x0}" y="{y+4}" width="{wb:.1f}" height="18" rx="3" '
                   f'fill="var(--outline)" opacity="0.4"><title>{_esc(b.label)} 여력 전 '
                   f'{b.before_capacity:.2f}억</title></rect>')
        out.append(f'<rect x="{x0}" y="{y+4}" width="{wa:.1f}" height="18" rx="3" '
                   f'fill="var(--secondary)"><title>{_esc(b.label)} 여력 후 '
                   f'{b.after_capacity:.2f}억</title></rect>')
        out.append(f'<text class="c-val" x="{x0+wb+7:.1f}" y="{y+17}">'
                   f'{("%.2f" % b.delta_capacity).replace("-", "−")}억</text>')
    out.append("</svg>")
    return f'<div class="chart-wrap">{"".join(out)}</div>'


def _svg_tornado(tornado: list[dict], base: float) -> str:
    """민감도 토네이도 — 가정을 하나씩 흔든 여력 감소율 범위(base 기준선)."""
    if not tornado:
        return ""
    data = sorted(tornado, key=lambda d: d["swing"], reverse=True)[:7]
    n = len(data)
    row_h, label_w, x0, plot_w, top, pad_r = 30, 150, 160, 210, 40, 60
    W, H = x0 + plot_w + pad_r, top + n * row_h + 14
    los = [d["lo"] for d in data] + [base]
    his = [d["hi"] for d in data] + [base]
    lo, hi = min(los), max(his)
    span = (hi - lo) or 1.0
    lo -= span * 0.08
    hi += span * 0.08
    span = hi - lo

    def sx(v: float) -> float:
        return x0 + (v - lo) / span * plot_w

    out = [f'<svg class="chart" viewBox="0 0 {W} {H}" role="img" '
           f'aria-label="민감도 토네이도 차트">']
    bx = sx(base)
    out.append(f'<line class="c-base" x1="{bx:.1f}" y1="{top-6}" x2="{bx:.1f}" y2="{H-10}"/>')
    out.append(f'<text class="c-base-lbl" x="{bx:.1f}" y="{H-2}" text-anchor="middle">'
               f'base {base:.1%}</text>')
    for i, d in enumerate(data):
        y = top + i * row_h
        out.append(f'<text class="c-lbl" x="{label_w}" y="{y+15}" text-anchor="end">'
                   f'{_esc(d["label"])}</text>')
        xa, xb = sx(d["lo"]), sx(d["hi"])
        w = max(3.0, xb - xa)
        out.append(f'<rect x="{xa:.1f}" y="{y+4}" width="{w:.1f}" height="14" rx="3" '
                   f'fill="var(--secondary)" opacity="0.85"><title>{_esc(d["label"])}: '
                   f'{d["lo"]:.1%}–{d["hi"]:.1%} (스윙 {d["swing"]:.1%})</title></rect>')
        out.append(f'<text class="c-val" x="{xb+6:.1f}" y="{y+15}">{d["swing"]:.1%}</text>')
    out.append("</svg>")
    return f'<div class="chart-wrap">{"".join(out)}</div>'


def _impact_section(matrix: ImpactMatrix) -> str:
    groups = _rows_by_region(matrix)
    body: list[str] = []
    for code, rows in groups:
        if code:
            name = region_display_name(code)
            body.append(
                f'<tr class="grp"><td colspan="5">{_esc(name)} '
                f'<span class="grp-code">{_esc(code)}</span></td></tr>'
            )
        for r in rows:
            dir_label, dir_cls = _DIR_LABEL[r.direction]
            star = ' <span class="star">★</span>' if r.high_impact else ""
            body.append(
                "<tr>"
                f'<td class="seg">{_esc(_display_label(r))}</td>'
                f'<td class="r num">{_ltv_cell(r.before)}</td>'
                f'<td class="r num">{_ltv_cell(r.after)}</td>'
                f'<td class="r">{_delta_cell(r)}</td>'
                f'<td><span class="dir {dir_cls}">{dir_label}</span>{star}</td>'
                "</tr>"
            )
    counts = matrix.count_by_direction()
    wmd = matrix.weighted_mean_delta()
    wmd_s = "—" if wmd is None else f"{wmd * 100:+.0f}pp".replace("+", "+").replace("-", "−")
    ds = matrix.direction_weight_share()
    rev = matrix.review_weight_share()
    foot = (
        f'<div class="tbl-foot">'
        f'<span>전체 <b>{len(matrix.rows)}</b>행</span>'
        f'<span>강화 <b>{counts["TIGHTENED"]}</b> · 유지 <b>{counts["UNCHANGED"]}</b> · '
        f'검토 <b>{counts["NEEDS_REVIEW"]}</b></span>'
        f'<span>중대영향 <b>{matrix.high_impact_count}</b>행</span>'
        f'<span>가중평균 Δ <b>{wmd_s}</b> '
        f'<span class="muted">(수치비교 {matrix.comparable_count}/{len(matrix.rows)}행)</span></span>'
        f'</div>'
        f'<div class="tbl-foot">'
        f'<span class="muted">비중(가정) 기준:</span>'
        f'<span>강화 <b>{ds["TIGHTENED"]:.0%}</b> · 유지 <b>{ds["UNCHANGED"]:.0%}</b> · '
        f'검토 <b>{ds["NEEDS_REVIEW"]:.0%}</b></span>'
        f'<span>사람검토 필요 <b>{rev:.0%}</b></span>'
        f'</div>'
    )
    return (
        '<section class="panel"><h2>누가 영향받나 — Impact Matrix</h2>'
        '<p class="lead">시행 전/후 두 시점을 결정적 룰엔진으로 판정한 고객 유형별 LTV 변화. '
        '★ = 중대영향, “검토” = 명세 여백을 정직하게 사람에게 넘긴 건.</p>'
        f'{_svg_impact(matrix)}'
        '<div class="tbl-wrap"><table>'
        '<thead><tr><th>고객 유형</th><th class="r">시행 전</th><th class="r">시행 후</th>'
        '<th class="r">Δ</th><th>방향</th></tr></thead>'
        f'<tbody>{"".join(body)}</tbody></table>'
        f'{foot}</div></section>'
    )


def _won(eok: float) -> str:
    sign = "−" if eok < 0 else ""
    v = abs(eok)
    if v >= 10000:
        return f"{sign}{v / 10000:.2f}조원"
    return f"{sign}{v:.1f}억"


def _sensitivity_note(sb) -> str:
    """민감도 밴드(선택)를 여력 패널에 견고성 한 줄로 덧붙인다."""
    if sb is None or not getattr(sb, "bands", None):
        return ""
    p5, _p50, p95 = sb.bands["exposure_pct_reduction"]
    rob = sb.robustness
    shrink = rob.get("여력 축소(감소율>0)", 0.0)
    tight = rob.get("강화 과반(강화>50%)", 0.0)
    return (
        f'<div class="tbl-foot">'
        f'<span class="muted">민감도(가정 섭동 n={sb.n}, 규칙 고정):</span>'
        f'<span>감소율 밴드 <b>[{p5:.1%}, {p95:.1%}]</b></span>'
        f'<span>여력 축소 결론 <b>{shrink:.0%}</b> 견고</span>'
        f'<span class="muted">강화 과반 {tight:.0%} 표본(가정 취약)</span>'
        f'</div>'
    )


def _exposure_section(exposure, sensitivity=None, tornado=None) -> str:
    if exposure is None or not getattr(exposure, "by_band", None):
        return ""
    rows: list[str] = []
    for b in exposure.by_band:
        d = b.delta_capacity
        dcls = "neg" if d < 0 else ("pos" if d > 0 else "")
        rows.append(
            "<tr>"
            f'<td class="seg">{_esc(b.label)}</td>'
            f'<td class="r num">{_won(b.before_capacity)}</td>'
            f'<td class="r num">{_won(b.after_capacity)}</td>'
            f'<td class="r"><span class="delta {dcls}">{_won(d)}</span></td>'
            "</tr>"
        )
    pct = exposure.pct_reduction
    pct_s = "—" if pct is None else f"{pct:.1%}"
    pu_b, pu_a = exposure.per_unit_before(), exposure.per_unit_after()
    pu_d = exposure.per_unit_delta()
    per_unit = ""
    if pu_b is not None:
        per_unit = (
            f'<span>1인당 평균 여력 <b>{pu_b:.2f}억</b> → <b>{pu_a:.2f}억</b> '
            f'<span class="delta neg">{pu_d:+.2f}억</span></span>'
        )
    foot = (
        f'<div class="tbl-foot">'
        f'<span>판정가능 여력 {_won(exposure.before_capacity)} → {_won(exposure.after_capacity)} '
        f'<span class="delta neg">{_won(exposure.delta_capacity)}</span></span>'
        f'<span>감소율 <b>{pct_s}</b></span>{per_unit}'
        f'<span class="muted">산정불가 비중 {exposure.undetermined_share:.0%}</span>'
        f'</div>'
    )
    return (
        '<section class="panel"><h2>영향 금액 — 대출 여력 <span class="draft">가정</span></h2>'
        '<p class="lead">LTV %p 변화를 <b>문서화된 담보가격 밴드</b>와 결합해 대출 <b>여력(한도)</b> '
        '변화 금액으로 환산. 주의: (1) 실행액이 아닌 <b>한도 여력</b> (2) LTV 규칙만 — '
        '가격대별 <b>최대한도 상한(6/4/2억) 미적용</b>(상한 성격) (3) 담보가격 분포는 <b>가정</b>(실측 아님) '
        '(4) 자동판정 불가분은 금액 <b>산정 불가</b>로 분리(0으로 뭉개지 않음).</p>'
        f'{_svg_exposure(exposure)}'
        '<div class="tbl-wrap"><table>'
        '<thead><tr><th>담보가격 밴드</th><th class="r">여력 전</th><th class="r">여력 후</th>'
        '<th class="r">Δ</th></tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table>{foot}{_sensitivity_note(sensitivity)}</div>'
        + _tornado_block(sensitivity, tornado)
        + '</section>'
    )


def _tornado_block(sensitivity, tornado) -> str:
    """민감도 토네이도 차트(선택). base는 sensitivity.base에서."""
    if not tornado or sensitivity is None:
        return ""
    base = getattr(getattr(sensitivity, "base", None), "exposure_pct_reduction", None)
    if base is None:
        return ""
    svg = _svg_tornado(tornado, base)
    if not svg:
        return ""
    return (
        '<div class="sub-chart"><div class="sc-cap">민감도 — 어떤 가정이 여력 감소율을 '
        '가장 크게 좌우하나 (규칙 고정, 가정만 섭동)</div>' + svg + '</div>'
    )


_DISP_META = {
    Disposition.MAPPED_CONSISTENT: ("반영됨", "ok"),
    Disposition.MAPPED_DIVERGENT: ("검토(불일치)", "warn"),
    Disposition.OUT_OF_SCOPE: ("코어밖", "muted"),
    Disposition.NEEDS_REVIEW: ("검토필요", "warn"),
}


def _proposal_section(proposal: Any) -> str:
    if proposal is None or not getattr(proposal, "deltas", None):
        return ""
    rows: list[str] = []
    for d in proposal.deltas:
        label, cls = _DISP_META[d.disposition]
        cat = _CAT_KO.get(d.category, d.category)
        ba = ""
        if d.extracted_before or d.extracted_after:
            b = _esc(d.extracted_before) if d.extracted_before else "—"
            a = _esc(d.extracted_after) if d.extracted_after else "—"
            ba = f'<span class="ba"><span class="b">{b}</span><span class="arr">→</span><span class="a">{a}</span></span>'
        eng = _esc(d.engine_current) if d.engine_current else "—"
        rows.append(
            "<tr>"
            f'<td><span class="cat cat-{_esc(d.category)}">{_esc(cat)}</span></td>'
            f'<td class="seg">{_esc(d.summary)}{ba}</td>'
            f'<td class="num">{_esc(d.target_field or "—")}</td>'
            f'<td class="num">{eng}</td>'
            f'<td><span class="disp {cls}">{_esc(label)}</span></td>'
            "</tr>"
        )
    c = proposal.counts()
    foot = (
        f'<div class="tbl-foot">'
        f'<span>제안 <b>{len(proposal.deltas)}</b>건</span>'
        f'<span>✓ 반영 <b>{c["MAPPED_CONSISTENT"]}</b></span>'
        f'<span>◦ 코어밖 <b>{c["OUT_OF_SCOPE"]}</b></span>'
        f'<span>▲ 검토 <b>{c["MAPPED_DIVERGENT"] + c["NEEDS_REVIEW"]}</b></span>'
        f'<span>승인상태 <b>{_esc(proposal.approval_status)}</b></span></div>'
    )
    return (
        '<section class="panel"><h2>제안된 룰 변경 <span class="draft">초안</span></h2>'
        '<p class="lead">추출된 각 변경을 룰엔진의 실제 룰 표면에 매핑하고 <b>사람이 확정한 룰엔진의 '
        '현재값과 대조</b>합니다. “반영됨”=엔진과 일치, “코어밖”=Discovery(자동판정 밖), '
        '“검토”=사람 판단 필요. <b>승인 전까지 적용되지 않습니다(자동 확정 없음).</b></p>'
        '<div class="tbl-wrap"><table>'
        '<thead><tr><th>구분</th><th>변경 요약</th><th>룰 필드</th>'
        '<th>엔진 현재값</th><th>대조</th></tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table>{foot}</div></section>'
    )


def render_report(
    policy_impact: Any,
    *,
    extraction: Any = None,
    grounding: Any = None,
    gold: Any = None,
    proposal: Any = None,
    exposure: Any = None,
    sensitivity: Any = None,
    tornado: Any = None,
    generated_on: Optional[date] = None,
    title: str = "규제 변경 영향분석 리포트",
) -> str:
    """PolicyImpact(+선택 추출/Assurance)를 자체완결 HTML 리포트로 렌더."""
    matrix = policy_impact.matrix
    regions = policy_impact.regions or matrix.regions
    region_names = "、".join(region_display_name(c) for c in regions) if regions else "—"
    gen = generated_on.isoformat() if generated_on else ""

    header = (
        '<header class="topband"><div class="inner">'
        '<div class="kicker">RegImpact AI · 규제 변경 영향분석</div>'
        f'<h1>{_esc(title)}</h1>'
        '<div class="meta">'
        f'<span><b>정책</b> {_esc(matrix.policy_id)}</span>'
        f'<span><b>시행일</b> {_esc(policy_impact.effective_from)}</span>'
        f'<span><b>대상지역</b> {_esc(region_names)}</span>'
        f'<span><b>비교시점</b> {_esc(policy_impact.before_date)} → {_esc(policy_impact.after_date)}</span>'
        '</div></div></header>'
    )
    footer = (
        '<footer class="disc"><p><b>초안 성격 고지.</b> 이 리포트의 변경 추출은 AI 초안이며, '
        'LTV 판정은 사람이 확정한 결정적 룰엔진 출력입니다(AI가 규칙을 만들지 않음). '
        '지표는 6·30 단일 정책 seed 기준으로, 독립 3자 벤치마크가 아닙니다.</p>'
        f'<p class="gen">생성 {_esc(gen)} · 값 출처: 룰엔진·추출 실제 출력(하드코딩 없음)</p></footer>'
    )

    return (
        f'<!doctype html><html lang="ko"><head><meta charset="utf-8">'
        f'<meta name="viewport" content="width=device-width, initial-scale=1">'
        f'<title>{_esc(title)} — {_esc(matrix.policy_id)}</title>'
        f'<style>{_CSS}</style></head><body>'
        f'{header}<main>'
        f'{_assurance_section(grounding, gold)}'
        f'{_changes_section(extraction)}'
        f'{_proposal_section(proposal)}'
        f'{_impact_section(matrix)}'
        f'{_exposure_section(exposure, sensitivity, tornado)}'
        f'</main>{footer}</body></html>'
    )


_CSS = """
:root{
  --surface:#fcf8ff; --container:#f5f2ff; --container-2:#efecff; --card:#ffffff;
  --ink:#1a1a2e; --ink-soft:#43474e; --outline:#c4c6cf; --line:#e2e0fc;
  --primary:#022448; --secondary:#0051d5;
  --tighten:#ba1a1a; --tighten-bg:#ffdad6;
  --hold:#2e6b4f; --hold-bg:#cde6d8;
  --review:#7a5300; --review-bg:#ffddb2;
  --sans:"Noto Sans","Malgun Gothic",system-ui,-apple-system,"Segoe UI",sans-serif;
  --mono:"JetBrains Mono",ui-monospace,"SF Mono",Menlo,monospace;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --surface:#111421; --container:#171b2b; --container-2:#1c2133; --card:#1a1f30;
  --ink:#e9e9f4; --ink-soft:#b6bac6; --outline:#3a3f52; --line:#2a3047;
  --primary:#adc8f5; --secondary:#8ab0ff;
  --tighten:#ffb4ab; --tighten-bg:#3a1512;
  --hold:#8fd6ac; --hold-bg:#123322;
  --review:#edbf7f; --review-bg:#33260f;
}}
:root[data-theme="dark"]{
  --surface:#111421; --container:#171b2b; --container-2:#1c2133; --card:#1a1f30;
  --ink:#e9e9f4; --ink-soft:#b6bac6; --outline:#3a3f52; --line:#2a3047;
  --primary:#adc8f5; --secondary:#8ab0ff;
  --tighten:#ffb4ab; --tighten-bg:#3a1512;
  --hold:#8fd6ac; --hold-bg:#123322;
  --review:#edbf7f; --review-bg:#33260f;
}
*{box-sizing:border-box}
body{margin:0;background:var(--surface);color:var(--ink);font-family:var(--sans);
  line-height:1.6;-webkit-font-smoothing:antialiased;font-size:15px}
.topband{background:var(--primary);color:#fff}
:root[data-theme="dark"] .topband,
:root:not([data-theme="light"]) .topband{color:#0b1220}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]) .topband{color:#0b1220}}
.topband .inner{max-width:940px;margin:0 auto;padding:30px 22px 26px}
.kicker{font-family:var(--mono);font-size:.72rem;letter-spacing:.12em;text-transform:uppercase;opacity:.72}
.topband h1{margin:10px 0 0;font-size:clamp(1.5rem,1.1rem+1.6vw,2rem);font-weight:700;letter-spacing:-.02em}
.meta{margin-top:16px;display:flex;flex-wrap:wrap;gap:8px 22px;font-size:.84rem;font-family:var(--mono)}
.meta b{font-family:var(--sans);font-weight:400;opacity:.66;margin-right:5px}
main{max-width:940px;margin:0 auto;padding:26px 22px}
.panel{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:22px;margin-bottom:20px}
.panel h2{margin:0;font-size:1.18rem;font-weight:640;letter-spacing:-.01em}
.lead{margin:8px 0 18px;color:var(--ink-soft);font-size:.86rem;max-width:66ch}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px}
.tile{background:var(--container);border:1px solid var(--line);border-radius:11px;padding:14px 15px}
.t-label{font-size:.76rem;color:var(--ink-soft)}
.t-val{font-family:var(--mono);font-weight:700;font-size:1.55rem;margin-top:6px;letter-spacing:-.02em}
.tile.good .t-val{color:var(--hold)} .tile.warn .t-val{color:var(--review)}
.t-note{font-size:.7rem;color:var(--ink-soft);opacity:.8;margin-top:4px}
.foot-warn{margin:14px 0 0;color:var(--review);font-size:.8rem}
.changes{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:2px}
.change{padding:13px 0;border-bottom:1px solid var(--line)}
.change:last-child{border-bottom:none}
.c-head{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap}
.cat{font-family:var(--mono);font-size:.66rem;font-weight:700;letter-spacing:.05em;padding:3px 8px;border-radius:6px;
  background:var(--container-2);color:var(--secondary);white-space:nowrap}
.c-sum{font-weight:560;font-size:.92rem}
.ba{font-family:var(--mono);font-size:.8rem;display:inline-flex;align-items:center;gap:8px;margin-left:auto}
.ba .b{color:var(--ink-soft)} .ba .arr{color:var(--outline)} .ba .a{color:var(--secondary);font-weight:600}
.cite{margin-top:6px;display:flex;gap:10px;align-items:baseline;flex-wrap:wrap}
.cite .q{font-size:.8rem;color:var(--ink-soft);font-style:italic;flex:1;min-width:60%}
.cite .src{font-family:var(--mono);font-size:.68rem;color:var(--outline)}
.tbl-wrap{overflow-x:auto;border:1px solid var(--line);border-radius:11px}
table{border-collapse:collapse;width:100%;min-width:520px;font-size:.87rem}
thead th{text-align:left;font-family:var(--mono);font-size:.66rem;letter-spacing:.05em;text-transform:uppercase;
  color:var(--ink-soft);font-weight:700;padding:11px 15px;background:var(--container);border-bottom:1px solid var(--line)}
th.r,td.r{text-align:right}
tbody td{padding:10px 15px;border-bottom:1px solid var(--line)}
tr.grp td{background:var(--container-2);font-weight:640;font-size:.82rem;padding:8px 15px;color:var(--primary)}
.grp-code{font-family:var(--mono);font-size:.68rem;color:var(--ink-soft);font-weight:400;margin-left:6px}
.seg{font-weight:540}
.num{font-family:var(--mono);font-variant-numeric:tabular-nums}
.delta{font-family:var(--mono);font-weight:650} .delta.neg{color:var(--tighten)} .delta.pos{color:var(--hold)}
.muted{color:var(--ink-soft);opacity:.65}
.dir{font-family:var(--mono);font-size:.72rem;font-weight:650;padding:3px 9px;border-radius:6px;white-space:nowrap}
.dir.t{background:var(--tighten-bg);color:var(--tighten)}
.dir.h{background:var(--hold-bg);color:var(--hold)}
.dir.r{background:var(--review-bg);color:var(--review)}
.dir.l{background:var(--hold-bg);color:var(--hold)}
.star{color:var(--tighten);font-weight:700}
.disp{font-family:var(--mono);font-size:.72rem;font-weight:650;padding:3px 9px;border-radius:6px;white-space:nowrap}
.disp.ok{background:var(--hold-bg);color:var(--hold)}
.disp.warn{background:var(--review-bg);color:var(--review)}
.disp.muted{background:var(--container-2);color:var(--ink-soft)}
h2 .draft{font-family:var(--mono);font-size:.6rem;font-weight:700;letter-spacing:.08em;
  vertical-align:middle;padding:2px 7px;border-radius:5px;background:var(--review-bg);color:var(--review);margin-left:8px}
.tbl-foot{display:flex;flex-wrap:wrap;gap:6px 20px;padding:12px 15px;font-size:.8rem;color:var(--ink-soft);
  background:var(--container);border-top:1px solid var(--line)}
.tbl-foot b{color:var(--ink);font-family:var(--mono)}
.chart-wrap{overflow-x:auto;margin:2px 0 16px}
svg.chart{max-width:100%;height:auto;min-width:340px}
svg.chart text{font-family:var(--sans)}
.c-lbl{fill:var(--ink);font-size:12px}
.c-val{fill:var(--ink-soft);font-size:11px;font-family:var(--mono)}
.c-cap{fill:var(--ink-soft);font-size:11px}
.c-review{fill:var(--review);font-size:11.5px;font-weight:600}
.c-axis{stroke:var(--outline);stroke-width:1}
.c-base{stroke:var(--primary);stroke-width:1.5;stroke-dasharray:3 3}
.c-base-lbl{fill:var(--primary);font-size:10px;font-family:var(--mono)}
.sub-chart{margin-top:16px;padding-top:14px;border-top:1px dashed var(--line)}
.sc-cap{font-size:.82rem;color:var(--ink-soft);margin-bottom:8px}
.disc{max-width:940px;margin:0 auto;padding:8px 22px 40px;color:var(--ink-soft);font-size:.78rem}
.disc b{color:var(--ink)} .disc .gen{font-family:var(--mono);font-size:.7rem;opacity:.7;margin-top:6px}
"""
