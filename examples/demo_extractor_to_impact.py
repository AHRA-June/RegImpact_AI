"""E2E 데모: 공문 추출 → 정규화 → Impact Matrix (진짜 데이터 관통).

저장된 6·30 추출 결과(`docs/eval/extractor_run_6_30_gemini.json`)를 입력으로,
추출된 policy_id·effective_from·target_regions(한글명)를 그대로 Impact Matrix 로 흘려보낸다.
→ API 키 없이 오프라인으로 "공문 → 추출 → 임팩트"가 끝까지 연결되는지 확인.

실행: python examples/demo_extractor_to_impact.py   (repo 루트에서)
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from regimpact.extractor import RegChangeExtraction  # noqa: E402
from regimpact.impact import format_report, impact_from_extraction  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
SAVED = REPO / "docs" / "eval" / "extractor_run_6_30_gemini.json"


def main() -> None:
    data = json.loads(SAVED.read_text(encoding="utf-8"))
    extraction = RegChangeExtraction.from_dict(data)

    print("입력 추출(저장본):")
    print(f"  policy_id={extraction.policy_id}  effective_from={extraction.effective_from}")
    print(f"  target_regions(원문 한글명)={extraction.target_regions}")
    print(f"  changes={len(extraction.changes)}건\n")

    result = impact_from_extraction(extraction)

    print(f"→ 시점 유도: before={result.before_date}  after={result.after_date} "
          f"(effective_from={result.effective_from} 기준)")
    print(f"→ 지역 정규화: {result.regions}"
          + (f"  ⚠ 미상={result.unmapped_regions}" if result.unmapped_regions else "")
          + "\n")

    print(format_report(result.matrix))


if __name__ == "__main__":
    main()
