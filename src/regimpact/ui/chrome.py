"""화면 공용 크롬(디자인 셸) — nav-aware 페이지 래퍼.

디자인 시스템(색·타이포·헤더)은 Stitch export에서 추출한 `templates/*.html`로 보존하고,
사이드바 nav는 활성 항목만 바꿔 각 화면이 올바른 위치를 강조하도록 동적 생성한다.
모든 화면 렌더러는 `page(active_path, main_html)`로 감싸 동일한 셸을 공유한다.
"""
from __future__ import annotations

import html
from pathlib import Path

_TPL = Path(__file__).resolve().parent / "templates"

# (data-path, material-icon, label) — 원본 export의 사이드바 순서 그대로.
NAV_ITEMS: list[tuple[str, str, str]] = [
    ("overview", "dashboard", "개요"),
    ("regulatory-analysis", "rule_folder", "규제 변경 분석"),
    ("impact-matrix", "grid_view", "임팩트 매트릭스"),
    ("rule-amendments", "edit_document", "Rule 변경안"),
    ("verification-assurance", "verified_user", "검증 (Assurance)"),
    ("portfolio-impact", "account_balance_wallet", "고객·포트폴리오 영향"),
    ("audit-trail", "history_edu", "감사추적"),
]

_ACTIVE = (
    'flex items-center gap-3 px-4 py-2.5 rounded transition-all '
    "bg-secondary-container text-on-secondary font-semibold"
)
_INACTIVE = (
    "flex items-center gap-3 px-4 py-2.5 rounded text-on-surface-variant "
    "hover:bg-surface-container hover:text-on-surface transition-all"
)


def esc(s: object) -> str:
    return html.escape(str(s))


def _nav(active_path: str) -> str:
    out = []
    for path, icon, label in NAV_ITEMS:
        if path == active_path:
            out.append(
                f'<a aria-current="page" class="{_ACTIVE}" data-path="{path}" href="#">'
                f'<span class="material-symbols-outlined text-[20px]">{icon}</span>'
                f"<span>{esc(label)}</span></a>"
            )
        else:
            out.append(
                f'<a class="{_INACTIVE}" data-path="{path}" href="#">'
                f'<span class="material-symbols-outlined text-[20px]">{icon}</span>'
                f"<span>{esc(label)}</span></a>"
            )
    return "".join(out)


def page(active_path: str, main_html: str) -> str:
    """활성 nav 경로 + main 콘텐츠 → 자기완결 HTML 페이지."""
    head_open = (_TPL / "head_open.html").read_text(encoding="utf-8")
    head_after_nav = (_TPL / "head_after_nav.html").read_text(encoding="utf-8")
    foot = (_TPL / "foot.html").read_text(encoding="utf-8")
    return head_open + _nav(active_path) + head_after_nav + main_html + foot


# ---- 공용 프레젠테이션 헬퍼 (여러 화면에서 재사용) ----

def title_block(title: str, subtitle_html: str) -> str:
    return (
        '<div class="flex flex-col gap-3 mb-2">'
        f'<div class="font-h1 text-h1 text-on-background">{esc(title)}</div>'
        f'<div class="font-body-md text-body-md text-on-surface-variant max-w-3xl">{subtitle_html}</div>'
        "</div>"
    )


def provenance_strip(items: list[str], engine_label: str = "regimpact (deterministic)") -> str:
    """엔진/평가 산출 근거 스트립 — '실제 출력'임을 명시."""
    extra = "".join(f"<span>{esc(x)}</span>" for x in items)
    return (
        '<div class="flex flex-wrap items-center gap-x-4 gap-y-1 font-mono-label text-mono-label '
        'text-on-surface-variant bg-surface-container-low px-4 py-2 rounded-lg '
        'border border-outline-variant/30">'
        '<span class="flex items-center gap-1.5 text-secondary">'
        '<span class="material-symbols-outlined text-[16px]">bolt</span>'
        f"{esc(engine_label)}</span>{extra}"
        '<span class="text-outline">· 값은 손으로 적지 않고 엔진/평가가 생성 (LOCKED §4)</span>'
        "</div>"
    )


def mono_chip(text: str, tone: str = "bg-surface-variant text-on-surface-variant") -> str:
    return (
        f'<span class="font-mono-data text-mono-data {tone} px-2 py-1 rounded">{esc(text)}</span>'
    )


def card(inner_html: str, extra: str = "") -> str:
    return (
        '<div class="bg-surface-container-lowest p-4 rounded-xl border '
        f'border-outline-variant/30 {extra}">{inner_html}</div>'
    )
