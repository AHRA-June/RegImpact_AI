"""문서 간 병합 임계값 스윕 — 저장된 실행 위에서 돌린다(LLM 호출 0회).

병합은 **누락을 만들지 않아야** 한다. 그래서 임계값을 고르는 기준은 "얼마나 줄였나"가 아니라
"줄이면서도 골드 대비 완전성·재현율이 유지되는가"다. 유지되지 않는 임계값은 아무리 깔끔해도 탈락.
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from regimpact.extractor import check_citation_grounding, score_against_gold  # noqa: E402
from regimpact.extractor.merge import merge_cross_document  # noqa: E402
from regimpact.extractor.schema import RegChangeExtraction  # noqa: E402
from regimpact.extractor.sources import load_sources  # noqa: E402

run = json.loads((REPO / "docs/eval/runs/run_perdoc_sonnet5.json").read_text(encoding="utf-8"))
gold = json.loads((REPO / "docs/eval/regchange_gold_6_30.json").read_text(encoding="utf-8"))
sources = load_sources()
base = RegChangeExtraction.from_dict(run["extraction"])

print(f"{'θ':>5} {'항목':>5} {'감소':>5} {'Completeness':>13} {'ExcRecall':>10} {'Citation':>9}  놓친 항목")
for th in (1.01, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2):
    items, removed = merge_cross_document(list(base.changes), threshold=th)
    ext = RegChangeExtraction(base.policy_id, list(base.target_regions), base.effective_from, items)
    s = score_against_gold(ext, gold)
    g = check_citation_grounding(ext, sources)
    flag = "" if (s.change_completeness == 1.0 and s.exception_recall == 1.0) else "  ❌ 누락 발생"
    print(f"{th:>5.2f} {len(items):>5} {removed:>5} {s.change_completeness:>12.0%} "
          f"{s.exception_recall:>10.0%} {g.citation_correctness:>9.0%}  "
          f"{','.join(s.missed_changes + s.missed_exceptions) or '-'}{flag}")
