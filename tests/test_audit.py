"""Audit Trail 테스트 — append-only 해시 체인·변조 탐지·영속·결정론.

핵심: ①체인 연결·verify OK ②사후 변조 시 verify FAIL(tamper-evident) ③JSONL 왕복
④시계 주입으로 결정론 ⑤제네시스·seq 규칙.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from regimpact.audit import GENESIS, Action, AuditLog  # noqa: E402


def _clock():
    n = {"t": 0}

    def c():
        n["t"] += 1
        return f"2026-01-01T00:00:{n['t']:02d}+00:00"
    return c


def _sample_log() -> AuditLog:
    log = AuditLog(clock=_clock())
    log.record(Action.SOURCE_INGESTED, "DOC", {"sha256": "abc"})
    log.record(Action.EXTRACTION, "POL", {"changes": 3})
    log.record(Action.HUMAN_REVIEW, "POL::R", {"decision": "APPROVED"}, actor="human:kim")
    return log


def test_chain_links_and_verifies():
    log = _sample_log()
    assert len(log) == 3
    assert log.events[0].prev_hash == GENESIS
    # 각 이벤트의 prev_hash = 직전 entry_hash
    assert log.events[1].prev_hash == log.events[0].entry_hash
    assert log.events[2].prev_hash == log.events[1].entry_hash
    assert log.verify().ok


def test_seq_is_monotonic():
    log = _sample_log()
    assert [e.seq for e in log.events] == [0, 1, 2]


def test_tamper_details_detected():
    """저장·로드 후 한 이벤트의 details를 변조하면 verify가 잡는다."""
    import json
    log = _sample_log()
    lines = log.to_jsonl().splitlines()
    d = json.loads(lines[2])
    d["details"]["decision"] = "REJECTED"     # 승인→반려 위조
    lines[2] = json.dumps(d, ensure_ascii=False)
    tampered = AuditLog.load_jsonl("\n".join(lines))
    v = tampered.verify()
    assert not v.ok
    assert any("변조" in p or "seq[2]" in p for p in v.problems)


def test_tamper_reorder_detected():
    """이벤트 순서를 바꾸면 prev_hash 연결이 끊겨 verify 실패."""
    log = _sample_log()
    lines = log.to_jsonl().splitlines()
    lines[1], lines[2] = lines[2], lines[1]
    v = AuditLog.load_jsonl("\n".join(lines)).verify()
    assert not v.ok


def test_jsonl_roundtrip_preserves_and_verifies():
    log = _sample_log()
    restored = AuditLog.load_jsonl(log.to_jsonl())
    assert [e.entry_hash for e in restored.events] == [e.entry_hash for e in log.events]
    assert restored.verify().ok


def test_deterministic_with_injected_clock():
    """동일 시계·동일 입력 → 동일 해시(재현 가능)."""
    a = _sample_log()
    b = _sample_log()
    assert a.head_hash == b.head_hash


def test_head_hash_changes_on_append():
    log = _sample_log()
    h0 = log.head_hash
    log.record(Action.REPORT_GENERATED, "rpt")
    assert log.head_hash != h0
    assert log.verify().ok
