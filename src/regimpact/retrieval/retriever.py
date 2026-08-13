"""Retriever 인터페이스 + 임베딩 검색(주입식) + grounding 보존 컨텍스트 빌더.

설계 원칙(Extractor와 동일): **주입식**. LexicalRetriever(BM25, 기본)든 EmbeddingRetriever(임베딩
함수 주입)든 `retrieve(query, k) -> [(Chunk, score)]` 시그니처만 맞추면 파이프라인에 꽂힌다.

grounding 체인 보존: `retrieve_context`는 검색된 청크를 **원본 doc_id로 묶어** 돌려준다.
→ Extractor 프롬프트는 여전히 원문 doc_id를 쓰고, 인용은 원문에 매핑되어 Assurance가 그대로 작동한다.
"""
from __future__ import annotations

import math
from typing import Callable, Protocol

from .chunk import Chunk

# 임베딩 함수: 텍스트 목록 → 벡터 목록 (무료/로컬 Ollama 등 주입 가능)
EmbedFn = Callable[[list[str]], list[list[float]]]


class Retriever(Protocol):
    def retrieve(self, query: str, k: int = 5) -> list[tuple[Chunk, float]]: ...


def _cosine(a: list[float], b: list[float]) -> float:
    num = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return num / (na * nb) if na and nb else 0.0


class EmbeddingRetriever:
    """임베딩 기반 검색(주입식 embed 함수). 벡터DB·numpy 없이 순수 파이썬 코사인.

    embed는 (texts) -> vectors. 무료/로컬(예: Ollama `/v1/embeddings`)을 주입할 수 있다.
    색인 시 청크 임베딩을 한 번 계산해 캐시한다(결정론은 embed 함수에 의존).
    """

    def __init__(self, chunks: list[Chunk], embed: EmbedFn):
        self.chunks = list(chunks)
        self._embed = embed
        self._vecs = embed([c.text for c in self.chunks]) if self.chunks else []

    def retrieve(self, query: str, k: int = 5) -> list[tuple[Chunk, float]]:
        if not self.chunks:
            return []
        qv = self._embed([query])[0]
        scored = [(self.chunks[i], _cosine(qv, self._vecs[i])) for i in range(len(self.chunks))]
        scored.sort(key=lambda cs: (-cs[1], cs[0].chunk_id))
        return scored[:k]


def retrieve_context(retriever: Retriever, query: str, k: int = 5) -> dict[str, str]:
    """top-k 청크를 **원본 doc_id로 묶어** {doc_id: 결합 텍스트}로 반환(grounding 보존).

    Extractor의 sources 인자로 그대로 쓸 수 있다. 같은 doc_id의 청크는 원문 순서(line_start)로 결합.
    """
    hits = retriever.retrieve(query, k=k)
    by_doc: dict[str, list[Chunk]] = {}
    for chunk, _score in hits:
        by_doc.setdefault(chunk.doc_id, []).append(chunk)
    out: dict[str, str] = {}
    for doc_id, chunks in by_doc.items():
        chunks.sort(key=lambda c: c.line_start)
        out[doc_id] = "\n…\n".join(c.text for c in chunks)
    return out
