# 03 — OPEN QUESTIONS (사용자 확인 대기 항목)

> 진행하려면 사용자의 도메인 판단·확인이 필요한 항목들. 답이 나오면 `02_DECISION_LOG.md`로 옮기고 여기서 제거(또는 해결 표시).
> 최신이 위. 각 항목에 `[상태]` 표기.

---

## Q1. 골드 평가셋 규모 — `[✅ 해결 2026-08-10]`
- **결정: 100~120으로 확정.** split = DEV 40 / LOCKED 40 / CHALLENGE 35 (총 ~115), CHALLENGE 카테고리 가중.
- 상세는 `02_DECISION_LOG.md` 2026-08-10 항목, `metrics_spec.md` "평가셋 규모·split" 섹션.
- **잔여:** CHALLENGE 내 카테고리별 세부 건수는 골드셋 설계 단계에서 도메인 검수로 확정.

## Q2. Assurance 11개 체크 중 "깊게 구현할 4개" — `[✅ 해결 2026-08-10]`
- **결정: 수를 줄임.** 깊게 정량 측정하는 4개 dimension + 나머지 로드맵/인프라. 상세는 `02_DECISION_LOG.md` 2026-08-10 항목.
- 깊게: ①Source Grounding & Citation ②Change & Exception Completeness ③Temporal/Policy-Version Consistency ④Rule Regression & Conflict.
- 레이어는 유지(LOCKED §0-6 정합), 구현 깊이만 차등.
- **잔여 여백:** escalation을 4번 대신 승격할지 여부만 열려 있음(현재는 위 4개 확정).

## Q3. 주차 계획 재배열(수직 슬라이스 우선) 수용 여부 — `[✅ 해결 2026-08-10]`
- **결정: 재배열 수용 + 총 9~10주.** 상세 계획 `docs/04_PLAN.md`, 결정 근거 `02_DECISION_LOG.md`.
- Phase 0(W1)/1(W2~3 Walking Skeleton)/2(W4~6)/3(W7~8 코어완성)/스트레치(W9~10).
- LOCKED §0-5 정합성 확인 완료(골드셋 freeze는 실제 튜닝 전, skeleton은 앵커 1건 스모크 테스트).

## Q4. 룰엔진 규칙 명세 — `[🟡 진행 중 2026-08-10: 스캐폴드 완료, ✍️ 도메인 값 대기]`
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
