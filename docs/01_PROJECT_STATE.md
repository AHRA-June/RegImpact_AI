# 01 — PROJECT STATE (살아있는 상태판)

> **이 파일은 프로젝트의 단일 진실 상태판이다.**
> 매 작업 세션 종료 시 갱신한다. 새 계정/새 세션은 이 파일부터 읽는다.
> 규칙: "지금 어디 / 다음 3개 액션 / 대기 중 결정 / 블로커"를 항상 최신으로 유지.

- **마지막 갱신:** 2026-08-11
- **갱신자:** Claude (E2E 완결 세션 — Assurance + Validation Report)
- **개발 브랜치:** `claude/work-start-sp37fd` (PR #2)
- **전체 단계:** 🟢 **Phase 3 코어 완성선 도달** — 룰엔진 + Extractor + TC Generator + Impact Matrix + Rule Change Proposal + Proposal→TC + **Assurance(4 dim)** + **Validation Report**. **6·30 E2E 관통 완료**(Source→추출→Impact→Proposal→TC→Regression→Assurance→Report, gate PASS). 테스트 103 통과.
- (해결됨) 원격 푸시 권한 부여됨.

---

## 지금 어디까지 왔나 (DONE)

- [x] 프로젝트 브리프 v2 확정 (`docs/00_BRIEF.md`)
- [x] 브리프에 대한 분석 피드백 완료 (6개 핵심 지적 — 아래 "피드백 요약" 참고)
- [x] 문서 구조(handoff scaffold) 생성 및 커밋
  - README, 01_PROJECT_STATE, 02_DECISION_LOG, 03_OPEN_QUESTIONS, regulatory_facts(스켈레톤), metrics_spec(스켈레톤)

---

## ✅ 방금 완료 (2026-08-11)
- **E2E 완결 — Assurance + Validation Report.** `src/regimpact/assurance/`(깊은 4 dimension 집계·gate·escalation),
  `src/regimpact/report/`(검증보고서 Markdown + 승인상태 + audit trail), `src/regimpact/e2e.py`(`run_six_thirty_e2e`
  오케스트레이터). 6·30을 **Source→추출→Impact→Proposal→TC→Regression→Assurance→Report** 끝까지 관통(gate PASS,
  decision DRAFT=사람 승인 대기). Assurance는 D1 Citation grounding·D2 Change/Exception completeness·D3 Temporal
  consistency·D4 Regression/Fidelity를 임계 대비 판정하고, 환각 인용·골드 누락을 실제로 잡아 REVIEW_REQUIRED로 승격
  (테스트로 실패 경로 증명). 정직한 gap(유주택 기준부재)은 gate를 막지 않는 note로 분리. canonical 추출 인용을
  **실제 원문 verbatim**으로 교정해 citation grounding 6/6·gold 완전성 100% 확보. audit source_hash=원문 sha256.
  `examples/demo_e2e.py`. 테스트 11개(총 103). **→ 브리프 §18 "코어 완성" 정의 충족.**
- **Proposal → Test Cases 연결** — `src/regimpact/tc_generator/from_proposal.py`. 변경안의 각 주장(claim)을
  겨냥해 회귀 케이스 생성 + 케이스↔주장 **추적성**. 시점·경계는 proposal 값(effective_from, cutoff)에서 유도.
  세 검증 산출: **Coverage**(모든 주장이 ≥1 케이스로 커버, 7/7), **Regression**(engine⟷oracle 재사용, 9/9=100%),
  **Fidelity**(engine⟷proposal, 9/9). fidelity는 실행 기반이라 엔진 상수 독립 부분(REG_EFFECTIVE)은 못 잡음 →
  `check_proposal_consistency`(상수 대조)와 상보(테스트로 문서화). mutation(잘못된 LTV/기준선)이 fidelity에
  잡힘. `examples/demo_proposal_to_tc.py`. 테스트 14개(총 92). **→ 수직 슬라이스 관통: 추출→변경안→TC→회귀.**
- **Rule Change Proposal** — `src/regimpact/proposal/` (schema·builder·consistency·samples). 브리프 §9 거버넌스
  구현: LLM은 룰엔진 코드를 직접 수정하지 않고, 인용 근거가 붙은 추출을 이 모듈이 구조화 변경안으로
  **deterministic 조립**(status=DRAFT). `build_proposal_from_extraction`(추출 카테고리→필드 매핑, 필드별 인용
  추적), `check_proposal_consistency`(변경안↔엔진 상수/Impact Matrix 교차검증 9건), `apply_consistency_status`
  (불일치 시 NEEDS_REVIEW 승격, 자동 승인 없음). 오프라인 canonical 추출 `six_thirty_extraction`(사람 확정
  대리)로 API 키 없이 E2E 관통. **mutation 테스트**로 각 필드 손상 시 consistency가 반드시 잡는지 증명.
  `examples/demo_rule_proposal.py`. 테스트 23개(총 78) 통과.
- **Impact Matrix E2E** — `src/regimpact/impact/` (segments·matrix). 룰엔진을 **시행 전(2026-06-30)·후
  (2026-07-02) 두 시점에 차등 실행**해 `지역×차주유형 → 기존 LTV/변경 LTV/경과규정/reason_code` 매트릭스를
  산출(모든 LTV = 엔진 실측, 하드코딩 아님). before는 경과규정 이벤트 제거(구규제 기준선 순수 평가), after는
  전부 반영. **정직한 escalation**: 유주택/다주택 '기존 LTV'는 명세 기준부재 → `검토필요`로 그대로 노출
  (Stitch 목업의 조작값 "70%→0%"를 엔진 실측 "기준부재→0%"로 교체). `to_dict()`로 UI 연동 JSON 제공,
  `format_report()`로 표 리포트. `examples/demo_impact_matrix.py`. 테스트 16개(총 55) 통과.
- **TC Generator + Rule-Regression** — `src/regimpact/tc_generator/` (oracle·generator·regression). 룰엔진을
  **독립 명세 오라클(challenger)** 로 차등 검증. 오라클은 rule_engine·regions·grandfathering 을 import 하지 않고
  명세(§H)를 독립 코드 경로로 재구현 → 지역·경과·판정 어느 구현 오차든 잡힘. 30개 케이스(SCOPE/BASELINE/
  EXCEPTION/BOUNDARY/GRANDFATHERING/CONFLICT) Pass Rate 100%. **mutation test**로 fixture 방어력 증명(엔진에
  버그 심으면 회귀가 실패로 잡음). 명세 내부 상충(유주택+생애최초) 발견 → Q8로 표면화. 테스트 11개(총 39) 통과.
- **룰엔진 v1** — `src/regimpact/` 알고리즘 H, 테스트 23.
- **RegChange Extractor + Citation Assurance** — `src/regimpact/extractor/` (schema·prompt·extractor·evaluate·sources). LLM 주입 가능(claude-opus-5, 오프라인 테스트 가능). Citation grounding으로 환각 탐지 실측. 골드 정답지 `docs/eval/regchange_gold_6_30.json`. 테스트 5개.
- 실행: `python -m pytest`(39), `python examples/demo_6_30.py`, `python examples/demo_tc_regression.py`, `python examples/run_extractor.py`(API 키 필요).

## 다음 액션 (NEXT)
- **Extractor 실제 LLM 1회 실행** — API 키로 `run_extractor.py` 돌려 6·30 실제 추출 확보 → `run_six_thirty_e2e(extraction=…)`에
  물려 전 파이프라인을 실제 LLM 출력으로 관통(현재는 canonical). Assurance 4 dim 첫 실측 지표.
- ~~**Assurance + Report로 E2E 완결**~~ — ✅ 완료(2026-08-11). `assurance/`·`report/`·`e2e.py`. gate PASS, 코어 완성.
  **후속:** ①metrics_spec 임계값 확정 후 `AssuranceThresholds` 교체 ②골드셋 100~120 확대 시 D2 실측 강화
  ③UI(개요/Assurance 화면)에서 `report.to_dict()` 소비 ④검증보고서 15~20쪽으로 확장(브리프 §18 스트레치).
- ~~**Rule Change Proposal**~~ — ✅ 완료(2026-08-11). `src/regimpact/proposal/`. 추출→구조화 변경안(DRAFT)+엔진 일치 검증.
- ~~**Test Case Generator ↔ Proposal 연결**~~ — ✅ 완료(2026-08-11). `tc_generator/from_proposal.py`. 변경안 주장별
  케이스+추적성+커버리지+fidelity. **수직 슬라이스(추출→변경안→TC→회귀) 관통 완료.**
  **후속:** ①Assurance Evaluation 노드 + 검증보고서 stub로 E2E 완결(브리프 §18 "코어 완성"의 남은 꼬리)
  ②UI Rule 변경안 화면에서 `to_dict()`/coverage 소비 ③실제 extractor LLM 출력으로 consistency·fidelity 실측.
- ~~**최소 Impact Matrix E2E**~~ — ✅ 완료(2026-08-11). `src/regimpact/impact/`. 룰엔진 실측값으로 매트릭스 산출.
  Stitch 하드코딩값 교체 가능(`to_dict()` JSON). **후속:** ①UI(Streamlit/HTML)에서 실제 `to_dict()` 소비
  ②유주택 '기존 LTV' 기준부재를 Rule Change Proposal/보고서에서 명시적 gap으로 다룰지 확정
  ③임계(15%p 하향 등) metrics_spec에 정식 등록.
- ~~**TC Generator**~~ — ✅ 완료(2026-08-10). Rule-regression Pass Rate 100%(30 케이스), mutation test 방어력 확인.
  - **후속(선택):** ①합성 포트폴리오(2,000~5,000) 층화 생성으로 케이스 수 확대 ②CFL-04(Q8) 도메인 확정 후 반영
    ③Boundary/Conflict Pass Rate를 metrics 리포트로 상시 노출(현재 `format_report`로 산출됨).
- (병행) `regulatory_facts.md` URL 채우기, 골드셋 100~120 작성 착수, metrics_spec 임계값 확정.

### (이전) Phase 0 기준선 항목

> 실행 계획은 `docs/04_PLAN.md`(수직 슬라이스 우선, 총 9~10주). Phase 0 항목:

1. **`regulatory_facts.md` 확정** — 6·30 사실 claim(C01~C13) 원문 인용·URL·hash 검수. (사용자 도메인 검수 필요)
2. **`metrics_spec.md` 확정** — 깊은 4 dimension 지표 공식/분모/임계/high-risk 정의.
3. ✅ **룰엔진 규칙 명세 v1 확정** — `05_RULE_SPEC.md` (LTV·precedence·경과규정·알고리즘 H). 정책대출→Discovery, 코어=LTV만. **다음: 이 알고리즘을 deterministic 코드+테스트로 구현.**
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

- **2026-08-11** — ✅ **E2E 완결(Assurance + Validation Report).** `src/regimpact/assurance/`(evaluate·README: 깊은 4 dimension 집계 D1 grounding/D2 completeness/D3 consistency/D4 regression·fidelity, gate PASS/REVIEW_REQUIRED, escalations vs notes 분리), `src/regimpact/report/`(validation_report·README: 검증보고서 Markdown 7섹션 + 결정상태 + audit trail §17), `src/regimpact/e2e.py`(run_six_thirty_e2e 오케스트레이터 + E2EResult 번들). 6·30 Source→추출→Impact→Proposal→TC→Regression→Assurance→Report 관통, gate PASS·decision DRAFT. 실패 경로(환각 인용·골드 누락)를 실제로 잡아 REVIEW_REQUIRED 승격(테스트 증명). 유주택 기준부재는 gate 무관 note로 분리. canonical 추출 인용을 실제 원문 verbatim으로 교정 → citation grounding 6/6, gold 완전성 100%. audit source_hash=원문 sha256. `examples/demo_e2e.py`(Markdown/--json/--save). 테스트 11개(총 103). **브리프 §18 "코어 완성" 정의 충족.**
- **2026-08-11** — ✅ **Proposal → Test Cases 연결 구현.** `src/regimpact/tc_generator/from_proposal.py`. 변경안(RuleChangeProposal)의 주장(claim)별로 겨냥 회귀 케이스 생성 + 케이스↔주장 추적성(traceability). 시점·경계를 proposal 값(effective_from·cutoff)에서 유도(하드코딩 방지). 3검증: Coverage(주장 7/7 커버) + Regression(engine⟷oracle 하네스 재사용, 9/9=100%) + Fidelity(engine⟷proposal, 9/9). fidelity(실행 기반)와 consistency(엔진 상수 대조)의 역할 분담을 테스트로 문서화(시행일 오류는 consistency가, 값 오류는 fidelity가 잡음). mutation으로 잘못된 LTV/기준선을 fidelity가 잡음 증명. `examples/demo_proposal_to_tc.py`. 테스트 14개(총 92). **수직 슬라이스 관통: 추출→변경안→TC→회귀.**
- **2026-08-11** — ✅ **Rule Change Proposal 구현.** `src/regimpact/proposal/`(schema·builder·consistency·samples·README). 브리프 §9 거버넌스: LLM은 룰엔진 코드 직접 수정 금지 → 인용 붙은 추출을 deterministic 코드가 구조화 변경안(DRAFT)으로 조립. `build_proposal_from_extraction`(카테고리별 필드 매핑 + 필드별 citation 추적), `check_proposal_consistency`(변경안↔엔진 상수/Impact Matrix 교차검증 9건, metrics 'Rule Regression·Policy-version Consistency' 정렬), `apply_consistency_status`(불일치→NEEDS_REVIEW, 자동승인 없음). API 키 없이 관통하도록 canonical 추출 `six_thirty_extraction`(사람 확정 대리, regulatory_facts 값·실제 source_doc_id 인용). mutation 테스트로 필드 손상 방어력 증명. `examples/demo_rule_proposal.py`(추출→변경안→검증 9/9). 테스트 23개(총 78) 통과.
- **2026-08-11** — ✅ **Impact Matrix E2E 구현.** `src/regimpact/impact/`(segments·matrix·README). 룰엔진을 시행 전(6/30)·후(7/2) **두 시점 차등 실행**해 `지역×차주유형 → 기존/변경 LTV·경과규정·reason_code` 매트릭스 산출. 모든 LTV = 엔진 실측(하드코딩 아님, UI/Stitch 교체용 `to_dict()` JSON 제공). before는 경과규정 이벤트 제거(구규제 기준선 순수 평가) → before에 `grandfathering_applied` 오적용 방지. **정직한 escalation**: 유주택/다주택 '기존 LTV'는 명세 기준부재 → `검토필요(BASELINE_GAP)`로 노출, Stitch 목업 조작값("70%→0%")을 엔진 실측("기준부재→0%")으로 교체. `ImpactDirection`(TIGHTENED/EASED/UNCHANGED/BASELINE_GAP/NON_CORE), `high_impact`(0%·15%p↓·기준부재) 플래그(metrics high-risk 정렬). Discovery(정책대출)·Out-of-scope(전세) 코어 분리. `examples/demo_impact_matrix.py`. 테스트 16개(총 55) 통과.
- **2026-08-10** — ✅ **TC Generator + Rule-Regression 구현.** `src/regimpact/tc_generator/`(oracle·generator·regression·README). 룰엔진을 **독립 명세 오라클**로 차등 검증(differential testing) — 엔진 출력을 스스로 채점하지 않고 명세(§H)에서 독립 유도한 challenger와 대조하여 회귀가 tautology가 되지 않게 함. 오라클은 rule_engine/regions/grandfathering 미import(구조적 독립). 30 케이스(6 카테고리) Pass Rate 100%. mutation test 2건으로 fixture 방어력 증명. 명세 내부 상충(§E vs §H, 유주택+생애최초) 발견 → `03_OPEN_QUESTIONS.md` Q8 신설. `examples/demo_tc_regression.py`. 테스트 11개(총 39) 통과.
- **2026-08-10** — ✅ **RegChange Extractor(E) + Citation Assurance(A) 구현.** `src/regimpact/extractor/`(structured output, LLM 주입 가능=오프라인 테스트, claude-opus-5 기본). Citation grounding으로 환각 인용 탐지 실측 + 골드 대조(Change Completeness/Exception Recall). 골드 `docs/eval/regchange_gold_6_30.json`. 테스트 5개(총 28) 통과. claude-api 스킬 참조. `examples/run_extractor.py` 추가.
- **2026-08-10** — ✅ **룰엔진 v1 구현·검증.** `src/regimpact/`(models·regions·grandfathering·rule_engine) + `tests/`(pytest 23 통과) + `examples/demo_6_30.py`. 알고리즘 H를 deterministic 코드로. LOCKED §4 준수(규칙값은 확정 명세에서). pyproject·gitignore·엔진 README 추가.
- **2026-08-10** — Stitch 1차 산출물(5화면) 수령·리뷰. 디자인 훌륭(Assurance·Rule변경안·임팩트매트릭스 서사 성공)하나 **도메인 데이터 환각**(지역을 세종/부산/강남으로, LTV 60→50 등). 정정 프롬프트 작성(`docs/ui/stitch_review.md`), export 보존(`docs/ui/stitch_export/`). → 재생성 또는 HTML 직접수정 필요.
- **2026-08-10** — UI 목업용 Google Stitch 프롬프트 작성(`docs/ui/stitch_prompts.md`, 5개 화면: 분석 워크스페이스/임팩트매트릭스/Rule변경안+검토/Assurance/고객영향). 구현은 Streamlit 수준 유지, Stitch는 포트폴리오·참고 디자인용.
- **2026-08-10** — ✅ **룰 명세 v1 확정.** 사용자 "다 OK, 정책대출은 Discovery로". precedence·경과규정·알고리즘 lock, 정책대출 Discovery 분리, 코어=LTV만. `05_RULE_SPEC` 전체 ✅ 전환. **다음 세션/단계: 엔진 코드+테스트 구현(Phase 1 Walking Skeleton).**
- **2026-08-10** — 예외 우선순위(E, P0~P8) + 경과규정(F, G1~G3) + 통합 판정 알고리즘(H, pseudocode) 🤖초안 작성. reason_codes(D) 확정 목록화. 입력 스키마에 real_demand_flag/policy_product/land_permit 등 추가. → ✍️ 사용자 확정 대기 후 엔진 코드화.
- **2026-08-10** — 사용자 제공 FAQ Q2 이미지로 LTV 표 재설정: DTI(투기과열40/조정50) + 최대한도(가격구간별) 추가, `regulated_type` 필드 신설, 기준선 "수도권외"→"非규제 수도권" 정정, 보금자리 비아파트55%/DTI50% 반영. 05_RULE_SPEC C표·regulatory_facts 갱신. (DTI/한도 코어 포함 여부 ✍️ 대기)
- **2026-08-10** — 공문 3건(FSC·MOLIT 보도참고자료 PDF, 관계기관 FAQ HWP) Source Snapshot 저장(해시)+원문 추출(pymupdf/olefile). 룰 LTV 초안 자동 채움(05_RULE_SPEC C표), regulatory_facts에 원문 반영 및 브리프 교정 7건(🔺 생애최초70/서민60/유주택0/토허제7.5 등). LOCKED §4 운영방식("AI초안→사람확정") DECISION_LOG 기록(사용자 확인 대기).
- **2026-08-10** — 룰엔진 규칙 명세 착수: `05_RULE_SPEC.md` 스캐폴드(스키마·의사결정표 구조·경과규정 뼈대) 생성·커밋. LOCKED §4에 따라 ✍️ 도메인 값은 사용자 입력 대기.
- **2026-08-10** — Q3 해결: 주차 계획 수직 슬라이스 우선 재배열 + 총 9~10주 확정. `04_PLAN.md` 신규, DECISION_LOG·OPEN_QUESTIONS·README·STATE 반영, 로컬 커밋.
- **2026-08-10** — Q1 해결: 골드셋 100~120 확정(split DEV40/LOCKED40/CHALLENGE35, CHALLENGE 가중). DECISION_LOG·OPEN_QUESTIONS·metrics_spec·STATE 반영, 로컬 커밋.
- **2026-08-10** — Q2 해결: Assurance 체크 "수를 줄임" 결정(깊은 4 dimension + 로드맵/인프라). DECISION_LOG·OPEN_QUESTIONS·metrics_spec 반영, 로컬 커밋. (원격 push는 권한 대기)
- **2026-08-10** — 브리프 v2 검토, 분석 피드백 제공, handoff 문서 구조 생성·커밋. (기획 단계)
