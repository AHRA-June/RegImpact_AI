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

### 2026-08-18 · 지역을 전국 레지스트리로 교체 + 미등록 코드는 escalation · ✅ 채택
- **문제:** 지역 버전 테이블에 6·30 신규 3곳만 있었고, 나머지는 `resolve_region_status`가 조용히
  `NON_REGULATED`로 반환했다. 그 결과 **이미 투기과열지구인 서울 강남구가 비규제 기준선 70%로 판정**됐다.
  (사용자 지적으로 발견 — "서울 강남은 원래 40 제한 걸려야 되는 거 아냐?")
- **결정 1 — 전국 레지스트리.** `src/regimpact/regions.py`에 전국 241개 시·군·구를 시점 버전과 함께 등록.
  권위 근거는 **MOLIT 보도자료 참고2 「투기과열지구 및 조정대상지역 현황」** 표(추가지정 전 서울 25·경기 12 /
  후 경기 15). 강남4구는 조정('16.11.3) → 투기과열('17.8.3) 2구간으로 모델링(DTI 참고값이 지정유형에 걸림).
- **결정 2 — 미등록 코드는 `UNKNOWN` → `NEEDS_HUMAN_REVIEW`.** 조용한 기본값이 틀린 답을 정답처럼 내놓았다.
  이제 레지스트리에 없는 코드는 추측하지 않고 사람에게 넘긴다(`UNKNOWN_REGION`). LOCKED §10 정합.
- **결정 3 — 열거주의 프레이밍.** 권위를 갖는 사실은 **규제지역 목록과 효력일**뿐이다. 나머지 시·군·구 목록은
  선택 편의용이며 판정에 영향을 주지 않는다. 따라서 비규제 목록에 누락이 있어도 규제 판정은 틀리지 않는다.
- **결정 4 — 오라클 독립성 계약을 심볼 단위로 정밀화.** 종전엔 오라클이 `regions` 모듈 전체를 import 금지했다.
  전국 241개 지역표를 오라클에 다시 옮겨 적는 것은 검증가치가 아니라 **전사 오류만 늘린다**. 그래서
  **데이터(REGISTRY)는 공유하고 시점 해석 로직만 독립 재구현**한다(엔진은 구간 양끝 검사, 오라클은
  "as_of 이하인 마지막 버전" 선택 — 알고리즘이 달라 경계 오차가 disagreement로 드러남).
  대신 데이터 자체는 **공문 원문의 지역 수와 대조하는 테스트**(`tests/test_regions.py`)로 검증한다.
  `resolve_region_status`(엔진 해석 함수) import는 여전히 금지이며 테스트가 강제한다.
- **결정 5 — 웹도 같은 표를 읽는다.** 샌드박스 JS는 지역표를 옮겨 적지 않고 `tools/export_fixtures.py`가
  내보낸 레지스트리를 읽는다. 추가로 **전국 241곳 × 7개 시점**의 Python 판정을 프로브 표로 고정해
  브라우저·CI 양쪽에서 대조한다(`node tools/verify_js_port.mjs`).
- **부수 발견 (임의 변경하지 않고 Q로 표면화):** 실제 지역이 생기며 도달 가능해진 경로에서 명세 상충 2건 발견.
  **Q9** 비규제 유주택 60%(MOLIT 참고1) 채택 여부, **Q10** 수도권 비규제 다주택 0%(FSC p2 / §C-1b R6) vs
  §H의 P3 위치. LOCKED §4에 따라 룰 값을 임의로 바꾸지 않고 회귀 케이스 `CFL-06`·`CFL-07`로 현재 동작을
  고정한 뒤 `spec_note`로 표면화했다.
- **회귀:** 43 케이스 Pass Rate 100%(REGION 분류 11건 신설), pytest 71 통과.

### 2026-08-18 · 온라인 테스트 환경을 2종으로 이원화 · ✅ 채택
- **결정:** 사용자가 온라인에서 직접 조작할 수 있는 표면을 **정적 샌드박스 + Streamlit 앱** 두 개로 나눈다.
  - `web/sandbox.html` — 엔진 JS 포팅, 자체완결 1파일, 서버 불필요. 링크 하나로 즉시 시연·모바일.
  - `app/streamlit_app.py` — 저장소 Python 엔진 그대로, LLM(Extractor) 실행 가능. 포트폴리오 실배포 URL.
- **이유:** 두 표면의 목적이 다르다. 전자는 "지금 당장 클릭해서 보여줄 수 있는가"(배포·계정·키 불필요),
  후자는 "실제 시스템이 도는가"(엔진 동일성·지표 산출·LLM). 하나로 합치면 둘 중 하나를 잃는다.
