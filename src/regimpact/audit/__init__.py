"""Audit Trail — append-only 해시 체인 감사로그(변조 탐지).

핵심 진입점:
    AuditLog(clock?)                         # append-only 로그, 시계 주입(결정론)
    log.record(action, target, details, actor)
    log.verify() -> VerifyResult             # 체인 무결성(변조 탐지)
    log.to_jsonl() / AuditLog.load_jsonl(text)
    Action.*                                 # 표준 파이프라인 이벤트 상수

거버넌스: 각 이벤트 해시가 직전 해시를 포함 → 사후 변조 시 체인이 깨져 verify가 잡는다.
의존성 0(hashlib·json), 결정론(시계 주입).
"""
from .log import GENESIS, Action, AuditEvent, AuditLog, VerifyResult

__all__ = [
    "AuditLog",
    "AuditEvent",
    "Action",
    "VerifyResult",
    "GENESIS",
]
