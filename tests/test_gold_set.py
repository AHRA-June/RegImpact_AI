"""Gold Set 테스트 — split 크기·누수 방지·DEV 회귀·manifest 무결성.

정답은 독립 명세 오라클에서 유도되므로 엔진 회귀가 tautology가 아니다. LOCKED/CHALLENGE는
sealed — 테스트에서 최종 검증 목적으로만 unlock한다(개발 튜닝에 쓰지 않음).
"""
import hashlib
import json

import pytest

from regimpact.eval import (
    GOLD_DIR,
    SEALED_SPLITS,
    load_manifest,
    load_split,
    run_gold_regression,
)


def test_split_sizes_115_total():
    m = load_manifest()
    assert m["splits"]["dev"]["count"] == 40
    assert m["splits"]["locked"]["count"] == 40
    assert m["splits"]["challenge"]["count"] == 35
    assert m["total"] == 115


def test_sealed_splits_require_unlock():
    for name in SEALED_SPLITS:
        with pytest.raises(RuntimeError):
            load_split(name)               # unlock 없이 열면 실패(누수 방지)
        assert load_split(name, unlock=True)  # unlock=True면 열림


def test_splits_are_disjoint_no_leakage():
    """같은 입력이 두 split에 있으면 평가 누수 → 금지."""
    sigs = {}
    for name in ("dev", "locked", "challenge"):
        for item in load_split(name, unlock=True):
            sig = json.dumps(item.input, sort_keys=True, ensure_ascii=False)
            assert sig not in sigs, f"누수: {item.id} == {sigs.get(sig)}"
            sigs[sig] = item.id


def test_dev_regression_100_percent():
    r = run_gold_regression("dev")
    assert r.total == 40
    assert r.pass_rate == 1.0, [f.item.id + ":" + ",".join(f.mismatches) for f in r.failures()]


def test_locked_and_challenge_pass_on_final_run():
    # 최종 1회 실행(unlock) — 엔진이 어려운 케이스도 명세대로 처리하는지 확인
    for name in ("locked", "challenge"):
        r = run_gold_regression(name, unlock=True)
        assert r.pass_rate == 1.0, [f.item.id for f in r.failures()]


def test_challenge_weighted_to_hard_categories():
    items = load_split("challenge", unlock=True)
    cats = {it.category for it in items}
    # 적대적 카테고리 포함(브리프 §11 철학)
    assert {"CONFLICT", "AMBIGUOUS"} <= cats
    # escalation 기대 문항(AMBIGUOUS)이 실제로 존재
    assert any(it.expected_escalation for it in items)


def test_manifest_hashes_match_files():
    m = load_manifest()
    for name, meta in m["splits"].items():
        text = (GOLD_DIR / f"{name}.json").read_text(encoding="utf-8")
        assert hashlib.sha256(text.encode("utf-8")).hexdigest() == meta["sha256"]


def test_items_have_required_metadata():
    for name in ("dev", "locked", "challenge"):
        for it in load_split(name, unlock=True):
            assert it.policy_version and it.rule_id and it.source_doc_id and it.source_note
            assert it.split == name
            # escalation 플래그와 기대 status 일치
            assert it.expected_escalation == (it.expected["status"] == "NEEDS_HUMAN_REVIEW")
