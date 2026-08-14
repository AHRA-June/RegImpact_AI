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


# ---------- 최종 평가 (Phase 3 개봉) ----------
def test_final_evaluation_record_and_100_percent():
    """최종 평가 기록이 존재하고 3개 split 전부 통과(개봉 결과)."""
    from regimpact.eval import load_final_eval

    rec = load_final_eval()
    assert rec is not None, "docs/eval/gold_set/FINAL_EVAL.json 필요 — run_final_evaluation로 개봉"
    assert rec["overall"]["total"] == 115
    assert rec["overall"]["pass_rate"] == 1.0
    for s in ("dev", "locked", "challenge"):
        assert rec["splits"][s]["pass_rate"] == 1.0
        assert not rec["splits"][s]["failures"]
    # 규율 note(재튜닝 금지)와 provenance
    assert "재튜닝" in rec["_meta"]["note"]
    assert rec["_meta"]["gold_version"] and rec["_meta"]["opened_date"]


def test_run_final_evaluation_is_deterministic():
    from regimpact.eval import run_final_evaluation

    a = run_final_evaluation("2026-08-14", save=False)
    b = run_final_evaluation("2026-08-14", save=False)
    assert a["overall"] == b["overall"]
    assert a["splits"]["locked"]["by_category"] == b["splits"]["locked"]["by_category"]


def test_report_reflects_opened_gold_set():
    from regimpact.report import build_validation_report

    gs = build_validation_report().gold_set
    assert gs["opened"] is True
    assert gs["overall"]["passed"] == gs["overall"]["total"] == 115
    assert gs["locked"]["total"] == 40 and gs["challenge"]["total"] == 35
