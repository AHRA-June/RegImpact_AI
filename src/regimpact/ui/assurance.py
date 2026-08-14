"""검증(Assurance) 화면 (data-path=verification-assurance) — 4 DEEP dimension 검증 결과.

Stitch 목업(assurance)의 가짜 수치(Citation 98%, Grandfathering 92% 등)를 정직하게 대체:
- ④ Rule-regression = tc_generator 회귀에서 **실측**(30/30, 카테고리별).
- ①②③ (Citation/Change/Exception) = RegChange Extractor **1회 실제 LLM 실행 산출물**을 결정론적
  채점기로 재계산해 실측. 추출 산출물이 없으면 '실측 대기'로 폴백(지어내지 않음, LOCKED §4).
근거: docs/metrics_spec.md §1~3, 브리프 §13.
"""
from __future__ import annotations

from ..extractor import measured_assurance
from ..report import build_validation_report
from ..tc_generator.regression import run_regression
from .chrome import esc, page, provenance_strip, title_block


def _dim_card(label: str, value: str | None, threshold: str, measured: bool, sub: str = "") -> str:
    if measured:
        border, icon, val_cls = "border-secondary/40", "check_circle text-secondary", "text-secondary"
        badge = ('<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full '
                 'bg-secondary-container text-on-secondary font-mono-label text-mono-label">실측</span>')
        val_html = f'<div class="font-h2 text-h2 {val_cls}">{esc(value)}</div>'
    else:
        border, icon, val_cls = "border-outline-variant/30", "schedule text-outline", "text-outline"
        badge = ('<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full '
                 'bg-tertiary-fixed text-on-tertiary-fixed-variant font-mono-label text-mono-label">실측 대기 (LLM 실행)</span>')
        val_html = '<div class="font-h2 text-h2 text-outline">—</div>'
    sub_html = f'<div class="font-mono-label text-mono-label text-on-surface-variant">{esc(sub)}</div>' if sub else ""
    return (
        f'<div class="bg-surface-container-lowest rounded-xl border {border} p-5">'
        '<div class="flex items-center justify-between mb-2">'
        f'<span class="font-body-md font-semibold">{esc(label)}</span>'
        f'<span class="material-symbols-outlined {icon}"></span></div>'
        f'{val_html}<div class="font-mono-label text-mono-label text-on-surface-variant">임계 {esc(threshold)}</div>'
        f'{sub_html}<div class="mt-2">{badge}</div></div>'
    )


def _dimension_cards() -> str:
    dims = build_validation_report().assurance_dimensions
    cards = "".join(
        _dim_card(d.label, d.value, d.threshold, d.measured)
        for d in dims
    )
    return '<div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">' + cards + "</div>"


def _regression_table(by_cat: dict[str, tuple[int, int, float]]) -> str:
    rows = []
    for cat, (passed, total, rate) in by_cat.items():
        ok = rate >= 1.0
        badge = (
            '<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-secondary-container '
            'text-on-secondary font-mono-label text-mono-label"><span class="material-symbols-outlined text-[14px]">check</span>PASS</span>'
            if ok else
            '<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-error-container '
            'text-on-error-container font-mono-label text-mono-label">FAIL</span>'
        )
        rows.append(
            '<tr class="hover:bg-surface-container-low/50">'
            f'<td class="p-3 font-mono-data text-mono-data font-semibold">{esc(cat)}</td>'
            f'<td class="p-3 text-right font-mono-data text-mono-data">{passed}/{total}</td>'
            f'<td class="p-3 text-right font-mono-data text-mono-data">{rate:.0%}</td>'
            f'<td class="p-3 text-center">{badge}</td></tr>'
        )
    return (
        '<div class="bg-surface-container-lowest rounded-xl border border-outline-variant/30 overflow-hidden">'
        '<div class="flex items-center gap-2 px-5 py-3 bg-surface-container-low">'
        '<span class="material-symbols-outlined text-secondary">rule</span>'
        '<h3 class="font-h3 text-h3">④ Rule-regression — 카테고리별 실측 (독립 오라클 차등 검증)</h3></div>'
        '<table class="w-full text-left border-collapse">'
        '<thead class="font-body-sm text-body-sm text-on-surface-variant">'
        '<tr><th class="p-3 font-semibold">카테고리</th><th class="p-3 font-semibold text-right">통과</th>'
        '<th class="p-3 font-semibold text-right">Pass Rate</th><th class="p-3 font-semibold text-center">판정</th></tr></thead>'
        f'<tbody class="divide-y divide-outline-variant/30">{"".join(rows)}</tbody></table></div>'
    )


def _honesty_note() -> str:
    m = measured_assurance()
    if m is not None:
        body = (
            f'<b>검증 기준 고정 · 실측 완료.</b> RegChange Extractor 1회 실제 LLM 실행'
            f'(<span class="font-mono-label">{esc(m.model)}</span>, {esc(m.run_date)})의 추출 {m.n_changes}건을 '
            '결정론적 채점기로 재계산해 ①②③을 실측했다(가짜 수치 없음). ④ Rule-regression은 명세에서 '
            '독립 유도한 오라클과의 차등 검증으로 실측된다. 지표는 저장값이 아니라 (추출+원문+gold)에서 항상 재계산된다.'
        )
    else:
        body = (
            '<b>검증 기준 고정 · 미측정은 미측정으로 표기.</b> Citation·Change·Exception 지표는 RegChange '
            'Extractor의 실제 LLM 1회 실행 후 채워지며, 그 전까지 임의 수치로 채우지 않는다.'
        )
    return (
        '<div class="flex items-start gap-3 bg-tertiary-fixed/20 border border-tertiary-fixed rounded-lg p-4 '
        'font-body-sm text-body-sm text-on-surface">'
        '<span class="material-symbols-outlined text-on-tertiary-fixed-variant">lock</span>'
        f'<span>{body}</span></div>'
    )


def _main() -> str:
    report = run_regression()
    by_cat = report.pass_rate_by_category()
    m = measured_assurance()
    subtitle = (
        '4개 DEEP dimension의 검증 결과. RegChange 계열(①②③)은 실제 LLM 추출 1회를 결정론적으로 '
        '재계산해 실측하고, Rule-regression(④)은 독립 오라클 차등 검증으로 실측한다.'
    )
    prov_items = [
        f"rule_regression={report.passed}/{report.total}",
        f"pass_rate={report.pass_rate:.0%}",
        f"categories={len(by_cat)}",
    ]
    if m is not None:
        prov_items = [f"extraction={m.n_changes}건({m.model})",
                      f"citation={m.citation_correctness:.0%}"] + prov_items
    prov = provenance_strip(prov_items, engine_label="RegChange 추출 + tc 회귀 (실측)")
    return (
        title_block("검증 (Assurance)", subtitle)
        + prov
        + _honesty_note()
        + _dimension_cards()
        + _regression_table(by_cat)
    )


def render() -> str:
    return page("verification-assurance", _main())
