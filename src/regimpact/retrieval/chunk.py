"""문서 청킹 — 원문을 검색 단위(passage)로 분할.

원본 doc_id를 보존한다(인용 grounding 체인 유지: 검색 결과도 원문 doc_id로 되돌아감).
결정론적: 동일 입력 → 동일 청크·chunk_id. 페이지 마커("----- pN -----")를 경계 힌트로 쓰되
너무 긴 블록은 줄 경계에서 최대 크기로 다시 나눈다.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_PAGE = re.compile(r"^-+\s*p\d+\s*-+$", re.MULTILINE)


@dataclass(frozen=True)
class Chunk:
    """검색 단위. 원본 doc_id와 위치를 보존한다."""
    chunk_id: str          # f"{doc_id}#{index}"
    doc_id: str            # 원본 문서 id (인용 매핑용)
    text: str
    line_start: int        # 원문 내 시작 줄(1-based, 추적용)


def chunk_document(doc_id: str, text: str, max_lines: int = 8) -> list[Chunk]:
    """한 문서를 청크 목록으로. max_lines 단위 슬라이스(줄 경계 유지, 페이지 마커 제외)."""
    chunks: list[Chunk] = []
    idx = 0
    for block_text, start_line in _iter_line_blocks(text, max_lines):
        if not block_text.strip():
            continue
        chunks.append(Chunk(
            chunk_id=f"{doc_id}#{idx}",
            doc_id=doc_id,
            text=block_text.strip(),
            line_start=start_line,
        ))
        idx += 1
    return chunks


def _iter_line_blocks(text: str, max_lines: int):
    """max_lines 줄씩(빈 줄·페이지 마커 제외) 묶어 (텍스트, 시작줄) 산출."""
    lines = text.splitlines()
    buf: list[str] = []
    start = 1
    cur_start = None
    for i, line in enumerate(lines, start=1):
        if _PAGE.match(line.strip()):
            if buf:
                yield "\n".join(buf), cur_start
                buf, cur_start = [], None
            continue
        if not line.strip():
            continue
        if cur_start is None:
            cur_start = i
        buf.append(line)
        if len(buf) >= max_lines:
            yield "\n".join(buf), cur_start
            buf, cur_start = [], None
    if buf:
        yield "\n".join(buf), cur_start


def chunk_documents(sources: dict[str, str], max_lines: int = 8) -> list[Chunk]:
    """여러 문서를 청킹. doc_id 순서 안정."""
    out: list[Chunk] = []
    for doc_id in sources:                       # dict 삽입 순서 유지(결정론)
        out.extend(chunk_document(doc_id, sources[doc_id], max_lines=max_lines))
    return out
