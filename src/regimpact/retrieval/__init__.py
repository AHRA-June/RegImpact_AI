"""검색(retrieval) 레이어 — BM25 + 지역 별칭 확장, 표준 라이브러리만 사용.

브리프의 무과금·런타임 의존성 0 원칙 안에서 RAG 의 검색 절반을 구현한다(S-13).
벡터 임베딩은 유료 외부 의존이 생기므로 쓰지 않는다 — 코퍼스가 커져서 어휘 매칭이
한계에 닿으면 그때 근거와 함께 결정한다.

생성(LLM 답변) 절반은 기존 provider 레이어(`extractor/backends.py`)가 담당하고,
이 모듈은 **무엇을 문맥으로 줄 것인가**만 결정한다. 검색 품질은 사람 확정 인용이 있는
QA 골드(DEV)로 측정한다 — `evaluate.citation_recall`.
"""
from .bm25 import BM25Index, expand_query, tokenize
from .chunker import Chunk, chunk_sources
from .evaluate import RetrievalReport, citation_recall

__all__ = [
    "BM25Index", "Chunk", "RetrievalReport",
    "chunk_sources", "citation_recall", "expand_query", "tokenize",
]
