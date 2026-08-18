"""골드 ⟷ 확정 명세 정합성 검사 테스트.

이 검사는 **정밀도가 생명**이다. 오탐이 많으면 사람이 무시하고, 그러면 없는 것과 같다.
(첫 버전은 115문항에서 13건을 잡았는데 10건이 오탐이라 규칙을 버리고 다시 만들었다.)
그래서 여기서는 "잡아야 할 것을 잡는가"와 "잡지 말아야 할 것을 놔두는가"를 같은 비중으로 고정한다.
"""
import pytest

from regimpact import rule_engine as R
from regimpact.eval import Split, check_gold_against_spec, load_split
from regimpact.eval.goldset import SEALED
from regimpact.eval.schema import Category, Citation, GoldItem

REASON = "정합성 검사 테스트 — 명세 대조 전용 (튜닝 아님)"


def _item(question, answer, **over):
    base = dict(
        id="DEV-X-001", split=Split.DEV, category=Category.NORMAL,
        question=question, gold_answer=answer, gold_facts=("x",),
        citations=(Citation("D1", "q"),), expect_escalation=False,
        policy_version="FSC_20260630",
    )
    base.update(over)
    return GoldItem(**base)


def _all_items():
    items = load_split(Split.DEV)
    for sp in SEALED:
        items += load_split(sp, unseal_reason=REASON)
    return items


# ------------------------------------------------------- 잡아야 하는 것

def test_flags_baseline_ltv_that_contradicts_the_spec():
    """非규제(수도권) 기준선을 명세와 다른 값으로 주장하면 잡아야 한다."""
    item = _item("6.30 이전 非규제지역(수도권) 일반 차주의 LTV는?", "60%였다")
    rep = check_gold_against_spec([item])
    assert not rep.ok and "기준선" in rep.conflicts[0]


def test_flags_regulated_ltv_that_differs_by_region_type():
    """LTV는 투기과열·조정 동일(40%)이고, 종류별로 갈리는 것은 DTI다."""
    item = _item("조정대상지역과 투기과열지구의 LTV는?", "조정대상지역 50%, 투기과열지구 40%")
    assert not check_gold_against_spec([item]).ok


def test_does_not_flag_an_answer_that_explicitly_separates_ltv_from_dti():
    """정정된 문항이 정정 때문에 다시 잡히면 검사가 사람을 되돌려 보낸다."""
    item = _item("조정대상지역과 투기과열지구의 LTV는?",
                 "둘 다 40%로 같다. 갈리는 40%/50%는 LTV가 아니라 DTI다.")
    assert check_gold_against_spec([item]).ok


# ------------------------------------------------------- 놔둬야 하는 것 (오탐 방지)

@pytest.mark.parametrize("q,a", [
    # 값을 주장하지 않고 "원문에 없다"고 말하는 문항
    ("非규제 수도권 비처분 1주택 LTV는?", "원문에 답이 없다. 60%는 수도권 外 값이라 전용 불가"),
    # 수도권 外 값을 인용하는 문항
    ("非규제지역(수도권 외)의 LTV 기준은?", "무주택 70%, 유주택 60%다"),
    # 규제지역을 다루지만 주제가 유주택인 문항 (40%가 없는 것이 정상)
    ("규제지역 유주택자의 LTV는?", "LTV 0%다"),
    # 규제지역 다주택 (40%가 없는 것이 정상)
    ("다주택자의 수도권 LTV는?", "규제지역 여부와 무관하게 LTV 0%"),
    # LTV를 아예 말하지 않는 문항
    ("경과규정 조건은?", "6.30일까지 접수 또는 계약금 납부"),
])
def test_does_not_flag_legitimate_items(q, a):
    assert check_gold_against_spec([_item(q, a)]).ok


def test_spec_conforming_baseline_passes():
    item = _item("지정 전 非규제(수도권) 기준선 LTV는?", f"{R.LTV_BASELINE:.0%}였다")
    assert check_gold_against_spec([item]).ok


# ------------------------------------------------------- 실제 골드셋 상태

def test_no_unresolved_conflicts_remain():
    """2026-08-18 검수로 3건 모두 해소됐다(전부 '명세가 맞음').

    새 충돌이 생기면 여기서 잡힌다 — 그때는 검수표를 다시 만들고 사람 판단을 받는다.
    """
    rep = check_gold_against_spec(_all_items())
    flagged = {c.split("]")[0].strip("[ ") for c in rep.conflicts}
    assert flagged == set()


def test_precision_is_high_on_the_real_goldset():
    """115문항에서 소수만 잡혀야 한다 — 오탐이 쏟아지면 검사가 무시된다."""
    rep = check_gold_against_spec(_all_items())
    assert rep.checked == 115
    assert len(rep.conflicts) <= 5
