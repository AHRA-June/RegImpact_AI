"""UI 자립 CSS/아이콘 에셋 빌드 — `src/regimpact/ui/templates/app.css` 재생성.

⚠️ **네트워크 필요** (Tailwind CLI 바이너리 + Material Symbols 폰트 다운로드). 런타임이 아니라
'빌드 타임' 도구다. 산출물(app.css, icon_codepoints.json)은 저장소에 커밋되어 오프라인에서도
화면이 완전히 스타일링된다. 이 스크립트는 그 산출물이 어떻게 만들어졌는지를 재현 가능하게 한다.

무엇을 하나:
1. Tailwind 디자인 토큰을 **보존된 Stitch export**(`docs/ui/stitch_export/_1/code.html`)에서 추출
   → 이것이 색·타이포 토큰의 단일 진실.
2. 생성 화면(`docs/ui/generated/*.html`)을 스캔해 실제 사용된 유틸리티만 JIT 빌드(Tailwind v3).
3. Material Symbols Outlined를 화면에서 쓰는 아이콘 코드포인트로만 서브셋 → woff2 → data URI.
4. app.css = (아이콘 @font-face) + (Tailwind 빌드)로 조립해 templates에 기록.

사전 준비:
    pip install pytailwindcss fonttools brotli
실행:
    python tools/build_ui_assets.py
"""
from __future__ import annotations

import base64
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STITCH = ROOT / "docs" / "ui" / "stitch_export" / "_1" / "code.html"
GENERATED = ROOT / "docs" / "ui" / "generated"
TPL = ROOT / "src" / "regimpact" / "ui" / "templates"

TAILWIND_VERSION = "v3.4.17"
FONT_URL = (
    "https://raw.githubusercontent.com/google/material-design-icons/master/"
    "variablefont/MaterialSymbolsOutlined%5BFILL,GRAD,opsz,wght%5D.ttf"
)
CODEPOINTS_URL = (
    "https://raw.githubusercontent.com/google/material-design-icons/master/"
    "variablefont/MaterialSymbolsOutlined%5BFILL,GRAD,opsz,wght%5D.codepoints"
)

_FONT_FALLBACK = (
    '["Noto Sans","system-ui","-apple-system","Segoe UI","Roboto",'
    '"Apple SD Gothic Neo","Malgun Gothic","sans-serif"]'
)
_MONO_FALLBACK = '["JetBrains Mono","ui-monospace","SFMono-Regular","Menlo","Consolas","monospace"]'


def _collect_icons() -> list[str]:
    """아이콘 '이름'을 수집. iconify(이름→코드포인트 치환)를 끈 상태로 렌더해야
    이름이 남으므로, chrome._iconify를 일시적으로 항등함수로 교체한다(순환 방지)."""
    sys.path.insert(0, str(ROOT / "src"))
    from regimpact.ui import SCREENS  # noqa: E402
    from regimpact.ui import chrome  # noqa: E402

    orig = chrome._iconify
    chrome._iconify = lambda h: h  # 이름 보존
    try:
        icons: set[str] = set()
        for _fname, render_fn, _label in SCREENS:
            for m in re.findall(r'material-symbols-outlined[^>]*>([a-z0-9_]+)<', render_fn()):
                icons.add(m)
    finally:
        chrome._iconify = orig
    return sorted(icons)


def _tailwind_bin() -> str:
    try:
        import pytailwindcss  # noqa: F401
    except ImportError:
        sys.exit("pytailwindcss 미설치: pip install pytailwindcss")
    bin_path = Path(__import__("pytailwindcss").__file__).parent / "bin" / TAILWINDCSS_DIR / "tailwindcss"
    if not bin_path.exists():
        os.environ["TAILWINDCSS_VERSION"] = TAILWIND_VERSION
        subprocess.run([sys.executable, "-m", "pytailwindcss"], check=False)
    if not bin_path.exists():
        sys.exit(f"Tailwind {TAILWIND_VERSION} 바이너리 없음: {bin_path}. TAILWINDCSS_VERSION={TAILWIND_VERSION} 로 재설치 필요.")
    return str(bin_path)


TAILWINDCSS_DIR = TAILWIND_VERSION  # bin/<version>/tailwindcss


