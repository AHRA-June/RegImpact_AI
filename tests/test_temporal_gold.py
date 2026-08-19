"""시점 질의 골드(TEMPORAL split) — Policy-version Consistency 가동용.

세 축을 본다:
1. 셋 자체 — 비봉인으로 열리고, as_of 문항이 Temporal Policy Resolver와 정합하는가.
   (인용 무결성은 test_goldset.py 의 split 파라미터 검사에 TEMPORAL 이 포함돼 함께 돈다.)
2. 검사기 — 골드가 resolver와 어긋나면 실제로 잡아내는가 (변이 테스트).
3. 한계의 갱신 — escalation 문항의 근거(DB가 답할 수 없음)가 사라지면,
   즉 2020 6·17이 해제일과 함께 confirm() 되면 검사가 갱신을 요구하는가.
"""
from datetime import date

import pytest

from regimpact.eval import Split, load_split, validate_items
from regimpact.eval.temporal import check_temporal_gold, policy_version_consistency
from regimpact.extractor.sources import load_corpus
from regimpact.policy.registry import load_registry, registry_from
from regimpact.policy.version import PolicyStatus


@pytest.fixture(scope="module")
def temporal_items():
    return load_split(Split.TEMPORAL)


def test_temporal_split_opens_without_a_reason(temporal_items):
    """TEMPORAL은 DEV처럼 비봉인 — 튜닝·검수에 자유롭게 쓴다."""
    assert temporal_items


def test_temporal_items_cite_the_wider_corpus(temporal_items):
    """이 셋의 존재 이유 — 과거 정책 원문(2020·2025)을 실제로 인용해야 한다."""
    docs = {c.source_doc_id for i in temporal_items for c in i.citations}
    assert any(d.endswith("20200617") for d in docs)
    assert any(d.endswith("20251015") for d in docs)
    rep = validate_items(temporal_items, load_corpus(), expected_split=Split.TEMPORAL)
    assert rep.ok, "\n".join(rep.errors[:5])


def test_answerable_items_agree_with_the_resolver(temporal_items):
    """as_of 문항의 policy_version은 '그 시점 유효 최신 정책' 주장 — resolver와 대조."""
    rep = check_temporal_gold(temporal_items)
    assert rep.ok, "\n".join(rep.conflicts)
    assert rep.answerable >= 5 and rep.escalations >= 2


def test_escalation_items_target_dates_the_db_cannot_answer(temporal_items):
    """escalation의 근거는 '2020 6·17이 해제일 미상이라 DRAFT'라는 사실이다."""
    esc = [i for i in temporal_items if i.expect_escalation]
    assert esc
    reg = load_registry()
    for item in esc:
        assert item.as_of is not None
        policy = reg.get(item.policy_version)
        assert policy is not None and policy.status is PolicyStatus.DRAFT, (
            f"{item.id}: escalation 근거가 사라졌다 — 답변형으로 갱신할 것")


def test_checker_catches_a_wrong_gold_policy_version(temporal_items):
    """변이: 답변형 문항의 policy_version을 틀리게 바꾸면 검사가 잡아야 한다."""
    from dataclasses import replace

    target = next(i for i in temporal_items if i.as_of and not i.expect_escalation)
    mutated = replace(target, policy_version="MOLIT_20161103"
                      if target.policy_version != "MOLIT_20161103" else "FSC_20260630")
    rep = check_temporal_gold([mutated])
    assert not rep.ok and mutated.id in rep.conflicts[0]


def test_checker_demands_update_when_a_draft_confirms(temporal_items):
    """★ 한계는 골드에 새겼으면 풀릴 때 함께 풀려야 한다.

    2020 6·17이 해제일과 함께 confirm() 되는 미래를 시뮬레이션 — escalation 문항의
    as_of 를 DB가 답할 수 있게 되면 검사가 '답변형으로 갱신하라'고 충돌을 낸다.
    """
    from dataclasses import replace

    esc = next(i for i in temporal_items if i.expect_escalation)
    reg = load_registry()
    p2020 = reg.get(esc.policy_version)
    # 해제일 없이 확정되는 시나리오(구간 열림) — as_of 시점에 유효해진다
    confirmed = registry_from(
        [p for p in reg.policies if p.policy_id != p2020.policy_id]
        + [replace(p2020, status=PolicyStatus.CONFIRMED)]
    )
    assert confirmed.get(esc.policy_version).is_active_at(date.fromisoformat(esc.as_of))
    rep = check_temporal_gold([esc], confirmed)
    assert not rep.ok and "갱신" in rep.conflicts[0]


def test_policy_version_consistency_is_measurable_now(temporal_items):
    """미측정이던 지표에 분모가 생겼다 — 단, 골드가 ai_draft인 동안은 상대 비교용."""
    hit, total = policy_version_consistency(temporal_items)
    assert total >= 5
    assert hit == total          # 현재 골드·정책 DB 정합 상태의 스냅샷


def test_as_of_format_is_validated():
    from dataclasses import replace

    item = load_split(Split.TEMPORAL)[0]
    bad = replace(item, as_of="2025.10.16")
    rep = validate_items([bad], load_corpus())
    assert any("as_of 형식 오류" in e for e in rep.errors)
