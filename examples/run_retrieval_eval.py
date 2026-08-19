"""검색 품질 실측 재현 — BM25 recall@k (사람 확정 인용 기준, DEV만).

실행:  python examples/run_retrieval_eval.py

LLM 호출 0회. LOCKED/CHALLENGE 는 열지 않는다(검색 튜닝도 튜닝이다 — 브리프 §12).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from regimpact.extractor.sources import load_corpus            # noqa: E402
from regimpact.retrieval import BM25Index, chunk_sources, citation_recall  # noqa: E402

corpus = load_corpus()
chunks = chunk_sources(corpus)
index = BM25Index(chunks)
print(f"색인: 코퍼스 {len(corpus)}건 → 청크 {len(chunks)}개 "
      "(6·30 스냅샷 3건 + 과거 정책 원문)\n")

from regimpact.extractor.sources import SOURCE_FILES  # noqa: E402

for label, kw in (
    ("기본 BM25 (전체 코퍼스)      ", {}),
    ("지역 별칭 확장 ON            ", {"expand": True}),
    ("시점 필터 (6·30 문서로 한정) ", {"doc_ids": set(SOURCE_FILES)}),
):
    rep = citation_recall(index, corpus, **kw)
    print(label + "— " + rep.summary())

rep = citation_recall(index, corpus, doc_ids=set(SOURCE_FILES))
if rep.misses_at_max_k:
    print(f"\ntop-{max(rep.ks)} 에도 못 찾은 인용 {len(rep.misses_at_max_k)}건:")
    for m in rep.misses_at_max_k:
        print(f"  {m.item_id:14} [{m.doc_id}] “{m.quote_head}…”")
    print("\n검색이 못 찾는 걸 LLM 이 메꾸면 그게 곧 환각이다 — 그래서 검색부터 측정한다.")
