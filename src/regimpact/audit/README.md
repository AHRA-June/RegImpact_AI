# Audit Trail — tamper-evident 해시 체인 감사로그

단순 로그가 아니라 **변조가 드러나는** 로그다. 각 항목의 해시가 직전 항목의 해시를
포함해 계산되므로, 어느 항목을 사후에 고치면 이후 체인이 전부 깨져 `verify()`가 잡는다.

의존성 0(`hashlib`·`json`), 시계 주입식이라 테스트에서 결정적이다.

```python
from regimpact.audit import AuditLog, Action

audit = AuditLog()
audit.record(Action.EXTRACTION, "FSC_20260630", {"changes": 75})
audit.record(Action.PROPOSAL_CREATED, "MORTGAGE_LTV", {"status": "NEEDS_REVIEW"})

audit.verify().ok        # 체인 무결성
audit.head_hash          # 로그 바깥에 남겨둘 앵커
audit.write_jsonl(path)
```

파이프라인 배선: `examples/demo_impact_e2e.py` 11단계.

## 무엇을 잡고 무엇을 못 잡나

| 변조 | 탐지 | 어떻게 |
|---|---|---|
| 항목 내용 수정 | ✅ | `entry_hash` 재계산 불일치 |
| 항목 순서 바꾸기 | ✅ | `prev_hash` 연결 끊김 |
| 중간 항목 삭제 | ✅ | 〃 |
| 수정 + 해시 재계산(은폐 시도) | ✅ | 다음 항목이 옛 해시를 가리킴 |
| **끝에서부터 잘라내기** | ⚠️ **`verify()` 단독으로는 불가** | 잘린 뒤에도 유효한 체인이다 |

마지막 줄이 이 구조의 진짜 한계다. 숨기지 않고 적는다 — 그래서
`verify(expected_head=...)` 를 둔다. 감사로그를 신뢰하려면 **head 해시가 로그 바깥**
(커밋 메시지·리포트·별도 저장소)에 남아 있어야 한다. 이건 구현 미비가 아니라
append-only 로그의 구조적 성질이고, 실무의 감사추적도 같은 이유로 외부 앵커를 둔다.

`tests/test_audit.py` 가 위 표의 각 행을 실제 변조 시나리오로 재현해 고정한다.
