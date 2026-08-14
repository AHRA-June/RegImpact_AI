# Gold Set — 6·30 규제 변경 평가셋 (freeze)

> version v1 · freeze 2026-08-14 · 총 115문항

브리프 §11~12. 각 문항: 입력 / 골드 정답 / 근거 문서·위치 / 카테고리 / human escalation 기대 /
정책 버전 / rule_id. **정답(expected)은 독립 명세 오라클(tc_generator.oracle)에서 유도** —
rule_engine 과 독립 코드 경로이므로 엔진 회귀가 tautology가 되지 않는다(LOCKED §4).

## Split (누수 방지 §12)

| split | 규모 | 용도 | 상태 |
|---|---:|---|---|
| DEV | 40 | 개발 중 상시 회귀·튜닝 | 개방 |
| LOCKED | 40 | 최종 성능평가 | **sealed** (Phase 3 1회) |
| CHALLENGE | 35 | 예외·경계·충돌·모호 적대적 평가 | **sealed** (Phase 3 1회) |

`regimpact.eval.load_split('locked'/'challenge')` 는 `unlock=True` 없이는 열리지 않는다.
개발 중 튜닝·상시 회귀는 `run_gold_regression('dev')` 만 사용한다.

## 카테고리 분포

| category | DEV | LOCKED | CHALLENGE |
|---|---:|---:|---:|
| AMBIGUOUS | 0 | 0 | 10 |
| BORROWER_TYPE | 5 | 4 | 0 |
| CONFLICT | 0 | 0 | 13 |
| EFFECTIVE_DATE | 3 | 3 | 6 |
| EXCEPTION | 8 | 7 | 0 |
| GRANDFATHERING | 6 | 5 | 6 |
| LOAN_PURPOSE | 7 | 7 | 0 |
| NORMAL | 8 | 8 | 0 |
| NO_CHANGE | 0 | 3 | 0 |
| REGION | 3 | 3 | 0 |

## 재현

```bash
python tools/build_gold_set.py     # 결정론적 재생성
python examples/demo_gold_set.py   # DEV 회귀 출력
```

## 무결성

MANIFEST.json 에 split별 sha256. LOCKED/CHALLENGE 개봉은 최종 보고 시 1회.
