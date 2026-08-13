# 골드 평가셋 (docs/eval/goldset/)

브리프 §11~12의 평가셋. **DEV / LOCKED / CHALLENGE 분리**, 결정적 채점, LOCKED §4(AI초안→사람확정).

## 파일

| 파일 | split | 용도 | 목표 | 현재 |
|---|---|---|---:|---:|
| `dev.jsonl` | DEV | 프롬프트·extractor 튜닝(개발 중 사용) | 40 | 24 (AI_DRAFT) |
| `locked.jsonl` | LOCKED | 최종 성능평가(튜닝 금지) | 40 | 0 (미착수) |
| `challenge.jsonl` | CHALLENGE | 예외·경계·충돌·모호 적대 평가 | 35 | 8 (AI_DRAFT) |

> 진척은 `python examples/demo_goldset.py` 또는 `format_coverage()`로 확인.

## 아이템 스키마 (브리프 §11 8필드 + 통제 메타)

각 줄은 하나의 JSON 아이템(jsonl):

- `question` — 질문/입력 · `gold_answer` — 골드 정답 · `category`(10종) · `policy_version`
- `source_doc_id` / `source_quote` — 근거 문서 + 원문 위치(verbatim) · `rule_id` · `expects_escalation`
- `scenario_input` — (선택) 구조화 borrower 입력 → **룰엔진으로 결정적 채점**(+ `expected_ltv`/`expected_status`)
- `answer_keywords` — (비-scenario) 정답 확인 키워드 · `claim_refs` — regulatory_facts claim id · `status`

## 채점은 결정적이다 (LOCKED §4 금지선)

**LLM이 LLM을 채점하지 않는다.** 두 경로 모두 deterministic:

1. **scenario 채점** — `scenario_input`을 룰엔진(`evaluate`)에 넣어 `expected_ltv`/`status`/escalation과 대조.
   룰엔진은 tc_generator 오라클로 독립 검증됨. 골드는 사람이 원문에서 확정 → 순환 아님(수용 테스트).
2. **grounding 채점** — `source_quote`가 원문에 verbatim 존재하는지 확인(근거 무결성 게이트).

현재 seed 실측: scenario 28/28(100%), Escalation Recall/Precision 100%, grounding 8/8(100%).

## LOCKED §4 — 전 항목 AI_DRAFT

모든 골드 정답은 `regulatory_facts.md`(현재 "AI추출·검수대기")에서 파생한 **AI 초안**이다.
`status: AI_DRAFT` 이며, **사람이 원문 대조로 확정(`HUMAN_CONFIRMED`)하기 전까지 최종 성능 보고에 쓰지 않는다.**
`claim_refs`로 각 아이템을 규제사실 claim(C01~)에 연결해 검수를 돕는다.

## 누수 방지 규율 (브리프 §12)

- `load_goldset()` 기본값은 **DEV만** 로드. LOCKED/CHALLENGE는 명시 요청 시에만(`splits=[...]`).
- LOCKED/CHALLENGE는 개발 중 튜닝 루프에 쓰지 않는다. 코어 완성 후 1회 실행.

## 다음 (사용자 확정 후)

1. seed 24 DEV + 8 CHALLENGE의 골드 정답 **도메인 검수·확정**(AI_DRAFT → HUMAN_CONFIRMED).
2. DEV 40 / LOCKED 40 / CHALLENGE 35 까지 확대 후 **freeze**(Phase 2 extractor 튜닝 전).
