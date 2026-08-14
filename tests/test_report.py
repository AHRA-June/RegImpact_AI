"""Validation Report 테스트 — E2E 파이프라인 관통·집계·정직성 검증."""
from regimpact.report import build_validation_report, format_report


def test_report_has_all_pipeline_steps():
    r = build_validation_report()
    names = [s.name for s in r.steps]
    # 브리프 §18 코어 완성의 정의 8단계
    assert names == [
        "Source Snapshot",
        "Policy Version / Temporal",
        "RegChange (Before/After)",
        "Impact Matrix",
        "Rule Change Proposal",
        "Test Cases / Rule Regression",
        "Assurance",
        "Human Review",
    ]


def test_report_aggregates_real_pipeline_outputs():
    r = build_validation_report()
    # Source Snapshot: 공식 원문 3건
    assert len(r.sources) == 3
    # RegChange gold
    assert r.regchange_gold["policy_id"] == "FSC_20260630"
    # Impact Matrix
    assert r.impact_matrix.summary["TOTAL"] == 9
    # Rule Change Proposal
    assert r.proposal.rule_id == "MORTGAGE_LTV_REGULATED_REGION"
    # Regression 실측 100%
    assert r.regression["pass_rate"] == 1.0
    assert r.regression["passed"] == r.regression["total"] == 30


def test_assurance_all_measured_with_recorded_extraction():
    # 기록된 추출 산출물(docs/eval/regchange_extraction_6_30.json)이 있으므로 4 dimension 전부 실측
    r = build_validation_report()
    measured = {d.key for d in r.assurance_dimensions if d.measured}
    assert measured == {"citation", "completeness", "recall", "regression"}
    for d in r.assurance_dimensions:
        assert d.value is not None


def test_assurance_falls_back_to_pending_without_extraction(monkeypatch):
    # 추출 산출물이 없으면 RegChange 계열은 '실측 대기'로 폴백(지어내지 않음)
    import regimpact.report as report_mod

    monkeypatch.setattr(report_mod, "measured_assurance", lambda: None)
    r = report_mod.build_validation_report()
    pending = {d.key for d in r.assurance_dimensions if not d.measured}
    assert pending == {"citation", "completeness", "recall"}
    # ④ Rule-regression은 추출과 무관하게 항상 실측
    reg = [d for d in r.assurance_dimensions if d.key == "regression"][0]
    assert reg.measured


def test_overall_status_review_required_due_to_escalation():
    r = build_validation_report()
    assert r.escalations  # OWNER_BASELINE_UNKNOWN
    assert r.overall_status == "REVIEW_REQUIRED"


def test_format_report_text_contains_all_sections():
    out = format_report(build_validation_report())
    for token in ["Source Snapshot", "Policy Version", "Impact Matrix",
                  "Rule Change Proposal", "Rule Regression", "Assurance",
                  "Human Review", "OWNER_BASELINE_UNKNOWN"]:
        assert token in out
    # RegChange 실측이 채워졌으므로 Citation/Change/Exception 값이 표기됨
    assert "Citation" in out and "Change Completeness" in out
