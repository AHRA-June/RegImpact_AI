"""UI 생성 — 6·30 파이프라인을 돌려 5개 화면을 실제 값으로 렌더한다.

Stitch 목업의 하드코딩 값을 대체한다. 기본은 LLM 호출 0회(저장된 추출 기록 재생) · 비용 0원.

    python examples/build_ui.py                      # docs/ui/generated/ 에 생성
    python examples/build_ui.py --provider cli       # 추출부터 실제 LLM 실행
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from regimpact.extractor import (  # noqa: E402
    check_citation_grounding,
    extract_regchange,
    load_sources,
    normalize_regions,
    resolve_completion,
    score_against_gold,
)
from regimpact.impact import (  # noqa: E402
    analyze_portfolio,
    build_impact_matrix,
    build_portfolio,
)
from regimpact.impact.portfolio import DEFAULT_SEED, DEFAULT_SIZE  # noqa: E402
from regimpact.tc_generator import run_regression  # noqa: E402
from regimpact.ui import render_site, write_site  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
DEFAULT_RUN = REPO / "docs" / "eval" / "runs" / "run_cli_sonnet5_v2.json"
OUT_DIR = REPO / "docs" / "ui" / "generated"


def main() -> None:
    p = argparse.ArgumentParser(description="RegImpact AI UI 생성")
    p.add_argument("--provider", default="replay")
    p.add_argument("--run", default=str(DEFAULT_RUN))
    p.add_argument("--model", default=None)
    p.add_argument("--size", type=int, default=DEFAULT_SIZE)
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p.add_argument("--out", default=str(OUT_DIR))
    a = p.parse_args()

    sources = load_sources()
    kwargs = {"run_path": a.run} if a.provider == "replay" else {}
    complete = resolve_completion(a.provider, model=a.model, **kwargs)
    extraction = extract_regchange(sources, complete=complete)
    grounding = check_citation_grounding(extraction, sources)
    extraction = normalize_regions(extraction).normalized

    gold = json.loads(
        (REPO / "docs" / "eval" / "regchange_gold_6_30.json").read_text(encoding="utf-8")
    )
    scored = score_against_gold(extraction, gold)

    impact = analyze_portfolio(build_portfolio(size=a.size, seed=a.seed), seed=a.seed)
    regression = run_regression()
    matrix = build_impact_matrix(
        extraction, impact, grounding=grounding, regression=regression
    )

    pages = render_site(
        extraction=extraction, grounding=grounding, scored=scored,
        impact=impact, matrix=matrix, regression=regression,
    )
    for path in write_site(pages, a.out):
        print(f"  {path.relative_to(REPO)}  ({path.stat().st_size:,} bytes)")
    print(f"\n{len(pages)}개 화면 생성 완료 — 값 출처: 추출 {len(extraction.changes)}건 · "
          f"포트폴리오 {impact.portfolio_size:,}건(seed={a.seed}) · 회귀 {regression.total}케이스")


if __name__ == "__main__":
    main()
