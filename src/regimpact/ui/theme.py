"""Stitch 디자인 시스템 — 목업에서 그대로 가져온 토큰·셸.

`docs/ui/stitch_export/`의 Stitch 1차 산출물에서 **디자인만** 추출했다. 디자인은 좋았고
문제는 데이터였으므로(2026-08-10 리뷰: 지역을 세종·부산·강남으로, LTV 60→50 등 환각),
껍데기는 보존하고 **내용물만 엔진 실제 출력으로 갈아끼운다**.

TAILWIND_CONFIG는 `stitch_export/_1/code.html`의 `<script id="tailwind-config">`를 **그대로**
옮긴 것이다(색·타이포·반경·간격 토큰). 손으로 고치지 말고, 디자인이 바뀌면 export에서 다시 가져온다.
"""
from __future__ import annotations

import html as _html
import re as _re

TAILWIND_CONFIG = r"""{theme:{extend:{"colors":{"on-background":"#1a1a2e","secondary":"#0051d5","on-primary-fixed":"#001c3b","surface-container-low":"#f5f2ff","on-primary-fixed-variant":"#2d486d","secondary-fixed-dim":"#b4c5ff","secondary-container":"#316bf3","tertiary-container":"#503300","surface-dim":"#dad7f3","on-secondary-container":"#fefcff","on-secondary":"#ffffff","on-secondary-fixed":"#00174b","on-surface":"#1a1a2e","on-primary":"#ffffff","on-error":"#ffffff","on-primary-container":"#8aa4cf","on-tertiary-container":"#c69b5f","error":"#ba1a1a","surface-container-lowest":"#ffffff","surface-tint":"#455f87","surface-variant":"#e2e0fc","on-surface-variant":"#43474e","surface-bright":"#fcf8ff","primary-container":"#1e3a5f","surface-container":"#efecff","on-tertiary-fixed":"#291800","primary":"#022448","inverse-primary":"#adc8f5","on-secondary-fixed-variant":"#003ea8","tertiary-fixed":"#ffddb2","on-tertiary-fixed-variant":"#60410c","background":"#fcf8ff","primary-fixed-dim":"#adc8f5","surface-container-highest":"#e2e0fc","surface-container-high":"#e8e5ff","surface":"#fcf8ff","secondary-fixed":"#dbe1ff","tertiary":"#341f00","inverse-on-surface":"#f2efff","error-container":"#ffdad6","outline":"#74777f","on-tertiary":"#ffffff","outline-variant":"#c4c6cf","primary-fixed":"#d5e3ff","on-error-container":"#93000a","inverse-surface":"#2f2e43","tertiary-fixed-dim":"#edbf7f"},"borderRadius":{"DEFAULT":"0.125rem","lg":"0.25rem","xl":"0.5rem","full":"0.75rem"},"spacing":{"unit":"4px","component-gap-sm":"8px","section-margin":"32px","component-gap-md":"12px","gutter":"16px","container-padding":"24px"},"fontFamily":{"body-sm":["Noto Sans"],"h3":["Noto Sans"],"body-lg":["Noto Sans"],"body-md":["Noto Sans"],"h1":["Noto Sans"],"mono-label":["JetBrains Mono"],"h2":["Noto Sans"],"mono-data":["JetBrains Mono"]},"fontSize":{"body-sm":["12px",{"lineHeight":"18px","fontWeight":"400"}],"h3":["20px",{"lineHeight":"28px","fontWeight":"600"}],"body-lg":["16px",{"lineHeight":"24px","fontWeight":"400"}],"body-md":["14px",{"lineHeight":"20px","fontWeight":"400"}],"h1":["30px",{"lineHeight":"38px","letterSpacing":"-0.02em","fontWeight":"700"}],"mono-label":["12px",{"lineHeight":"16px","letterSpacing":"0.02em","fontWeight":"500"}],"h2":["24px",{"lineHeight":"32px","letterSpacing":"-0.01em","fontWeight":"600"}],"mono-data":["13px",{"lineHeight":"20px","fontWeight":"400"}]}}}}"""

