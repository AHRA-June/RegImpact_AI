"""RAG/Retrieval 테스트 — 청킹·BM25·recall@k·grounding 보존·임베딩 주입.

핵심 검증: ①청킹 결정론·doc_id 보존 ②BM25 관련도 랭킹 ③recall@k(근거 회수)
④retrieve_context가 원문 verbatim·원본 doc_id 보존(grounding 체인) ⑤임베딩 검색 주입식.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from regimpact.extractor import load_sources  # noqa: E402
from regimpact.retrieval import (  # noqa: E402
    EmbeddingRetriever,
    LexicalRetriever,
    chunk_documents,
    recall_at_k,
    recall_curve,
    retrieve_context,
    tokenize,
)

ROOT = Path(__file__).resolve().parent.parent
GOLD = json.loads((ROOT / "docs/eval/regchange_gold_6_30.json").read_text(encoding="utf-8"))


def _sources():
    return load_sources()


# --- 토큰화 ---
def test_tokenize_korean_bigrams_and_latin():
    toks = tokenize("규제지역 LTV 40%")
    assert "규제지역" in toks
    assert "규제" in toks and "지역" in toks       # 한글 bigram
    assert "ltv" in toks                            # 라틴 소문자화
    assert "40%" in toks                            # 퍼센트 토큰


# --- 청킹 ---
def test_chunking_deterministic_and_preserves_docid():
    a = chunk_documents(_sources())
    b = chunk_documents(_sources())
    assert [c.chunk_id for c in a] == [c.chunk_id for c in b]     # 결정론
    assert len({c.chunk_id for c in a}) == len(a)                 # 유일
    doc_ids = set(_sources())
    assert all(c.doc_id in doc_ids for c in a)                    # 원본 doc_id 보존
    assert all(c.chunk_id.startswith(c.doc_id + "#") for c in a)


# --- BM25 랭킹 ---
def test_bm25_retrieves_relevant():
    r = LexicalRetriever(chunk_documents(_sources()))
    hits = r.retrieve("경과규정 계약금 종전규정", k=3)
    assert hits and hits[0][1] > 0
    joined = " ".join(c.text for c, _ in hits)
    assert "계약금" in joined or "종전규정" in joined


def test_bm25_deterministic_tie_break():
    r = LexicalRetriever(chunk_documents(_sources()))
    a = [c.chunk_id for c, _ in r.retrieve("규제지역 LTV", k=5)]
    b = [c.chunk_id for c, _ in r.retrieve("규제지역 LTV", k=5)]
    assert a == b


# --- recall@k ---
def test_recall_at_k_full_on_gold():
    r = LexicalRetriever(chunk_documents(_sources()))
    rep = recall_at_k(r, GOLD, k=5)
    assert rep.recall == 1.0
    assert rep.missed == []


def test_recall_curve_monotone_nondecreasing():
    r = LexicalRetriever(chunk_documents(_sources()))
    curve = recall_curve(r, GOLD, ks=(1, 3, 5, 8))
    vals = [curve[k] for k in (1, 3, 5, 8)]
    assert vals == sorted(vals)              # k↑ → recall 비감소
    assert vals[-1] == 1.0


# --- grounding 보존 ---
def test_retrieve_context_preserves_source_docids_and_verbatim():
    sources = _sources()
    r = LexicalRetriever(chunk_documents(sources))
    ctx = retrieve_context(r, "규제지역 주담대 LTV 예외 경과규정 시행일", k=8)
    assert set(ctx).issubset(set(sources))              # 원본 doc_id만
    # 각 결합 텍스트의 실제 줄이 원문에 verbatim 존재(인용 매핑 보장)
    for doc_id, text in ctx.items():
        for line in text.split("\n"):
            line = line.strip()
            if line and line != "…":
                assert line in sources[doc_id]


# --- 임베딩 검색(주입식) ---
def test_embedding_retriever_with_injected_embed():
    """토큰 겹침 기반 가짜 임베딩으로 코사인 검색이 동작(주입식 확인)."""
    from regimpact.retrieval.chunk import Chunk

    vocab = ["ltv", "규제지역", "생애최초", "경과규정", "계약금"]

    def fake_embed(texts):
        vecs = []
        for t in texts:
            toks = set(tokenize(t))
            vecs.append([1.0 if v in toks else 0.0 for v in vocab])
        return vecs

    chunks = [
        Chunk("D#0", "D", "규제지역 LTV 강화", 1),
        Chunk("D#1", "D", "생애최초 완화", 2),
        Chunk("D#2", "D", "경과규정 계약금 종전규정", 3),
    ]
    r = EmbeddingRetriever(chunks, fake_embed)
    top = r.retrieve("경과규정 계약금", k=1)
    assert top[0][0].chunk_id == "D#2"
