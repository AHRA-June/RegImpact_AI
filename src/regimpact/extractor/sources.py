"""공문 원문 로더 — docs/sources/raw/*.txt를 doc_id로 읽는다."""
from __future__ import annotations

from pathlib import Path

# doc_id -> raw 텍스트 파일명 (docs/sources/SOURCES.md 레지스트리)
SOURCE_FILES = {
    "FSC_PRESS_20260630": "fsc_press_20260630.txt",
    "MOLIT_PRESS_20260630": "molit_press_20260630.txt",
    "FAQ_20260630": "faq_20260630.txt",
}


def load_sources(raw_dir: str | Path | None = None) -> dict[str, str]:
    """docs/sources/raw/에서 원문 텍스트를 로드한다."""
    if raw_dir is None:
        raw_dir = Path(__file__).resolve().parents[3] / "docs" / "sources" / "raw"
    raw_dir = Path(raw_dir)
    out: dict[str, str] = {}
    for doc_id, fname in SOURCE_FILES.items():
        p = raw_dir / fname
        if p.exists():
            out[doc_id] = p.read_text(encoding="utf-8")
    return out