# ---------------------------------------------------------------- 토큰 → 정적 CSS
#
# Stitch export는 `cdn.tailwindcss.com`(런타임 JIT)에 의존한다. 그러면 네트워크 없이 열었을 때
# 스타일이 통째로 사라지고, 포트폴리오 산출물로는 취약하다. 그래서 **같은 토큰에서 정적 CSS를
# 생성**해 문서에 인라인한다 — 외부 요청 0회로 동일한 디자인이 나온다.
# 색·타이포 값은 위 TAILWIND_CONFIG 하나에서만 읽는다(단일 출처).

_COLORS: dict[str, str] = dict(
    _re.findall(r'"([a-z0-9\-]+)":"(#[0-9a-fA-F]{6})"', TAILWIND_CONFIG)
)
_FONT_SIZES: dict[str, tuple[str, str, str]] = {
    name: (size, lh, fw)
    for name, size, lh, fw in _re.findall(
        r'"([a-z0-9\-]+)":\["(\d+px)",\{"lineHeight":"(\d+px)"(?:,"letterSpacing":"[^"]*")?,"fontWeight":"(\d+)"\}\]',
        TAILWIND_CONFIG,
    )
}
_MONO = ("mono-data", "mono-label")


def _rgba(name: str, alpha: int) -> str:
    h = _COLORS[name].lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha / 100:.2f})"


def _css_vars() -> str:
    """같은 토큰을 CSS 변수로도 낸다.

    유틸리티 클래스(`.bg-primary`)는 Stitch 목업을 그대로 옮기는 데 쓰고, 장문 문서·랜딩은
    직접 쓴 CSS 라 변수(`var(--primary)`)가 필요하다. **출처는 하나(_COLORS)** 여야
    두 표현이 갈라지지 않는다.
    """
    body = "".join(f"--{name}:{hexv};" for name, hexv in _COLORS.items())
    return f":root{{{body}}}"


def _color_rules() -> str:
    out = []
    for name, hexv in _COLORS.items():
        out.append(f".bg-{name}{{background-color:{hexv}}}")
        out.append(f".text-{name}{{color:{hexv}}}")
        out.append(f".border-{name}{{border-color:{hexv}}}")
    # 실제로 쓰는 반투명 변형만 명시적으로 생성 (rgba 사전 계산 — 구형 브라우저 안전)
    for name, alpha, prop in (
        ("primary-fixed", 60, "background-color"),
        ("surface", 90, "background-color"),
        ("tertiary-fixed", 30, "background-color"),
        ("outline-variant", 20, "border-color"),
        ("outline-variant", 30, "border-color"),
        ("outline-variant", 40, "border-color"),
        ("outline-variant", 50, "border-color"),
    ):
        key = "bg" if prop == "background-color" else "border"
        out.append(f".{key}-{name}\\/{alpha}{{{prop}:{_rgba(name, alpha)}}}")
    out.append(
        f".divide-outline-variant\\/30>*+*{{border-color:{_rgba('outline-variant', 30)}}}"
    )
    out.append(
        f".hover\\:bg-surface-container-low\\/50:hover"
        f"{{background-color:{_rgba('surface-container-low', 50)}}}"
    )
    # 사이드바·탭 hover
    for name in ("surface-container", "surface-container-highest"):
        out.append(f".hover\\:bg-{name}:hover{{background-color:{_COLORS[name]}}}")
    out.append(f".hover\\:text-on-surface:hover{{color:{_COLORS['on-surface']}}}")
    return "".join(out)


def _type_rules() -> str:
    out = []
    for name, (size, lh, fw) in _FONT_SIZES.items():
        family = "\'JetBrains Mono\',ui-monospace,monospace" if name in _MONO else \
                 "\'Noto Sans\',system-ui,-apple-system,\'Malgun Gothic\',sans-serif"
        out.append(f".font-{name}{{font-family:{family}}}")
        out.append(f".text-{name}{{font-size:{size};line-height:{lh};font-weight:{fw}}}")
    return "".join(out)


