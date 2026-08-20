"""사이트 생성 — 실제 파이프라인 출력을 5개 화면으로 렌더해 디렉터리에 쓴다."""
from __future__ import annotations

from pathlib import Path

from ..extractor.evaluate import GoldReport, GroundingReport
from ..extractor.schema import RegChangeExtraction
from ..impact.customer import CustomerImpactReport
from ..impact.schema import ImpactMatrix
from ..tc_generator.regression import RegressionReport
from .pages import (
    assurance_page,
    impact_matrix_page,
    portfolio_page,
    regchange_page,
    rule_page,
)


def render_site(
    *,
    extraction: RegChangeExtraction,
    grounding: GroundingReport,
    scored: GoldReport,
    impact: CustomerImpactReport,
    matrix: ImpactMatrix,
    regression: RegressionReport,
) -> dict[str, str]:
    """파일명 → HTML. 파일로 쓰기 전에 테스트가 내용을 검사할 수 있게 dict로 돌려준다."""
    return {
        "regchange.html": regchange_page(extraction, grounding, scored),
        "impact_matrix.html": impact_matrix_page(matrix),
        "rule.html": rule_page(extraction, regression),
        "assurance.html": assurance_page(grounding, scored, regression, matrix, impact),
        "portfolio.html": portfolio_page(impact),
    }


def write_site(pages: dict[str, str], out_dir: str | Path) -> list[Path]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for name, html in pages.items():
        p = out / name
        p.write_text(html, encoding="utf-8")
        written.append(p)
    # 진입점 — 첫 화면으로 리다이렉트
    index = out / "index.html"
    index.write_text(
        '<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8"/>'
        '<meta name="robots" content="noindex, nofollow"/>'
        '<meta http-equiv="refresh" content="0; url=regchange.html"/>'
        "<title>RegImpact AI</title></head>"
        '<body><a href="regchange.html">RegImpact AI</a></body></html>',
        encoding="utf-8",
    )
    written.append(index)
    return written
