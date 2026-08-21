"""골드셋 QA 평가 하네스 테스트 — 채점기 자체를 검증한다 (LLM 호출 0회).

첫 실측에서 실패 12건이 전부 채점기의 표현 차이 때문이었다. 채점기가 틀리면 그 위의
모든 튜닝 판단이 틀리므로, 여기서 채점기의 관대함과 엄격함을 **양쪽 다** 고정한다.
"""
import pytest

from regimpact.eval import (
    Category,
    Split,
    fact_matches,
    format_qa_report,
    load_split,
    score_qa,
    validate_qa_response,
)
from regimpact.eval.qa import QAResponse, _canon_dates, build_qa_prompt
from regimpact.eval.schema import Citation, GoldItem

SOURCES = {"D1": "규제\n지역 내 3억원 초과 APT 취득과 규제지역 여부와 무관하게 LTV 0% 적용"}


def _item(**over):
    base = dict(
        id="DEV-X-001", split=Split.DEV, category=Category.NORMAL,
        question="q", gold_answer="a", gold_facts=("0%",),
        citations=(Citation("D1", "LTV 0% 적용"),),
        expect_escalation=False, policy_version="FSC_20260630",
    )
    base.update(over)
    return GoldItem(**base)


def _resp(**over):
    base = dict(item_id="DEV-X-001", answer="LTV 0%가 적용된다",
                citations=(("D1", "LTV 0% 적용"),), needs_human_review=False)
    base.update(over)
    return QAResponse(**base)


# ------------------------------------------------- 표면 정규화 (관대해야 하는 쪽)

@pytest.mark.parametrize("fact,answer", [
    ("25.9.7", "2025년 9월 7일부터 시행된 제도이다"),
    ("20.11.16", "2020년 11월 16일부터"),
    ("2027년 12월 31일", "2027.12.31.까지"),
    ("증액 없는 대환대출", "증액없는 대환대출에는"),
    ("무주택자·처분조건부", "무주택자처분조건부"),
    ("'25.9.7", "’25.9.7 조치"),
])
def test_surface_differences_do_not_count_as_misses(fact, answer):
    """표현 차이로 실패를 만들면, 그것을 고치려는 튜닝은 채점기에 맞추는 훈련이 된다."""
    assert fact_matches(fact, answer)


@pytest.mark.parametrize("raw,canon", [
    ("2025년 9월 7일", "25.9.7"),
    ("’25.9.7", "25.9.7"),
    ("2020.11.16", "20.11.16"),
])
def test_date_canonicalization(raw, canon):
    assert _canon_dates(raw).replace(" ", "") == canon


def test_explicit_alternatives_are_honored():
    assert fact_matches("旣 마련된 규정|이미 마련", "이미 마련되어 있던 규정에 따라")


# ------------------------------------------------- 엄격해야 하는 쪽 (게이밍 방지)

@pytest.mark.parametrize("fact,answer", [
    ("40%", "LTV는 0%이다"),
    ("생애최초", "서민·실수요자에게 적용된다"),
    ("7월 5일|26.7.5", "2026년 7월 1일부터 적용된다"),
    ("규제지역 여부와 무관|규제지역 지정 여부와 무관", "규제지역에서만 적용된다"),
])
def test_different_content_still_counts_as_a_miss(fact, answer):
    """정규화가 내용 차이까지 덮어 버리면 지표가 무의미해진다."""
    assert not fact_matches(fact, answer)


# ------------------------------------------------------------------ 채점 로직

def test_scoring_counts_facts_and_citations():
    rep = score_qa([_item()], {"DEV-X-001": _resp()}, SOURCES)
    assert rep.fact_coverage == 1.0 and rep.exact_rate == 1.0
    assert rep.citation_correctness == 1.0 and rep.unsupported_claim_rate == 0.0


def test_citation_matching_tolerates_pdf_line_breaks():
    """원문이 단어 중간에서 줄바꿈된 경우에도 실제 인용은 grounded 여야 한다."""
    rep = score_qa(
        [_item()],
        {"DEV-X-001": _resp(citations=(("D1", "규제지역 내 3억원 초과 APT 취득"),))},
        SOURCES,
    )
    assert rep.citation_correctness == 1.0


def test_fabricated_citation_is_counted_as_unsupported():
    rep = score_qa(
        [_item()],
        {"DEV-X-001": _resp(citations=(("D1", "규제지역 내 5억원 초과 APT 취득"),))},
        SOURCES,
    )
    assert rep.unsupported_claim_rate == 1.0


def test_escalation_recall_falls_when_the_model_invents_an_answer():
    """원문에 답이 없는데 답해 버리면 escalation recall이 떨어져야 한다 — 가장 위험한 실패."""
    item = _item(category=Category.AMBIGUOUS, expect_escalation=True)
    rep = score_qa([item], {"DEV-X-001": _resp(needs_human_review=False)}, SOURCES)
    assert rep.escalation_recall == 0.0
    assert "지어냄" in " ".join(rep.failure_modes())


def test_escalation_precision_falls_on_over_escalation():
    rep = score_qa([_item()], {"DEV-X-001": _resp(needs_human_review=True)}, SOURCES)
    assert rep.escalation_precision == 0.0
    assert not rep.scores[0].exact


def test_unanswered_items_are_reported_not_silently_dropped():
    rep = score_qa([_item()], {}, SOURCES)
    assert rep.unanswered == ["DEV-X-001"]
    assert rep.total == 0


def test_missing_citation_is_a_failure_mode():
    rep = score_qa([_item()], {"DEV-X-001": _resp(citations=())}, SOURCES)
    assert rep.items_without_citation == 1
    assert "근거 인용 없음" in rep.failure_modes()


