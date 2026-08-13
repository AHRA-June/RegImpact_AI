"""RAG / Retrieval 층 — 근거 문단 검색 + 검색 평가.

핵심 진입점:
    chunk_documents(sources) -> list[Chunk]
    LexicalRetriever(chunks)          # BM25, 순수 stdlib·결정론·무료 (기본)
    EmbeddingRetriever(chunks, embed) # 임베딩 주입식 (무료/로컬 Ollama 등)
    retrieve_context(retriever, query, k) -> {doc_id: text}   # grounding 보존
    recall_at_k(retriever, gold, k) / recall_curve(...)       # 검색 평가

설계: Extractor와 동일한 **주입식**. 검색이 근거를 놓치면 하류 완전성이 떨어지므로 검색층도 평가한다.
"""
from .chunk import Chunk, chunk_document, chunk_documents
from .evaluate import RecallReport, recall_at_k, recall_curve
from .lexical import BM25, LexicalRetriever, tokenize
from .retriever import EmbeddingRetriever, Retriever, retrieve_context

__all__ = [
    "Chunk",
    "chunk_document",
    "chunk_documents",
    "tokenize",
    "BM25",
    "LexicalRetriever",
    "EmbeddingRetriever",
    "Retriever",
    "retrieve_context",
    "recall_at_k",
    "recall_curve",
    "RecallReport",
]