_LAYOUT_CSS = """
*,*::before,*::after{box-sizing:border-box}
html,body{margin:0;padding:0}
body{overscroll-behavior:none;font-family:'Noto Sans',system-ui,-apple-system,'Malgun Gothic',sans-serif}
a{text-decoration:none;color:inherit}
table{border-collapse:collapse}
pre{margin:0}
ul{margin:0;padding:0;list-style:none}
button{font:inherit;border:0;cursor:pointer}
[hidden]{display:none!important}
.flex{display:flex}.grid{display:grid}.flex-col{flex-direction:column}
.flex-wrap{flex-wrap:wrap}.flex-1{flex:1 1 0%}.shrink-0{flex-shrink:0}
.grid-cols-2{grid-template-columns:repeat(2,minmax(0,1fr))}
.grid-cols-3{grid-template-columns:repeat(3,minmax(0,1fr))}
.grid-cols-4{grid-template-columns:repeat(4,minmax(0,1fr))}
.items-center{align-items:center}.items-start{align-items:flex-start}
.items-baseline{align-items:baseline}
.justify-between{justify-content:space-between}.justify-center{justify-content:center}
.gap-1{gap:4px}.gap-2{gap:8px}.gap-3{gap:12px}.gap-4{gap:16px}.gap-6{gap:24px}.gap-8{gap:32px}
.space-y-1>*+*{margin-top:4px}
.p-4{padding:16px}.p-5{padding:20px}.p-6{padding:24px}
.px-2{padding-left:8px;padding-right:8px}.px-3{padding-left:12px;padding-right:12px}
.px-4{padding-left:16px;padding-right:16px}.px-6{padding-left:24px;padding-right:24px}
.px-8{padding-left:32px;padding-right:32px}
.py-1{padding-top:4px;padding-bottom:4px}.py-1\.5{padding-top:6px;padding-bottom:6px}
.py-2{padding-top:8px;padding-bottom:8px}.py-2\.5{padding-top:10px;padding-bottom:10px}
.py-3{padding-top:12px;padding-bottom:12px}.py-4{padding-top:16px;padding-bottom:16px}
.py-8{padding-top:32px;padding-bottom:32px}
.pl-6{padding-left:24px}.pl-72{padding-left:288px}.pt-16{padding-top:64px}.pt-6{padding-top:24px}
.pt-4{padding-top:16px}.pb-1{padding-bottom:4px}
.glance{scroll-margin-top:80px}
.pg-explain .pe-row{display:grid;grid-template-columns:170px minmax(0,1fr);gap:12px}
.pg-explain .pe-q{font-size:12.5px;font-weight:600;color:var(--on-surface-variant)}
.pg-explain .pe-a{font-size:13.5px;line-height:21px}
@media (max-width:640px){.pg-explain .pe-row{grid-template-columns:minmax(0,1fr);gap:2px}}
.mb-2{margin-bottom:8px}.mb-3{margin-bottom:12px}.mb-4{margin-bottom:16px}.mt-6{margin-top:24px}
.fixed{position:absolute}.top-0{top:0}.left-0{left:0}.right-0{right:0}.left-72{left:288px}
.z-40{z-index:40}.z-50{z-index:50}
.w-2{width:8px}.w-7{width:28px}.w-8{width:32px}.w-40{width:160px}.w-44{width:176px}
.w-72{width:288px}.w-full{width:100%}
.h-2{height:8px}.h-6{height:24px}.h-7{height:28px}.h-8{height:32px}.h-16{height:64px}
.h-px{height:1px}.h-full{height:100%}.min-h-screen{min-height:100vh}
.max-w-xs{max-width:320px}.max-w-md{max-width:448px}.max-w-3xl{max-width:768px}
.overflow-hidden{overflow:hidden}.overflow-x-auto{overflow-x:auto}.overflow-y-auto{overflow-y:auto}
.rounded{border-radius:2px}.rounded-lg{border-radius:4px}.rounded-xl{border-radius:8px}
.rounded-full{border-radius:9999px}
.border{border-width:1px;border-style:solid}
.border-b{border-bottom-width:1px;border-bottom-style:solid}
.border-t{border-top-width:1px;border-top-style:solid}
.border-l{border-left-width:1px;border-left-style:solid}
.border-r{border-right-width:1px;border-right-style:solid}
.border-collapse{border-collapse:collapse}
.divide-y>*+*{border-top-width:1px;border-top-style:solid}
.last\:border-0:last-child{border-width:0}
.shadow-sm{box-shadow:0 1px 2px rgba(0,0,0,.06),0 1px 3px rgba(0,0,0,.08)}
.text-left{text-align:left}.text-center{text-align:center}.text-right{text-align:right}
.align-top{vertical-align:top}
.font-medium{font-weight:500}.font-semibold{font-weight:600}
.uppercase{text-transform:uppercase}.tracking-tight{letter-spacing:-.01em}
.leading-6{line-height:24px}
.whitespace-nowrap{white-space:nowrap}
.truncate{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.transition-all,.transition-colors{transition:all .15s ease}
.backdrop-blur-md{backdrop-filter:blur(8px)}
.text-\[18px\]{font-size:18px}.text-\[20px\]{font-size:20px}.text-\[22px\]{font-size:22px}
.animate-pulse{animation:rip-pulse 2s cubic-bezier(.4,0,.6,1) infinite}
@keyframes rip-pulse{0%,100%{opacity:1}50%{opacity:.5}}
.rip-icon{display:inline-block;vertical-align:-.15em;fill:none;stroke:currentColor;
stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}
"""


