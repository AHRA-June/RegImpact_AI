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
        + _gold_set_panel()
    )


def _gold_set_tile(label: str, value: str, sub: str, opened: bool) -> str:
    border = "border-secondary/40" if opened else "border-outline-variant/30"
    icon = "lock_open" if opened else "lock"
    sub_cls = "text-secondary" if opened else "text-on-tertiary-fixed-variant"
    return (
        f'<div class="bg-surface-container-low rounded-lg p-4 border {border}">'
        f'<div class="font-body-sm text-body-sm text-on-surface-variant mb-1">{esc(label)}</div>'
        f'<div class="font-h2 text-h2 text-secondary">{esc(value)}</div>'
        f'<div class="inline-flex items-center gap-1 font-mono-label text-mono-label {sub_cls}">'
        f'<span class="material-symbols-outlined text-[14px]">{icon}</span>{esc(sub)}</div></div>'
    )


def _gold_set_panel() -> str:
    """평가셋 freeze 상태 + 회귀(누수 방지 §12 / 최종 개봉)."""
    from ..eval import load_final_eval, load_manifest, run_gold_regression

    m = load_manifest()
    dev = run_gold_regression("dev")
    final = load_final_eval()
    cats = "".join(
        '<div class="flex items-center justify-between font-body-sm text-body-sm py-0.5">'
        f'<span>{esc(cat)}</span><span class="font-mono-data text-mono-data">{p}/{t} ({r:.0%})</span></div>'
        for cat, (p, t, r) in sorted(dev.pass_rate_by_category().items())
    )
    dev_tile = _gold_set_tile("DEV (상시 회귀)", f"{dev.pass_rate:.0%}", f"{dev.passed}/{dev.total}", True)
    if final is not None:
        ls, cs = final["splits"]["locked"], final["splits"]["challenge"]
        locked_tile = _gold_set_tile("LOCKED (개봉)", f"{ls['pass_rate']:.0%}", f"{ls['passed']}/{ls['total']}", True)
        chal_tile = _gold_set_tile("CHALLENGE (개봉)", f"{cs['pass_rate']:.0%}", f"{cs['passed']}/{cs['total']}", True)
        footer = (f'최초·최종 개봉({esc(final["_meta"]["opened_date"])}, §12): 전체 '
                  f'{final["overall"]["passed"]}/{final["overall"]["total"]} '
                  f'({final["overall"]["pass_rate"]:.0%}). 이후 재튜닝·재보고 금지. 정답은 독립 명세 오라클에서 유도.')
    else:
        locked_tile = _gold_set_tile("LOCKED TEST", str(m["splits"]["locked"]["count"]), "sealed", False)
        chal_tile = _gold_set_tile("CHALLENGE", str(m["splits"]["challenge"]["count"]), "sealed", False)
        footer = ('누수 방지(§12): LOCKED·CHALLENGE는 개발 중 열지 않는다(코어 완성 후 최종 1회). '
                  '정답은 독립 명세 오라클에서 유도.')
    return (
        '<div class="bg-surface-container-lowest rounded-xl border border-outline-variant/30 p-6 mt-2">'
        '<div class="flex items-center gap-2 mb-3"><span class="material-symbols-outlined text-secondary">dataset</span>'
        f'<h3 class="font-h3 text-h3">Gold Set 평가셋 (freeze {esc(m["version"])} · 총 {m["total"]}문항)</h3></div>'
        f'<div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">{dev_tile}{locked_tile}{chal_tile}</div>'
        f'<div class="grid grid-cols-1 md:grid-cols-2 gap-x-8">{cats}</div>'
        f'<div class="font-body-sm text-body-sm text-on-surface-variant mt-3">{footer}</div></div>'
    )


def render() -> str:
    return page("verification-assurance", _main())
