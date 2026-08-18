"""골드셋 테스트 — 정답지 무결성 + 누수 방지 통제.

두 축을 본다:
1. **무결성** — 인용이 원문에 실제로 존재하는가, 필드가 규격을 지키는가.
   정답지가 틀리면 그 위의 모든 지표가 틀린다.
2. **봉인** — LOCKED/CHALLENGE가 코드 레벨에서 실제로 막히는가.
   브리프 §12의 규율은 문서에만 적으면 지켜지지 않는다.
"""
import json
import re
from pathlib import Path

import pytest

from regimpact.eval import (
    Category,
    Split,
    SealedSplitError,
    category_counts,
    coverage_report,
    load_split,
    split_path,
    split_stats,
    validate_items,
)
from regimpact.eval.goldset import MIN_REASON_CHARS, SEALED, save_split
from regimpact.eval.schema import Citation, GoldItem
from regimpact.extractor.sources import load_sources

REPO = Path(__file__).resolve().parent.parent
SOURCES = load_sources()
REASON = "테스트에서 봉인 동작을 검증하기 위한 접근 (튜닝 아님)"


def _all_items():
    items = load_split(Split.DEV)
    for sp in SEALED:
        items += load_split(sp, unseal_reason=REASON, log_path=REPO / ".tmp_seal_log.md")
    return items


@pytest.fixture(scope="module", autouse=True)
def _cleanup_tmp_log():
    yield
    tmp = REPO / ".tmp_seal_log.md"
    if tmp.exists():
        tmp.unlink()


# ------------------------------------------------------------------ 봉인 통제

def test_dev_opens_without_a_reason():
    assert load_split(Split.DEV)


@pytest.mark.parametrize("split", sorted(SEALED, key=lambda s: s.value))
def test_sealed_splits_refuse_to_open(split):
    """개발 중 무심코 여는 것이 누수의 실제 경로 — 코드가 거부해야 한다."""
    with pytest.raises(SealedSplitError, match="봉인된 셋"):
        load_split(split)


def test_trivial_unseal_reason_is_rejected():
    """'test' 같은 형식적 사유로 봉인이 열리면 통제가 아니라 장식이다."""
    with pytest.raises(SealedSplitError):
        load_split(Split.LOCKED, unseal_reason="test")
    assert MIN_REASON_CHARS >= 20


def test_unsealing_records_an_access_entry(tmp_path):
    log = tmp_path / "log.md"
    load_split(Split.LOCKED, unseal_reason=REASON, log_path=log)
    text = log.read_text(encoding="utf-8")
    assert "LOCKED" in text and REASON in text

    load_split(Split.CHALLENGE, unseal_reason=REASON, log_path=log)
    assert text in log.read_text(encoding="utf-8")   # append-only: 기존 기록이 남는다
    assert log.read_text(encoding="utf-8").count("| 2") == 2


def test_stats_do_not_require_unsealing():
    """일상적인 커버리지 점검이 봉인 해제를 요구하면 사람은 습관적으로 봉인을 열게 된다."""
    stats = split_stats(Split.LOCKED)
    assert stats["count"] == 40
    assert "categories" in stats
    # 정답·질문·인용은 새어 나오면 안 된다
    blob = json.dumps(stats, ensure_ascii=False)
    assert "gold_answer" not in blob and "question" not in blob and "quote" not in blob


