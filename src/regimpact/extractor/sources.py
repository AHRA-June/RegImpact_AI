"""공문 원문 로더 — docs/sources/raw/*.txt를 doc_id로 읽는다.

두 층이 있다:
  SOURCE_FILES — 6·30 사건의 추출·골드 채점 대상(3건). 추출 파이프라인·골드 검증이
    이 셋에 고정돼 있으므로 **여기에 문서를 더하면 기존 실측의 의미가 바뀐다.**
  CORPUS_FILES — 검색(retrieval) 코퍼스 전체. 과거 정책 원문(2020 6·17, 2025 10·15)을
    포함한다. 검색·시점 질의는 이 층을 쓴다.
"""
from __future__ import annotations

from pathlib import Path

# doc_id -> raw 텍스트 파일명 (docs/sources/SOURCES.md 레지스트리)
SOURCE_FILES = {
    "FSC_PRESS_20260630": "fsc_press_20260630.txt",
    "MOLIT_PRESS_20260630": "molit_press_20260630.txt",
    "FAQ_20260630": "faq_20260630.txt",
}

# 검색 코퍼스 = 6·30 스냅샷 + 과거 정책 원문 (2026-08-19 사용자 제공)
CORPUS_FILES = {
    **SOURCE_FILES,
    "FSC_PRESS_20251015": "fsc_press_20251015.txt",
    "FAQ_20251015": "faq_20251015.txt",
    "MOLIT_PRESS_20200617": "molit_press_20200617.txt",
    "QNA_20200617": "qna_20200617.txt",
}

# 문서 시점 메타데이터 — 규제 FAQ 는 대책마다 거의 같은 문구로 다시 나오므로(실측:
# 2025 FAQ ↔ 2026 FAQ), 시점 없이 검색하면 유사 문서 간 혼동이 생긴다. 발표일은
# SOURCES.md 레지스트리와 같아야 하며 테스트가 대조한다.
CORPUS_EVENTS = {
    "FSC_PRESS_20260630": ("2026-06-30", "2026 6·30 대책"),
    "MOLIT_PRESS_20260630": ("2026-06-30", "2026 6·30 대책"),
    "FAQ_20260630": ("2026-06-30", "2026 6·30 대책"),
    "FSC_PRESS_20251015": ("2025-10-15", "2025 10·15 대책"),
    "FAQ_20251015": ("2025-10-15", "2025 10·15 대책"),
    "MOLIT_PRESS_20200617": ("2020-06-17", "2020 6·17 대책"),
    "QNA_20200617": ("2020-06-17", "2020 6·17 대책"),
}


def _load(files: dict[str, str], raw_dir: str | Path | None) -> dict[str, str]:
    if raw_dir is None:
        raw_dir = Path(__file__).resolve().parents[3] / "docs" / "sources" / "raw"
    raw_dir = Path(raw_dir)
    out: dict[str, str] = {}
    for doc_id, fname in files.items():
        p = raw_dir / fname
        if p.exists():
            out[doc_id] = p.read_text(encoding="utf-8")
    return out


def load_sources(raw_dir: str | Path | None = None) -> dict[str, str]:
    """6·30 추출·채점 대상 원문 (3건)."""
    return _load(SOURCE_FILES, raw_dir)


def load_corpus(raw_dir: str | Path | None = None) -> dict[str, str]:
    """검색 코퍼스 전체 — 과거 정책 원문 포함."""
    return _load(CORPUS_FILES, raw_dir)
