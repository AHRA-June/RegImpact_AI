"""Rule Change Proposal — 추출 → 구조화 변경안 → 엔진 교차검증.

거버넌스(LOCKED §4·브리프 §9): LLM은 룰엔진을 직접 고치지 않는다. 인용 근거가 붙은
사실만 추출하고, 이 모듈이 결정적으로 변경안(DRAFT)을 조립하며, 사람 승인 후에야
registry에 반영된다. 여기 테스트는 그 조립이 원문보다 커지지도(값 창작) 작아지지도
(조용한 누락) 않는지를 고정한다.
"""
from datetime import date

import pytest

from regimpact.extractor.schema import Citation, RegChangeExtraction, RegChangeItem
from regimpact.grandfathering import CUTOFF
from regimpact.impact.builder import derive_rule_diff
from regimpact.proposal import (
    ProposalStatus,
    RuleChangeProposal,
    apply_consistency_status,
    build_proposal_from_extraction,
    check_proposal_consistency,
    newly_designated_regions,
    parse_ltv,
)
from regimpact.proposal.builder import parse_kr_date
from regimpact.regions import REG_EFFECTIVE
from regimpact.rule_engine import LTV_BASELINE, LTV_REGULATED_STANDARD


def _item(category, summary, before=None, after=None, quote="원문 인용"):
    return RegChangeItem(
        category=category, summary=summary, before=before, after=after,
        citation=Citation(source_doc_id="FSC_PRESS_20260630", quote=quote),
    )


def _extraction(*items):
    return RegChangeExtraction(
        policy_id="FSC_20260630",
        effective_from="2026-07-01",
        target_regions=["GURI", "YONGIN_GIHEUNG", "HWASEONG_DONGTAN"],
        changes=list(items),
    )


# ---------- parse_ltv: 없는 값을 만들지 않는다 ----------
@pytest.mark.parametrize("text,expected", [
    ("70%", 0.70), ("40 %", 0.40), ("0.70", 0.70), (".7", 0.70),
])
def test_parse_ltv_accepts_ratio_forms(text, expected):
    assert parse_ltv(text) == expected


@pytest.mark.parametrize("text", [
    "6억원 제한",              # 한도 → LTV 0.06 이 되면 안 된다
    "최대 만기 30년 이내",      # 만기 → LTV 0.30 이 되면 안 된다
    "6개월 이내 전입의무 부과",  # 전입의무
    "종전 규정 적용",
])
def test_parse_ltv_rejects_bare_numbers(text):
    """맨숫자를 100으로 나누던 fallback이 없는 LTV를 만들어냈다."""
    assert parse_ltv(text) is None


# ---------- 날짜 ----------
@pytest.mark.parametrize("text,expected", [
    ("2026-06-30", "2026-06-30"),
    ("2026년 6월 30일", "2026-06-30"),
    ("2026.6.30", "2026-06-30"),
    ("효력발생일 전일(6.30일)까지", "2026-06-30"),   # 연도 생략 → year_hint 로 복원
])
def test_parse_kr_date(text, expected):
    assert parse_kr_date(text, year_hint=2026) == expected


def test_parse_kr_date_without_hint_does_not_guess_year():
    assert parse_kr_date("6.30일까지") is None


# ---------- 세그먼트: 스칼라 하나로 누르지 않는다 ----------
def test_ltv_is_kept_per_segment_not_last_wins():
    """이전 판은 항목을 돌며 max_ltv 를 덮어써서 마지막 항목이 이겼다.

    6·30 추출에서는 마지막 LTV 항목이 보금자리론(60%)이라 규제지역 표준이 0.6이 됐다.
    """
    p = build_proposal_from_extraction(_extraction(
        _item("LTV", "규제지역 무주택 주담대 LTV 강화", "70%", "40%"),
        _item("LTV", "생애최초 LTV", "70%", "70%"),
        _item("LTV", "서민·실수요자 LTV", "70%", "60%"),
        _item("LTV", "보금자리론 LTV 강화", "70%", "60%"),   # 마지막 항목
    ))
    assert p.after.max_ltv == 0.40, "표준 세그먼트가 마지막 항목에 덮어씌워지면 안 된다"
    assert p.after.ltv_by_segment["FIRST_HOME_BUYER"] == 0.70
    assert p.after.ltv_by_segment["REAL_DEMAND"] == 0.60
    assert p.after.ltv_by_segment["POLICY_MORTGAGE"] == 0.60


