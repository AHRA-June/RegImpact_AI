"""5개 화면을 모두 렌더해 docs/ui/generated/ 에 기록.

각 화면은 엔진/평가 산출물이다. `python examples/render_ui.py`로 실행하거나
`from regimpact.ui import render_all`로 호출한다.
"""
from __future__ import annotations

from pathlib import Path

from . import assurance, impact_matrix, portfolio, regchange, report, rule_proposal

_ROOT = Path(__file__).resolve().parents[3]
GENERATED_DIR = _ROOT / "docs" / "ui" / "generated"

# (파일명, 렌더 함수, 사람이 읽는 화면명)
SCREENS: list[tuple[str, object, str]] = [
    ("regulatory_analysis.html", regchange.render, "규제 변경 분석"),
    ("impact_matrix.html", impact_matrix.render, "임팩트 매트릭스"),
    ("rule_amendment.html", rule_proposal.render, "Rule 변경안"),
    ("assurance.html", assurance.render, "검증 (Assurance)"),
    ("portfolio_impact.html", portfolio.render, "고객·포트폴리오 영향"),
    ("validation_report.html", report.render, "검증 보고서 (Report)"),
]


def _index_html() -> str:
    """5개 화면으로 가는 간단한 인덱스(엔진 산출물 링크 허브)."""
    from .chrome import page
    links = "".join(
        f'<a class="block bg-surface-container-lowest rounded-xl border border-outline-variant/30 '
        f'p-5 hover:bg-surface-container-low transition-colors" href="{fname}">'
        f'<div class="font-h3 text-h3 text-secondary mb-1">{label}</div>'
        f'<div class="font-mono-label text-mono-label text-on-surface-variant">{fname}</div></a>'
        for fname, _fn, label in SCREENS
    )
    main = (
        '<div class="flex flex-col gap-3 mb-2">'
        '<div class="font-h1 text-h1 text-on-background">RegImpact AI — 화면(엔진 산출물)</div>'
        '<div class="font-body-md text-body-md text-on-surface-variant max-w-3xl">'
        '아래 화면은 모두 rule_engine·RegChange gold·tc_generator 회귀·합성 포트폴리오에서 '
        '자동 생성된다. 값을 손으로 적지 않으므로 목업의 환각이 재발할 수 없다.</div></div>'
        f'<div class="grid grid-cols-1 md:grid-cols-2 gap-4">{links}</div>'
    )
    return page("overview", main)


def render_all(out_dir: str | Path | None = None) -> list[Path]:
    """모든 화면 + 인덱스를 렌더해 파일로 저장하고 경로 리스트 반환."""
    out_dir = Path(out_dir) if out_dir else GENERATED_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for fname, render_fn, _label in SCREENS:
        path = out_dir / fname
        path.write_text(render_fn(), encoding="utf-8")
        written.append(path)
    index = out_dir / "index.html"
    index.write_text(_index_html(), encoding="utf-8")
    written.append(index)
    return written
