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
