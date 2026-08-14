"""검증(Assurance) 화면 (data-path=verification-assurance) — 4 DEEP dimension 검증 결과.

Stitch 목업(assurance)의 가짜 수치(Citation 98%, Grandfathering 92% 등)를 정직하게 대체:
- ④ Rule-regression = tc_generator 회귀에서 **실측**(30/30, 카테고리별).
- ①②③ (Citation/Change/Exception) = RegChange Extractor LLM 실행이 필요 → **미측정(실측 대기)**로
  표기하고 임계값만 노출. 미측정 지표를 임의 수치로 채우지 않는다(LOCKED §4, 정직성).
근거: docs/metrics_spec.md §1~3, 브리프 §13.
"""
from __future__ import annotations

from ..tc_generator.regression import run_regression
from .chrome import esc, page, provenance_strip, title_block


def _dimension_cards(pass_rate: float, passed: int, total: int) -> str:
    measured = (
        '<div class="bg-surface-container-lowest rounded-xl border border-secondary/40 p-5">'
        '<div class="flex items-center justify-between mb-2">'
        '<span class="font-body-md font-semibold">④ Rule-regression</span>'
        '<span class="material-symbols-outlined text-secondary">check_circle</span></div>'
        f'<div class="font-h2 text-h2 text-secondary">{pass_rate:.0%}</div>'
        f'<div class="font-mono-label text-mono-label text-on-surface-variant">{passed}/{total} · 임계 100%</div>'
        '<div class="mt-2"><span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full '
        'bg-secondary-container text-on-secondary font-mono-label text-mono-label">실측(deterministic)</span></div></div>'
    )
    pending_dims = [
        ("① Citation/Source grounding", "환각 인용 탐지", "≥ 임계(초안)"),
        ("② Change Completeness", "변경 포착 완전성", "≥ 임계(초안)"),
        ("③ Exception · GF Recall", "예외·경과규정 재현율", "≥ 95%(초안)"),
    ]
    cards = [measured]
    for name, desc, thr in pending_dims:
        cards.append(
            '<div class="bg-surface-container-lowest rounded-xl border border-outline-variant/30 p-5">'
            '<div class="flex items-center justify-between mb-2">'
            f'<span class="font-body-md font-semibold text-on-surface-variant">{esc(name)}</span>'
            '<span class="material-symbols-outlined text-outline">schedule</span></div>'
            '<div class="font-h2 text-h2 text-outline">—</div>'
            f'<div class="font-mono-label text-mono-label text-on-surface-variant">{esc(desc)} · {esc(thr)}</div>'
            '<div class="mt-2"><span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full '
            'bg-tertiary-fixed text-on-tertiary-fixed-variant font-mono-label text-mono-label">실측 대기 (LLM 실행)</span></div></div>'
        )
    return '<div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">' + "".join(cards) + "</div>"


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
    return (
        '<div class="flex items-start gap-3 bg-tertiary-fixed/20 border border-tertiary-fixed rounded-lg p-4 '
        'font-body-sm text-body-sm text-on-surface">'
        '<span class="material-symbols-outlined text-on-tertiary-fixed-variant">lock</span>'
        '<span><b>검증 기준 고정 · 미측정은 미측정으로 표기.</b> Rule-regression은 명세에서 독립 유도한 '
        '오라클과의 차등 검증으로 지금 실측된다. Citation·Change·Exception 지표는 RegChange Extractor의 '
        '실제 LLM 1회 실행 후 첫 실측값이 채워지며, 그 전까지 임의 수치로 채우지 않는다.</span></div>'
    )


def _main() -> str:
    report = run_regression()
    by_cat = report.pass_rate_by_category()
    subtitle = (
        '4개 DEEP dimension의 검증 결과. 결정론적으로 계산 가능한 지표는 지금 실측하고, '
        'LLM 실행이 필요한 지표는 임계값만 노출한 채 <b>실측 대기</b>로 정직하게 표기한다.'
    )
    prov = provenance_strip([
        f"rule_regression={report.passed}/{report.total}",
        f"pass_rate={report.pass_rate:.0%}",
        f"categories={len(by_cat)}",
    ], engine_label="tc_generator 회귀 (실측)")
    return (
        title_block("검증 (Assurance)", subtitle)
        + prov
        + _honesty_note()
        + _dimension_cards(report.pass_rate, report.passed, report.total)
        + _regression_table(by_cat)
    )


def render() -> str:
    return page("verification-assurance", _main())
