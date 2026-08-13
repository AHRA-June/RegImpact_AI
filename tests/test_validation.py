"""Validation Report(검증보고서 stub) 테스트.

검증: ①노드 산출 조립·present/missing ②관통 판정 ③마크다운 렌더 실데이터 반영
④부분 관통(노드 누락) 시 정직 표기 ⑤사람 검토 필요 건수 노출.
"""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from regimpact.extractor.schema import Citation, RegChangeExtraction, RegChangeItem  # noqa: E402
from regimpact.impact import (  # noqa: E402
    DEFAULT_REGION,
    SIX_THIRTY_SEGMENTS,
    analyze_impact,
)
from regimpact.proposal import ApprovalStatus, build_proposal, record_decision  # noqa: E402
from regimpact.tc_generator import run_regression  # noqa: E402
from regimpact.validation import (  # noqa: E402
    build_report,
    format_report_md,
    render_report_html,
)

BEFORE = date(2026, 6, 30)
AFTER = date(2026, 7, 2)


def _extraction():
    cite = Citation(source_doc_id="FSC_20260630", quote="70%→40%")
    return RegChangeExtraction(
        policy_id="FSC_20260630",
        effective_from="2026-07-01",
        target_regions=["GURI", "YONGIN_GIHEUNG", "HWASEONG_DONGTAN"],
        changes=[RegChangeItem("LTV", "규제지역 표준 LTV 70%→40%", cite,
                               before="70%", after="40%")],
    )


def _matrix():
    return analyze_impact(SIX_THIRTY_SEGMENTS, DEFAULT_REGION, BEFORE, AFTER,
                          policy_id="FSC_20260630")


def _full_report():
    ext = _extraction()
    m = _matrix()
    prop = record_decision(build_proposal(m, ext), ApprovalStatus.APPROVED, reviewer="심사역")
    reg = run_regression()
    return build_report("2026-06-30 규제지역 추가 지정", extraction=ext, matrix=m,
                        proposal=prop, regression=reg)


def test_node_status_all_present():
    r = _full_report()
    s = r.node_status()
    assert s["extraction"] and s["impact_matrix"] and s["rule_proposal"] and s["rule_regression"]
    assert s["assurance"] is False   # 부분(미제공)


def test_pipeline_complete_when_core_nodes_present():
    assert _full_report().is_pipeline_complete is True


def test_pipeline_incomplete_when_proposal_missing():
    """제안 노드가 없으면 부분 관통."""
    r = build_report("t", extraction=_extraction(), matrix=_matrix())
    assert r.is_pipeline_complete is False


def test_meta_derived_from_sources():
    r = _full_report()
    assert r.policy_id == "FSC_20260630"
    assert r.effective_from == "2026-07-01"
    assert "GURI" in r.target_regions


def test_review_required_count():
    assert _full_report().review_required_count == 2


def test_format_md_contains_real_pipeline_output():
    md = format_report_md(_full_report())
    assert "검증보고서" in md
    assert "무주택 일반" in md
    assert "70%" in md and "40%" in md
    assert "REVIEW" in md                     # 매트릭스 방향
    assert "Rule-regression Pass Rate: 30/30" in md
    assert "APPROVED" in md                    # 제안 승인 상태
    assert "한계" in md                        # 정직성 섹션


def test_format_md_flags_pending_when_not_approved():
    ext, m = _extraction(), _matrix()
    prop = build_proposal(m, ext)   # PENDING_REVIEW
    md = format_report_md(build_report("t", extraction=ext, matrix=m, proposal=prop))
    assert "PENDING_REVIEW" in md
    assert "초안" in md


# --- 정식 HTML 보고서 ---------------------------------------------------------
def test_render_html_self_contained_and_bound():
    doc = render_report_html(_full_report())
    assert "<!doctype html>" in doc.lower()
    assert "cdn" not in doc.lower().replace("cdn.jsdelivr", "")  # 외부 스크립트 없음
    # 실데이터 바인딩
    assert "무주택 일반" in doc
    assert "APPROVED" in doc
    assert "Pass Rate" in doc
    assert "FSC_20260630" in doc
    assert "Citation Correctness" in doc or "Assurance" in doc
    assert "한계" in doc                       # 정직성 섹션


def test_render_html_shows_all_pipeline_nodes():
    doc = render_report_html(_full_report())
    for label in ("RegChange Extractor", "Impact Matrix", "Rule Change Proposal",
                  "Rule-Regression"):
        assert label in doc


def test_render_html_partial_pipeline_marks_missing():
    """제안·회귀 없는 부분 관통은 '부분 관통'으로 표기."""
    r = build_report("t", extraction=_extraction(), matrix=_matrix())
    doc = render_report_html(r)
    assert "부분 관통" in doc


def test_render_html_no_hardcoded_hallucinations():
    doc = render_report_html(_full_report())
    for bad in ("세종", "부산", "강남", "50%→50%"):
        assert bad not in doc
