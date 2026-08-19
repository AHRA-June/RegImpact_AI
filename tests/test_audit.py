"""감사추적 — tamper-evident 해시 체인.

단순 로그가 아니라 **변조가 드러나는** 로그여야 한다. 각 테스트는 실제 변조 시나리오
하나씩을 재현하고, 체인이 그것을 잡는지(또는 구조상 못 잡는지)를 고정한다.
"""
import json

import pytest

from regimpact.audit import GENESIS, Action, AuditLog


def _clock():
    seq = iter(f"2026-08-19T00:00:{i:02d}+00:00" for i in range(100))
    return lambda: next(seq)


def _log(n=3):
    log = AuditLog(clock=_clock())
    log.record(Action.SOURCE_INGESTED, "FSC_PRESS_20260630", {"bytes": 6470})
    log.record(Action.EXTRACTION, "FSC_20260630", {"changes": 75})
    log.record(Action.PROPOSAL_CREATED, "MORTGAGE_LTV", {"status": "NEEDS_REVIEW"})
    return log


def test_clean_chain_verifies():
    assert _log().verify().ok


def test_first_event_links_to_genesis():
    assert _log().events[0].prev_hash == GENESIS


def test_same_content_same_hash():
    """결정론 — 시계를 주입했으므로 같은 입력은 같은 체인을 낸다."""
    assert _log().head_hash == _log().head_hash


# ---------- 변조 탐지 ----------
def test_modified_detail_breaks_chain():
    """숫자 하나만 고쳐도 잡혀야 한다."""
    log = _log()
    lines = log.to_jsonl().splitlines()
    d = json.loads(lines[1])
    d["details"]["changes"] = 74               # 75 → 74
    lines[1] = json.dumps(d, ensure_ascii=False)
    result = AuditLog.load_jsonl("\n".join(lines)).verify()
    assert not result.ok
    assert any("entry_hash" in p for p in result.problems)


def test_reordered_events_break_chain():
    log = _log()
    lines = log.to_jsonl().splitlines()
    lines[0], lines[1] = lines[1], lines[0]
    assert not AuditLog.load_jsonl("\n".join(lines)).verify().ok


def test_deleted_middle_event_breaks_chain():
    log = _log()
    lines = log.to_jsonl().splitlines()
    del lines[1]
    assert not AuditLog.load_jsonl("\n".join(lines)).verify().ok


def test_rehashed_forgery_still_breaks_chain():
    """변조자가 그 항목의 해시까지 다시 계산해도, 이후 항목의 prev_hash 가 안 맞는다."""
    from regimpact.audit.log import _hash
    log = _log()
    lines = log.to_jsonl().splitlines()
    d = json.loads(lines[1])
    d["details"]["changes"] = 74
    body = {k: d[k] for k in ("seq", "timestamp", "actor", "action", "target", "details")}
    d["entry_hash"] = _hash(d["prev_hash"], body)       # 해시 재계산으로 은폐 시도
    lines[1] = json.dumps(d, ensure_ascii=False)
    result = AuditLog.load_jsonl("\n".join(lines)).verify()
    assert not result.ok
    assert any("prev_hash" in p for p in result.problems), \
        "다음 항목이 옛 해시를 가리키므로 체인이 끊겨야 한다"


# ---------- 구조적 한계: 끝에서 자르기 ----------
def test_truncation_is_invisible_without_an_external_anchor():
    """해시 체인만으로는 **끝에서 잘라낸 로그**를 구분할 수 없다.

    잘린 뒤에도 그 자체로 유효한 체인이기 때문이다. 이건 구현 미비가 아니라
    append-only 로그의 구조적 성질이라, 문서(audit/log.py docstring)에도 적혀 있다.
    """
    log = _log()
    truncated = AuditLog.load_jsonl("\n".join(log.to_jsonl().splitlines()[:2]))
    assert truncated.verify().ok, "체인 자체는 유효하다 — 그래서 anchor가 필요하다"


def test_truncation_is_caught_with_expected_head():
    log = _log()
    head = log.head_hash                       # 로그 바깥에 남겨둔 앵커
    truncated = AuditLog.load_jsonl("\n".join(log.to_jsonl().splitlines()[:2]))
    result = truncated.verify(expected_head=head)
    assert not result.ok
    assert any("head_hash" in p for p in result.problems)


def test_expected_head_passes_on_intact_log():
    log = _log()
    assert log.verify(expected_head=log.head_hash).ok


# ---------- 영속 ----------
def test_jsonl_roundtrip_preserves_hashes():
    log = _log()
    loaded = AuditLog.load_jsonl(log.to_jsonl())
    assert loaded.head_hash == log.head_hash
    assert loaded.verify().ok


def test_write_and_read_file(tmp_path):
    log = _log()
    path = tmp_path / "audit.jsonl"
    log.write_jsonl(path)
    loaded = AuditLog.load_jsonl(path.read_text(encoding="utf-8"))
    assert len(loaded) == len(log)
    assert loaded.verify(expected_head=log.head_hash).ok
