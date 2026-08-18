"""UI 렌더러 — Stitch 디자인 + 엔진 실제 출력.

Stitch 목업(`docs/ui/stitch_export/`)은 디자인은 훌륭했지만 도메인 데이터를 환각했다.
이 패키지는 **디자인만 가져오고 값은 전부 실제 컴포넌트 출력에서** 렌더한다.

    render_site(extraction=..., grounding=..., impact=..., matrix=..., regression=...)
    write_site(pages, "docs/ui/generated")
"""
from .site import render_site, write_site
from .theme import NAV, TAILWIND_CONFIG

__all__ = ["render_site", "write_site", "NAV", "TAILWIND_CONFIG"]
