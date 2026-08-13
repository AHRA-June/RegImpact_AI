"""어휘 검색(BM25) — 순수 표준 라이브러리, 의존성 0, 결정론.

무료·오프라인·재현 가능. 한국어 대응: 어절 토큰 + 한글 문자 bigram(부분 매칭 recall 향상).
임베딩/벡터DB 없이도 근거 문단을 찾는다. 임베딩 검색은 retriever.EmbeddingRetriever(주입식)로 별도.
"""
from __future__ import annotations

import math
import re
from collections import Counter

from .chunk import Chunk

# 어절: 라틴 단어 / 퍼센트·숫자 / 한글 음절 런
_TOKEN = re.compile(r"[a-zA-Z]+|\d+%|\d+|[가-힣]+")


def tokenize(text: str) -> list[str]:
    """토큰화. 한글 런은 원형 + 문자 bigram을 함께 넣어 부분 매칭을 돕는다."""
    toks: list[str] = []
    for tok in _TOKEN.findall(text.lower()):
        toks.append(tok)
        if len(tok) >= 2 and "가" <= tok[0] <= "힣":   # 한글 런
            toks.extend(tok[i:i + 2] for i in range(len(tok) - 1))
    return toks


class BM25:
    """표준 BM25 (k1, b). 결정론적 랭킹."""

    def __init__(self, corpus_tokens: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.docs = corpus_tokens
        self.N = len(corpus_tokens)
        self.doc_len = [len(d) for d in corpus_tokens]
        self.avgdl = (sum(self.doc_len) / self.N) if self.N else 0.0
        self.tf = [Counter(d) for d in corpus_tokens]
        df: Counter = Counter()
        for d in corpus_tokens:
            df.update(set(d))
        # idf (BM25+ 스타일, 음수 방지)
        self.idf = {
            t: math.log(1 + (self.N - n + 0.5) / (n + 0.5)) for t, n in df.items()
        }

    def score(self, query_tokens: list[str], i: int) -> float:
        if self.avgdl == 0:
            return 0.0
        s = 0.0
        tf, dl = self.tf[i], self.doc_len[i]
        for t in query_tokens:
            if t not in tf:
                continue
            idf = self.idf.get(t, 0.0)
            freq = tf[t]
            denom = freq + self.k1 * (1 - self.b + self.b * dl / self.avgdl)
            s += idf * (freq * (self.k1 + 1)) / denom
        return s


class LexicalRetriever:
    """BM25 어휘 검색기. chunks를 색인하고 query에 대한 top-k 청크를 반환한다."""

    def __init__(self, chunks: list[Chunk], k1: float = 1.5, b: float = 0.75):
        self.chunks = list(chunks)
        self._corpus = [tokenize(c.text) for c in self.chunks]
        self.bm25 = BM25(self._corpus, k1=k1, b=b)

    def retrieve(self, query: str, k: int = 5) -> list[tuple[Chunk, float]]:
        """query 상위 k개 (chunk, score). 동점은 chunk_id로 안정 정렬."""
        q = tokenize(query)
        scored = [(self.chunks[i], self.bm25.score(q, i)) for i in range(len(self.chunks))]
        scored = [cs for cs in scored if cs[1] > 0.0]
        scored.sort(key=lambda cs: (-cs[1], cs[0].chunk_id))
        return scored[:k]
