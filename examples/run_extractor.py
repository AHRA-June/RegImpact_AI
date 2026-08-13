"""RegChange Extractor 실행 — 공문 → AI 추출 → Assurance 채점.

**anthropic(유료) 없이도 무료 제공자로 실행 가능.** Extractor는 완성 함수 주입식이라
어떤 OpenAI 호환 제공자든 꽂을 수 있다(표준 라이브러리 어댑터, 외부 SDK 불필요).

무료로 실행하기 (택1):
    # 1) Ollama (로컬, 완전 무료·가입 불필요) — `ollama pull llama3.1` 후:
    REGIMPACT_LLM_PROVIDER=ollama python examples/run_extractor.py

    # 2) Groq / OpenRouter / Gemini (무료 티어, 무료 키 발급):
    GROQ_API_KEY=... REGIMPACT_LLM_PROVIDER=groq python examples/run_extractor.py
    OPENROUTER_API_KEY=... REGIMPACT_LLM_PROVIDER=openrouter python examples/run_extractor.py
    GEMINI_API_KEY=... REGIMPACT_LLM_PROVIDER=gemini python examples/run_extractor.py

    # 3) 직접 지정:
    REGIMPACT_LLM_BASE_URL=... REGIMPACT_LLM_MODEL=... [REGIMPACT_LLM_KEY_ENV=MYKEY] \
      python examples/run_extractor.py

    # (선택) anthropic 유료:
    REGIMPACT_LLM_PROVIDER=anthropic ANTHROPIC_API_KEY=... python examples/run_extractor.py

오프라인 로직 검증은 `python -m pytest -k extractor`.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from regimpact.extractor import (  # noqa: E402
    FREE_PROVIDERS,
    anthropic_completion,
    check_citation_grounding,
    completion_from_env,
    extract_regchange,
    load_sources,
    score_against_gold,
)

REPO = Path(__file__).resolve().parent.parent
GOLD = json.loads((REPO / "docs" / "eval" / "regchange_gold_6_30.json").read_text(encoding="utf-8"))


def _build_completion():
    """환경변수로 완성 함수를 구성. 무료 제공자 우선, anthropic은 명시 시에만."""
    provider = (os.environ.get("REGIMPACT_LLM_PROVIDER") or "").lower()
    if provider == "anthropic":
        return anthropic_completion(model=os.environ.get("REGIMPACT_LLM_MODEL", "claude-opus-5"))
    return completion_from_env()  # ollama/groq/openrouter/gemini/직접지정, 미설정이면 None


def _guidance() -> None:
    print("\n[안내] LLM 제공자가 설정되지 않았습니다. 무료로 실행하려면(택1):")
    for name, p in FREE_PROVIDERS.items():
        keyhint = "키 불필요" if not p["key_env"] else f"{p['key_env']}=..."
        print(f"  - {name:<11} REGIMPACT_LLM_PROVIDER={name}  ({keyhint})  · {p['note']}")
    print("  예) REGIMPACT_LLM_PROVIDER=ollama python examples/run_extractor.py")


def main() -> None:
    sources = load_sources()
    if not sources:
        print("원문을 찾지 못했습니다. docs/sources/raw/*.txt 확인.")
        return
    print(f"원문 {len(sources)}건 로드: {', '.join(sources)}")

    complete = _build_completion()
    if complete is None:
        _guidance()
        return

    try:
        extraction = extract_regchange(sources, complete=complete)
    except ImportError as e:
        print(f"\n[안내] 의존성 부족: {e}. 무료 옵션은 REGIMPACT_LLM_PROVIDER=ollama (SDK 불필요).")
        return
    except Exception as e:  # 인증·네트워크·파싱 등
        print(f"\n[안내] LLM 호출/파싱 실패: {type(e).__name__}: {e}")
        print("키·엔드포인트를 확인하거나, 로컬 무료 옵션(Ollama)을 사용하세요.")
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