- **감수한 비용과 그 통제:** JS 포팅본은 Python 엔진과 **어긋날 수 있다(드리프트)**. 이를 문서로 부탁하지 않고
  구조로 막았다 — 골든 기대값을 사람이 적지 않고 `tools/export_fixtures.py`가 **실제 엔진을 돌려** 생성하고,
  ①페이지가 로드 시 브라우저 계산값과 전 케이스 대조해 불일치 시 배지를 붉게 바꾸며
  ②`node tools/verify_js_port.mjs`가 커밋 전 헤드리스로 같은 대조를 한다(현재 30/30).
  **룰 변경 시 재빌드가 필수**임을 `docs/ui/DEPLOY.md`에 명시.
- **LOCKED 정합:** §4(규칙 로직 LLM 미생성) 유지 — JS 포팅본도 확정 명세 §H의 구현이며 값은 명세에서 온다.
  §10(검증가능성·추적가능성 우선) 강화 — 우선순위 트레이스로 "왜 이 판정인가"가 화면에서 추적된다.
- **판정 주체 단일화:** Streamlit의 우선순위 트레이스는 규칙을 다시 구현하지 않고 **엔진 출력(reason_code·rule_id)을
  단계 라벨로 역매핑**한다. 엔진이 유일한 판정 주체라는 원칙을 UI가 깨지 않게 하기 위함.
- **사용자 액션 필요:** Streamlit Community Cloud 배포와 `ANTHROPIC_API_KEY` Secrets 등록은 계정 소유자만 가능.

### 2026-08-10 · RegChange Extractor 구현 + LLM 선택 · ✅ 완료
- **LLM:** Anthropic Claude, 기본 `claude-opus-5` (ADJUSTABLE §0 — 비용/성능 따라 교체 가능). structured output(`output_config.format`).
- **아키텍처:** LLM 호출 주입 가능(injectable) → API 키·비용 없이 오프라인 테스트. `src/regimpact/extractor/`.
- **첫 Assurance 지표(A):** ①Citation grounding(인용의 원문 verbatim 존재를 deterministic 검증 → Citation Correctness/Unsupported Claim Rate, **LLM이 LLM 채점 회피**) ②Gold 대조(`docs/eval/regchange_gold_6_30.json` → Change Completeness/Exception Recall).
- **테스트 28개 통과**(룰엔진 23 + extractor 5, 환각 탐지 포함). LOCKED 정합: 추출=초안(§9), 룰엔진=독립 기준(§4), 골드=사람 authoring(§0-5).

### 2026-08-10 · LOCKED §4 운영방식: "AI 초안 → 사람 확정" + 검증 독립성 · ✅ 승인됨(사용자 채택)
- **배경:** 사용자가 "공문 업로드 → AI가 룰 명세 1차 초안" 플로우를 원함(제품 dogfooding).
- **결정:** 룰 명세를 AI가 공문에서 **1차 추출(초안)** → **사용자가 원문 대조로 최종 확정(authority)**. 확정 전 초안은 authority 없음. (2026-08-10 사용자 "채택".)
- **LOCKED §4 정합성:** §4의 취지는 "LLM이 검증 기준점을 생성해 순환검증이 되는 것"을 막는 데 있음. 따라서:
  - ✅ AI 초안 + **사람 확정**은 허용 (사람이 authority). §24-3 "사용자에게 입력 요청"도 충족(확정 요청).
  - ✅ **검증 독립성 보전:** ①deterministic 룰엔진 코드/스펙은 사람이 서명(확정), ②Gold eval 정답지는 원문과 **독립 대조**로 사람이 확정, ③보고서에 "rule spec = AI추출+사람확정" **provenance 명시**(§12 정직성).
  - ⚠️ 금지선 유지: Assurance 평가에서 **LLM이 LLM을 채점하는 구조 금지**. 정답지는 사람이 원문 대조로 확정.
- **상태:** 사용자 최종 확인 후 ✅로 전환. 확인 전까지 05_RULE_SPEC의 🤖 값은 "초안"으로만 취급.

### 2026-08-10 · 룰엔진 규칙 명세 v1 확정 (precedence·경과규정·알고리즘) · ✅ 승인됨
- **결정:** `05_RULE_SPEC.md` v1 확정. 코어 LTV 판정 로직 전체 lock.
  - **precedence(E):** P0 스코프 → P0b 정책대출=Discovery → P1 경과규정 → P2 지역 → P3 다주택0 → P4 유주택0 → P5 생애최초70 → P6 서민실수요60 → P7 일반40.
  - **경과규정(F):** 경계 `<= 2026-06-30`(날짜, 자정 포함), 계약금 일부납부 인정, 토허제 G3 코어 포함, 종전규정=非규제수도권(70%), 유주택 grandfathered=escalate.
  - **정책대출 → Discovery 분리** (디딤돌·보금자리 코어 자동판정 제외).
  - **알고리즘(H)** pseudocode 확정 → 그대로 코드화.
- **확정 방식:** AI 초안 → 사용자 "다 OK, 정책대출은 Discovery로" 확정 (2026-08-10).
- **다음:** deterministic 엔진 코드 + 테스트 하네스 구현(Phase 1 Walking Skeleton).

