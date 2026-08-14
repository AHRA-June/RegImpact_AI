# 03 — OPEN QUESTIONS (사용자 확인 대기 항목)

> 진행하려면 사용자의 도메인 판단·확인이 필요한 항목들. 답이 나오면 `02_DECISION_LOG.md`로 옮기고 여기서 제거(또는 해결 표시).
> 최신이 위. 각 항목에 `[상태]` 표기.

---

## Q1. 골드 평가셋 규모 — `[✅ 해결 2026-08-10 · 빌드 2026-08-14 · 개봉·검수 2026-08-14]`
- **결정: 100~120으로 확정.** split = DEV 40 / LOCKED 40 / CHALLENGE 35 (총 115), CHALLENGE 카테고리 가중.
- **✅ 빌드(2026-08-14):** `docs/eval/gold_set/`, 정답=독립 오라클 유도, 누수 방지 규율.
- **✅ 최종 개봉(2026-08-14):** LOCKED/CHALLENGE 1회 개봉, 전체 115/115. `FINAL_EVAL.json`. 재튜닝 금지.
- **✅ 도메인 검수 v2(2026-08-14):** 115문항 전부 원문 grounding·수치 일관성 검증 후 사람 확정(CONFIRMED 92·escalation 10·precedence 13). `REVIEW_v2.json`·`REVIEW_REPORT.md`. **→ Q1 완전 종료.**

## Q2. Assurance 11개 체크 중 "깊게 구현할 4개" — `[✅ 해결 2026-08-10]`
- **결정: 수를 줄임.** 깊게 정량 측정하는 4개 dimension + 나머지 로드맵/인프라. 상세는 `02_DECISION_LOG.md` 2026-08-10 항목.
- 깊게: ①Source Grounding & Citation ②Change & Exception Completeness ③Temporal/Policy-Version Consistency ④Rule Regression & Conflict.
- 레이어는 유지(LOCKED §0-6 정합), 구현 깊이만 차등.
- **잔여 여백:** escalation을 4번 대신 승격할지 여부만 열려 있음(현재는 위 4개 확정).

## Q3. 주차 계획 재배열(수직 슬라이스 우선) 수용 여부 — `[✅ 해결 2026-08-10]`
- **결정: 재배열 수용 + 총 9~10주.** 상세 계획 `docs/04_PLAN.md`, 결정 근거 `02_DECISION_LOG.md`.
- Phase 0(W1)/1(W2~3 Walking Skeleton)/2(W4~6)/3(W7~8 코어완성)/스트레치(W9~10).
- LOCKED §0-5 정합성 확인 완료(골드셋 freeze는 실제 튜닝 전, skeleton은 앵커 1건 스모크 테스트).

## Q4. 룰엔진 규칙 명세 — `[✅ v1 확정 2026-08-10]`
- **확정:** `05_RULE_SPEC.md` v1 — LTV 값(FAQ Q2), precedence(E, P0~P7), 경과규정(F), 알고리즘(H). 정책대출→Discovery. 코어=LTV만.
- **다음:** deterministic 엔진 코드 + 테스트 하네스 구현(Phase 1). 상세 이력은 `02_DECISION_LOG.md`.
- (구) 진행 이력 아래 보존:
- LOCKED §4: 규칙 로직은 LLM이 생성하지 않음. 사용자 본인이 규칙 명세를 작성해야 함.
- **스캐폴드 완료:** `docs/05_RULE_SPEC.md` (입력/출력 스키마, 의사결정표 구조, reason_codes 라벨, 경과규정 뼈대).
- **사용자 입력 대기(✍️):** 05_RULE_SPEC.md의 미결 질문 G섹션 —
  - Q-스키마(입력 필드/처분조건부 표현), Q-지역(status 세분화 여부), Q-값1(생애최초·정책대출 LTV),
    Q-값2(비처분 1주택), Q-우선순위(복합조건), Q-경과1~3(날짜경계·증빙·토허제).
- 값 확정 후 Claude가 deterministic 코드 + 테스트 하네스(🔧) 구현.
- **2026-08-10 업데이트:** 공문 3건 추출로 LTV 초안 자동 채움(🤖, `05_RULE_SPEC` C표). "AI초안→사람확정" 워크플로 ✅ 채택.
  - **사용자 최종 확정 대기(도메인 검수):** ①규제사실 교정 7건(`regulatory_facts` 🔺) ②LTV 초안값 ③예외 우선순위 ④경과규정 날짜경계·계약금 일부납부 ⑤토허제(G3) 룰엔진 포함 여부.

## Q5. 6·30 수기 Impact 정답 — `[미착수, 사용자 확인 필요]`
- 브리프 §24-4: 메인 시나리오 수기 정답을 사용자에게 확인받을 것.
- `regulatory_facts.md` 확정 후 진행.

## Q6. 규제 사실 검수 — `[대기]`
- `regulatory_facts.md`의 각 claim(LTV 수치, 경과규정 컷오프, 예외 조건 등)을 사용자가 원문과 대조 검수.
- 실제 감독규정(사실 인용) vs 은행 내규(공개 규정 기반 모의 문서)의 경계 확정.

## Q7. 기술 스택 (ADJUSTABLE) — `[대기, 착수 시 결정]`
- LLM 제공자/모델, RAG/Agent 프레임워크, Vector DB/저장소, 로컬 DB, UI(Streamlit 수준 권장).
- 코드 착수 시점에 결정. 지금 확정 불필요.

## Q8. 명세 내부 상충: 유주택 + 생애최초 처리 — `[대기, 도메인 확인 필요]`
- **발견 경위:** TC Generator 충돌 케이스(CFL-04) 작성 중 `05_RULE_SPEC` 내부 두 서술이 상충함을 확인.
  - `§E` 주석: "유주택 AND 생애최초 = 논리상 불가(생애최초=세대원 전원 무주택 이력). **데이터 충돌 시 → `NEEDS_HUMAN_REVIEW`.**"
  - `§H` 의사코드("엔진 구현의 기준"): P4(유주택 비처분)에서 **0%로 short-circuit** → P5(생애최초)에 도달하지 않음.
- **현재 채택(잠정):** `§H`가 "엔진 구현의 기준"으로 명시되어 있으므로 **0%(§H)** 를 권위 기준으로 두고,
  룰엔진·오라클·회귀 모두 0%로 일치. CFL-04 케이스에 `spec_note`로 이 모호성을 표면화.
- **사용자 판단 필요:** 실제 운영에서 house_count≥1 & first_home_buyer=True 라는 **모순 입력**이 들어오면
  ①§H대로 0% 자동판정할지, ②§E대로 데이터 무결성 오류로 보고 `NEEDS_HUMAN_REVIEW`로 escalate할지.
  후자를 택하면 엔진에 "입력 모순 감지 → escalation" 분기를 추가하고 오라클·회귀도 함께 갱신.
