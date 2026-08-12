"""층화 합성 포트폴리오 회귀 데모 + 골드셋 매니페스트 freeze.

seed 케이스(~30) 를 넘어 수백 건의 층화 포트폴리오를 엔진 ⟷ 독립 오라클로 차등 검증하고,
DEV/LOCKED/CHALLENGE 분할별·카테고리별 Pass Rate를 낸다. metrics_spec §3 분모 확대.

실행: python examples/demo_portfolio.py
  → 콘솔에 회귀 요약, docs/eval/goldset_manifest.json 에 분할 freeze(재현/감사용).
"""
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from regimpact.tc_generator import (  # noqa: E402
    category_counts,
    format_report,
    generate_portfolio,
    run_regression,
    split_counts,
)

REPO = Path(__file__).resolve().parent.parent
MANIFEST = REPO / "docs" / "eval" / "goldset_manifest.json"


def main() -> None:
    cases = generate_portfolio()
    report = run_regression(cases)

    print(format_report(report))
    print()
    print(f"총 {len(cases)}건 | split={split_counts(cases)}")
    print(f"category={category_counts(cases)}")

    # split × category 교차표
    m = Counter((c.split, c.category.value) for c in cases)
    cats = ["SCOPE", "BASELINE", "EXCEPTION", "BOUNDARY", "GRANDFATHERING", "CONFLICT"]
    print("\nsplit × category:")
    print(f"  {'':<10}" + "".join(f"{c[:5]:>7}" for c in cats))
    for split in ("DEV", "LOCKED", "CHALLENGE"):
        print(f"  {split:<10}" + "".join(f"{m.get((split, c), 0):>7}" for c in cats))

    # 매니페스트 freeze (case_id → category/split) — 재현·감사·LOCKED §0-5 근거
    manifest = {
        "_note": "층화 합성 골드셋 freeze. generate_portfolio()로 결정적 재생성 가능. "
                 "개발 중 LOCKED/CHALLENGE 미개봉(LOCKED §0-5).",
        "total": len(cases),
        "split_counts": split_counts(cases),
        "category_counts": category_counts(cases),
        "cases": [
            {"case_id": c.case_id, "category": c.category.value, "split": c.split}
            for c in cases
        ],
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nfreeze: {MANIFEST.relative_to(REPO)} ({len(cases)}건)")


if __name__ == "__main__":
    main()
