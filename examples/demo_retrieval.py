"""RAG/Retrieval 데모 — BM25 어휘 검색 + recall@k 평가.

실행: python examples/demo_retrieval.py   (repo 루트, 의존성·API 키 불필요)
출력: 청크 통계 · recall@k 곡선 · 예시 질의 top-k · docs/reports/retrieval_stats.md

핵심: 검색이 근거 문단을 놓치지 않는 k를 recall@k로 고른다(하류 Assurance 완전성 보호).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from regimpact.extractor import load_sources  # noqa: E402
from regimpact.retrieval import (  # noqa: E402
    LexicalRetriever,
    chunk_documents,
    recall_curve,
    retrieve_context,
)

GOLD = json.loads((ROOT / "docs/eval/regchange_gold_6_30.json").read_text(encoding="utf-8"))


def main() -> None:
    sources = load_sources()
    chunks = chunk_documents(sources)
    retriever = LexicalRetriever(chunks)

    lines = ["# Retrieval Stats (BM25 어휘 검색, 무료·결정론)", ""]
    lines.append(f"- 문서 {len(sources)}건 → 청크 {len(chunks)}개")
    per_doc = {}
    for c in chunks:
        per_doc[c.doc_id] = per_doc.get(c.doc_id, 0) + 1
    for d, n in per_doc.items():
        lines.append(f"  - {d}: {n} 청크")
    lines.append("")

    curve = recall_curve(retriever, GOLD, ks=(1, 3, 5, 8))
    lines.append("## recall@k (골드 근거 문단 회수율)")
    for k, r in curve.items():
        lines.append(f"- recall@{k} = {r:.0%}")
    lines.append("")

    lines.append("## 예시 질의 top-3")
    for q in ["규제지역 LTV 70 40 강화", "생애최초 서민 실수요 완화", "경과규정 종전규정 계약금"]:
        hits = retriever.retrieve(q, k=3)
        lines.append(f"- q=\"{q}\"")
        for c, s in hits:
            snippet = c.text.replace("\n", " ")[:60]
            lines.append(f"    [{c.chunk_id}] score={s:.2f}  {snippet}…")
    lines.append("")

    ctx = retrieve_context(retriever, "규제지역 주담대 LTV 예외 경과규정 시행일", k=8)
    lines.append("## retrieve_context (grounding 보존, 원본 doc_id로 묶음)")
    for doc_id, text in ctx.items():
        lines.append(f"- {doc_id}: {len(text)}자")

    md = "\n".join(lines)
    print(md)
    out = ROOT / "docs" / "reports" / "retrieval_stats.md"
    out.write_text(md + "\n", encoding="utf-8")
    print(f"\n생성됨: {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