_MOBILE_CSS = """
/* ------------------------------------------------------------------ 모바일
 * Stitch 목업은 데스크톱 전용이라 사이드바가 fixed w-72(288px)이고 본문에 pl-72 가 걸려 있다.
 * 390px 화면에서는 본문에 102px 밖에 남지 않아 글자가 통째로 무너진다.
 * 좁은 화면에서는 사이드바를 가로 스크롤 탭바로 눕히고 본문 패딩을 되돌린다.
 */
@media (max-width: 1023px){
  aside.fixed{position:static;width:100%;height:auto;border-right:0;
    border-bottom:1px solid var(--outline-variant);flex-direction:column}
  aside.fixed > div:first-child{height:auto;padding:12px 16px}
  aside.fixed nav{display:flex;flex-direction:row;gap:4px;overflow-x:auto;overflow-y:hidden;
    padding:0 12px 10px;-webkit-overflow-scrolling:touch;scrollbar-width:none}
  aside.fixed nav::-webkit-scrollbar{display:none}
  aside.fixed nav .nav-sec{display:none}   /* 섹션 라벨은 가로 탭바에서 자리만 차지한다 */
  aside.fixed nav > a{flex:0 0 auto;white-space:nowrap;padding:7px 12px;font-size:13px}
  aside.fixed > div:last-child{display:none}       /* 하단 캡션은 좁은 화면에서 생략 */
  header.fixed{position:static;left:0;height:auto;padding:10px 16px;flex-wrap:wrap;gap:8px;
    backdrop-filter:none}
  .pl-72{padding-left:0}
  .pt-16{padding-top:0}
  main{padding-left:16px !important;padding-right:16px !important}
  main table{display:block;width:100%;overflow-x:auto;white-space:nowrap}
  main pre{overflow-x:auto}
  /* 고정폭 열(w-40 등)이 좁은 화면에서 줄어들지 않아 페이지를 밀어낸다 */
  main .shrink-0{flex-shrink:1;min-width:0}
  main .w-40{width:auto;max-width:40%}
  /* 고정 열수 그리드가 안 접혀서 칸이 78px 이 되고 글자가 칸 밖으로 나간다 */
  main .grid-cols-4,main .grid-cols-3{grid-template-columns:repeat(2,minmax(0,1fr))}
  main .grid-cols-2{grid-template-columns:minmax(0,1fr)}
  main .grid > *{min-width:0}
  /* 카드 제목과 우측 주석이 한 줄을 나눠 가지면 제목이 두 줄로 쪼개진다 */
  main .items-baseline.justify-between{flex-direction:column;align-items:flex-start;gap:2px}
  /* 지표 숫자가 카드 폭을 넘겨 단위만 다음 줄로 떨어지는 것을 막는다 */
  main .text-h1{font-size:24px;line-height:32px}
  main .text-h2{font-size:20px;line-height:28px}
  main .p-5,main .p-6{padding:14px}
}
"""


