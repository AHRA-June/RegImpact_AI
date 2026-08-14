"""고객·포트폴리오 영향 화면 (data-path=portfolio-impact) — 합성 포트폴리오 집계 렌더.

Stitch 목업(_3)의 환각(지역 "강남/부산/분당", "Normal 60→40" 등)을 대체. 합성 포트폴리오
각 차주의 Before/After LTV는 rule_engine 실제 판정이며, 집계 수치를 지어내지 않는다.
포트폴리오 자체는 **합성(synthetic)** 임을 화면 상단에 명시한다(LOCKED §8).
"""
from __future__ import annotations

from ..impact.portfolio import PortfolioImpact, analyze_portfolio
from .chrome import esc, page, provenance_strip, title_block

# LTV 버킷 표시 순서·색
_BUCKET_ORDER = ["70%", "60%", "40%", "0%", "명세부재", "Discovery", "범위외"]
_BUCKET_TONE = {
    "70%": "bg-secondary-container",
    "60%": "bg-tertiary-fixed-dim",
    "40%": "bg-error-container",
    "0%": "bg-error",
    "명세부재": "bg-surface-container-highest",
    "Discovery": "bg-surface-variant",
    "범위외": "bg-surface-variant",
}


def _kpi_cards(r: PortfolioImpact) -> str:
    pct = (r.impacted / r.size * 100) if r.size else 0
    cards = [
        ("영향 차주 (Impacted)", f"{r.impacted:,}", f"{pct:.0f}% of {r.size:,}", "text-error", "groups"),
        ("경과규정 보호", f"{r.grandfathered:,}", "종전규정 유지", "text-on-tertiary-fixed-variant", "history"),
        ("고위험 (LTV 0%)", f"{r.high_risk:,}", "사실상 신규취급 불가", "text-error", "warning"),
        ("Discovery (수동검토)", f"{r.discovery:,}", "자동판정 제외", "text-on-surface-variant", "search_insights"),
    ]
    out = ['<div class="grid grid-cols-2 md:grid-cols-4 gap-4">']
    for label, value, sub, color, icon in cards:
        out.append(
            '<div class="bg-surface-container-lowest p-4 rounded-xl border border-outline-variant/30">'
            '<div class="flex items-center gap-2 text-on-surface-variant mb-2">'
            f'<span class="material-symbols-outlined text-[18px]">{icon}</span>'
            f'<span class="font-body-sm text-body-sm">{esc(label)}</span></div>'
            f'<div class="font-h2 text-h2 {color}">{esc(value)}</div>'
            f'<div class="font-body-sm text-body-sm text-on-surface-variant">{esc(sub)}</div></div>'
        )
    out.append("</div>")
    return "".join(out)


def _bar_row(label: str, count: int, total: int, tone: str) -> str:
    pct = (count / total * 100) if total else 0
    return (
        '<div class="flex items-center gap-3">'
        f'<div class="w-28 shrink-0 font-body-sm text-body-sm text-on-surface-variant text-right">{esc(label)}</div>'
        '<div class="flex-1 bg-surface-container-high rounded-full h-5 overflow-hidden">'
        f'<div class="{tone} h-5 rounded-full" style="width:{pct:.1f}%"></div></div>'
        f'<div class="w-24 shrink-0 font-mono-data text-mono-data">{count:,} ({pct:.0f}%)</div>'
        "</div>"
    )


def _borrower_type_chart(r: PortfolioImpact) -> str:
    total = r.size
    items = sorted(r.by_borrower_type.items(), key=lambda kv: -kv[1])
    bars = "".join(
        _bar_row(name, cnt, total, "bg-secondary-container") for name, cnt in items
    )
    return (
        '<div class="bg-surface-container-lowest rounded-xl border border-outline-variant/30 p-6">'
        '<div class="flex items-center gap-2 mb-4"><span class="material-symbols-outlined text-secondary">bar_chart</span>'
        '<h3 class="font-h3 text-h3">차주 유형 분포 (Impact by Borrower Type)</h3></div>'
        f'<div class="flex flex-col gap-2">{bars}</div></div>'
    )


def _ltv_dist_column(header: str, dist: dict[str, int], total: int) -> str:
    bars = "".join(
        _bar_row(b, dist[b], total, _BUCKET_TONE.get(b, "bg-surface-variant"))
        for b in _BUCKET_ORDER if dist.get(b)
    )
    return (
        '<div>'
        f'<div class="font-mono-label text-mono-label text-on-surface-variant mb-3">{esc(header)}</div>'
        f'<div class="flex flex-col gap-2">{bars}</div></div>'
    )


def _ltv_distribution(r: PortfolioImpact) -> str:
    return (
        '<div class="bg-surface-container-lowest rounded-xl border border-outline-variant/30 p-6">'
        '<div class="flex items-center gap-2 mb-4"><span class="material-symbols-outlined text-secondary">stacked_bar_chart</span>'
        '<h3 class="font-h3 text-h3">Before / After LTV 분포</h3></div>'
        '<div class="grid grid-cols-1 md:grid-cols-2 gap-8">'
        + _ltv_dist_column(f"Before ({r.before_date.isoformat()})", r.before_ltv_dist, r.size)
        + _ltv_dist_column(f"After ({r.after_date.isoformat()})", r.after_ltv_dist, r.size)
        + "</div></div>"
    )


def _synthetic_banner(r: PortfolioImpact) -> str:
    return (
        '<div class="flex items-start gap-3 bg-tertiary-fixed/20 border border-tertiary-fixed rounded-lg p-4 '
        'font-body-sm text-body-sm text-on-surface">'
        '<span class="material-symbols-outlined text-on-tertiary-fixed-variant">warning</span>'
        f'<span><b>합성 포트폴리오 결과(실데이터 아님).</b> {r.size:,}명을 층화 비율로 결정론적 생성한 '
        '가정 데이터이며(LOCKED §8), 각 차주의 Before/After LTV는 rule_engine 실제 판정이다. '
        '집계 수치는 지어내지 않는다.</span></div>'
    )


def _main(r: PortfolioImpact) -> str:
    subtitle = (
        '규제 변경이 포트폴리오에 미치는 영향을 합성 차주 집합으로 시뮬레이션한다. 분포·KPI는 '
        '모두 각 차주를 룰엔진에 Before/After로 관통시킨 실제 판정의 집계다.'
    )
    prov = provenance_strip([
        f"size={r.size}",
        f"impacted={r.impacted}",
        f"high_risk={r.high_risk}",
        f"before={r.before_date.isoformat()}",
        f"after={r.after_date.isoformat()}",
    ], engine_label="synthetic portfolio × rule_engine")
    return (
        title_block("고객·포트폴리오 영향", subtitle)
        + _synthetic_banner(r)
        + prov
        + _kpi_cards(r)
        + _borrower_type_chart(r)
        + _ltv_distribution(r)
    )


def render(result: PortfolioImpact | None = None) -> str:
    result = result if result is not None else analyze_portfolio()
    return page("portfolio-impact", _main(result))
