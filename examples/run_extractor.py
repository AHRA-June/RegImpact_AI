"""RegChange Extractor 실행 — 공문 → AI 추출 → Assurance 채점.

실행(실제 LLM 호출, ANTHROPIC_API_KEY 필요):
    python examples/run_extractor.py

키가 없으면 방법을 안내하고 종료. 오프라인 로직 검증은 `python -m pytest -k extractor`.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from regimpact.extractor import (  # noqa: E402
    anthropic_completion,
    check_citation_grounding,
    extract_regchange,
    load_sources,
    score_against_gold,
)

REPO = Path(__file__).resolve().parent.parent
GOLD = json.loads((REPO / "docs" / "eval" / "regchange_gold_6_30.json").read_text(encoding="utf-8"))


def main() -> None:
    sources = load_sources()
    if not sources:
        print("원문을 찾지 못했습니다. docs/sources/raw/*.txt 확인.")
        return
    print(f"원문 {len(sources)}건 로드: {', '.join(sources)}")

    try:
        complete = anthropic_completion(model="claude-opus-5")
        extraction = extract_regchange(sources, complete=complete)
    except ImportError:
        print("\n[안내] anthropic SDK 미설치. 실제 실행하려면: pip install anthropic")
        return
    except Exception as e:  # 인증/네트워크 등
        print(f"\n[안내] LLM 호출 실패: {type(e).__name__}: {e}")
        print("ANTHROPIC_API_KEY 설정(또는 `ant auth login`) 후 재시도하세요.")
        return

    print(f"\n=== 추출 결과 ({len(extraction.changes)}건) ===")
    for c in extraction.changes:
        ba = f"{c.before} → {c.after}" if (c.before or c.after) else ""
        print(f"[{c.category}] {c.summary}  {ba}  (conf {c.confidence:.2f})")
        print(f"    ⤷ {c.citation.source_doc_id}: \"{c.citation.quote[:60]}...\"")

    print("\n=== Assurance: Citation Grounding ===")
    g = check_citation_grounding(extraction, sources)
    print(f"Citation Correctness: {g.citation_correctness:.0%}  "
          f"Unsupported Claim Rate: {g.unsupported_claim_rate:.0%}")
    for u in g.ungrounded:
        print(f"    ⚠ 원문 미확인(환각 가능): [{u.category}] {u.summary}")

    print("\n=== Assurance: Gold 대조 ===")
    s = score_against_gold(extraction, GOLD)
    print(f"Change Completeness: {s.change_completeness:.0%}  "
          f"Exception Recall: {s.exception_recall:.0%}  "
          f"Effective-date: {'OK' if s.effective_date_correct else 'MISS'}  "
          f"Regions: {'OK' if s.regions_correct else 'MISS'}")
    if s.missed_changes:
        print(f"    놓친 변경: {s.missed_changes}")
    if s.missed_exceptions:
        print(f"    놓친 예외: {s.missed_exceptions}")


if __name__ == "__main__":
    main()