def build_css() -> str:
    """디자인 토큰에서 정적 CSS를 만든다 — 외부 CDN 없이 동일한 화면."""
    return _css_vars() + _LAYOUT_CSS + _color_rules() + _type_rules() + _MOBILE_CSS


CSS = build_css()

# 아이콘: Material Symbols 폰트도 외부 요청이라, 오프라인에서 글자("shield_lock")로 새는 것을
# 막기 위해 인라인 SVG로 대체한다. 형태는 단순화하되 의미는 유지.
_ICON_PATHS = {
    "shield_lock": "M12 3l7 3v6c0 4-3 7-7 9-4-2-7-5-7-9V6l7-3z",
    "target": "M12 3v3M12 18v3M3 12h3M18 12h3M12 8a4 4 0 100 8 4 4 0 000-8z",
    "person": "M12 12a4 4 0 100-8 4 4 0 000 8zM4 20c0-3.3 3.6-5 8-5s8 1.7 8 5",
    "rule_folder": "M3 6a2 2 0 012-2h4l2 2h8a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V6zM8 13l2 2 4-4",
    "grid_view": "M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h6v6h-6z",
    "edit_document": "M14 3H7a2 2 0 00-2 2v14a2 2 0 002 2h10a2 2 0 002-2v-8M14 3l5 5M14 3v5h5M9 14l6-6",
    "verified_user": "M12 3l7 3v6c0 4-3 7-7 9-4-2-7-5-7-9V6l7-3zM9 12l2 2 4-4",
    "account_balance_wallet": "M3 8a2 2 0 012-2h12a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V8zM16 12h4M17 12h.01",
    "travel_explore": "M12 3a9 9 0 100 18 9 9 0 000-18zM3 12h18M12 3c2.5 2.5 2.5 15 0 18M12 3c-2.5 2.5-2.5 15 0 18",
    "gavel": "M6 18h8M4 14l6-6M8 4l6 6M11 3l4 4M7 7l4 4",
    "science": "M9 3v6l-5 9a2 2 0 002 3h12a2 2 0 002-3l-5-9V3M8 3h8M7 15h10",
    "dashboard": "M4 4h6v6H4zM14 4h6v4h-6zM14 12h6v8h-6zM4 14h6v6H4z",
    "home": "M3 11l9-8 9 8M5 10v10h5v-6h4v6h5V10",
    "upload_file": "M12 16V5M8 9l4-4 4 4M4 19h16",
    "hub": "M12 5a2 2 0 100-4 2 2 0 000 4zM5 21a2 2 0 100-4 2 2 0 000 4zM19 21a2 2 0 100-4 2 2 0 000 4zM12 5v6M12 11l-6 7M12 11l6 7",
    "search": "M10 4a6 6 0 100 12 6 6 0 000-12zM14.5 14.5L20 20",
}

FONTS = (
    '<link href="https://fonts.googleapis.com/css2?family=Noto+Sans:wght@400;500;600;700'
    '&amp;family=JetBrains+Mono:wght@400;500&amp;display=swap" rel="stylesheet"/>'
)

# 검색 색인 거부 — 이 사이트는 **링크를 받은 사람이 보는 자료**이지 검색으로 찾아올 자료가
# 아니다(공모전 제출·검증용). 저장소가 공개라 페이지 자체는 열리지만, 검색 결과로 흘러
# 다니지는 않게 한다. robots.txt 로 크롤링을 막지 않는 이유: 크롤러가 못 읽으면 이 태그도
# 못 읽어서 색인 제거가 오히려 안 된다.
NOINDEX = '<meta name="robots" content="noindex, nofollow"/>'

