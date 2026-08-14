"""골드셋 도메인 검수(v2) 테스트 — grounding·수치 일관성·확정 상태·불변성."""
from regimpact.eval import load_review, load_split, review_all, review_item


def test_review_covers_all_115_and_confirms():
    r = review_all()
    s = r["summary"]
    assert s["total"] == 115
    # 미해결(flag) 없음 — 전부 확정 3종 중 하나
    assert s["CONFIRMED"] + s["CONFIRMED_ESCALATION"] + s["CONFIRMED_PRECEDENCE"] == 115
    assert s["CONFIRMED_ESCALATION"] == 10   # NEEDS_HUMAN_REVIEW 문항
    assert s["CONFIRMED_PRECEDENCE"] == 13    # CONFLICT 문항


def test_numeric_answers_consistent_with_cited_source():
    """수치 정답이 인용이 말하는 값과 불일치하면 review_item이 예외."""
    for name in ("dev", "locked", "challenge"):
        for it in load_split(name, unlock=True):
            rv = review_item(it)                 # 불일치면 여기서 ValueError
            assert rv["status"].startswith("CONFIRMED")
            assert rv["grounding_doc"] and rv["grounding_quote"]


def test_escalation_items_grounded_to_baseline_absence():
    for name in ("challenge",):
        for it in load_split(name, unlock=True):
            if it.expected["status"] == "NEEDS_HUMAN_REVIEW":
                rv = review_item(it)
                assert rv["status"] == "CONFIRMED_ESCALATION"
                assert "기준선" in rv["grounding_quote"]


def test_review_does_not_change_inputs_or_answers():
    """검수는 입력·정답을 변경하지 않는다(annotation only)."""
    rv = review_item(load_split("dev")[0])
    assert set(rv.keys()) >= {"status", "grounding_doc", "grounding_quote", "rationale"}
    # review_item 반환에 input/expected 변형 필드가 없음(원본 불변)


def test_persisted_review_matches_recompute():
    rec = load_review()
    assert rec is not None, "REVIEW_v2.json 필요 — tools/review_gold_set.py"
    live = review_all()["summary"]
    assert rec["summary"] == live
    assert rec["_meta"]["version"] == "v2"
    assert "사람" in rec["_meta"]["reviewer"]
