"""내규 영향도 매핑 테스트.

검증 축:
  1. 6·30 매핑 분포(수정필요/검토/간접/무관) 고정 — 회귀.
  2. 과잉 플래그 없음 — 무관 규정(예금·카드)은 UNAFFECTED·드라이버 0.
  3. 키워드 좁힘 — 다주택 규정은 다주택 변경으로만 매핑.
  4. 초안·승인 — 수정안은 초안, 승인 PENDING(자동 확정 없음).
  5. 결정성 — 같은 입력 같은 결과.
  6. 변경 없으면 전부 무관.
"""
import json
from pathlib import Path

from regimpact.extractor import RegChangeExtraction
from regimpact.rule_catalog import (
    DEFAULT_CATALOG,
    Disposition,
    map_catalog_impact,
)

REPO = Path(__file__).resolve().parents[1]
SAVED = json.loads((REPO / "docs" / "eval" / "extractor_run_6_30_gemini.json").read_text(encoding="utf-8"))
EXT = RegChangeExtraction.from_dict(SAVED)


def test_6_30_distribution():
    ci = map_catalog_impact(EXT)
    c = ci.counts()
    assert c["EDIT_REQUIRED"] == 9
    assert c["NEEDS_REVIEW"] == 1
    assert c["INDIRECT"] == 1
    assert c["UNAFFECTED"] == 2
    assert len(ci.items) == len(DEFAULT_CATALOG) == 13


def test_no_over_flag_unrelated_rules():
    ci = map_catalog_impact(EXT)
    by_id = {i.rule.rid: i for i in ci.items}
    for rid in ("R-DEP-12", "R-CARD-13"):
        assert by_id[rid].disposition == Disposition.UNAFFECTED
        assert by_id[rid].drivers == []


def test_keyword_narrowing_multihome():
    ci = map_catalog_impact(EXT)
    by_id = {i.rule.rid: i for i in ci.items}
    multi = by_id["R-LTV-02"]
    assert multi.disposition == Disposition.EDIT_REQUIRED
    # 다주택 규정의 드라이버는 '다주택' 변경만
    assert all("다주택" in d["summary"] for d in multi.drivers)
    # 표준 LTV 규정은 다주택 변경이 아닌 규제지역 강화 변경으로
    std = by_id["R-LTV-01"]
    assert any("규제지역" in d["summary"] for d in std.drivers)


def test_edits_are_draft_and_pending():
    ci = map_catalog_impact(EXT)
    assert ci.approval_status == "PENDING"
    for i in ci.edits():
        assert i.approval_status == "PENDING"
        assert "초안" in i.suggested_edit
        assert i.drivers                      # 근거 변경이 있어야 함


def test_deterministic():
    a = map_catalog_impact(EXT).counts()
    b = map_catalog_impact(EXT).counts()
    assert a == b


def test_no_changes_all_unaffected():
    class _Empty:
        changes: list = []
    ci = map_catalog_impact(_Empty())
    assert all(i.disposition == Disposition.UNAFFECTED for i in ci.items)
    assert ci.counts()["UNAFFECTED"] == len(DEFAULT_CATALOG)