# 전역 내비게이션 — **모든 페이지가 같은 메뉴를 쓴다** (랜딩 제외: 랜딩이 곧 홈이다).
# 화면마다 메뉴가 달라 길을 잃는 문제(2026-08-19 사용자 리뷰)를 이 단일 정의로 해소한다.
# (섹션 라벨, ((파일명, 라벨, 아이콘), ...))
NAV_SECTIONS = (
    (None, (
        ("index.html", "홈", "home"),
    )),
    ("파이프라인", (
        ("sources.html", "규제 문서 등록", "upload_file"),
        ("regchange.html", "규제 변경 분석", "rule_folder"),
        ("impact_matrix.html", "임팩트 매트릭스", "grid_view"),
        ("rule.html", "룰 변경안", "edit_document"),
        ("portfolio.html", "고객·포트폴리오 영향", "account_balance_wallet"),
        ("assurance.html", "검증", "verified_user"),
        ("playground.html", "판정 플레이그라운드", "science"),
        ("graph.html", "영향 지식그래프", "hub"),
        ("search.html", "규제 원문 검색", "search"),
    )),
    ("검증 문서", (
        ("validation_summary.html", "검증 요약", "dashboard"),
        ("validation_report.html", "검증보고서", "gavel"),
        ("model_system_card.html", "모델·시스템 카드", "person"),
        ("ai_risk_register.html", "AI 리스크 레지스터", "shield_lock"),
    )),
)

# 평탄화된 목록 — 기존 사용처(테스트 포함) 호환
NAV = tuple(item for _, items in NAV_SECTIONS for item in items)


def esc(value) -> str:
    """모든 데이터는 이스케이프해서 넣는다 — 추출 텍스트가 원문에서 오므로."""
    return _html.escape("" if value is None else str(value), quote=True)


def icon(name: str, size: int = 20) -> str:
    """인라인 SVG 아이콘 — 외부 폰트 요청 없음."""
    path = _ICON_PATHS.get(name, _ICON_PATHS["dashboard"])
    return (
        f'<svg class="rip-icon" width="{size}" height="{size}" viewBox="0 0 24 24" '
        f'aria-hidden="true"><path d="{path}"/></svg>'
    )


def _sidebar(active: str) -> str:
    items = []
    for section, entries in NAV_SECTIONS:
        if section:
            items.append(
                f'<div class="nav-sec px-4 pt-4 pb-1 font-mono-label text-mono-label '
                f'uppercase text-on-surface-variant">{esc(section)}</div>'
            )
        for href, label, ico in entries:
            if href == active:
                cls = ("flex items-center gap-3 px-4 py-2.5 rounded transition-all "
                       "bg-secondary-container text-on-secondary font-semibold")
                aria = ' aria-current="page"'
            else:
                cls = ("flex items-center gap-3 px-4 py-2.5 rounded text-on-surface-variant "
                       "transition-all")
                aria = ""
            items.append(
                f'<a class="{cls}"{aria} href="{href}">{icon(ico)}<span>{label}</span></a>')
    return (
        '<aside class="fixed left-0 top-0 h-full w-72 bg-surface-container-lowest '
        'border-r border-outline-variant/30 z-50 flex flex-col">'
        '<a class="h-16 flex items-center px-6 gap-3" href="index.html" title="홈으로">'
        + icon("shield_lock", 22)
        + '<span class="font-h3 text-h3 text-primary tracking-tight">RegImpact AI</span></a>'
        '<nav class="flex-1 px-3 py-4 space-y-1 overflow-y-auto">' + "".join(items) + "</nav>"
        '<div class="px-6 py-4 border-t border-outline-variant/30 text-body-sm '
        'text-on-surface-variant">모든 수치는 엔진 실제 출력에서 생성됨</div>'
        "</aside>"
    )


