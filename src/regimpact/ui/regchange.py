"""규제 변경 분석 화면 (data-path=regulatory-analysis) — RegChange 추출 결과 렌더.

Stitch 목업(_2)의 환각(예: "용인시 수지구", 가상 "AI CONFIDENCE 98.5%")을 사람이 확정한
골드 정답지(`docs/eval/regchange_gold_6_30.json`, LOCKED §4)와 원문 스냅샷 메타데이터
(`docs/sources/SOURCES.md`), 룰엔진 상수로 대체한다. 값을 지어내지 않는다.
"""
from __future__ import annotations

import json
from pathlib import Path

from ..extractor import measured_assurance
from ..impact.segments import REGION_LABELS
from ..rule_engine import LTV_BASELINE, LTV_REGULATED_STANDARD
from .chrome import card, esc, mono_chip, page, provenance_strip, title_block

_ROOT = Path(__file__).resolve().parents[3]
_GOLD_PATH = _ROOT / "docs" / "eval" / "regchange_gold_6_30.json"

# 원문 스냅샷 메타데이터 (docs/sources/SOURCES.md — 사람 확정, 공개 보도자료/FAQ만).
SOURCE_REGISTRY: list[dict[str, str]] = [
    {"doc_id": "FSC_PRESS_20260630", "org": "금융위원회", "published": "2026-06-30",
     "title": "규제지역 추가 지정 관련 긴급 가계부채 점검회의 (보도참고자료)", "hash": "403fb8fb…e8f39d23"},
    {"doc_id": "MOLIT_PRESS_20260630", "org": "국토교통부", "published": "2026-06-30",
     "title": "투기과열지구 및 조정대상지역 추가 지정 (보도참고자료)", "hash": "6115271b…66c11edd"},
    {"doc_id": "FAQ_20260630", "org": "관계기관 합동", "published": "2026-06-30",
     "title": "규제지역 추가 지정 관련 FAQ", "hash": "ef3dad7b…14ea7c9a"},
]

_CHANGE_LABELS = {
    "LTV_70_to_40": "주택담보대출 LTV 한도 축소",
    "effective_7_1": "시행일",
    "grandfathering": "경과규정(종전규정 적용)",
    "region_designation": "규제지역 신규 지정",
}


def load_gold(path: str | Path | None = None) -> dict:
    p = Path(path) if path else _GOLD_PATH
    return json.loads(p.read_text(encoding="utf-8"))


def _source_cards(gold: dict) -> str:
    cards = []
    for src in SOURCE_REGISTRY:
        cards.append(
            '<div class="bg-surface-container-lowest p-4 rounded-lg border border-outline-variant/30">'
            '<div class="flex items-center justify-between mb-2">'
            f'<span class="font-body-md font-semibold text-secondary">{esc(src["org"])}</span>'
            f'<span class="font-mono-label text-mono-label text-on-surface-variant">{esc(src["published"])}</span></div>'
            f'<div class="font-body-sm text-body-sm text-on-surface mb-2">{esc(src["title"])}</div>'
            f'<div class="flex items-center gap-2">{mono_chip(src["doc_id"])}'
            f'<span class="font-mono-label text-mono-label text-outline" title="sha256">#{esc(src["hash"])}</span></div>'
            "</div>"
        )
    return (
        '<div class="flex items-center gap-2 mb-3">'
        '<span class="material-symbols-outlined text-secondary">description</span>'
        f'<h3 class="font-h3 text-h3">공식 원문 {len(SOURCE_REGISTRY)}건 (Source Snapshot)</h3></div>'
        '<div class="grid grid-cols-1 md:grid-cols-3 gap-4">' + "".join(cards) + "</div>"
    )