def test_no_tuning_code_reads_sealed_splits():
    """봉인 셋을 참조하는 코드는 작성 도구·테스트뿐이어야 한다."""
    offenders = []
    for path in list((REPO / "src").rglob("*.py")) + list((REPO / "examples").rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        if "locked.json" in text or "challenge.json" in text:
            offenders.append(str(path.relative_to(REPO)))
    # goldset.py 는 파일명 매핑을 갖는 로더 자신이므로 허용
    offenders = [o for o in offenders if not o.endswith("eval/goldset.py")]
    assert not offenders, f"봉인 셋을 참조하는 코드: {offenders}"


# ------------------------------------------------------------------ 무결성

@pytest.mark.parametrize("split", list(Split))
def test_every_split_passes_integrity_validation(split):
    kw = {} if split not in SEALED else {"unseal_reason": REASON, "log_path": REPO / ".tmp_seal_log.md"}
    items = load_split(split, **kw)
    rep = validate_items(items, SOURCES, expected_split=split)
    assert rep.ok, "무결성 오류:\n" + "\n".join(rep.errors[:10])


def test_every_citation_exists_verbatim_in_the_sources():
    """★ 골드셋 자신에게 Citation Assurance를 적용한다 — 인용을 지어내지 않았는가."""
    norm = {k: re.sub(r"\s+", " ", v).strip() for k, v in SOURCES.items()}
    for item in _all_items():
        for cit in item.citations:
            quote = re.sub(r"\s+", " ", cit.quote).strip()
            assert quote in norm[cit.source_doc_id], f"{item.id}: {quote[:60]}"


def test_split_sizes_match_the_agreed_design():
    """metrics_spec §0-A 확정: DEV 40 / LOCKED 40 / CHALLENGE 35."""
    assert split_stats(Split.DEV)["count"] == 40
    assert split_stats(Split.LOCKED)["count"] == 40
    assert split_stats(Split.CHALLENGE)["count"] == 35


def test_ids_are_globally_unique_across_splits():
    ids = [i.id for i in _all_items()]
    assert len(ids) == len(set(ids))


def test_questions_do_not_repeat_across_splits():
    """DEV에서 튜닝한 문항이 LOCKED에 그대로 있으면 고정 테스트가 아니다."""
    seen: dict[str, str] = {}
    for item in _all_items():
        key = re.sub(r"\s+", " ", item.question).strip()
        assert key not in seen, f"{item.id}와 {seen[key]}의 질문이 같다"
        seen[key] = item.id


def test_dev_and_locked_share_the_same_category_shape():
    """LOCKED가 DEV와 다른 분포면 최종 성능이 난이도 차이인지 성능 차이인지 알 수 없다."""
    assert split_stats(Split.DEV)["categories"] == split_stats(Split.LOCKED)["categories"]


def test_all_ten_categories_are_covered_overall():
    counts = category_counts(_all_items())
    assert set(counts) == {c.value for c in Category}


def test_challenge_is_weighted_to_high_risk_failure_modes():
    """CHALLENGE는 예외·경과규정·시행일·충돌 가중 (브리프 §11, metrics_spec §0-A)."""
    assert split_stats(Split.CHALLENGE)["high_risk_ratio"] >= 0.7


def test_dev_and_locked_keep_high_risk_weighting():
    for split in (Split.DEV, Split.LOCKED):
        assert split_stats(split)["high_risk_ratio"] >= 0.4


def test_ambiguous_items_always_expect_escalation():
    """원문에 답이 없으면 지어내지 말고 사람에게 올려야 한다 — 정답이 곧 escalation."""
    ambiguous = [i for i in _all_items() if i.category == Category.AMBIGUOUS]
    assert ambiguous
    assert all(i.expect_escalation for i in ambiguous)


def test_items_carry_every_field_the_brief_requires():
    """브리프 §11 필드 목록 — 하나라도 비면 문항이 채점 근거를 잃는다."""
    for item in _all_items():
        assert item.question and item.gold_answer
        assert item.gold_facts and item.citations
        assert item.policy_version
        assert isinstance(item.expect_escalation, bool)
        assert item.category in Category and item.split in Split


def test_rule_ids_reference_real_engine_rules():
    from regimpact.eval import KNOWN_RULE_IDS

    for item in _all_items():
        if item.rule_id is not None:
            assert item.rule_id in KNOWN_RULE_IDS, f"{item.id}: {item.rule_id}"


def test_authored_by_marks_human_confirmation_state():
    """🤖 ai_draft → ✅ human_confirmed. 지금은 전부 초안이며 그렇게 표시돼 있어야 한다."""
    for split in Split:
        assert "ai_draft" in split_stats(split)["authored_by"]


# ------------------------------------------------------------------ 검증기 자체

def _dummy(**over):
    base = dict(
        id="DEV-X-001", split=Split.DEV, category=Category.NORMAL,
        question="q", gold_answer="a 40%", gold_facts=("40%",),
        citations=(Citation("FSC_PRESS_20260630", "규제지역 내 주담대 취급시 LTV 강화"),),
        expect_escalation=False, policy_version="FSC_20260630",
    )
    base.update(over)
    return GoldItem(**base)


def test_validator_catches_a_fabricated_citation():
    """★ 이 검사가 죽으면 골드셋에 환각 인용이 들어가도 아무도 모른다."""
    bad = _dummy(citations=(Citation("FSC_PRESS_20260630", "원문에 없는 그럴듯한 문장"),))
    rep = validate_items([bad], SOURCES)
    assert any("인용이 원문에 없음" in e for e in rep.errors)


def test_validator_catches_duplicate_ids_and_questions():
    rep = validate_items([_dummy(), _dummy()], SOURCES)
    assert any("id 중복" in e for e in rep.errors)


def test_validator_requires_escalation_for_ambiguous():
    rep = validate_items([_dummy(category=Category.AMBIGUOUS, expect_escalation=False)], SOURCES)
    assert any("AMBIGUOUS" in e for e in rep.errors)


def test_validator_rejects_unknown_rule_id_and_policy_version():
    rep = validate_items([_dummy(rule_id="MADE_UP", policy_version="NOPE")], SOURCES)
    assert any("rule_id" in e for e in rep.errors)
    assert any("policy_version" in e for e in rep.errors)


def test_validator_rejects_id_prefix_mismatch():
    rep = validate_items([_dummy(id="WRONG-001")], SOURCES)
    assert any("로 시작해야 함" in e for e in rep.errors)


def test_coverage_report_warns_on_missing_categories():
    rep = coverage_report([_dummy()])
    assert any("미커버 카테고리" in w for w in rep.warnings)


def test_save_and_load_roundtrip(tmp_path):
    items = [_dummy()]
    save_split(items, Split.DEV, gold_dir=tmp_path)
    assert split_path(Split.DEV, tmp_path).exists()
    assert load_split(Split.DEV, gold_dir=tmp_path)[0].to_dict() == items[0].to_dict()
