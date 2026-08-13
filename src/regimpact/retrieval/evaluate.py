"""검색 평가 — recall@k. "필요한 근거 문단을 top-k가 실제로 찾아오는가."

RAG의 급소는 검색이 정답 근거를 놓치면(누락) 하류 추출의 완전성이 함께 떨어진다는 것.
따라서 검색층도 **평가**한다. 골드(required_changes·exceptions)의 keywords를 지지 근거로 보고,
질의별 top-k 청크 합집합이 그 근거를 포함하는지로 recall@k를 측정한다.

이 지표는 "검색이 하류 Assurance(Change Completeness·Exception Recall)를 훼손하지 않을 k"를 고른다.
"""
from __future__ import annotations

from dataclasses import dataclass

from .retriever import Retriever


def _covered(chunks_text: str, keywords: list[str]) -> bool:
    hay = chunks_text.lower()
    return any(kw.lower() in hay for kw in keywords)


def _gold_items(gold: dict) -> list[tuple[str, list[str]]]:
    """(id, keywords) 목록 — required_changes + exceptions."""
    items: list[tuple[str, list[str]]] = []
    for r in gold.get("required_changes", []):
        items.append((r.get("id", r["keywords"][0]), r["keywords"]))
    for e in gold.get("exceptions", []):
        items.append((f"exc:{e['name']}", e["keywords"]))
    return items


@dataclass
class RecallReport:
    k: int
    total: int
    hits: int
    missed: list[str]

    @property
    def recall(self) -> float:
        return self.hits / self.total if self.total else 1.0


def recall_at_k(retriever: Retriever, gold: dict, k: int = 5) -> RecallReport:
    """각 골드 항목의 keywords를 질의로 top-k 검색 → 근거 포함 여부로 recall@k."""
    items = _gold_items(gold)
    hits = 0
    missed: list[str] = []
    for item_id, keywords in items:
        query = " ".join(keywords)
        hit_chunks = retriever.retrieve(query, k=k)
        joined = "\n".join(c.text for c, _ in hit_chunks)
        if _covered(joined, keywords):
            hits += 1
        else:
            missed.append(item_id)
    return RecallReport(k=k, total=len(items), hits=hits, missed=missed)


def recall_curve(retriever: Retriever, gold: dict, ks=(1, 3, 5, 8)) -> dict[int, float]:
    """k별 recall 곡선 — '충분한 k'를 고르는 근거."""
    return {k: recall_at_k(retriever, gold, k=k).recall for k in ks}