### 2026-08-10 · 룰엔진 코어 출력 범위: LTV만 (DTI·한도는 참고) · ✅ 승인됨
- **결정:** deterministic 룰엔진의 코어 판정 출력 = **max_ltv**. DTI·최대한도는 `ref_*` 참고값으로 기록만(코어 판정·회귀 대상 아님).
- **이유:** 브리프 코어 = LTV 중심. 수직 슬라이스 빠른 관통 우선. DTI는 나중에 확장 가능.
- **부수:** `regulated_type`(투기과열/조정)은 DTI 참고 표시용으로만 보관. LTV 판정은 REGULATED/NON_REGULATED 2값으로 충분.
- FAQ Q2 이미지로 LTV 표 재설정(생애최초70/서민60/보금자리 아파트60·비55, 기준선 非규제수도권 정정) 반영: `05_RULE_SPEC` C표.

### 2026-08-10 · 6·30 공문 3건 Source Snapshot 저장 + 원문 추출 · ✅ 완료
- 원본(PDF·HWP) + 추출텍스트 + sha256 → `docs/sources/`. `SOURCES.md` 레지스트리.
- 추출로 브리프 §4 교정 7건 발견(생애최초 70%, 서민실수요 60%, 유주택 0%, 토허제 7.5 등) → `regulatory_facts.md` 🔺.

### 2026-08-10 · 주차 계획 재배열(수직 슬라이스 우선) + 총 9~10주 (Q3) · ✅ 승인됨
- **결정 1 (재배열):** 브리프 §18의 "레이어별 완성"을 **"6·30 1건 E2E 관통 우선(Walking Skeleton)"**으로 재배열. 상세 계획은 `docs/04_PLAN.md`.
- **결정 2 (기간):** 총 기간을 **9~10주**로. (브리프 원안 6+2=8주에서 확장. 코어 ~8주 + 스트레치 ~2주.)
  - Phase 0(W1) 기준선 / Phase 1(W2~3) Walking Skeleton / Phase 2(W4~6) 노드 심화 / Phase 3(W7~8) Assurance+검증=코어완성선 / W9~10 스트레치.
- **이유:** 최대 리스크가 "E2E 관통 실패"라 관통을 앞당김. 기간 확장으로 심화 단계 여유 확보.
- **LOCKED 정합성:**
  - §0-5("평가셋을 개발보다 먼저"): **위반 아님.** 골드셋 freeze는 Phase 2 실제 튜닝 전 완료. Walking Skeleton은 6·30 앵커 1건 대상 "배관 스모크 테스트"(성능 튜닝 아님). LOCKED/CHALLENGE는 Phase 3까지 미개봉. 상세 근거는 `04_PLAN.md` 상단.
  - 재배열은 실행 순서 변경이며 §18 "코어 완성의 정의"·"자르면 안 되는 것"은 그대로 유지.
- **참고:** 사용자가 "18주"로 언급했으나 이는 브리프 §18(섹션 번호)를 지칭한 것으로 이해, 목표 기간은 9~10주로 확정. 이견 시 조정.
- **관련 파일:** `docs/04_PLAN.md`(신규), `docs/03_OPEN_QUESTIONS.md` Q3 해결.

### 2026-08-10 · 골드 평가셋 규모 100~120으로 축소 (Q1) · ✅ 승인됨
- **결정:** 골드셋 총 규모를 원안 150~200에서 **100~120**으로 축소. CHALLENGE 비중을 상대적으로 강화.
- **확정 split (권장 수치, 총 ~115):**
  | Split | 규모 | 용도 |
  |---|---:|---|
  | DEV | 40 | 프롬프트·retrieval·extractor 튜닝 |
  | LOCKED TEST | 40 | 최종 성능평가 (개발 중 튜닝 금지) |
  | CHALLENGE | 35 | 예외·경계·충돌·모호 중심 적대적 평가 |
- **CHALLENGE 카테고리 가중:** EXCEPTION / GRANDFATHERING / EFFECTIVE_DATE / CONFLICT 비중을 높게(브리프 §11 철학). 세부 건수는 도메인 검수 시 확정.
- **이전값:** 150~200 (브리프 §11, §12).
- **이유:** 1인이 전체 메타데이터 완비+도메인 검수+3-way split을 손수 만들면 그 자체가 2~3주. 빌드 시간과 충돌. 포트폴리오는 양보다 질 — 잘 만든 CONFLICT 10개 > NORMAL 40개. CHALLENGE가 프로젝트의 진짜 차별점.
- **LOCKED 정합성:** ADJUSTABLE. 브리프 §0은 "평가셋 세부 건수(총 150~200 범위)"를 ADJUSTABLE로 명시. 축소는 LOCKED §0-5(평가셋 우선·3-way 분리)를 훼손하지 않음 — split 구조는 유지.
- **성공 기준 변경:** "150 못 채우면 실패"가 아니라 **"실패모드 카테고리 커버리지가 채워지면 충분"**.
- **관련 파일:** `docs/metrics_spec.md`(평가셋 규모·split 섹션), `docs/03_OPEN_QUESTIONS.md` Q1 해결.

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
