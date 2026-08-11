"""E2E Report node 테스트 — 6·30 1건이 전 노드를 관통하는지(Walking Skeleton) 검증.

오프라인(API 키 불필요): 추출은 stub. 각 노드가 실제 산출물을 냈는지 + 정합성 확인.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from regimpact.extractor import load_sources
from regimpact.report import build_proposal, render_markdown, run_e2e
from regimpact.report.pipeline import default_6_30_portfolio, offline_stub_extraction
from regimpact.rule_engine import (
    LTV_MULTI,
    LTV_OWNER,
    LTV_REGULATED_STANDARD,
)

REPO = Path(__file__).resolve().parents[1]
GOLD = json.loads(
    (REPO / "docs" / "eval" / "regchange_gold_6_30.json").read_text(encoding="utf-8")
)


def test_e2e_passes_through_all_nodes():
    rep = run_e2e(gold=GOLD)
    assert rep.e2e_ok is True
    # 각 노드 산출물 존재
    assert len(rep.snapshots) == 3
    assert len(rep.transitions) == 3
    assert len(rep.extraction.changes) == 5
    assert rep.matrix.n == 10
    assert len(rep.proposal.ltv_lines) == 5
    assert rep.regression.total == 30
    assert rep.grounding.total == 5


def test_offline_run_marks_not_live_llm():
    rep = run_e2e(gold=GOLD)
    assert rep.used_live_llm is False


def test_injected_complete_marks_live_llm():
    """complete를 주입하면 live LLM 경로로 표시되고 그 출력이 쓰인다."""
    called = {"n": 0}

    def fake_complete(system, user):
        called["n"] += 1
        # stub과 동일 구조지만 별도 함수 → 주입 경로 검증
        return offline_stub_extraction(load_sources())

    rep = run_e2e(complete=fake_complete, gold=GOLD)
    assert rep.used_live_llm is True
    assert called["n"] == 1


def test_policy_version_all_newly_regulated():
    rep = run_e2e()
    assert all(t.newly_regulated for t in rep.transitions)
    assert {t.region_code for t in rep.transitions} == {
        "GURI", "YONGIN_GIHEUNG", "HWASEONG_DONGTAN"
    }


def test_regression_100_percent():
    rep = run_e2e()
    assert rep.regression.pass_rate == 1.0
    assert rep.regression.failures == []


def test_assurance_offline_grounding_perfect():
    """stub 인용은 실제 원문 substring → grounding 100%, 환각 0."""
    rep = run_e2e(gold=GOLD)
    assert rep.grounding.citation_correctness == 1.0
    assert rep.grounding.unsupported_claim_rate == 0.0
    assert rep.gold.change_completeness == 1.0
    assert rep.gold.exception_recall == 1.0


def test_proposal_values_come_from_engine_constants():
    """규칙 변경안 LTV는 rule_engine 상수(확정 명세)와 일치해야 한다(LOCKED §4)."""
    ext = run_e2e().extraction
    proposal = build_proposal(ext)
    by_rule = {ln.rule_id: ln for ln in proposal.ltv_lines}
    assert by_rule["REG_STD"].after_ltv == LTV_REGULATED_STANDARD
    assert by_rule["REG_OWNER_0"].after_ltv == LTV_OWNER
    assert by_rule["MULTI_0"].after_ltv == LTV_MULTI
    assert proposal.approval_status == "PENDING_HUMAN_APPROVAL"
    assert proposal.effective_from == "2026-07-01"


def test_human_review_gate_surfaces_discovery_and_high_impact():
    rep = run_e2e()
    refs = {it.ref for it in rep.review_items}
    # 정책대출(C10) → DISCOVERY 로 검토 게이트에 올라옴
    assert "C10" in refs
    reasons = {it.ref: it.reason for it in rep.review_items}
    assert "DISCOVERY" in reasons["C10"]
    # 고임팩트 건(유주택/다주택/무주택 30%p)도 게이트에 존재
    assert any("고임팩트" in it.reason for it in rep.review_items)


def test_portfolio_is_stratified():
    apps = default_6_30_portfolio()
    assert len(apps) == 10
    # 커스터머 id 유일
    ids = [a.customer_id for a in apps]
    assert len(set(ids)) == len(ids)


def test_render_markdown_contains_all_sections():
    md = render_markdown(run_e2e(gold=GOLD))
    for section in (
        "Validation Report",
        "Source Snapshot",
        "Policy Version Resolution",
        "Before/After",
        "Impact Matrix",
        "Rule Change Proposal",
        "Rule Regression",
        "Assurance",
        "Human Review",
        "한계",
    ):
        assert section in md, f"missing section: {section}"
    assert "관통 성공" in md


def test_render_markdown_without_gold():
    """gold 없이도 렌더링이 깨지지 않는다(Assurance는 grounding만)."""
    md = render_markdown(run_e2e())
    assert "Citation Correctness" in md
    assert "Change Completeness" not in md   # gold 없으면 생략
