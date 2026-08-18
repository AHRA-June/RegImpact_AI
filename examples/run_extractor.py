"""RegChange Extractor 실행 — 공문 → AI 추출 → Assurance 채점 → 실행 기록 저장.

**유료 API 키 없이 실행된다.** 기본 provider는 로컬 `claude` CLI(Claude Code 구독에
포함, 별도 키 발급·결제수단 불필요)이며, Gemini 무료 티어·수동 중계·저장본 재생도 지원한다.

    python examples/run_extractor.py                      # auto: 무과금 경로 우선
    python examples/run_extractor.py --provider gemini    # GEMINI_API_KEY(무료 티어)
    python examples/run_extractor.py --provider manual    # 키·CLI 없이 사람이 중계
    python examples/run_extractor.py --provider replay --run docs/eval/runs/<파일>.json

오프라인 로직 검증(호출 0회): `python -m pytest -k "extractor or backends"`.
"""
import argparse
import hashlib
import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from regimpact.extractor import (  # noqa: E402
    LLMBackendError,
    available_providers,
    check_citation_grounding,
    extract_regchange,
    load_sources,
    normalize_regions,
    resolve_completion,
    score_against_gold,
)

REPO = Path(__file__).resolve().parent.parent
GOLD_PATH = REPO / "docs" / "eval" / "regchange_gold_6_30.json"
GOLD = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
RUNS_DIR = REPO / "docs" / "eval" / "runs"


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="RegChange Extractor 실행 + Assurance 채점")
    p.add_argument("--provider", default="auto",
                   help="auto|cli|gemini|manual|replay|anthropic (기본 auto = 무과금 우선)")
    p.add_argument("--model", default=None, help="provider별 모델 이름(생략 시 기본값)")
    p.add_argument("--run", default=None, help="--provider replay 일 때 재생할 run JSON 경로")
    p.add_argument("--tag", default=None, help="실행 기록 파일명에 붙일 태그")
    p.add_argument("--no-save", action="store_true", help="실행 기록을 저장하지 않음")
    return p.parse_args()


def main() -> None:
    args = _parse_args()

    sources = load_sources()
    if not sources:
        print("원문을 찾지 못했습니다. docs/sources/raw/*.txt 확인.")
        return
    print(f"원문 {len(sources)}건 로드: {', '.join(sources)}")
    print(f"사용 가능 provider: "
          f"{', '.join(n for n, ok in available_providers().items() if ok)}")

    kwargs = {"run_path": args.run} if args.provider == "replay" else {}
    if args.provider == "manual":
        kwargs["workdir"] = RUNS_DIR / "manual"
    try:
        complete = resolve_completion(args.provider, model=args.model, **kwargs)
        extraction = extract_regchange(sources, complete=complete)
    except LLMBackendError as e:
        print(f"\n[LLM 백엔드] {e}")
        return
    except ImportError:
        print("\n[안내] anthropic SDK 미설치. `pip install anthropic` 또는 무과금 provider를 쓰세요.")
        return

    print(f"\n=== 추출 결과 ({len(extraction.changes)}건) ===")
    for c in extraction.changes:
        ba = f"{c.before} → {c.after}" if (c.before or c.after) else ""
        print(f"[{c.category}] {c.summary}  {ba}  (conf {c.confidence:.2f})")
        print(f"    ⤷ {c.citation.source_doc_id}: \"{c.citation.quote[:60]}...\"")

    # 경계 변환: 한글 지역명 → 룰엔진 지역코드 (결정적, LLM 미개입)
    norm = normalize_regions(extraction)
    print(f"\n=== 지역 코드 정규화 (coverage {norm.coverage:.0%}) ===")
    for name, code in norm.mapping.items():
        print(f"    {name} → {code}")
    for name in norm.unmapped:
        print(f"    ⚠ 코드 미확인(사람 확인 필요): {name}")
    extraction = norm.normalized

    print("\n=== Assurance: Citation Grounding ===")
    g = check_citation_grounding(extraction, sources)
    print(f"Citation Correctness: {g.citation_correctness:.0%}  "
          f"Unsupported Claim Rate: {g.unsupported_claim_rate:.0%}")
    for u in g.ungrounded:
        print(f"    ⚠ 원문 미확인(환각 가능): [{u.category}] {u.summary}")
        print(f"        인용: \"{u.citation.quote[:80]}\"")

    print("\n=== Assurance: Gold 대조 ===")
    s = score_against_gold(extraction, GOLD)
    print(f"Change Completeness: {s.change_completeness:.0%}  "
          f"Exception Recall: {s.exception_recall:.0%}  "
          f"Effective-date: {'OK' if s.effective_date_correct else 'MISS'}  "
          f"Regions: {'OK' if s.regions_correct else 'MISS'}")
    if not s.effective_date_correct:
        print(f"    시행일: 추출 {extraction.effective_from!r} vs 골드 {GOLD['effective_from']!r}")
    if not s.regions_correct:
        print(f"    지역: 추출 {extraction.target_regions} vs 골드 {GOLD['target_regions']}")
    if s.missed_changes:
        print(f"    놓친 변경: {s.missed_changes}")
    if s.missed_exceptions:
        print(f"    놓친 예외: {s.missed_exceptions}")

    if args.no_save:
        return

    # 실행 기록 — 재현(replay)·재채점·리포트의 원본. 원문 해시로 입력 동일성을 고정한다.
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    record = {
        "provider": args.provider,
        "model": args.model,
        "source_sha256": {
            doc_id: hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
            for doc_id, text in sources.items()
        },
        "gold_file": str(GOLD_PATH.relative_to(REPO)),
        "extraction": asdict(extraction),
        "region_normalization": {
            "mapping": norm.mapping,
            "unmapped": norm.unmapped,
            "coverage": norm.coverage,
        },
        "assurance": {
            "citation_correctness": g.citation_correctness,
            "unsupported_claim_rate": g.unsupported_claim_rate,
            "grounded": g.grounded,
            "total_changes": g.total,
            "ungrounded_summaries": [u.summary for u in g.ungrounded],
            "change_completeness": s.change_completeness,
            "exception_recall": s.exception_recall,
            "effective_date_correct": s.effective_date_correct,
            "regions_correct": s.regions_correct,
            "missed_changes": s.missed_changes,
            "missed_exceptions": s.missed_exceptions,
        },
    }
    name = f"run_{args.tag or args.provider}.json"
    out = RUNS_DIR / name
    out.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n실행 기록 저장: {out.relative_to(REPO)}")
    print(f"재현: python examples/run_extractor.py --provider replay --run {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