def _build_tailwind(tmp: Path) -> str:
    cfg = re.search(r'tailwind\.config=(\{.*?\})</script>', STITCH.read_text(encoding="utf-8"), re.S).group(1)
    cfg = cfg.replace('["Noto Sans"]', _FONT_FALLBACK).replace('["JetBrains Mono"]', _MONO_FALLBACK)
    (tmp / "tailwind.config.js").write_text(
        "module.exports = Object.assign(\n"
        f"  {{ content: ['{GENERATED}/*.html'] }},\n  {cfg}\n);\n",
        encoding="utf-8",
    )
    (tmp / "input.css").write_text("@tailwind base;\n@tailwind components;\n@tailwind utilities;\n", encoding="utf-8")
    subprocess.run(
        [_tailwind_bin(), "-c", str(tmp / "tailwind.config.js"),
         "-i", str(tmp / "input.css"), "-o", str(tmp / "tw.css"), "--minify"],
        check=True, cwd=tmp,
    )
    return (tmp / "tw.css").read_text(encoding="utf-8")


def _build_icon_font(tmp: Path, icons: list[str]) -> tuple[str, dict[str, str]]:
    from fontTools import subset
    from fontTools.ttLib import TTFont
    from fontTools.varLib.instancer import instantiateVariableFont

    ttf = tmp / "ms.ttf"
    urllib.request.urlretrieve(FONT_URL, ttf)
    cp_txt = tmp / "cp.txt"
    urllib.request.urlretrieve(CODEPOINTS_URL, cp_txt)
    all_cp = dict(line.split() for line in cp_txt.read_text().splitlines() if line.strip())
    codepoints = {i: all_cp[i] for i in icons if i in all_cp}
    missing = [i for i in icons if i not in all_cp]
    if missing:
        sys.exit(f"코드포인트 없음: {missing}")

    f = TTFont(ttf)
    instantiateVariableFont(f, {"FILL": 0, "GRAD": 0, "opsz": 24, "wght": 400}, inplace=True)
    static = tmp / "ms_static.ttf"
    f.save(static)

    opts = subset.Options()
    opts.flavor = "woff2"
    opts.layout_features = []
    opts.desubroutinize = True
    opts.glyph_names = False
    font = subset.load_font(str(static), opts)
    sub = subset.Subsetter(options=opts)
    sub.populate(unicodes=[int(c, 16) for c in codepoints.values()])
    sub.subset(font)
    woff2 = tmp / "icons.woff2"
    subset.save_font(font, str(woff2), opts)
    b64 = base64.b64encode(woff2.read_bytes()).decode()
    return b64, codepoints


def _assemble_css(tw_css: str, icon_b64: str) -> str:
    ms = (
        "@font-face{font-family:'Material Symbols Outlined';font-style:normal;font-weight:400;"
        f"src:url(data:font/woff2;base64,{icon_b64}) format('woff2');}}"
        ".material-symbols-outlined{font-family:'Material Symbols Outlined';font-weight:normal;"
        "font-style:normal;line-height:1;letter-spacing:normal;text-transform:none;display:inline-block;"
        "white-space:nowrap;word-wrap:normal;direction:ltr;-webkit-font-smoothing:antialiased;}"
    )
    return (
        "/* RegImpact AI — self-contained styles (Tailwind v3.4.17 build + subset Material Symbols).\n"
        "   생성: tools/build_ui_assets.py. 오프라인 자립(외부 CDN·웹폰트 없음). */\n"
        + ms + "\n" + tw_css
    )


def main() -> None:
    # 1) 아이콘 이름 수집(iconify off) + 2) 화면 렌더로 클래스 스캔 대상 확보
    icons = _collect_icons()
    print(f"아이콘 {len(icons)}개 스캔")
    from regimpact.ui import render_all  # noqa: E402
    render_all()   # Tailwind JIT가 스캔할 HTML(현 에셋 기준) 생성
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        tw_css = _build_tailwind(tmp)
        icon_b64, codepoints = _build_icon_font(tmp, icons)
    app_css = _assemble_css(tw_css, icon_b64)
    (TPL / "app.css").write_text(app_css, encoding="utf-8")
    (TPL / "icon_codepoints.json").write_text(json.dumps(codepoints), encoding="utf-8")
    print(f"app.css {len(app_css)} bytes → {TPL/'app.css'}")
    print(f"icon_codepoints.json {len(codepoints)}개 → {TPL/'icon_codepoints.json'}")
    # 3) 새 에셋으로 화면 최종 렌더(iconify on)
    render_all()
    print("완료 — docs/ui/generated/ 재생성됨.")


if __name__ == "__main__":
    main()
