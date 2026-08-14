"""Rule Change Proposal 테스트 — 구조화 제안이 엔진에서 정확히 유도되는지 검증."""
from datetime import date

from regimpact.proposal import (
    ApprovalStatus,
    build_rule_change_proposal,
    render_rule_dsl,
)


def test_proposal_core_fields():
    p = build_rule_change_proposal()
    assert p.rule_id == "MORTGAGE_LTV_REGULATED_REGION"
    assert p.effective_date == date(2026, 7, 1)
    assert p.grandfathering_cutoff == date(2026, 6, 30)
    assert p.target_regions == ["GURI", "YONGIN_GIHEUNG", "HWASEONG_DONGTAN"]
    assert p.approval_status == ApprovalStatus.REVIEW_REQUIRED


def test_parameter_changes_from_engine_constants():
    p = build_rule_change_proposal()
    by_tier = {pc.tier: pc for pc in p.parameter_changes}
    # 무주택 표준 70→40 (변경)
    assert by_tier["무주택 표준"].before == 0.70 and by_tier["무주택 표준"].after == 0.40
    assert by_tier["무주택 표준"].changed
    # 생애최초 70→70 (유지)
    assert by_tier["생애최초"].after == 0.70 and not by_tier["생애최초"].changed
    # 서민실수요 70→60
    assert by_tier["서민·실수요"].after == 0.60
    # 유주택/다주택: before 명세부재(None) → 0
    assert by_tier["유주택(비처분 1주택)"].before is None
    assert by_tier["유주택(비처분 1주택)"].after == 0.0
    assert by_tier["유주택(비처분 1주택)"].before_label == "명세부재"
    assert by_tier["다주택"].before is None and by_tier["다주택"].after == 0.0


def test_impacted_count_and_sources():
    p = build_rule_change_proposal()
    # 하향(무주택·서민실수요·처분조건부) + 신규제한(유주택·다주택) = 5
    assert p.impacted_segment_count == 5
    assert "FSC_20260630" in p.source_policy_ids


def test_escalation_owner_baseline_unknown():
    p = build_rule_change_proposal()
    codes = {e.reason_code for e in p.escalations}
    assert "OWNER_BASELINE_UNKNOWN" in codes


def test_render_dsl_correct_grandfathering_direction():
    p = build_rule_change_proposal()
    before, after = render_rule_dsl(p)
    after_txt = "\n".join(after)
    # 경과규정 컷오프 방향이 <= (목업의 반대 >= 아님)
    assert 'application_date <= "2026-06-30"' in after_txt
    assert ">=" not in after_txt
    # rule_id + 대상지역이 코드에 반영
    assert p.rule_id in after_txt
    assert '"GURI"' in after_txt
    # before 는 비규제 기준선 0.70
    assert "0.70" in "\n".join(before)
