"""RegChange Extractor 실행 — 공문 → AI 추출 → Assurance 채점.

실행(실제 LLM 호출, ANTHROPIC_API_KEY 필요):
    python examples/run_extractor.py

키가 없으면 **기록된 1회 실측 추출 산출물**(docs/eval/regchange_extraction_6_30.json)을
로드해 동일한 결정론적 Assurance 채점을 보여준다. 오프라인 로직 검증은 `python -m pytest -k extractor`.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from regimpact.extractor import (  # noqa: E402
    anthropic_completion,
    check_citation_grounding,
    extract_regchange,
    load_recorded_extraction,
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

    extraction = None
    try:
        complete = anthropic_completion(model="claude-opus-5")
        extraction = extract_regchange(sources, complete=complete)
        print("\n[모드] 실제 LLM 호출 성공.")
    except (ImportError, Exception) as e:  # SDK 미설치/인증/네트워크
        recorded = load_recorded_extraction()
        if recorded is None:
            print(f"\n[안내] LLM 호출 불가({type(e).__name__}) + 기록된 추출도 없음.")
            print("실제 실행: pip install anthropic + ANTHROPIC_API_KEY. 로직 검증: pytest -k extractor.")
            return
        extraction = recorded
        print(f"\n[모드] LLM 호출 불가 → 기록된 1회 실측 추출 산출물 로드 "
              f"(docs/eval/regchange_extraction_6_30.json).")

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
