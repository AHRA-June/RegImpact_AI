"""원문 → 검색 단위(passage) 분할 — 결정적, 원문 위치 보존.

청크는 (doc_id, start, end) 로 **정규화된 원문 안의 위치**를 기억한다.
검색 품질 평가가 "골드 인용 구간을 top-k 가 덮었는가"로 정의되기 때문에(§evaluate),
위치를 잃으면 평가 자체가 성립하지 않는다.

경계는 공백 위에서만 자른다 — PDF/HWP 추출본은 문장 구두점이 불안정해서
문장 분할기가 오히려 비결정적 경계를 만든다(이 프로젝트가 두 번 겪은 함정).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# 창 크기·겹침(문자 단위). 겹침이 골드 인용 최대 길이(~220자)의 절반을 넘어야
# 인용이 두 청크 사이에서 완전히 조각나는 일이 없다.
SIZE = 420
OVERLAP = 140

_WS = re.compile(r"\s+")


def normalize(text: str) -> str:
    """공백 정규화 — 검증기·골드 인용과 같은 규칙을 쓴다 (어긋나면 위치가 어긋난다)."""
    return _WS.sub(" ", text).strip()


@dataclass(frozen=True)
class Chunk:
    id: str
    doc_id: str
    start: int      # 정규화 원문 내 문자 오프셋
    end: int
    text: str

    def to_dict(self) -> dict:
        return {"id": self.id, "doc_id": self.doc_id,
                "start": self.start, "end": self.end, "text": self.text}


def _window_bounds(n: int, size: int, overlap: int) -> list[tuple[int, int]]:
    step = size - overlap
    out, s = [], 0
    while s < n:
        out.append((s, min(n, s + size)))
        if s + size >= n:
            break
        s += step
    return out


def chunk_sources(
    sources: dict[str, str], *, size: int = SIZE, overlap: int = OVERLAP
) -> list[Chunk]:
    chunks: list[Chunk] = []
    for doc_id in sorted(sources):
        text = normalize(sources[doc_id])
        for s, e in _window_bounds(len(text), size, overlap):
            # 경계를 공백 위로 — 단어 중간에서 자르면 어휘 매칭이 깨진다
            if s > 0:
                sp = text.rfind(" ", max(0, s - 40), s + 1)
                if sp != -1:
                    s = sp + 1
            if e < len(text):
                sp = text.find(" ", e, min(len(text), e + 40))
                if sp != -1:
                    e = sp
            chunks.append(Chunk(id=f"{doc_id}#{len([c for c in chunks if c.doc_id == doc_id])}",
                                doc_id=doc_id, start=s, end=e, text=text[s:e]))
    return chunks