def _before_after(gold: dict) -> str:
    regions = "".join(
        f'<span class="inline-flex items-center gap-1 px-3 py-1 rounded-full '
        f'bg-secondary-container text-on-secondary font-body-sm">'
        f'<span class="material-symbols-outlined text-[16px]">location_on</span>'
        f'{esc(REGION_LABELS.get(code, code))}</span>'
        for code in gold["target_regions"]
    )
    return (
        '<div class="bg-surface-container-lowest rounded-xl border border-outline-variant/30 p-6">'
        '<div class="flex items-center gap-2 mb-4">'
        '<span class="material-symbols-outlined text-secondary">difference</span>'
        '<h3 class="font-h3 text-h3">핵심 변경 — Before/After 파라미터 매핑</h3></div>'
        # LTV before/after
        '<div class="grid grid-cols-1 md:grid-cols-2 gap-6 items-stretch">'
        '<div class="bg-surface-container-low rounded-lg p-5 border border-outline-variant/30">'
        '<div class="font-mono-label text-mono-label text-on-surface-variant mb-1">AS-IS (비규제지역 기준)</div>'
        f'<div class="font-h1 text-h1 text-on-surface">{LTV_BASELINE:.0%}</div>'
        '<div class="font-body-sm text-body-sm text-on-surface-variant">무주택자 표준 LTV</div></div>'
        '<div class="bg-error-container/40 rounded-lg p-5 border border-error/30">'
        '<div class="font-mono-label text-mono-label text-on-error-container mb-1">TO-BE (규제지역 지정 후) '
        '<span class="text-outline">[FSC][FAQ Q2]</span></div>'
        f'<div class="font-h1 text-h1 text-error">{LTV_REGULATED_STANDARD:.0%}</div>'
        '<div class="font-body-sm text-body-sm text-on-surface-variant">무주택자 표준 LTV</div></div>'
        "</div>"
        # regions
        '<div class="mt-6">'
        '<div class="font-mono-label text-mono-label text-on-surface-variant mb-2">적용 대상 지역 (신규 규제지역)</div>'
        f'<div class="flex flex-wrap gap-2">{regions}</div></div>'
        "</div>"
    )


def _exceptions(gold: dict) -> str:
    ex_items = "".join(
        '<li class="flex items-start gap-2">'
        '<span class="material-symbols-outlined text-[18px] text-secondary">check_circle</span>'
        f'<span>{esc(e["name"])} — 예외 계층 유지 (키워드: {esc(", ".join(e["keywords"]))})</span></li>'
        for e in gold["exceptions"]
    )
    return (
        '<div class="bg-surface-container-lowest rounded-xl border border-outline-variant/30 p-6">'
        '<div class="flex items-center gap-2 mb-4">'
        '<span class="material-symbols-outlined text-on-tertiary-fixed-variant">history</span>'
        '<h3 class="font-h3 text-h3">예외 · 경과규정 (Grandfathering)</h3></div>'
        '<ul class="flex flex-col gap-2 font-body-md text-body-md text-on-surface mb-4">'
        '<li class="flex items-start gap-2">'
        '<span class="material-symbols-outlined text-[18px] text-on-tertiary-fixed-variant">check_circle</span>'
        '<span>지정일 이전(2026-06-30까지) 대출 신청 전산 등록 완료 또는 계약+계약금 → 종전규정(LTV 70%) 적용 '
        '<span class="text-outline">[FAQ Q5][FSC]</span></span></li>'
        f"{ex_items}</ul></div>"
    )


def _required_changes(gold: dict) -> str:
    rows = []
    for ch in gold["required_changes"]:
        label = _CHANGE_LABELS.get(ch["id"], ch["id"])
        cats = " ".join(mono_chip(c) for c in ch["categories"])
        kws = ", ".join(ch["keywords"])
        rows.append(
            '<tr class="hover:bg-surface-container-low/50">'
            f'<td class="p-3 font-semibold">{esc(label)}</td>'
            f'<td class="p-3">{cats}</td>'
            f'<td class="p-3 font-body-sm text-on-surface-variant">{esc(kws)}</td>'
            '<td class="p-3 text-center"><span class="material-symbols-outlined text-secondary">fact_check</span></td>'
            "</tr>"
        )
    return (
        '<div class="w-full overflow-x-auto bg-surface-container-lowest rounded-xl border border-outline-variant/30">'
        '<table class="w-full text-left border-collapse">'
        '<thead class="bg-surface-container-low font-body-sm text-body-sm text-on-surface-variant">'
        '<tr><th class="p-3 font-semibold">필수 변경 항목</th><th class="p-3 font-semibold">카테고리</th>'
        '<th class="p-3 font-semibold">근거 키워드</th><th class="p-3 font-semibold text-center">채점 대상</th></tr></thead>'
        f'<tbody class="divide-y divide-outline-variant/30 font-body-md text-body-md">{"".join(rows)}</tbody>'
        "</table></div>"
    )


