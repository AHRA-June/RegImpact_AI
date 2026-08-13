"""RegChange Extractor 실제 실행 (run 1) — 세션 모델 경로.

배경: 이 원격 환경에는 ANTHROPIC_API_KEY가 없어 run_extractor.py의 SDK 경로
(api.anthropic.com structured output)로는 인증할 수 없다. 대신 **세션 모델
(claude-opus-4-8)** 이 run_extractor와 동일한 SYSTEM_PROMPT + build_user_prompt(원문 3건)을
근거로 생성한 구조화 추출을 `docs/eval/regchange_extraction_6_30_run1.json`에 저장했다.

이 스크립트는 그 저장된 LLM 출력을 **실제 extractor 코드 경로**(extract_regchange의
complete 주입점)로 흘려보내, 결정적 Assurance 하네스로 채점한다:
    ① Citation Grounding (원문 verbatim 대조, 오프라인)
    ② Gold 대조 (Change Completeness / Exception Recall / Effective-date / Regions)
그리고 동일 추출을 impact.run_e2e(extraction=...)에 주입해 E2E까지 관통시킨다.

한계(투명성): 고립된 API 호출이 아니라 세션 모델 in-loop이며, 동일 세션에서 gold를
사전 열람했다(오염 가능). → 파이프라인 실배선 실증 + grounding 실측 용도이지 독립 벤치마크가 아니다.

실행:
    python examples/run_extractor_session_model.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from regimpact.extractor import (  # noqa: E402
    check_citation_grounding,
    extract_regchange,
    load_sources,
    score_against_gold,
)
from regimpact.extractor.prompt import SYSTEM_PROMPT, build_user_prompt  # noqa: E402
from regimpact.impact import format_e2e_report, run_e2e  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
EVAL = REPO / "docs" / "eval"
GOLD = json.loads((EVAL / "regchange_gold_6_30.json").read_text(encoding="utf-8"))
LLM_OUTPUT = json.loads((EVAL / "regchange_extraction_6_30_run1.json").read_text(encoding="utf-8"))


def session_model_completion(system: str, user: str) -> dict:
    """세션 모델이 생성한 추출(JSON)을 반환하는 completion 함수.

    system/user 프롬프트는 run_extractor의 실제 프롬프트와 동일하게 구성되어 전달되며
    (아래 main에서 build_user_prompt로 확인), 이 함수는 그 프롬프트를 근거로 세션 모델이
    사전 생성한 결과를 돌려준다. 실제 SDK 경로에서는 이 자리에 anthropic_completion이 들어간다.
    """
    return LLM_OUTPUT


def main() -> None:
    sources = load_sources()
    if not sources:
        print("원문을 찾지 못했습니다. docs/sources/raw/*.txt 확인.")
        return
    print(f"원문 {len(sources)}건 로드: {', '.join(sorted(sources))}")

    # 실제 프롬프트 구성(감사용): run_extractor와 동일 경로
    user_prompt = build_user_prompt(sources)
    print(f"프롬프트: system {len(SYSTEM_PROMPT)}자 / user {len(user_prompt)}자 "
          "(run_extractor와 동일 구성)")

    # 실제 extractor 코드 경로로 주입 (complete=session_model_completion)
    extraction = extract_regchange(sources, complete=session_model_completion)

    print(f"\n=== 추출 결과 ({len(extraction.changes)}건) ===")
    for c in extraction.changes:
        ba = f"{c.before or '-'} → {c.after or '-'}"
        print(f"[{c.category:<14}] {c.summary}")
        print(f"    ⤷ {ba}  (conf {c.confidence:.2f})")
        print(f"    ⤷ {c.citation.source_doc_id}: \"{c.citation.quote[:56]}...\"")

    # ① Citation Grounding (결정적, 오프라인)
    print("\n=== Assurance ① Citation Grounding ===")
    g = check_citation_grounding(extraction, sources)
    print(f"Citation Correctness  : {g.citation_correctness:.0%} (grounded {g.grounded}/{g.total})")
    print(f"Unsupported Claim Rate: {g.unsupported_claim_rate:.0%}")
    for u in g.ungrounded:
        print(f"    ⚠ 원문 미확인(환각 가능): [{u.category}] {u.summary}")
        print(f"       quote=\"{u.citation.quote[:60]}\"")

    # ② Gold 대조
    print("\n=== Assurance ② Gold 대조 ===")
    s = score_against_gold(extraction, GOLD)
    print(f"Change Completeness : {s.change_completeness:.0%}")
    print(f"Exception Recall    : {s.exception_recall:.0%}")
    print(f"Effective-date      : {'OK' if s.effective_date_correct else 'MISS'}")
    print(f"Regions             : {'OK' if s.regions_correct else 'MISS'}")
    if s.missed_changes:
        print(f"    놓친 변경: {s.missed_changes}")
    if s.missed_exceptions:
        print(f"    놓친 예외: {s.missed_exceptions}")

    # E2E 관통 (실제 추출 주입)
    print("\n=== E2E 관통 (이 실제 추출을 파이프라인에 주입) ===")
    report = run_e2e(extraction=extraction)
    print(format_e2e_report(report))

    # 실측 요약 아티팩트 저장
    out = EVAL / "regchange_run1_metrics.json"
    metrics = {
        "run": "run1_session_model",
        "model": "claude-opus-4-8 (세션 모델 in-loop)",
        "num_changes": len(extraction.changes),
        "citation_correctness": g.citation_correctness,
        "unsupported_claim_rate": g.unsupported_claim_rate,
        "grounded": g.grounded,
        "total_citations": g.total,
        "change_completeness": s.change_completeness,
        "exception_recall": s.exception_recall,
        "effective_date_correct": s.effective_date_correct,
        "regions_correct": s.regions_correct,
        "e2e_ok": report.e2e_ok,
        "regression_pass_rate": report.regression_pass_rate,
    }
    out.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n실측 요약 저장: {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