def test_report_renders_all_metrics():
    rep = score_qa([_item()], {"DEV-X-001": _resp()}, SOURCES, provider="cli", batch_size=5)
    text = format_qa_report(rep)
    for key in ("Fact Coverage", "Exact Rate", "Citation Correctness",
                "Escalation Precision", "Escalation Recall"):
        assert key in text


# ---------------------------------------------- 0건 중 0건은 100%가 아니다 (미측정)
#
# `x / total if total else 1.0` 은 **아무것도 대조하지 않은 실행을 만점으로 보고**한다.
# 그 만점은 하한 임계를 그대로 통과하므로, 게이트가 비어 있는데 초록으로 보인다.
# 여기 검사들은 각 지표가 "잴 것이 없으면 값을 내지 않는다"를 고정한다.

def test_no_citations_is_not_100_percent_citation_correctness():
    """인용을 하나도 달지 않은 답변이 만점이면, **근거를 안 댈수록 점수가 좋아진다.**"""
    rep = score_qa([_item()], {"DEV-X-001": _resp(citations=())}, SOURCES)
    assert rep.citation_correctness is None, "대조할 인용이 0건인데 비율을 냈다"
    assert rep.unsupported_claim_rate is None, "인용이 없으면 미지원 비율도 낼 수 없다"
    assert rep.items_without_citation == 1        # 사실 자체는 그대로 보고된다


def test_escalating_nothing_is_not_perfect_precision():
    """아무것도 안 올린 모델이 만점을 받으면, 절대 escalation 하지 않는 쪽이 이긴다."""
    rep = score_qa([_item()], {"DEV-X-001": _resp(needs_human_review=False)}, SOURCES)
    assert rep.escalation_precision is None, "escalation 한 문항이 0건인데 비율을 냈다"


def test_no_item_needs_escalation_is_not_perfect_recall():
    """올려야 할 문항이 없었던 것은 만점이 아니라 **시험에 안 나온 것**이다."""
    rep = score_qa([_item(expect_escalation=False)],
                   {"DEV-X-001": _resp(needs_human_review=False)}, SOURCES)
    assert rep.escalation_recall is None


def test_item_without_gold_facts_is_not_100_percent_covered():
    """escalation 형 문항은 gold_facts 가 비어 있다 — 담을 사실이 없는 것이지 만점이 아니다.

    100% 로 세면 "원문에 답이 없다"만 답한 문항이 완전성 집계를 끌어올린다.
    """
    rep = score_qa([_item(gold_facts=(), expect_escalation=True)],
                   {"DEV-X-001": _resp(needs_human_review=True)}, SOURCES)
    s = rep.scores[0]
    assert s.fact_coverage is None, "대조할 사실이 0건인데 비율을 냈다"
    assert rep.fact_coverage is None
    assert s.exact, "사실이 없어도 escalation 판단이 맞았으면 그 문항은 맞은 것이다"


def test_empty_report_reports_nothing_rather_than_zero():
    """채점된 문항이 0건이면 0% 가 아니다 — 0% 는 '전부 틀렸다'는 주장이다."""
    rep = score_qa([], {}, SOURCES)
    assert rep.exact_rate is None and rep.fact_coverage is None
    assert rep.citation_correctness is None


def test_unmeasured_metrics_say_why_instead_of_going_blank():
    """빈칸은 읽는 사람이 각자 해석하고, 대개 '괜찮은가 보다'로 읽힌다."""
    rep = score_qa([_item(gold_facts=())], {"DEV-X-001": _resp(citations=())}, SOURCES)
    text = format_qa_report(rep)
    assert "미측정" in text
    assert "대조할 인용이 0건" in text and "대조할 골드 사실이 0건" in text
    # 무엇으로 쟀는지(재료 건수)가 같이 보여야 "왜 미측정인지"를 확인할 수 있다
    assert "대조 재료:" in text


def test_worst_items_still_sorts_when_some_items_are_unmeasured():
    """미측정을 도입하면서 정렬이 None 에 넘어지면, 실패 문항 목록이 통째로 사라진다."""
    items = [_item(id="A"), _item(id="B", gold_facts=(), expect_escalation=True)]
    resps = {"A": _resp(item_id="A", answer="관련 없는 답"),
             "B": _resp(item_id="B", needs_human_review=False)}
    rep = score_qa(items, resps, SOURCES)
    worst = rep.worst_items
    assert [s.item_id for s in worst] == ["A", "B"], \
        "잴 수 있는 실패가 먼저, 비율로 줄 세울 수 없는 것이 뒤에 와야 한다"


# ------------------------------------------------------------------ 프롬프트·응답 형식

def test_prompt_includes_sources_and_every_question_id():
    items = load_split(Split.DEV)[:3]
    prompt = build_qa_prompt(SOURCES, items)
    assert "<doc id=D1>" in prompt
    for it in items:
        assert it.id in prompt and it.question in prompt


def test_qa_response_validator_requires_citations_and_flag():
    ok = {"answers": [{"id": "A", "answer": "x", "citations": [
        {"source_doc_id": "D1", "quote": "q"}], "needs_human_review": False}]}
    assert validate_qa_response(ok) == []

    no_cite = {"answers": [{"id": "A", "answer": "x", "citations": [],
                            "needs_human_review": False}]}
    assert any("citations" in e for e in validate_qa_response(no_cite))

    bad_flag = {"answers": [{"id": "A", "answer": "x", "citations": [
        {"source_doc_id": "D1", "quote": "q"}], "needs_human_review": "yes"}]}
    assert any("needs_human_review" in e for e in validate_qa_response(bad_flag))

    assert validate_qa_response({}) == ["필수 키 누락 또는 형식 오류: answers(배열)"]
