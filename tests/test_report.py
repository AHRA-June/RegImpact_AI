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


def test_assurance_only_regression_measured():
    r = build_validation_report()
    measured = [d for d in r.assurance_dimensions if d.measured]
    pending = [d for d in r.assurance_dimensions if not d.measured]
    # ④ Rule-regression만 실측, ①②③은 실측 대기(지어내지 않음)
    assert len(measured) == 1 and measured[0].key == "regression"
    assert {d.key for d in pending} == {"citation", "completeness", "recall"}
    for d in pending:
        assert d.value is None


def test_overall_status_review_required_due_to_escalation():
    r = build_validation_report()
    assert r.escalations  # OWNER_BASELINE_UNKNOWN
    assert r.overall_status == "REVIEW_REQUIRED"


def test_format_report_text_contains_all_sections():
    out = format_report(build_validation_report())
    for token in ["Source Snapshot", "Policy Version", "Impact Matrix",
                  "Rule Change Proposal", "Rule Regression", "Assurance",
                  "Human Review", "OWNER_BASELINE_UNKNOWN", "미측정"]:
        assert token in out
    # 정직성: 미측정을 지어낸 수치로 채우지 않음(가짜 98% 없음)
    assert "98%" not in out