def test_conflicting_values_in_one_segment_are_recorded_not_hidden():
    p = build_proposal_from_extraction(_extraction(
        _item("LTV", "규제지역 주담대 LTV", "70%", "40%"),
        _item("LTV", "규제지역 주담대 LTV", "70%", "40%"),
        _item("LTV", "규제지역 주담대 LTV", "60%", "50%"),   # 다른 범위의 표
    ))
    assert p.after.max_ltv == 0.40, "최빈값 채택"
    assert p.conflicts, "충돌은 조용히 사라지면 안 된다"
    assert any("0.5" in c for c in p.conflicts)


def test_tied_conflict_refuses_to_pick():
    """동률이면 고르지 않는다 — 임의 선택은 값 창작이다."""
    p = build_proposal_from_extraction(_extraction(
        _item("LTV", "규제지역 주담대 LTV", "70%", "40%"),
        _item("LTV", "규제지역 주담대 LTV", "70%", "50%"),
    ))
    assert p.after.max_ltv is None
    assert p.conflicts


def test_non_ratio_ltv_items_are_surfaced_not_dropped():
    """LTV로 분류됐지만 비율이 아닌 항목은 버리지 않고 사람에게 넘긴다."""
    p = build_proposal_from_extraction(_extraction(
        _item("LTV", "규제지역 주담대 LTV 강화", "70%", "40%"),
        _item("LTV", "주택구입목적 주담대 최대한도 제한", None, "6억원 제한"),
        _item("LTV", "주택구입목적 주담대 최대 만기 제한", None, "최대 만기 30년 이내"),
    ))
    assert len(p.unmapped) == 2
    assert p.after.max_ltv == 0.40


# ---------- 경과규정 ----------
def test_grandfathering_cutoff_from_relative_wording():
    """원문이 '효력발생일 전일'이라고만 하면 시행일에서 계산한다(관계의 복원)."""
    p = build_proposal_from_extraction(_extraction(
        _item("LTV", "규제지역 LTV", "70%", "40%"),
        _item("GRANDFATHERING", "효력발생일 전일까지 접수 완료시 종전규정 적용",
              None, "종전 규정 적용"),
    ))
    assert p.grandfathering.cutoff_date == CUTOFF.isoformat()
    assert "APPLICATION_ACCEPTED" in p.grandfathering.conditions


# ---------- 신규지정 델타 ----------
def test_newly_designated_is_delta_not_snapshot():
    """정책 하나가 지정한 지역(3곳)이지, 그 시점 규제지역 전체(40곳)가 아니다."""
    new = newly_designated_regions(REG_EFFECTIVE)
    assert new == {"GURI", "YONGIN_GIHEUNG", "HWASEONG_DONGTAN"}
    assert "SEOUL_GANGNAM" not in new, "강남은 2017년부터 규제지역 — 6·30이 지정한 게 아니다"


def test_newly_designated_finds_2025_designation_too():
    new = newly_designated_regions(date(2025, 10, 16))
    assert "SEOUL_DOBONG" in new
    assert "GURI" not in new


# ---------- 엔진 교차검증 ----------
def _clean_extraction():
    return _extraction(
        _item("REGION", "구리·용인기흥·화성동탄 투기과열지구 지정"),
        _item("LTV", "규제지역 무주택 주담대 LTV 강화", "70%", "40%"),
        _item("EXCEPTION", "생애최초 구입자 LTV 70% 좌동"),
        _item("EXCEPTION", "서민·실수요자 LTV 60%"),
        _item("GRANDFATHERING", "효력발생일 전일까지 접수 또는 계약금 납부시 종전규정",
              None, "종전 규정 적용"),
    )