def _main(gold: dict) -> str:
    subtitle = (
        '공식 원문에서 <b>무엇이 달라졌는지</b>를 구조화 추출한 결과. 수치·지역·예외는 사람이 확정한 '
        '골드 정답지와 룰엔진 상수에서 오며, 화면에서 지어내지 않는다(신뢰도 수치 등 미검증 값 표기 금지).'
    )
    prov = provenance_strip([
        f"gold={_GOLD_PATH.name}",
        f'policy={gold["policy_id"]}',
        f'effective_from={gold["effective_from"]}',
        f'sources={len(SOURCE_REGISTRY)}',
    ], engine_label="RegChange gold (사람 확정)")
    return (
        title_block("규제 변경 분석", subtitle)
        + prov
        + _extraction_assurance()
        + _source_cards(gold)
        + _before_after(gold)
        + _exceptions(gold)
        + '<div class="flex items-center gap-2 mt-2 mb-1">'
          '<span class="material-symbols-outlined text-secondary">checklist</span>'
          '<h3 class="font-h3 text-h3">필수 변경 항목 (Extractor 채점 기준)</h3></div>'
        + _required_changes(gold)
    )


def _extraction_assurance() -> str:
    """AI 추출 1회 실측 결과(있으면). Citation grounding·완전성·재현율."""
    m = measured_assurance()
    if m is None:
        return ""
    metrics = [
        ("Citation Correctness", f"{m.citation_correctness:.0%}", f"환각 {m.unsupported_claim_rate:.0%}"),
        ("Change Completeness", f"{m.change_completeness:.0%}", "필수 변경 포착"),
        ("Exception Recall", f"{m.exception_recall:.0%}", "예외 재현"),
        ("추출 항목", f"{m.n_changes}건", "원문 verbatim 인용"),
    ]
    cells = "".join(
        '<div class="bg-surface-container-lowest rounded-lg border border-secondary/40 p-4">'
        f'<div class="font-body-sm text-body-sm text-on-surface-variant mb-1">{esc(label)}</div>'
        f'<div class="font-h3 text-h3 text-secondary">{esc(val)}</div>'
        f'<div class="font-mono-label text-mono-label text-on-surface-variant">{esc(sub)}</div></div>'
        for label, val, sub in metrics
    )
    return (
        '<div class="bg-secondary-container/20 rounded-xl border border-secondary/30 p-5">'
        '<div class="flex items-center gap-2 mb-3">'
        '<span class="material-symbols-outlined text-secondary">psychology</span>'
        '<h3 class="font-h3 text-h3">AI 추출 실측 (RegChange Extractor 1회 실행)</h3>'
        f'<span class="font-mono-label text-mono-label text-on-surface-variant">{esc(m.model)} · {esc(m.run_date)}</span></div>'
        '<p class="font-body-sm text-body-sm text-on-surface-variant mb-4 max-w-3xl">'
        '모델이 원문만 읽고 추출한 결과를 결정론적 채점기로 재계산한 실측값. 인용은 원문 verbatim '
        '존재를 확인했고(grounding), 완전성·재현율은 gold와 대조했다. 지어낸 수치가 아니다.</p>'
        f'<div class="grid grid-cols-2 md:grid-cols-4 gap-4">{cells}</div></div>'
    )


def render(gold: dict | None = None) -> str:
    gold = gold if gold is not None else load_gold()
    return page("regulatory-analysis", _main(gold))
