"""공문 원문 로더 + Source Snapshot 메타데이터 — docs/sources/SOURCES.md 레지스트리."""
from __future__ import annotations

from pathlib import Path

# doc_id -> raw 텍스트 파일명 (docs/sources/SOURCES.md 레지스트리)
SOURCE_FILES = {
    "FSC_PRESS_20260630": "fsc_press_20260630.txt",
    "MOLIT_PRESS_20260630": "molit_press_20260630.txt",
    "FAQ_20260630": "faq_20260630.txt",
}

# Source Snapshot 메타데이터 (docs/sources/SOURCES.md — 사람 확정, 공개 보도자료/FAQ만).
# 원문 무결성(hash)과 함께 리포트·규제분석 화면의 근거 추적에 쓴다. LOCKED §8.
SOURCE_REGISTRY: list[dict[str, str]] = [
    {"doc_id": "FSC_PRESS_20260630", "org": "금융위원회", "published": "2026-06-30",
     "title": "규제지역 추가 지정 관련 긴급 가계부채 점검회의 (보도참고자료)", "hash": "403fb8fb…e8f39d23"},
    {"doc_id": "MOLIT_PRESS_20260630", "org": "국토교통부", "published": "2026-06-30",
     "title": "투기과열지구 및 조정대상지역 추가 지정 (보도참고자료)", "hash": "6115271b…66c11edd"},
    {"doc_id": "FAQ_20260630", "org": "관계기관 합동", "published": "2026-06-30",
     "title": "규제지역 추가 지정 관련 FAQ", "hash": "ef3dad7b…14ea7c9a"},
]


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
