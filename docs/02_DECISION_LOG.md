# 02 — DECISION LOG (의사결정 이력)

> 프로젝트의 결정을 시간순으로 기록한다. **LOCKED 원칙 변경은 반드시 여기 남기고 사용자 승인을 받는다.**
> 형식: 날짜 · 결정 · 이유 · (변경이면) 이전값 · 상태(제안됨/승인됨/보류).
> 최신이 위.

---

## LOCKED 원칙 (브리프 §0 — 정체성, 임의 변경 금지)

아래는 확정된 정체성 결정이다. 변경하려면 먼저 사용자에게 이유를 설명하고 승인받은 뒤 이 로그에 기록한다.

1. E가 제품이고 A가 신뢰의 기반이다. (E=규제 변경 영향분석, A=Assurance)
2. 챗봇이 아니라 검증 가능한 의사결정 지원 시스템을 만든다.
3. 주택구입목적 주담대 규제의 수직 슬라이스를 유지한다.
4. 실행 가능한 룰엔진의 규칙 로직은 LLM이 생성하지 않는다.
5. 평가셋을 개발보다 먼저 만들고, DEV / LOCKED TEST / CHALLENGE를 분리한다.
6. Assurance Layer와 Test Case Generator는 일정이 밀려도 자르지 않는다.
7. 임팩트 매트릭스의 시간축(Phase)은 삭제하지 않는다.
8. 실제 회사 내부문서·고객데이터를 사용하지 않는다.
9. LLM은 금융 의사결정을 직접 실행하지 않고 변경안·영향분석·검토자료를 제안한다.
10. 자동화 범위보다 검증 가능성과 추적 가능성을 우선한다.

**현재까지 LOCKED 변경 이력: 없음.**

---

## 결정 로그

### 2026-08-10 · Assurance 체크 "구현 깊이" 차등 (수를 줄임) · ✅ 승인됨
- **결정:** Assurance Layer의 11개 체크를 전부 동일 깊이로 구현하지 않는다.
  **정량 측정하는 4개 dimension**만 깊게 가고, 나머지는 "정의+루브릭+소규모 예시(로드맵)"로 둔다.
  - **① 깊게 정량 측정 (4):**
    1. Source Grounding & Citation → Citation Correctness, Unsupported Claim Rate, Source Contradiction Rate
    2. Change & Exception Completeness → Change Completeness, Exception Recall, Grandfathering Recall
    3. Temporal / Policy-Version Consistency → Policy-version Consistency, Effective-date Accuracy
    4. Rule Regression & Conflict → Rule-regression Pass Rate, Conflict/Boundary-case Pass Rate
  - **② 유지하되 가볍게 (로드맵):** Human Escalation Evaluation (Escalation Recall/Precision, High-risk Miss Rate)
  - **③ 항상 켜지는 인프라 (metric 아님):** Audit trail, Approval status field
- **이유:** 6주·1인·LLM 첫 실무에 11개를 모두 깊게 구현하면 전부 얕은 스텁이 되어 오히려 핵심(A)이 약해 보임. 폭보다 깊이 우선.
- **LOCKED 정합성:** 브리프 §0-6 "Assurance Layer는 자르지 않는다"와 충돌하지 않음.
  **레이어(컴포넌트)와 아키텍처상 위치는 그대로 유지**하고, 개별 체크의 *구현 깊이*만 차등한다. 레이어를 제거·삭제하는 것이 아님. → LOCKED 변경 아님.
- **미확정 여백:** "깊게 갈 4개"의 구체 조합은 사용자가 escalation을 4번 대신 승격하고 싶으면 조정 가능. (현재는 위 4개로 확정)
- **관련 파일:** `docs/metrics_spec.md`(깊이 태그 반영), `docs/03_OPEN_QUESTIONS.md` Q2 해결.

### 2026-08-10 · handoff 문서 구조 채택 · ✅ 승인됨
- **결정:** README + `docs/`(00_BRIEF, 01_PROJECT_STATE, 02_DECISION_LOG, 03_OPEN_QUESTIONS, regulatory_facts, metrics_spec, prd/) 구조로 프로젝트 상태를 저장소에 유지.
- **이유:** 2~3주 후 Claude 계정 교체 예정. 대화 메모리는 계정 넘어가면 소실되므로 모든 상태를 git에 두어 무손실 인계.
- **영향:** LOCKED 무관 (문서화 방식). ADJUSTABLE 범위 — 폴더 구조.

### 2026-08-10 · 브리프 v2를 기반 컨텍스트로 확정 · ✅ 승인됨
- **결정:** 사용자가 제공한 브리프 v2를 프로젝트의 기반 문서로 채택, 원본을 `docs/00_BRIEF.md`에 보존.
- **이유:** PRD·개발의 기반 컨텍스트.

---

## 제안됨 / 미확정 (사용자 승인 대기)

> 아래는 기획 세션의 제안. **아직 결정 아님.** 확정되면 위 로그로 이동.

- **[제안] 주차 계획을 수직 슬라이스 우선으로 재배열** — §18 순서만 변경(레이어별→E2E 관통 우선). LOCKED 미변경(실행 순서). 상태: 보류.
- **[제안] 골드셋 100~120으로 축소** — ADJUSTABLE(§0, 총 150~200 범위는 조정 가능 명시). 상태: 보류.
