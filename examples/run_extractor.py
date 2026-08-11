"""RegChange Extractor 실행 — 공문 → AI 추출 → Assurance 채점 → (선택) 전체 E2E.

실제 LLM 호출은 인증이 필요하다. 인증 해석 순서(anthropic SDK 기준):
    ANTHROPIC_API_KEY  →  ANTHROPIC_AUTH_TOKEN  →  `ant auth login` 프로필  →  기본 프로필
키가 없으면 방법을 안내하고 종료한다.

실행:
    python examples/run_extractor.py              # 실제 LLM 추출 + Assurance 채점
    python examples/run_extractor.py --e2e        # 위 + 실제 추출을 전체 E2E에 물려 검증보고서까지
    python examples/run_extractor.py --offline     # API 없이 canonical 추출로 배선만 확인(데모)
    python examples/run_extractor.py --e2e --offline

모델은 REGIMPACT_EXTRACTOR_MODEL 환경변수로 교체 가능(기본 claude-opus-5).
오프라인 로직 검증은 `python -m pytest -k extractor`.
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
    load_sources,
    ollama_completion,
    openai_compatible_completion,
    score_against_gold,
)

REPO = Path(__file__).resolve().parent.parent
GOLD = json.loads((REPO / "docs" / "eval" / "regchange_gold_6_30.json").read_text(encoding="utf-8"))

# 백엔드 선택: anthropic(기본, 유료) | ollama(로컬·무료) | openai(무료 티어 호환)
BACKEND = os.environ.get("REGIMPACT_EXTRACTOR_BACKEND", "anthropic").lower()
MODEL = os.environ.get("REGIMPACT_EXTRACTOR_MODEL", "")

_AUTH_HELP = """\
[안내] 실제 LLM 호출에 사용할 백엔드를 찾지 못했습니다. 무료 옵션이 있습니다:

  # 1) Ollama — 로컬·완전 무료·키 불필요
  #    ollama pull qwen2.5   (또는 llama3 등) 후:
  REGIMPACT_EXTRACTOR_BACKEND=ollama REGIMPACT_EXTRACTOR_MODEL=qwen2.5 \\
    python examples/run_extractor.py --e2e

  # 2) OpenAI 호환 무료 티어 (Groq/OpenRouter/Gemini-호환 등, 무료 키 발급)
  REGIMPACT_EXTRACTOR_BACKEND=openai \\
  REGIMPACT_OPENAI_BASE_URL=https://api.groq.com/openai/v1 \\
  REGIMPACT_OPENAI_API_KEY=... REGIMPACT_EXTRACTOR_MODEL=llama-3.3-70b-versatile \\
    python examples/run_extractor.py --e2e

  # 3) Anthropic (유료)
  ANTHROPIC_API_KEY=sk-ant-... REGIMPACT_EXTRACTOR_MODEL=claude-opus-5 \\
    python examples/run_extractor.py --e2e

배선만 먼저 확인: python examples/run_extractor.py --e2e --offline
"""


def _make_complete():
    """선택된 백엔드의 complete 함수를 만든다. 미설정/실패 시 None + 안내."""
    if BACKEND == "ollama":
        model = MODEL or "qwen2.5"
        host = os.environ.get("REGIMPACT_OLLAMA_HOST", "http://localhost:11434")
        print(f"백엔드: ollama  model={model}  host={host}")
        return ollama_completion(model=model, host=host)
    if BACKEND == "openai":
        base = os.environ.get("REGIMPACT_OPENAI_BASE_URL")
        if not base or not MODEL:
            print("[안내] openai 백엔드는 REGIMPACT_OPENAI_BASE_URL 과 REGIMPACT_EXTRACTOR_MODEL 이 필요합니다.")
            return None
        print(f"백엔드: openai-compatible  model={MODEL}  base={base}")
        return openai_compatible_completion(
            base_url=base, model=MODEL, api_key=os.environ.get("REGIMPACT_OPENAI_API_KEY"),
        )
    # 기본: anthropic
    model = MODEL or "claude-opus-5"
    print(f"백엔드: anthropic  model={model}")
    return anthropic_completion(model=model)


def _get_extraction(offline: bool):
    """실제 LLM 추출(기본) 또는 canonical 오프라인 추출을 반환한다."""
    sources = load_sources()
    if not sources:
        print("원문을 찾지 못했습니다. docs/sources/raw/*.txt 확인.")
        return None, sources
    print(f"원문 {len(sources)}건 로드: {', '.join(sources)}")

    if offline:
        from regimpact.proposal import six_thirty_extraction
        print("[offline] canonical 추출 사용(실제 LLM 미호출) — 배선 확인용.")
        return six_thirty_extraction(), sources

    try:
        complete = _make_complete()
        if complete is None:
            print(_AUTH_HELP)
            return None, sources
        print("LLM 추출 호출 …")
        extraction = extract_regchange(sources, complete=complete)
        return extraction, sources
    except ImportError as e:
        print(f"\n[안내] SDK/모듈 미설치: {e}")
        print(_AUTH_HELP)
        return None, sources
    except Exception as e:  # 인증/네트워크/서버 등
        print(f"\n[안내] LLM 호출 실패/미설정: {type(e).__name__}: {e}\n")
        print(_AUTH_HELP)
        return None, sources


def _print_assurance(extraction, sources) -> None:
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


def main() -> None:
    args = sys.argv[1:]
    offline = "--offline" in args
    run_e2e = "--e2e" in args

    extraction, sources = _get_extraction(offline)
    if extraction is None:
        return

    _print_assurance(extraction, sources)

    if run_e2e:
        # 실제(또는 canonical) 추출을 전체 파이프라인에 물려 검증보고서까지 산출.
        from regimpact.e2e import run_six_thirty_e2e
        print("\n" + "=" * 64)
        print("E2E: 이 추출을 Impact→Proposal→TC→Regression→Assurance→Report에 관통")
        print("=" * 64)
        result = run_six_thirty_e2e(extraction=extraction)
        print(result.report.render_markdown())
        print(f"\n[gate] {result.assurance.gate.value}  "
              f"[decision] {result.report.decision_status}")


if __name__ == "__main__":
    main()
