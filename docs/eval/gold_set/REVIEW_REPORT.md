# Gold Set 도메인 검수 보고 (v2)

> version v2 · 검수일 2026-08-14 · 검수자 도메인 검수 — 사람 확정(authority: 사용자, LOCKED §4 'AI초안→사람확정')

v1 정답은 독립 명세 오라클(§H)에서 유도됐다(AI초안). 본 검수는 각 정답을 **원문 규제사실의 실제 인용**에 grounding하고, 수치 정답이 인용이 말하는 값과 일치하는지 결정론적으로 검증한 뒤(불일치 시 검수 실패) 확정한다. **입력·정답은 변경하지 않는다** — 오라클 유도값이 원문과 일치함을 확인하는 것이 검수의 결론이다.

## 확정 요약

| 상태 | 의미 | 건수 |
|---|---|---:|
| CONFIRMED | 원문 인용에 직접 grounding·수치 일치 | 92 |
| CONFIRMED_ESCALATION | 원문 기준선 부재 → escalation이 정답 | 10 |
| CONFIRMED_PRECEDENCE | §H 우선순위로 충돌 해소 | 13 |
| **합계** | | **115** |

모든 115문항이 확정되었다. 미해결(flag)로 남은 항목은 없으며, escalation·precedence 항목도 각각 '원문 기준선 부재'와 '§H 우선순위(DECISION_LOG 2026-08-10 확정)'라는 문서화된 근거로 확정된다.

## split별 확정 상태

| split | CONFIRMED | CONFIRMED_ESCALATION | CONFIRMED_PRECEDENCE |
|---|---|---|---|
| dev | 40 | 0 | 0 |
| locked | 40 | 0 | 0 |
| challenge | 12 | 10 | 13 |

## 방법

- **Grounding:** 각 근거코드를 원문 문서·verbatim 인용에 매핑(FSC·MOLIT·FAQ / regulatory_facts).
- **수치 일관성:** 정답 LTV = 인용이 말하는 LTV 여야 함(예: 40% 정답 ↔ 'LTV(70→40%)'). 불일치 시 예외.
- **escalation:** 원문에 기준선이 없는 케이스는 값을 지어내지 않고 사람 검토가 정답 — 이를 확정.
- **precedence:** 복수 조건 충돌은 §H 우선순위로 해소되며, 해소 결과의 수치도 원문과 대조.
- **권한:** 확정의 최종 권한은 사람(사용자)이다(LOCKED §4). 본 문서는 그 검수의 근거·결과 기록이다.

## 재현

```bash
python tools/review_gold_set.py     # 검수 재생성
python examples/demo_gold_set.py    # (참고) DEV 회귀
```

문항별 grounding·rationale 전체는 `REVIEW_v2.json` 참조.
