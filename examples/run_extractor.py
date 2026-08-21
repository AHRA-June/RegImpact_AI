"""RegChange Extractor 실행 — 공문 → AI 추출 → Assurance 채점 → 실행 기록 저장.

**유료 API 키 없이 실행된다.** 기본 provider는 로컬 `claude` CLI(Claude Code 구독에
포함, 별도 키 발급·결제수단 불필요)이며, Gemini 무료 티어·수동 중계·저장본 재생도 지원한다.

    python examples/run_extractor.py                      # auto: 무과금 경로 우선
    python examples/run_extractor.py --event 20251015     # 다른 규제 이벤트로
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
    extract_per_document,
    available_providers,
    check_citation_grounding,
    extract_regchange,
    load_sources,
    normalize_regions,
    resolve_completion,
    score_against_gold,
)
from regimpact.extractor.sources import EVENTS, get_event  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
RUNS_DIR = REPO / "docs" / "eval" / "runs"


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="RegChange Extractor 실행 + Assurance 채점")
    p.add_argument("--event", default=None,
                   help=f"규제 이벤트 ({'|'.join(EVENTS)}, 기본 6·30)")
    p.add_argument("--provider", default="auto",
                   help="auto|cli|gemini|manual|replay|anthropic (기본 auto = 무과금 우선)")
    p.add_argument("--model", default=None, help="provider별 모델 이름(생략 시 기본값)")
    p.add_argument("--run", default=None, help="--provider replay 일 때 재생할 run JSON 경로")
    p.add_argument("--tag", default=None, help="실행 기록 파일명에 붙일 태그")
    p.add_argument("--no-save", action="store_true", help="실행 기록을 저장하지 않음")
    p.add_argument("--per-document", action="store_true",
                   help="문서별 개별 추출 후 병합 (호출 N배, 문서 간 축약 손실 방지)")
    return p.parse_args()


def _score_against(extraction, gold: dict):
    """골드가 있는 이벤트에서만 부르는 채점 출력. 기록용으로 결과를 돌려준다."""
    print("\n=== Assurance: Gold 대조 ===")
    s = score_against_gold(extraction, gold)
    print(f"Change Completeness: {s.change_completeness:.0%}  "
          f"Exception Recall: {s.exception_recall:.0%}  "
          f"Effective-date: {'OK' if s.effective_date_correct else 'MISS'}  "
          f"Regions: {'OK' if s.regions_correct else 'MISS'}")
    if not s.effective_date_correct:
        print(f"    시행일: 추출 {extraction.effective_from!r} vs 골드 {gold['effective_from']!r}")
    if not s.regions_correct:
        print(f"    지역: 추출 {extraction.target_regions} vs 골드 {gold['target_regions']}")
    if s.missed_changes:
        print(f"    놓친 변경: {s.missed_changes}")
    if s.missed_exceptions:
        print(f"    놓친 예외: {s.missed_exceptions}")
    return s


def main() -> None:
    args = _parse_args()

    event = get_event(args.event)
    gold = (json.loads((REPO / event.gold).read_text(encoding="utf-8"))
            if event.gold else None)

    sources = load_sources(event=event.event_id)
    if not sources:
        print("원문을 찾지 못했습니다. docs/sources/raw/*.txt 확인.")
        return
    print(f"이벤트: {event.label} ({event.published_at})"
          f"{'' if gold else '  · 골드 없음 — 인용 대조까지만 실측'}")
    print(f"원문 {len(sources)}건 로드: {', '.join(sources)}")
    print(f"사용 가능 provider: "
          f"{', '.join(n for n, ok in available_providers().items() if ok)}")

    kwargs = {"run_path": args.run} if args.provider == "replay" else {}
    if args.provider == "manual":
        kwargs["workdir"] = RUNS_DIR / "manual"
    merge_report = None
    try:
        complete = resolve_completion(args.provider, model=args.model, **kwargs)
        if args.per_document:
            extraction, merge_report = extract_per_document(
                sources, complete=complete, cache_dir=RUNS_DIR / 'perdoc_cache'
            )
        else:
            extraction = extract_regchange(sources, complete=complete)
    except LLMBackendError as e:
        print(f"\n[LLM 백엔드] {e}")
        return
    except ImportError:
        print("\n[안내] anthropic SDK 미설치. `pip install anthropic` 또는 무과금 provider를 쓰세요.")
        return

    if merge_report is not None:
        print(f"\n=== 문서별 추출 → 병합 ===")
        for doc_id, n in merge_report.per_document.items():
            print(f"    {doc_id}: {n}건")
        print(f"    병합 {merge_report.merged_count}건 (중복 제거 {merge_report.duplicates_removed}건)")
        for c in merge_report.conflicts:
            print(f"    ⚠ {c}")

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

    if gold is None:
        # 정답이 없는 이벤트에 점수를 내지 않는다. 낼 수 있는 것만 낸다(인용 대조는 위에서 끝).
        print("\n=== Assurance: Gold 대조 — 건너뜀 ===")
        print("    이 이벤트는 사람이 확정한 골드가 아직 없습니다. 정답 없이 점수를 내지 않습니다.")
        print("    추출 결과는 🤖 초안이며, 검수 후 골드로 승격하면 완전성·예외 재현율이 켜집니다.")
        score = None
    else:
        score = _score_against(extraction, gold)

    if args.no_save:
        return

    # 실행 기록 — 재현(replay)·재채점·리포트의 원본. 원문 해시로 입력 동일성을 고정한다.
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    record = {
        "provider": args.provider,
        "per_document": args.per_document,
        "merge": None if merge_report is None else {
            "per_document": merge_report.per_document,
            "raw_count": merge_report.raw_count,
            "merged_count": merge_report.merged_count,
            "duplicates_removed": merge_report.duplicates_removed,
            "cross_document_merged": merge_report.cross_document_merged,
            "conflicts": merge_report.conflicts,
        },
        "model": args.model,
        "source_sha256": {
            doc_id: hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
            for doc_id, text in sources.items()
        },
        "event": {"id": event.event_id, "label": event.label,
                  "published_at": event.published_at},
        "gold_file": event.gold,
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
            # 골드가 없는 이벤트에서는 이 칸을 채우지 않는다 — 빈 값을 0 으로 적으면
            # 나중에 "0% 였다"로 읽힌다. 없는 것은 없는 채로 남긴다.
            **({} if score is None else {
                "change_completeness": score.change_completeness,
                "exception_recall": score.exception_recall,
                "effective_date_correct": score.effective_date_correct,
                "regions_correct": score.regions_correct,
                "missed_changes": score.missed_changes,
                "missed_exceptions": score.missed_exceptions,
            }),
        },
    }
    stem = args.tag or (args.provider if event.event_id == "20260630"
                        else f"{args.provider}_{event.event_id}")
    name = f"run_{stem}.json"
    out = RUNS_DIR / name
    out.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n실행 기록 저장: {out.relative_to(REPO)}")
    print(f"재현: python examples/run_extractor.py --provider replay --run {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
