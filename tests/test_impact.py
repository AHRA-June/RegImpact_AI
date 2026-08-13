"""Impact Matrix + Proposal + E2E Pipeline 테스트.

검증 초점:
    - Impact Matrix가 룰엔진 2시점(before/after)으로 올바른 delta·escalation을 낸다.
    - 앵커 추출이 원문에 grounding된다(Citation Correctness 100%).
    - Proposal이 LOCKED §4대로 AI_DRAFT로 태어난다.
    - E2E 파이프라인이 관통(e2e_ok)하며 provenance가 분리된다.
"""
from datetime import date

from regimpact.extractor import check_citation_grounding, load_sources
from regimpact.impact import (
    AFTER_DATE,
    BEFORE_DATE,
    ApprovalStatus,
    Provenance,
    anchor_extraction,
    build_impact_matrix,
    build_proposal,
    format_e2e_report,
    run_e2e,
)
from regimpact.impact.matrix import ImpactRow
from regimpact.models import EvaluationStatus
from regimpact.rule_engine import evaluate


# --- Impact Matrix -----------------------------------------------------------
def test_matrix_headline_ltv_drop_70_to_40():
    """무주택 일반: 시행 전 非규제 70% → 시행 후 규제 40% (-30%p)."""
    rows = build_impact_matrix(regions=["GURI"])
    general = next(r for r in rows if r.persona_id == "P-NOHOME-GENERAL")
    assert general.before_ltv == 0.70
    assert general.after_ltv == 0.40
    assert general.delta_ltv == -0.30
    assert general.high_impact is True
    assert general.escalated is False


def test_matrix_first_home_no_change():
    """생애최초: 70% → 70% (완화 유지, delta 0)."""
    rows = build_impact_matrix(regions=["GURI"])
    fh = next(r for r in rows if r.persona_id == "P-FIRST-HOME")
    assert fh.before_ltv == 0.70
    assert fh.after_ltv == 0.70
    assert fh.delta_ltv == 0.0
    assert fh.high_impact is False


def test_matrix_owner_escalates_before_side():
    """비처분 1주택: 시행 전 非규제 유주택 기준값 부재 → escalation. delta 정의불가(None)."""
    rows = build_impact_matrix(regions=["GURI"])
    owner = next(r for r in rows if r.persona_id == "P-OWNER-1")
    assert owner.before.status == EvaluationStatus.NEEDS_HUMAN_REVIEW
    assert owner.after.status == EvaluationStatus.DECIDED
    assert owner.after_ltv == 0.0
    assert owner.delta_ltv is None       # 한쪽 escalation → 기계 비교 불가
    assert owner.escalated is True
    assert owner.high_impact is True


def test_matrix_covers_all_regions_and_personas():
    rows = build_impact_matrix()
    assert len(rows) == 3 * 6           # 3지역 × 6페르소나
    assert {r.region_code for r in rows} == {"GURI", "YONGIN_GIHEUNG", "HWASEONG_DONGTAN"}


def test_matrix_uses_rule_engine_values_not_hardcoded():
    """Impact Matrix의 값이 실제 룰엔진 출력과 동일해야 한다(LOCKED §4)."""
    rows = build_impact_matrix(regions=["GURI"])
    row = next(r for r in rows if r.persona_id == "P-NOHOME-GENERAL")
    from regimpact.impact.personas import SIX_THIRTY_PERSONAS
    persona = next(p for p in SIX_THIRTY_PERSONAS if p.persona_id == "P-NOHOME-GENERAL")
    assert row.after.max_ltv == evaluate(persona.application("GURI", AFTER_DATE)).max_ltv
    assert row.before.max_ltv == evaluate(persona.application("GURI", BEFORE_DATE)).max_ltv


# --- Anchor 추출 grounding ----------------------------------------------------
def test_anchor_extraction_is_fully_grounded():
    """앵커의 모든 citation이 원문에 verbatim(공백정규화) 존재 → Citation Correctness 100%."""
    extraction = anchor_extraction()
    sources = load_sources()
    grounding = check_citation_grounding(extraction, sources)
    assert grounding.total == len(extraction.changes)
    assert grounding.citation_correctness == 1.0
    assert grounding.ungrounded == []


def test_anchor_matches_gold_targets():
    extraction = anchor_extraction()
    assert extraction.policy_id == "FSC_20260630"
    assert extraction.effective_from == "2026-07-01"
    assert set(extraction.target_regions) == {"GURI", "YONGIN_GIHEUNG", "HWASEONG_DONGTAN"}


# --- Proposal ----------------------------------------------------------------
def test_proposal_born_as_ai_draft():
    """LOCKED §4: 제안은 AI초안으로 태어나고, 사람 확정 전엔 확정이 아니다."""
    extraction = anchor_extraction()
    matrix = build_impact_matrix()
    proposal = build_proposal(extraction, matrix)
    assert proposal.approval_status == ApprovalStatus.AI_DRAFT
    assert proposal.is_confirmed is False
    proposal.confirm("검토완료")
    assert proposal.approval_status == ApprovalStatus.HUMAN_CONFIRMED
    assert proposal.is_confirmed is True


def test_proposal_separates_provenance():
    """서술 변경=LLM 추출, 세그먼트 영향=룰엔진 — provenance가 분리된다."""
    extraction = anchor_extraction()
    matrix = build_impact_matrix()
    proposal = build_proposal(extraction, matrix)
    assert len(proposal.narrative_changes) == len(extraction.changes)
    assert all(c.provenance == Provenance.EXTRACTION_LLM for c in proposal.narrative_changes)
    assert all(c.citations for c in proposal.narrative_changes)   # 추출은 citation 보존
    assert len(proposal.segment_impacts) == len(matrix)
    assert all(c.provenance == Provenance.RULE_ENGINE_DETERMINISTIC for c in proposal.segment_impacts)


# --- E2E Pipeline ------------------------------------------------------------
def test_e2e_pipeline_passes_through():
    """6·30 E2E가 관통(e2e_ok)하고 Assurance 지표가 산출된다."""
    report = run_e2e()
    assert report.e2e_ok is True
    assert report.regression_pass_rate == 1.0
    assert report.citation_correctness == 1.0
    assert report.unsupported_claim_rate == 0.0
    assert report.gold.change_completeness == 1.0
    assert report.gold.exception_recall == 1.0
    assert report.gold.effective_date_correct is True
    assert report.gold.regions_correct is True
    assert len(report.impact_matrix) == 18
    assert len(report.high_impact_rows) >= 1


def test_e2e_report_dict_and_text_render():
    report = run_e2e()
    d = report.to_dict()
    assert d["e2e_ok"] is True
    assert d["assurance"]["regression_pass_rate"] == 1.0
    assert len(d["impact_matrix"]) == 18
    text = format_e2e_report(report)
    assert "E2E 관통 성공" in text
    assert "Impact Matrix" in text


def test_e2e_detects_ungrounded_injection():
    """환각 인용을 주입하면 파이프라인이 관통 실패로 잡는다(회귀 방어)."""
    extraction = anchor_extraction()
    # 원문에 없는 quote로 오염
    extraction.changes[0].citation.quote = "이 문장은 원문에 존재하지 않는 환각 인용이다"
    report = run_e2e(extraction=extraction)
    assert report.unsupported_claim_rate > 0.0
    assert report.e2e_ok is False
