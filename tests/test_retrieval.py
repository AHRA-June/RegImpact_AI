"""검색 레이어 — 청킹 보장·BM25 결정성·recall 측정 정의를 고정한다."""
import pytest

from regimpact.extractor.sources import load_sources
from regimpact.retrieval import (
    BM25Index,
    chunk_sources,
    citation_recall,
    expand_query,
    tokenize,
)
from regimpact.retrieval.chunker import OVERLAP, SIZE, normalize
from regimpact.retrieval.evaluate import COVER_RATIO


@pytest.fixture(scope="module")
def sources():
    return load_sources()


@pytest.fixture(scope="module")
def index(sources):
    return BM25Index(chunk_sources(sources))


# ---------------------------------------------------------------- 청킹

def test_chunks_cover_the_whole_document(sources):
    """구간 합집합이 원문 전체를 덮는다 — 빈틈이 있으면 그 구간의 인용은 영원히 못 찾는다."""
    for doc_id, text in sources.items():
        n = len(normalize(text))
        chunks = [c for c in chunk_sources({doc_id: text}) if c.doc_id == doc_id]
        covered = 0
        for c in sorted(chunks, key=lambda c: c.start):
            assert c.start <= covered, f"{doc_id}: {covered}~{c.start} 빈틈"
            covered = max(covered, c.end)
        assert covered == n


def test_chunk_text_matches_offsets(sources):
    """(start, end) 가 실제 원문 위치와 어긋나면 recall 측정 전체가 무의미해진다."""
    for c in chunk_sources(sources):
        assert normalize(sources[c.doc_id])[c.start:c.end] == c.text


def test_overlap_exceeds_half_of_max_citation():
    """겹침 보장 — 인용(최대 ~220자)이 두 청크 사이에서 60% 미만으로 조각나지 않는다."""
    assert OVERLAP >= 220 * COVER_RATIO
    assert OVERLAP < SIZE


# ---------------------------------------------------------------- 토크나이저·BM25

def test_tokenizer_handles_korean_particles():
    """조사(이/은/을)가 달라도 2-gram 이 겹친다 — 형태소 분석기 없는 한국어 매칭의 근거."""
    a, b = set(tokenize("규제지역이")), set(tokenize("규제지역은"))
    assert a & b >= {"규제", "제지", "지역"}


def test_search_is_deterministic(index):
    q = "규제지역 LTV"
    r1 = [(s.chunk.id, s.score) for s in index.search(q, k=10)]
    r2 = [(s.chunk.id, s.score) for s in index.search(q, k=10)]
    assert r1 == r2


def test_alias_expansion_is_deterministic_and_bounded():
    """확장은 별칭 테이블(D-01)에서만 온다 — 없는 지역이 생기지 않는다."""
    q = expand_query("동탄 LTV")
    assert "동탄" in q
    assert q == expand_query("동탄 LTV")
    assert expand_query("경과규정이란") == "경과규정이란"   # 지역 없으면 그대로


def test_expansion_connects_colloquial_region_names(index):
    """'동탄' 단독 질의가 확장으로 '화성시 동탄구' 원문과 만난다."""
    hits = index.search("동탄", k=5, expand=True)
    assert any("동탄" in s.chunk.text for s in hits)


# ---------------------------------------------------------------- recall 측정

def test_recall_is_monotonic_in_k(index, sources):
    rep = citation_recall(index, sources)
    rs = [rep.recall(k) for k in rep.ks]
    assert rs == sorted(rs), "k 가 커지는데 recall 이 줄면 측정이 잘못된 것"


def test_recall_counts_every_dev_citation(index, sources):
    from regimpact.eval import Split, load_split
    rep = citation_recall(index, sources)
    expected = sum(len(i.citations) for i in load_split(Split.DEV))
    assert rep.n_citations == expected


def test_misses_are_reported_not_hidden(index, sources):
    """미적중 인용은 목록으로 남는다 — recall 수치만 보이고 뭘 놓쳤는지 안 보이면 개선이 없다."""
    rep = citation_recall(index, sources)
    assert len(rep.misses_at_max_k) == rep.n_citations - rep.hits[max(rep.ks)]


def test_every_citation_is_reachable_by_some_chunk(sources):
    """분모 검증 — 오라클 검색기라면 100%에 닿는가. 어떤 인용을 **어느 청크도** 60% 이상
    덮지 못하면 그 인용은 검색기가 아무리 좋아져도 영원히 미적중이고, recall 상한이
    조용히 낮아진다. 그건 검색 문제가 아니라 청킹 결함이므로 여기서 잡는다."""
    from regimpact.eval import Split, load_split
    from regimpact.retrieval.evaluate import _covered

    chunks = chunk_sources(sources)
    norm = {d: normalize(t) for d, t in sources.items()}
    for it in load_split(Split.DEV):
        for cit in it.citations:
            q = normalize(cit.quote)
            pos = norm[cit.source_doc_id].find(q)
            assert pos >= 0
            span = (pos, pos + len(q))
            assert any(
                c.doc_id == cit.source_doc_id and _covered(span, c.start, c.end)
                for c in chunks
            ), f"[{it.id}] 인용을 덮는 청크가 없다 — 청킹 파라미터 결함"
