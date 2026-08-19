"""고객용 내러티브 — 시스템 용어가 고객 화면으로 새지 않는지 고정한다.

번역이 빠진 코드는 영문 상수 그대로 노출된다. 그건 버그가 아니라 사고다.
"""
import pytest

from regimpact.impact import analyze_portfolio, build_portfolio
from regimpact.impact.customer import Segment
from regimpact.impact.narrative import (
    ACTION_KO,
    DRAFT_NOTICE,
    HEADLINE_KO,
    REASON_KO,
    explain,
)
from regimpact.models import EvaluationStatus, ReasonCode


@pytest.fixture(scope="module")
def impacts():
    return analyze_portfolio(build_portfolio(size=600, seed=20260630)).impacts


# ---------- 번역 누락이 없는가 ----------
@pytest.mark.parametrize("code", list(ReasonCode), ids=lambda c: c.value)
def test_every_reason_code_has_a_translation(code):
    assert code in REASON_KO, f"{code.value} 번역이 없다 — 고객 화면에 영문 상수가 노출된다"


@pytest.mark.parametrize("seg", list(Segment), ids=lambda s: s.name)
def test_every_segment_has_headline_and_action(seg):
    assert seg in HEADLINE_KO
    assert seg in ACTION_KO


def test_no_system_term_leaks_into_customer_text(impacts):
    """reason_code·status 문자열이 고객 문장에 그대로 나오면 안 된다."""
    leaked = []
    for imp in impacts[:200]:
        text = explain(imp)
        for token in [c.value for c in ReasonCode] + [s.value for s in EvaluationStatus]:
            if token in text:
                leaked.append((imp.customer_id, token))
    assert not leaked, f"시스템 용어 노출: {leaked[:5]}"


# ---------- 정직성 ----------
def test_human_review_says_it_is_a_draft(impacts):
    """사람 검토 대상이면 '자동 초안'임을 반드시 말한다 — 과대약속 금지."""
    reviewed = [i for i in impacts
                if i.after.status is EvaluationStatus.NEEDS_HUMAN_REVIEW]
    assert reviewed, "사람 검토 케이스가 없다 — 테스트가 무력화됐는지 확인"
    for imp in reviewed[:50]:
        assert DRAFT_NOTICE in explain(imp)


def test_missing_baseline_is_stated_not_shown_as_zero(impacts):
    """시행 전 기준값이 없는 것을 '0원에서 시작'처럼 보여주면 안 된다."""
    unknown = [i for i in impacts if i.segment is Segment.IMPACT_UNKNOWN]
    assert unknown
    text = explain(unknown[0])
    assert "시행 전 기준값은 원문에 없습니다" in text
    assert "0원 →" not in text


def test_zero_ltv_unaffected_does_not_read_as_fine(impacts):
    """0%→0% 인 고객에게 '달라지지 않습니다'만 말하면 빌릴 수 있다는 오해를 준다."""
    zeros = [i for i in impacts
             if i.segment is Segment.UNAFFECTED and i.after.max_ltv == 0]
    assert zeros, "0%→0% 케이스가 없다 — 포트폴리오 구성 확인"
    text = explain(zeros[0])
    assert "대출이 어렵습니다" in text
    assert "별도 조치는 필요하지 않습니다" not in text


def test_reduced_shows_both_ltv_and_amount(impacts):
    reduced = [i for i in impacts if i.segment is Segment.REDUCED]
    text = explain(reduced[0])
    assert "최대 LTV:" in text and "→" in text
    assert "대출 한도:" in text and "원" in text


def test_explain_never_raises(impacts):
    for imp in impacts:
        assert explain(imp)