def _header(scenario: str, status: str) -> str:
    return (
        '<header class="fixed top-0 left-72 right-0 h-16 bg-surface/90 backdrop-blur-md '
        'border-b border-outline-variant/20 z-40 flex items-center justify-between px-8">'
        '<div class="flex items-center gap-3 bg-surface-container-low px-3 py-1.5 rounded-lg '
        'border border-outline-variant/50">'
        + icon("target", 18)
        + f'<span class="text-body-sm font-medium">{esc(scenario)}</span></div>'
        '<div class="flex items-center gap-6">'
        '<div class="flex items-center gap-2 bg-tertiary-fixed/30 text-on-tertiary-fixed-variant '
        'px-3 py-1 rounded-full border border-tertiary-fixed">'
        '<span class="w-2 h-2 rounded-full bg-tertiary-fixed-dim animate-pulse"></span>'
        f'<span class="text-body-sm font-semibold">{esc(status)}</span></div>'
        '<div class="flex items-center gap-3 border-l border-outline-variant/30 pl-6">'
        '<div class="w-8 h-8 rounded-full bg-primary flex items-center justify-center '
        'text-on-primary">'
        + icon("person", 18)
        + "</div></div></div></header>"
    )


def page(
    *, title: str, active: str, scenario: str, status: str, body: str,
    extra_script: str = "", extra_css: str = ""
) -> str:
    """Stitch 셸(사이드바 + 헤더) 안에 본문을 넣어 **자기완결적** HTML 문서를 만든다."""
    return (
        '<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8"/>'
        '<meta content="width=device-width, initial-scale=1.0" name="viewport"/>'
        f"{NOINDEX}"
        f"<title>{esc(title)} · RegImpact AI</title>"
        f"{FONTS}<style>{CSS}{extra_css}</style></head>"
        '<body class="bg-background font-body-md text-body-md text-on-surface">'
        f"{_sidebar(active)}"
        '<div class="pl-72">'
        f"{_header(scenario, status)}"
        '<main class="pt-16 min-h-screen bg-background px-8 py-8">'
        '<div class="flex flex-col w-full gap-8">'
        f"{body}"
        "</div></main></div>"
        f"{extra_script}"
        "</body></html>"
    )


def explainer(what: str, made_of: str, how: str = "") -> str:
    """페이지 최상단 '이 페이지는?' 밴드 — 비전공자용 기능 설명 (2026-08-19 사용자 리뷰).

    glance 가 "결과가 어떤가"라면 explainer 는 "이게 뭐 하는 화면이고 무엇으로
    만들었나"다. 전문용어 없이, 처음 온 사람이 3줄로 이 화면의 역할을 이해하게 한다.
    """
    rows = [("무엇을 보는 화면인가요?", what), ("무엇으로 만들었나요?", made_of)]
    if how:
        rows.append(("어떻게 보나요?", how))
    items = "".join(
        '<div class="pe-row">'
        f'<div class="pe-q">{esc(q)}</div><div class="pe-a">{esc(a)}</div></div>'
        for q, a in rows
    )
    return (
        '<div class="pg-explain rounded-xl border border-outline-variant '
        'bg-surface-container-low p-5 flex flex-col gap-3">'
        '<div class="flex items-center gap-2 font-mono-label text-mono-label uppercase '
        'text-secondary">' + icon("travel_explore", 16) + "<span>이 페이지는?</span></div>"
        + items + "</div>"
    )


def glance(headline: str, chips: list[str]) -> str:
    """페이지 최상단 '한눈에' 밴드 — 결론 한 문장 + 핵심 수치 칩.

    구구절절한 본문을 다 읽지 않아도 이 화면이 말하는 것을 3초 안에 알 수 있게 한다
    (2026-08-19 사용자 리뷰). headline 의 수치는 호출측이 실제 객체에서 뽑아 넣는다.
    """
    return (
        '<div class="glance flex flex-col gap-3 bg-primary-fixed/60 border '
        'border-primary-fixed rounded-xl p-5">'
        f'<div class="font-h3 text-h3 text-on-primary-fixed">{esc(headline)}</div>'
        '<div class="flex flex-wrap gap-2">' + "".join(chips) + "</div></div>"
    )


def page_title(title: str, subtitle: str) -> str:
    return (
        '<div class="flex flex-col gap-4 mb-4">'
        f'<div class="font-h1 text-h1 text-on-background">{esc(title)}</div>'
        '<div class="font-body-md text-body-md text-on-surface-variant max-w-3xl">'
        f"{esc(subtitle)}</div></div>"
    )