def test_consistent_proposal_passes_and_stays_draft():
    p = build_proposal_from_extraction(_clean_extraction())
    rep = check_proposal_consistency(p, rule_diff=derive_rule_diff())
    assert rep.all_passed, [c.name for c in rep.failed]
    assert apply_consistency_status(p, rep).status == ProposalStatus.DRAFT


# --- mutation: 변경안의 각 필드를 손상시키면 반드시 잡혀야 한다 ---
def _mutate_ltv(p):
    p.after.max_ltv = 0.35
    p.after.ltv_by_segment["STANDARD"] = 0.35


def _mutate_baseline(p):
    p.before.max_ltv = 0.65


def _mutate_effective(p):
    p.after.effective_from = "2026-08-01"


def _mutate_cutoff(p):
    p.grandfathering.cutoff_date = "2026-07-15"


def _mutate_regions(p):
    p.after.target_regions = ["GURI"]              # 2곳 누락


def _mutate_regions_overreach(p):
    p.after.target_regions = [*p.after.target_regions, "SEOUL_GANGNAM"]   # 기존 규제지역 혼입


def _mutate_exceptions(p):
    p.exceptions = ["FIRST_HOME_BUYER"]            # 서민·실수요 누락


@pytest.mark.parametrize("mutate", [
    _mutate_ltv, _mutate_baseline, _mutate_effective, _mutate_cutoff,
    _mutate_regions, _mutate_regions_overreach, _mutate_exceptions,
], ids=lambda f: f.__name__)
def test_mutation_of_any_field_is_caught(mutate):
    """어느 필드를 손상시켜도 consistency가 잡고 자동 승인 경로에서 빠져야 한다."""
    p = build_proposal_from_extraction(_clean_extraction())
    assert check_proposal_consistency(p, rule_diff=derive_rule_diff()).all_passed, "기준선 확인"
    mutate(p)
    rep = check_proposal_consistency(p, rule_diff=derive_rule_diff())
    assert not rep.all_passed, "손상이 통과하면 검증이 무의미하다"
    assert apply_consistency_status(p, rep).status == ProposalStatus.NEEDS_REVIEW


def test_consistency_compares_against_engine_not_proposal():
    """기준은 엔진 상수다. 변경안이 기준이 되면 검증이 무의미해진다."""
    p = build_proposal_from_extraction(_clean_extraction())
    rep = check_proposal_consistency(p)
    baseline = next(c for c in rep.checks if "기준선" in c.name)
    assert baseline.expected == LTV_BASELINE
    std = next(c for c in rep.checks if "규제표준" in c.name)
    assert std.expected == LTV_REGULATED_STANDARD


def test_every_proposal_field_carries_a_citation():
    """변경안의 각 필드는 원문 인용으로 추적 가능해야 한다(Assurance ①)."""
    p = build_proposal_from_extraction(_clean_extraction())
    fields = {s.field_name for s in p.sources}
    assert any(f.startswith("ltv_by_segment") for f in fields)
    assert "after.target_regions" in fields
    assert "grandfathering" in fields
    assert all(s.evidence_span for s in p.sources)


def test_proposal_is_always_draft_on_creation():
    """LLM 산출은 절대 APPROVED로 태어나지 않는다."""
    p = build_proposal_from_extraction(_clean_extraction())
    assert p.status == ProposalStatus.DRAFT


def test_to_dict_roundtrips_conflicts_and_unmapped():
    p = build_proposal_from_extraction(_extraction(
        _item("LTV", "규제지역 LTV", "70%", "40%"),
        _item("LTV", "규제지역 LTV", "70%", "40%"),
        _item("LTV", "규제지역 LTV", "60%", "50%"),
        _item("LTV", "최대한도 제한", None, "6억원"),
    ))
    d = p.to_dict()
    assert d["conflicts"] and d["unmapped"]
    assert d["after"]["ltv_by_segment"]["STANDARD"] == 0.40
