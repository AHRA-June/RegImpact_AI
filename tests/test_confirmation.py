"""확정 지문 테스트 — "검수했다"가 시간이 지나도 참인지 지키는 장치.

authored_by=human_confirmed 는 **그 시점의 내용**에 대한 확정이다. 이후 골드를 손보면
그 표시가 사실이 아니게 되는데, 그 사실은 아무 데도 드러나지 않는다. 지문이 그것을 드러낸다.
"""
import copy
import json
from pathlib import Path

from regimpact.eval import check_confirmation, compute_digest

REPO = Path(__file__).resolve().parent.parent
GOLD = json.loads((REPO / "docs/eval/regchange_gold_6_30.json").read_text(encoding="utf-8"))


def test_extraction_gold_is_confirmed_and_unchanged_since():
    st = check_confirmation(GOLD)
    assert st.confirmed, "추출 골드가 확정 상태가 아니다"
    assert st.digest_matches, f"확정 이후 내용이 바뀌었다 — 재검수 필요: {st.summary()}"
    assert not st.needs_review


def test_every_entry_is_marked_confirmed():
    entries = GOLD["required_changes"] + GOLD["exceptions"]
    assert entries
    assert all(e.get("authored_by") == "human_confirmed" for e in entries)


def test_changing_a_keyword_breaks_the_digest():
    """채점 키워드를 바꾸면 채점 결과가 달라지므로 재검수 대상이다."""
    g = copy.deepcopy(GOLD)
    g["required_changes"][0]["keywords"] = ["완전히 다른 키워드"]
    assert check_confirmation(g).needs_review


def test_changing_a_citation_breaks_the_digest():
    g = copy.deepcopy(GOLD)
    g["required_changes"][0]["citations"][0]["quote"] = "다른 인용"
    assert check_confirmation(g).needs_review


def test_adding_an_entry_breaks_the_digest():
    g = copy.deepcopy(GOLD)
    g["exceptions"].append({"name": "new", "keywords": ["x"], "claim": "c", "citations": []})
    assert check_confirmation(g).needs_review


def test_editing_prose_does_not_break_the_digest():
    """설명 문구가 바뀌었다고 재검수를 요구하면 통제가 성가심으로 전락한다."""
    g = copy.deepcopy(GOLD)
    g["_note"] = "설명만 고쳤다"
    g["_limitation"] = "다르게 적었다"
    assert not check_confirmation(g).needs_review


def test_digest_is_order_independent_for_json_formatting():
    """키 순서·들여쓰기 같은 직렬화 차이로 재검수가 발동하면 안 된다."""
    g = json.loads(json.dumps(GOLD, sort_keys=True))
    assert compute_digest(g) == compute_digest(GOLD)


def test_unconfirmed_gold_is_not_flagged_as_needing_review():
    """미확정 골드는 '재검수 필요'가 아니라 그냥 '미확정'이다."""
    g = copy.deepcopy(GOLD)
    g["authored_by"] = "ai_draft"
    st = check_confirmation(g)
    assert not st.confirmed and not st.needs_review
