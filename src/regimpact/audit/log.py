"""정식 감사추적(Audit Trail) — append-only + 해시 체인(변조 탐지).

단순 로그가 아니라 **tamper-evident** 감사로그다. 각 항목의 해시는 직전 항목의 해시를 포함해
계산되므로(hash chain), 어느 항목을 사후에 변조하면 이후 체인 전체가 깨져 `verify()`가 잡는다.
금융권 모델검증/거버넌스의 감사추적 요건(무결성·부인방지·재현)을 경량으로 충족한다.

설계(프로젝트 원칙 준수):
    - 의존성 0: 표준 라이브러리(hashlib·json)만.
    - 결정론: 시각은 주입식 clock. 테스트는 고정 시계, 실사용은 UTC 실시간.
    - 영속: JSONL(한 줄=한 이벤트). 로드 시 저장된 해시를 보존하고 verify로 무결성 확인.

한계 — 해시 체인이 혼자 못 잡는 것:
    중간 항목을 고치거나 지우면 체인이 끊겨 잡힌다. 그러나 **끝에서부터 잘라내면**
    남은 부분은 그 자체로 유효한 체인이라 `verify()` 만으로는 알 수 없다.
    그래서 `verify(expected_head=...)` 로 외부에 기록해 둔 head 해시와 대조할 수 있게 했다.
    감사로그를 신뢰하려면 head 해시가 로그 **바깥**(커밋 메시지·리포트·별도 저장소)에
    남아 있어야 한다. 이건 구현의 미비가 아니라 append-only 로그의 구조적 성질이다.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Callable, Optional

GENESIS = "0" * 64   # 제네시스 prev_hash


# 표준 액션(파이프라인 이벤트) — 문자열 상수
class Action:
    SOURCE_INGESTED = "SOURCE_INGESTED"
    EXTRACTION = "EXTRACTION"
    IMPACT_ANALYZED = "IMPACT_ANALYZED"
    PROPOSAL_CREATED = "PROPOSAL_CREATED"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    REGRESSION_RUN = "REGRESSION_RUN"
    ASSURANCE_SCORED = "ASSURANCE_SCORED"
    REPORT_GENERATED = "REPORT_GENERATED"


@dataclass(frozen=True)
class AuditEvent:
    seq: int
    timestamp: str
    actor: str                 # "system" | "human:<name>"
    action: str
    target: str
    details: dict = field(default_factory=dict)
    prev_hash: str = GENESIS
    entry_hash: str = ""

    def body(self) -> dict:
        """해시 계산 대상(해시 필드 제외)."""
        return {
            "seq": self.seq, "timestamp": self.timestamp, "actor": self.actor,
            "action": self.action, "target": self.target, "details": self.details,
        }


def _canonical(body: dict) -> str:
    return json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def _hash(prev_hash: str, body: dict) -> str:
    return hashlib.sha256((prev_hash + _canonical(body)).encode("utf-8")).hexdigest()


def _default_clock() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


@dataclass
class VerifyResult:
    ok: bool
    problems: list[str] = field(default_factory=list)


class AuditLog:
    """append-only 해시 체인 감사로그."""

    def __init__(self, clock: Optional[Callable[[], str]] = None):
        self._events: list[AuditEvent] = []
        self._clock = clock or _default_clock

    @property
    def events(self) -> list[AuditEvent]:
        return list(self._events)

    def __len__(self) -> int:
        return len(self._events)

    @property
    def head_hash(self) -> str:
        return self._events[-1].entry_hash if self._events else GENESIS

    def record(
        self,
        action: str,
        target: str,
        details: Optional[dict] = None,
        actor: str = "system",
        timestamp: Optional[str] = None,
    ) -> AuditEvent:
        """이벤트를 append하고 해시 체인을 잇는다(반환: 생성된 이벤트)."""
        seq = len(self._events)
        prev = self.head_hash
        body = {
            "seq": seq, "timestamp": timestamp or self._clock(), "actor": actor,
            "action": action, "target": target, "details": details or {},
        }
        ev = AuditEvent(**body, prev_hash=prev, entry_hash=_hash(prev, body))
        self._events.append(ev)
        return ev

    def verify(self, expected_head: Optional[str] = None) -> VerifyResult:
        """체인 무결성 검증. seq 연속·prev 연결·해시 재계산 일치.

        `expected_head` 를 주면 마지막 해시까지 대조한다 — 이것 없이는 **끝에서부터
        잘라낸 로그**를 구분할 수 없다(잘린 뒤에도 그 자체로 유효한 체인이므로).
        """
        problems: list[str] = []
        prev = GENESIS
        for i, e in enumerate(self._events):
            if e.seq != i:
                problems.append(f"seq[{i}]: expected {i}, got {e.seq}")
            if e.prev_hash != prev:
                problems.append(f"seq[{i}]: prev_hash 불일치(체인 끊김)")
            recomputed = _hash(e.prev_hash, e.body())
            if recomputed != e.entry_hash:
                problems.append(f"seq[{i}]: entry_hash 불일치(변조 탐지)")
            prev = e.entry_hash
        if expected_head is not None and prev != expected_head:
            problems.append(
                "head_hash 불일치 — 로그가 끝에서부터 잘렸거나 다른 로그다 "
                f"(기대 {expected_head[:12]}…, 실제 {prev[:12]}…)"
            )
        return VerifyResult(ok=not problems, problems=problems)

    # --- 영속 ---
    def to_jsonl(self) -> str:
        return "\n".join(json.dumps(asdict(e), ensure_ascii=False) for e in self._events)

    def write_jsonl(self, path) -> None:
        from pathlib import Path
        Path(path).write_text(self.to_jsonl() + "\n", encoding="utf-8")

    @classmethod
    def load_jsonl(cls, text: str) -> "AuditLog":
        """저장된 JSONL을 로드(해시 보존). 무결성은 verify()로 확인한다."""
        log = cls()
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            log._events.append(AuditEvent(
                seq=d["seq"], timestamp=d["timestamp"], actor=d["actor"],
                action=d["action"], target=d["target"], details=d.get("details", {}),
                prev_hash=d["prev_hash"], entry_hash=d["entry_hash"],
            ))
        return log
