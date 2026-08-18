"""골드셋 QA 평가 실행 — DEV 문항을 LLM에 태우고 채점한다.

**기본은 DEV만 연다.** LOCKED/CHALLENGE는 `--split`으로 지정해도 사유를 요구하고 기록된다.

    python examples/run_goldset_eval.py                       # DEV 40, cli 백엔드(0원)
    python examples/run_goldset_eval.py --tag v2              # 실행 기록 태그
    python examples/run_goldset_eval.py --provider replay --run <경로>
"""
import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from regimpact.eval import (  # noqa: E402
    Split,
    answer_questions,
    QA_JSON_INSTRUCTION,
    format_qa_report,
    load_split,
    score_qa,
    validate_qa_response,
)
from regimpact.eval.qa import QAResponse  # noqa: E402
from regimpact.extractor import LLMBackendError, resolve_completion  # noqa: E402
from regimpact.extractor.sources import load_sources  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
RUNS = REPO / "docs" / "eval" / "runs"


def _args():
    p = argparse.ArgumentParser(description="골드셋 QA 평가")
    p.add_argument("--split", default="DEV", choices=[s.value for s in Split])
    p.add_argument("--unseal-reason", default=None, help="LOCKED/CHALLENGE 사용 시 필수")
    p.add_argument("--provider", default="cli")
    p.add_argument("--model", default="claude-sonnet-5")
    p.add_argument("--batch-size", type=int, default=5)
    p.add_argument("--limit", type=int, default=None, help="앞에서 N문항만 (스모크 테스트용)")
    p.add_argument("--tag", default=None)
    p.add_argument("--run", default=None, help="--provider replay 시 재생할 응답 기록")
    return p.parse_args()


def main() -> None:
    a = _args()
    split = Split(a.split)
    sources = load_sources()
    items = load_split(split, unseal_reason=a.unseal_reason)
    if a.limit:
        items = items[: a.limit]
    print(f"{split.value} {len(items)}문항 · 원문 {len(sources)}건 · batch_size={a.batch_size}")

    if a.provider == "replay":
        saved = json.loads(Path(a.run).read_text(encoding="utf-8"))
        responses = {
            k: QAResponse(v["item_id"], v["answer"],
                          tuple(tuple(c) for c in v["citations"]), v["needs_human_review"])
            for k, v in saved["responses"].items()
        }
    else:
        try:
            complete = resolve_completion(
                a.provider, model=a.model,
                validator=validate_qa_response, instruction=QA_JSON_INSTRUCTION,
            )
        except LLMBackendError as e:
            print(f"[LLM 백엔드] {e}")
            return
        try:
            responses = answer_questions(
                items, sources, complete=complete, batch_size=a.batch_size,
                on_batch=lambda n, t: print(f"  배치 {n}/{t} …", flush=True),
            )
        except LLMBackendError as e:
            print(f"[LLM 백엔드] {e}")
            return

    rep = score_qa(items, responses, sources,
                   batch_size=a.batch_size, provider=a.provider, model=a.model or "")
    print()
    print(format_qa_report(rep))

    worst = rep.worst_items[:8]
    if worst:
        print("\n  실패 문항 (하위 8):")
        for s in worst:
            bits = []
            if s.missed_facts:
                bits.append(f"놓친 사실 {s.missed_facts}")
            if not s.escalation_ok:
                bits.append(f"escalation 기대={s.escalation_expected} 실제={s.escalation_given}")
            if s.citations_total and s.citations_grounded < s.citations_total:
                bits.append(f"환각 인용 {s.citations_total - s.citations_grounded}건")
            print(f"    {s.item_id} [{s.category}] — {' / '.join(bits) or '기타'}")

    RUNS.mkdir(parents=True, exist_ok=True)
    name = f"qa_{split.value.lower()}_{a.tag or a.provider}.json"
    out = RUNS / name
    out.write_text(json.dumps({
        "split": split.value, "provider": a.provider, "model": a.model,
        "batch_size": a.batch_size, "item_count": len(items),
        "metrics": {
            "fact_coverage": rep.fact_coverage, "exact_rate": rep.exact_rate,
            "citation_correctness": rep.citation_correctness,
            "unsupported_claim_rate": rep.unsupported_claim_rate,
            "escalation_precision": rep.escalation_precision,
            "escalation_recall": rep.escalation_recall,
            "by_category": rep.by_category(), "failure_modes": rep.failure_modes(),
        },
        "scores": [asdict(s) for s in rep.scores],
        "responses": {k: asdict(v) for k, v in responses.items()},
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n실행 기록 저장: {out.relative_to(REPO)}")


if __name__ == "__main__":
    main()
