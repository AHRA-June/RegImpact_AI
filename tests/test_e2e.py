"""E2E 완결 테스트 — Assurance 집계 + Validation Report + 파이프라인 관통.

정상 경로(전 dimension PASS, gate PASS, decision DRAFT)와 실패 탐지 경로
(환각 인용/골드 누락 → gate REVIEW_REQUIRED, decision NEEDS_REVIEW)를 함께 검증한다.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from regimpact.assurance import AssuranceGate  # noqa: E402
from regimpact.e2e import run_six_thirty_e2e  # noqa: E402
from regimpact.proposal import six_thirty_extraction  # noqa: E402
from regimpact.proposal.schema import ProposalStatus  # noqa: E402
from regimpact.report import ReportMeta  # noqa: E402


@pytest.fixture(scope="module")
def result():
    return run_six_thirty_e2e(meta=ReportMeta(generated_at="2026-08-11T00:00:00Z",
                                              event_id="test-0001"))


# ── 정상 경로 ──
def test_gate_pass(result):
    assert result.assurance.gate == AssuranceGate.PASS


def test_all_four_dimensions_pass(result):
    dims = result.assurance.dimensions
    assert len(dims) == 4
    assert {d.dim_id for d in dims} == {"D1", "D2", "D3", "D4"}
    assert all(d.passed for d in dims)


def test_decision_draft(result):
    # gate PASS면 proposal status(DRAFT) 유지 — 자동 승인 아님
    assert result.report.decision_status == ProposalStatus.DRAFT.value


def test_key_metrics(result):
    d1 = result.assurance.dimension("D1")
    assert d1.metrics["citation_correctness"] == 1.0
    d4 = result.assurance.dimension("D4")
    assert d4.metrics["regression_pass_rate"] == 1.0
    assert d4.metrics["coverage_covered"] is True


def test_notes_surface_baseline_gap(result):
    # 유주택 기준부재는 게이트를 막지 않는 note로 노출
    assert any("기준부재" in n for n in result.assurance.notes)
    assert result.assurance.gate == AssuranceGate.PASS  # note는 gate 무관


# ── Validation Report ──
def test_report_markdown_sections(result):
    md = result.report.render_markdown()
    for heading in (
        "# 검증보고서", "## 1. 규제 변경 요약", "## 2. Impact Matrix",
        "## 3. Rule Change Proposal", "## 4. 테스트 커버리지",
        "## 5. Assurance Evaluation", "## 6. Human Review", "## 7. Audit Trail",
    ):
        assert heading in md
    assert "PASS" in md


def test_report_to_dict_contract(result):
    d = result.report.to_dict()
    for key in ("policy_id", "decision_status", "assurance", "impact_summary",
                "proposal", "coverage", "regression", "fidelity", "grounding", "audit"):
        assert key in d
    assert d["policy_id"] == "FSC_20260630"
    # audit trail 재현 필드(브리프 §17)
    audit = d["audit"]
    for key in ("event_id", "timestamp", "policy_id", "source_hashes",
                "system_version", "model_name", "decision_status"):
        assert key in audit
    assert len(audit["source_hashes"]) == 3   # FSC·MOLIT·FAQ


def test_source_hashes_deterministic(result):
    # 동일 원문 → 동일 해시 (재현 가능)
    again = run_six_thirty_e2e()
    assert result.report.source_hashes == again.report.source_hashes


# ── 실패 탐지: 환각 인용 → D1 실패 → gate REVIEW_REQUIRED ──
def test_assurance_catches_ungrounded_citation():
    ext = six_thirty_extraction()
    ext.changes[1].citation.quote = "원문에없는_환각문구_xyz"   # LTV 항목 인용 손상
    res = run_six_thirty_e2e(extraction=ext)
    assert res.assurance.gate == AssuranceGate.REVIEW_REQUIRED
    assert not res.assurance.dimension("D1").passed
    assert res.assurance.dimension("D1").metrics["citation_correctness"] < 1.0
    assert any("근거 없는" in e for e in res.assurance.escalations)
    # 결정상태는 승인 불가로 승격
    assert res.report.decision_status == ProposalStatus.NEEDS_REVIEW.value


# ── 실패 탐지: 골드 변경 누락 → D2 실패 → gate REVIEW_REQUIRED ──
def test_assurance_catches_missing_change():
    ext = six_thirty_extraction()
    # 경과규정 항목 제거 → gold required_changes 'grandfathering' 미포착
    ext.changes = [c for c in ext.changes if c.category != "GRANDFATHERING"]
    res = run_six_thirty_e2e(extraction=ext)
    assert res.assurance.gate == AssuranceGate.REVIEW_REQUIRED
    assert not res.assurance.dimension("D2").passed
    assert res.assurance.dimension("D2").metrics["change_completeness"] < 1.0


# ── 실패 시 보고서에 사유가 노출된다 ──
def test_failure_shows_in_report():
    ext = six_thirty_extraction()
    ext.changes[0].citation.quote = "존재하지않는문구"
    res = run_six_thirty_e2e(extraction=ext)
    md = res.report.render_markdown()
    assert "REVIEW REQUIRED" in md
    assert "검토 필수 사유" in md
