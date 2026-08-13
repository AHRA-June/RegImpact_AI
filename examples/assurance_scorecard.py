"""Assurance 스코어카드 데모 — 4 dimension을 확정 임계값(Strict)으로 판정.

실행: python examples/assurance_scorecard.py   (repo 루트, API 키 불필요)
출력: 콘솔 + docs/reports/assurance_scorecard.md
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from regimpact.assurance import build_scorecard, format_scorecard_md  # noqa: E402
from regimpact.extractor import load_sources  # noqa: E402
from regimpact.extractor.schema import RegChangeExtraction  # noqa: E402
from regimpact.tc_generator import generate_grid, run_regression  # noqa: E402

GOLD = json.loads((ROOT / "docs/eval/regchange_gold_6_30.json").read_text(encoding="utf-8"))
EXTRACTED = json.loads((ROOT / "docs/eval/regchange_extracted_6_30.json").read_text(encoding="utf-8"))


def main() -> None:
    extraction = RegChangeExtraction.from_dict(EXTRACTED)
    sources = load_sources()
    regression = run_regression(generate_grid())      # ④ = 격자 3,200
    sc = build_scorecard(extraction, sources, GOLD, regression)

    md = format_scorecard_md(sc)
    print(md)
    out = ROOT / "docs" / "reports" / "assurance_scorecard.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md + "\n", encoding="utf-8")
    print(f"\n생성됨: {out.relative_to(ROOT)}  (overall={sc.overall.value})")


if __name__ == "__main__":
    main()
