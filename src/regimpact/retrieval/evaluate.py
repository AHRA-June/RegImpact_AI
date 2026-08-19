"""검색 품질 실측 — 사람 확정 인용이 있는 QA 골드(DEV)로 recall@k 를 잰다.

측정 정의(임의로 바꾸면 수치 비교가 무의미해지므로 여기 못박는다):
  질의  = 골드 문항의 질문 원문
  정답  = 그 문항의 골드 인용(원문 verbatim — 검증기가 매번 원문 대조)
  hit   = top-k 청크 중 하나가 **같은 문서에서 인용 구간의 60% 이상을 덮으면** 적중
  recall@k = 적중 인용 수 / 전체 인용 수

부분 덮음(60%)을 허용하는 이유: 청크 경계는 인용 경계와 무관하게 결정되므로
완전 포함을 요구하면 청킹 파라미터가 지표를 지배한다. 겹침(overlap)이 인용
최대 길이의 절반을 넘도록 chunker 가 보장하므로, 60% 덮음이면 사람이 그 청크에서
해당 근거를 읽을 수 있다.

LOCKED/CHALLENGE 는 열지 않는다 — 검색 튜닝도 튜닝이다(브리프 §12).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..eval import Split, load_split
from ..eval.schema import GoldItem
from .bm25 import BM25Index
from .chunker import normalize

COVER_RATIO = 0.6
DEFAULT_KS = (1, 3, 5, 10)


@dataclass
class Miss:
    item_id: str
    doc_id: str
    quote_head: str


@dataclass
class RetrievalReport:
    ks: tuple[int, ...]
    expanded: bool
    n_items: int
    n_citations: int
    hits: dict[int, int] = field(default_factory=dict)
    misses_at_max_k: list[Miss] = field(default_factory=list)
    doc_filtered: bool = False

    def recall(self, k: int) -> float:
        return self.hits[k] / self.n_citations if self.n_citations else 0.0

    def summary(self) -> str:
        parts = [f"recall@{k} {self.recall(k):.0%}" for k in self.ks]
        return (f"DEV {self.n_items}문항 · 인용 {self.n_citations}건 · "
                + " / ".join(parts)
                + (" · 지역 별칭 확장 ON" if self.expanded else "")
                + (" · 시점 필터 ON" if self.doc_filtered else ""))


def _covered(citation_span: tuple[int, int], chunk_start: int, chunk_end: int) -> bool:
    s, e = citation_span
    if e <= s:
        return False
    overlap = max(0, min(e, chunk_end) - max(s, chunk_start))
    return overlap / (e - s) >= COVER_RATIO


def citation_recall(
    index: BM25Index,
    sources: dict[str, str],
    *,
    items: list[GoldItem] | None = None,
    ks: tuple[int, ...] = DEFAULT_KS,
    expand: bool = False,
    doc_ids: set[str] | None = None,
) -> RetrievalReport:
    """doc_ids: 시점 필터 — DEV 질문은 전부 6·30 대책에 대한 것이므로, 6·30 문서로
    한정한 측정은 "질의 시점을 아는 시스템"의 성능이다(부풀리기가 아니라 올바른 동작 —
    어느 시점의 규제를 묻는지는 Temporal Policy Resolver 계열이 아는 정보다)."""
    if items is None:
        items = load_split(Split.DEV)
    norm_sources = {d: normalize(t) for d, t in sources.items()}

    max_k = max(ks)
    rep = RetrievalReport(ks=tuple(ks), expanded=expand,
                          n_items=len(items), n_citations=0,
                          hits={k: 0 for k in ks},
                          doc_filtered=doc_ids is not None)
    for item in items:
        top = index.search(item.question, k=max_k, expand=expand, doc_ids=doc_ids)
        for cit in item.citations:
            src = norm_sources.get(cit.source_doc_id, "")
            pos = src.find(normalize(cit.quote))
            if pos < 0:
                # 검증기가 이미 원문 존재를 강제하므로 여기 오면 측정 자체가 잘못된 것
                raise ValueError(f"[{item.id}] 골드 인용을 원문에서 찾지 못했다 — 정규화 불일치")
            span = (pos, pos + len(normalize(cit.quote)))
            rep.n_citations += 1
            for k in ks:
                if any(
                    s.chunk.doc_id == cit.source_doc_id
                    and _covered(span, s.chunk.start, s.chunk.end)
                    for s in top[:k]
                ):
                    rep.hits[k] += 1
            if not any(
                s.chunk.doc_id == cit.source_doc_id
                and _covered(span, s.chunk.start, s.chunk.end)
                for s in top[:max_k]
            ):
                rep.misses_at_max_k.append(Miss(
                    item_id=item.id, doc_id=cit.source_doc_id,
                    quote_head=" ".join(cit.quote.split())[:60]))
    return rep
