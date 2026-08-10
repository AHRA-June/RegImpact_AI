# 01 — PROJECT STATE (살아있는 상태판)

> **이 파일은 프로젝트의 단일 진실 상태판이다.**
> 매 작업 세션 종료 시 갱신한다. 새 계정/새 세션은 이 파일부터 읽는다.
> 규칙: "지금 어디 / 다음 3개 액션 / 대기 중 결정 / 블로커"를 항상 최신으로 유지.

- **마지막 갱신:** 2026-08-10
- **갱신자:** Claude (기획 문서화 세션)
- **개발 브랜치:** `claude/portfolio-project-planning-9sip11`
- **전체 단계:** 🟡 기획/문서화 (코드 착수 전)
- **⚠️ 미해결 블로커:** 원격 푸시가 403(GitHub 연동에 쓰기 권한 없음). 로컬 커밋만 존재. 권한 부여 후 일괄 push 필요.

---

## 지금 어디까지 왔나 (DONE)

- [x] 프로젝트 브리프 v2 확정 (`docs/00_BRIEF.md`)
- [x] 브리프에 대한 분석 피드백 완료 (6개 핵심 지적 — 아래 "피드백 요약" 참고)
- [x] 문서 구조(handoff scaffold) 생성 및 커밋
  - README, 01_PROJECT_STATE, 02_DECISION_LOG, 03_OPEN_QUESTIONS, regulatory_facts(스켈레톤), metrics_spec(스켈레톤)

---

## 다음 액션 (NEXT — Phase 0 = `04_PLAN.md` 기준선)

> 실행 계획은 `docs/04_PLAN.md`(수직 슬라이스 우선, 총 9~10주). Phase 0 항목:

1. **`regulatory_facts.md` 확정** — 6·30 사실 claim(C01~C13) 원문 인용·URL·hash 검수. (사용자 도메인 검수 필요)
2. **`metrics_spec.md` 확정** — 깊은 4 dimension 지표 공식/분모/임계/high-risk 정의.
3. **룰엔진 규칙 명세 v0** 🟡진행중 — `05_RULE_SPEC.md` 스캐폴드 완료. **✍️ 사용자 도메인 값 입력 대기**(생애최초/정책대출 LTV, 예외 우선순위, 경과규정 날짜경계 — 05_RULE_SPEC.md §G).
4. **6·30 수기 Impact 정답(앵커)** — 사용자 확인 (§24-4). Walking Skeleton의 E2E 테스트 케이스.
- 이후 Phase 1(Walking Skeleton) 착수 → `04_PLAN.md` 참고.

> ⚠️ **선행 조건: 원격 push 권한.** 아래 블로커 해결 전까지 새 계정 인계 불가.

---

## 대기 중 결정 (BLOCKED ON USER)

`docs/03_OPEN_QUESTIONS.md`에 상세. 요약:
- ~~골드셋 규모~~ — **✅ 해결(2026-08-10): 100~120 확정, split DEV40/LOCKED40/CHALLENGE35**
- ~~Assurance 깊게 갈 4개 선택~~ — **✅ 해결(2026-08-10): 수를 줄임, 깊은 4 dimension + 로드맵**
- ~~주차 계획 재배열 + 총 기간~~ — **✅ 해결(2026-08-10): 수직 슬라이스 우선, 총 9~10주 (`04_PLAN.md`)**
- 룰엔진 규칙 명세(사용자 본인 작성 — LOCKED §4) — **미착수 (Phase 0)**
- 6·30 수기 Impact 정답(사용자 확인 필요 — 브리프 §24-4) — **미착수 (Phase 0)**

---

## 블로커 / 리스크

- **최대 리스크:** 6주·1인·LLM 첫 실무에 컴포넌트 11개 → E2E 관통 실패 위험. (수직 슬라이스로 완화)
- **계정 교체:** 2~3주 후 예정. 모든 상태는 저장소에 유지. 대화 메모리 의존 금지.

---

## 피드백 요약 (2026-08-10 세션에서 도출)

브리프에 대한 6개 핵심 지적 (LOCKED 원칙은 하나도 건드리지 않음 — 실행 순서·깊이·문서화 제안):

1. **범위 vs 시간** — "레이어별 완성"이 아니라 "수직 슬라이스 우선"으로 재배열. 2~3주 내 E2E 1회 관통.
2. **Assurance 11 → 깊은 4개** — 폭보다 깊이. 후보: ①Citation/Source grounding ②Exception+Grandfathering recall ③Temporal consistency ④Rule-regression.
3. **지표 공식·임계값 부재** — `metrics_spec.md`로 정의. Model Risk 직무의 급소.
4. **규제 사실 인용 무결성** — `regulatory_facts.md`. 실제 감독규정(사실) vs 은행 내규(모의 문서) 경계 명확화.
5. **골드셋 100~120 권장** — 질 우선, CHALLENGE 강화. (원안 150~200 유지도 가능)
6. **가치 제안 과대약속 경계** — "정확한 자동화"가 아니라 "검증 가능한 초안화 + 실패의 명시적 통제".

---

## 작업 로그 (append-only, 최신이 위)

- **2026-08-10** — 공문 3건(FSC·MOLIT 보도참고자료 PDF, 관계기관 FAQ HWP) Source Snapshot 저장(해시)+원문 추출(pymupdf/olefile). 룰 LTV 초안 자동 채움(05_RULE_SPEC C표), regulatory_facts에 원문 반영 및 브리프 교정 7건(🔺 생애최초70/서민60/유주택0/토허제7.5 등). LOCKED §4 운영방식("AI초안→사람확정") DECISION_LOG 기록(사용자 확인 대기).
- **2026-08-10** — 룰엔진 규칙 명세 착수: `05_RULE_SPEC.md` 스캐폴드(스키마·의사결정표 구조·경과규정 뼈대) 생성·커밋. LOCKED §4에 따라 ✍️ 도메인 값은 사용자 입력 대기.
- **2026-08-10** — Q3 해결: 주차 계획 수직 슬라이스 우선 재배열 + 총 9~10주 확정. `04_PLAN.md` 신규, DECISION_LOG·OPEN_QUESTIONS·README·STATE 반영, 로컬 커밋.
- **2026-08-10** — Q1 해결: 골드셋 100~120 확정(split DEV40/LOCKED40/CHALLENGE35, CHALLENGE 가중). DECISION_LOG·OPEN_QUESTIONS·metrics_spec·STATE 반영, 로컬 커밋.
- **2026-08-10** — Q2 해결: Assurance 체크 "수를 줄임" 결정(깊은 4 dimension + 로드맵/인프라). DECISION_LOG·OPEN_QUESTIONS·metrics_spec 반영, 로컬 커밋. (원격 push는 권한 대기)
- **2026-08-10** — 브리프 v2 검토, 분석 피드백 제공, handoff 문서 구조 생성·커밋. (기획 단계)
