"""공문 원문 로더 — docs/sources/raw/*.txt를 doc_id로 읽는다.

세 층이 있다:
  CORPUS_FILES — doc_id → 파일명 **단일 레지스트리**. 아래 두 층이 여기서 파생된다.
  EVENTS — 규제 이벤트(대책) 단위 묶음. 추출→룰→영향 파이프라인은 **이벤트 하나**를
    받아 돈다. 이벤트가 파이프라인의 입력 단위라는 것을 코드로 못박은 것이다.
  SOURCE_FILES — 기본 이벤트(6·30)의 문서. 기존 실측·골드가 전부 이 셋에 고정돼 있어
    **여기에 문서를 더하면 기존 수치의 의미가 바뀐다.** 그래서 더하지 않고,
    새 이벤트는 EVENTS 에 항목으로 추가한다(테스트가 이 셋을 고정한다).

검색(retrieval)은 이벤트와 무관하게 CORPUS_FILES 전체를 본다 — 고객 질문은 대책
경계를 지키지 않기 때문이다. 대신 시점 필터로 가른다(`CORPUS_EVENTS`).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# doc_id -> raw 텍스트 파일명 (docs/sources/SOURCES.md 레지스트리). 단일 출처.
CORPUS_FILES = {
    "FSC_PRESS_20260630": "fsc_press_20260630.txt",
    "MOLIT_PRESS_20260630": "molit_press_20260630.txt",
    "FAQ_20260630": "faq_20260630.txt",
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


@dataclass(frozen=True)
class RegEvent:
    """규제 이벤트 하나 — 파이프라인의 입력 단위.

    `gold` 가 None 이면 **아직 사람이 확정한 정답이 없다**는 뜻이다. 그런 이벤트는
    인용 대조(원문 verbatim — 골드 불필요)까지만 실측하고, 골드 기반 점수는 내지
    않는다. 정답 없이 점수를 내는 것이 이 프로젝트가 가장 피하는 일이다.
    """

    event_id: str
    label: str
    published_at: str
    doc_ids: tuple[str, ...]
    gold: str | None = None

    @property
    def files(self) -> dict[str, str]:
        return {d: CORPUS_FILES[d] for d in self.doc_ids}


EVENTS: dict[str, RegEvent] = {
    "20260630": RegEvent(
        event_id="20260630",
        label="2026 6·30 대책",
        published_at="2026-06-30",
        doc_ids=("FSC_PRESS_20260630", "MOLIT_PRESS_20260630", "FAQ_20260630"),
        gold="docs/eval/regchange_gold_6_30.json",
    ),
    # 2026-08-21 편입. 원문은 2026-08-19 사용자 제공분이 이미 해시 봉인돼 있었고,
    # 그동안 검색 코퍼스로만 쓰였다. 골드는 아직 없다 — 사람 확정 전이다.
    "20251015": RegEvent(
        event_id="20251015",
        label="2025 10·15 대책",
        published_at="2025-10-15",
        doc_ids=("FSC_PRESS_20251015", "FAQ_20251015"),
        gold=None,
    ),
}
DEFAULT_EVENT = "20260630"

# 기본 이벤트(6·30)의 문서 — 기존 호출부·테스트가 이 이름을 쓴다. EVENTS 에서 파생하므로
# 레지스트리가 두 벌이 되지 않는다.
SOURCE_FILES = EVENTS[DEFAULT_EVENT].files


def get_event(event_id: str | None = None) -> RegEvent:
    """이벤트 조회. 이름을 틀리면 가능한 목록과 함께 즉시 실패한다."""
    key = event_id or DEFAULT_EVENT
    if key not in EVENTS:
        raise KeyError(f"알 수 없는 규제 이벤트: {key!r} (가능: {', '.join(EVENTS)})")
    return EVENTS[key]


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


def load_sources(raw_dir: str | Path | None = None,
                 event: str | None = None) -> dict[str, str]:
    """한 규제 이벤트의 추출 대상 원문. 기본은 6·30(기존 호출부 전부 그대로 동작)."""
    return _load(get_event(event).files, raw_dir)


def load_corpus(raw_dir: str | Path | None = None) -> dict[str, str]:
    """검색 코퍼스 전체 — 과거 정책 원문 포함."""
    return _load(CORPUS_FILES, raw_dir)