def card(title: str, inner: str, *, note: str = "") -> str:
    note_html = (
        f'<div class="text-body-sm text-on-surface-variant">{esc(note)}</div>' if note else ""
    )
    return (
        '<section class="bg-surface-container-lowest rounded-xl shadow-sm p-6 flex flex-col gap-4">'
        '<div class="flex items-baseline justify-between gap-4">'
        f'<h2 class="font-h2 text-h2 text-on-background">{esc(title)}</h2>{note_html}</div>'
        f"{inner}</section>"
    )


def stat(label: str, value: str, *, tone: str = "neutral", sub: str = "") -> str:
    """지표 카드. tone: neutral | good | warn | bad"""
    tones = {
        "neutral": "text-on-background",
        "good": "text-secondary",
        "warn": "text-on-tertiary-fixed-variant",
        "bad": "text-error",
    }
    sub_html = (
        f'<div class="text-body-sm text-on-surface-variant">{esc(sub)}</div>' if sub else ""
    )
    return (
        '<div class="bg-surface-container-lowest rounded-xl shadow-sm p-5 flex flex-col gap-1">'
        f'<div class="font-mono-label text-mono-label text-on-surface-variant uppercase">{esc(label)}</div>'
        f'<div class="font-h2 text-h2 {tones[tone]}">{esc(value)}</div>{sub_html}</div>'
    )


def chip(text: str, *, tone: str = "neutral", mono: bool = False) -> str:
    tones = {
        "neutral": "bg-surface-variant text-on-surface-variant",
        "good": "bg-secondary-container text-on-secondary",
        "warn": "bg-tertiary-fixed text-on-tertiary-fixed-variant",
        "bad": "bg-error-container text-on-error-container",
        "primary": "bg-primary-fixed text-on-primary-fixed",
    }
    font = "font-mono-data text-mono-data" if mono else "text-body-sm font-medium"
    return (
        f'<span class="{font} {tones[tone]} px-2 py-1 rounded whitespace-nowrap">'
        f"{esc(text)}</span>"
    )


def table(headers: list[str], rows: list[list[str]], *, align_center: tuple = ()) -> str:
    """셀 내용은 **이미 HTML인 것으로 취급**한다 — 호출측이 esc()/chip()으로 만들어 넘긴다."""
    th = "".join(
        f'<th class="p-4 font-semibold{" text-center" if i in align_center else ""}">{esc(h)}</th>'
        for i, h in enumerate(headers)
    )
    tr = []
    for row in rows:
        tds = "".join(
            f'<td class="p-4 align-top{" text-center" if i in align_center else ""}">{c}</td>'
            for i, c in enumerate(row)
        )
        tr.append(f'<tr class="hover:bg-surface-container-low/50 transition-colors">{tds}</tr>')
    return (
        '<div class="w-full overflow-x-auto bg-surface-container-lowest rounded-xl shadow-sm">'
        '<table class="w-full text-left border-collapse">'
        '<thead class="bg-surface-container-low font-body-md text-body-md text-on-surface-variant">'
        f"<tr>{th}</tr></thead>"
        '<tbody class="font-body-md text-body-md text-on-surface divide-y divide-outline-variant/30">'
        + "".join(tr)
        + "</tbody></table></div>"
    )


def bar(label: str, value: int, total: int, *, tone: str = "primary", caption: str = "") -> str:
    """CDN 차트 라이브러리 없이 그리는 가로 막대 — 외부 의존성 0."""
    pct = (value / total * 100) if total else 0.0
    tones = {
        "primary": "bg-primary", "secondary": "bg-secondary",
        "warn": "bg-tertiary-fixed-dim", "bad": "bg-error", "muted": "bg-outline-variant",
    }
    return (
        '<div class="flex items-center gap-3">'
        f'<div class="w-44 shrink-0 text-body-sm text-on-surface-variant truncate">{esc(label)}</div>'
        '<div class="flex-1 h-6 bg-surface-container rounded overflow-hidden">'
        f'<div class="h-full {tones[tone]}" style="width:{pct:.1f}%"></div></div>'
        f'<div class="w-40 shrink-0 font-mono-data text-mono-data text-right">'
        f"{value:,} ({pct:.1f}%) {esc(caption)}</div></div>"
    )
