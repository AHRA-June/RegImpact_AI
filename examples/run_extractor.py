"""RegChange Extractor 실행 — 공문 → AI 추출 → Assurance 채점.

백엔드 자동 선택:
  - GEMINI_API_KEY(또는 GOOGLE_API_KEY) 있으면 Google AI Studio(Gemini) REST 사용 (기본).
  - 아니면 ANTHROPIC_API_KEY 로 Anthropic Claude 사용.
  - REGIMPACT_LLM=gemini|anthropic 로 강제 지정 가능. REGIMPACT_MODEL 로 모델 교체 가능.

실행:
    GEMINI_API_KEY=... python examples/run_extractor.py
    (키 없으면 방법 안내 후 종료. 오프라인 로직 검증은 `python -m pytest -k extractor`.)
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from regimpact.extractor import (  # noqa: E402
    anthropic_completion,
    check_citation_grounding,
    extract_regchange,
    gemini_completion,
    load_sources,
    score_against_gold,
)

REPO = Path(__file__).resolve().parent.parent
GOLD = json.loads((REPO / "docs" / "eval" / "regchange_gold_6_30.json").read_text(encoding="utf-8"))


def _select_backend():
    """(이름, 모델, complete함수)를 반환. 키/환경변수로 백엔드 결정."""
    forced = os.environ.get("REGIMPACT_LLM", "").lower()
    model_override = os.environ.get("REGIMPACT_MODEL")
    has_gemini = bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))
    has_anthropic = bool(os.environ.get("ANTHROPIC_API_KEY"))

    use_gemini = forced == "gemini" or (forced == "" and has_gemini)
    use_anthropic = forced == "anthropic" or (forced == "" and not has_gemini and has_anthropic)

    if use_gemini:
        model = model_override or "gemini-flash-latest"
        return "Gemini", model, gemini_completion(model=model)
    if use_anthropic:
        model = model_override or "claude-opus-5"
        return "Anthropic", model, anthropic_completion(model=model)
    return None, None, None


def main() -> None:
    sources = load_sources()
    if not sources:
        print("원문을 찾지 못했습니다. docs/sources/raw/*.txt 확인.")
        return
    print(f"원문 {len(sources)}건 로드: {', '.join(sources)}")

    name, model, complete = _select_backend()
    if complete is None:
        print(
            "\n[안내] API 키가 없습니다. 다음 중 하나를 설정하세요:\n"
            "  - Google AI Studio: https://aistudio.google.com/apikey 에서 발급 후\n"
            "      export GEMINI_API_KEY=...   (기본 백엔드)\n"
            "  - 또는 export ANTHROPIC_API_KEY=...\n"
            "강제 지정: REGIMPACT_LLM=gemini|anthropic, 모델 교체: REGIMPACT_MODEL=..."
        )
        return

    print(f"백엔드: {name} ({model})")
    try:
        extraction = extract_regchange(sources, complete=complete)
    except Exception as e:  # 인증/네트워크/스키마 등
        print(f"\n[안내] LLM 호출 실패: {type(e).__name__}: {e}")
        return

    print(f"\n=== 추출 결과 ({len(extraction.changes)}건) ===")
    print(f"policy_id={extraction.policy_id}  effective_from={extraction.effective_from}  "
          f"regions={extraction.target_regions}")
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
