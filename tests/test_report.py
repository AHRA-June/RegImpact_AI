"""HTML 리포트 생성기 테스트.

핵심: 리포트 값이 **엔진 실제 출력에서만** 오는지(하드코딩·환각 불가) + well-formed.
Stitch 목업이 지역을 세종·부산으로 환각한 문제(docs/ui/stitch_review.md)의 회귀 방지.
"""
import json
from datetime import date
from pathlib import Path

from regimpact.extractor import (
    RegChangeExtraction,
    check_citation_grounding,
    load_sources,
    score_against_gold,
)
from regimpact.impact import impact_from_extraction
from regimpact.report import render_report

REPO = Path(__file__).resolve().parents[1]
SAVED = json.loads((REPO / "docs" / "eval" / "extractor_run_6_30_gemini.json").read_text(encoding="utf-8"))
GOLD = json.loads((REPO / "docs" / "eval" / "regchange_gold_6_30.json").read_text(encoding="utf-8"))


def _render():
    ext = RegChangeExtraction.from_dict(SAVED)
    srcs = load_sources()
    pi = impact_from_extraction(ext)
    g = check_citation_grounding(ext, srcs)
    gold = score_against_gold(ext, GOLD)
    return render_report(pi, extraction=ext, grounding=g, gold=gold, generated_on=date(2026, 8, 12))


def test_report_is_wellformed_html():
    html = _render()
    assert html.startswith("<!doctype html>")
    assert html.rstrip().endswith("</html>")
    assert html.count("<body>") == 1 and html.count("</body>") == 1
    assert "<title>" in html


def test_report_contains_real_engine_values():
    html = _render()
    for token in ["FSC_20260630", "2026-07-01", "70%", "40%", "60%",
                  "구리시", "용인시 기흥구", "화성시 동탄",
                  "생애최초", "서민·실수요", "경과규정", "Impact Matrix"]:
        assert token in html, f"리포트에 실제값 누락: {token}"


def test_report_shows_real_assurance_metrics():
    html = _render()
    assert "Citation" in html
    assert "100%" in html          # citation/completeness/exception 모두 100%
    assert "환각" in html


def test_report_has_no_hallucinated_domain_data():
    """Stitch가 환각했던 지역·수치가 데이터 주도 리포트엔 나타나지 않는다."""
    html = _render()
    for bad in ["세종", "부산", "해운대", "강남", "분당", "서초"]:
        assert bad not in html, f"환각 지역명 발견: {bad}"
    # 표준 LTV 변경은 70→40 이어야 하며 60→50 같은 환각값이 없어야 함
    assert "50%" not in html


def test_report_reflects_all_regions_and_rows():
    html = _render()
    # 3개 규제지역 그룹 헤더 code가 모두 노출
    for code in ["GURI", "YONGIN_GIHEUNG", "HWASEONG_DONGTAN"]:
        assert code in html
    # 24행(3지역×8) — 세그먼트 라벨 반복 확인(무주택 일반이 3번)
    assert html.count("무주택 일반") >= 3


def test_render_works_without_optional_sections():
    """추출/Assurance 없이 PolicyImpact만으로도 렌더(임팩트 표 단독)."""
    ext = RegChangeExtraction.from_dict(SAVED)
    pi = impact_from_extraction(ext)
    html = render_report(pi)
    assert html.startswith("<!doctype html>")
    assert "Impact Matrix" in html
    assert "무엇이 달라졌나" not in html   # 추출 미제공 → 섹션 생략
