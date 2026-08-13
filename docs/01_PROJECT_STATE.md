# 01 — PROJECT STATE (살아있는 상태판)

> **이 파일은 프로젝트의 단일 진실 상태판이다.**
> 매 작업 세션 종료 시 갱신한다. 새 계정/새 세션은 이 파일부터 읽는다.
> 규칙: "지금 어디 / 다음 3개 액션 / 대기 중 결정 / 블로커"를 항상 최신으로 유지.

- **마지막 갱신:** 2026-08-13
- **갱신자:** Claude (Impact Matrix E2E 관통 세션)
- **개발 브랜치:** `claude/work-start-dq1gtz`
- **전체 단계:** 🟢 Phase 1 관통 완료 → Phase 2 진행 — 룰엔진 v1 + Extractor(실측 run1) + TC Generator/Rule-Regression + Impact Matrix E2E + 층화 합성 포트폴리오(~3천) + **골드셋 인프라·seed 32(AI_DRAFT)**(테스트 66 통과)
- (해결됨) 원격 푸시 권한 부여됨.

---

## 지금 어디까지 왔나 (DONE)

- [x] 프로젝트 브리프 v2 확정 (`docs/00_BRIEF.md`)
- [x] 브리프에 대한 분석 피드백 완료 (6개 핵심 지적 — 아래 "피드백 요약" 참고)
- [x] 문서 구조(handoff scaffold) 생성 및 커밋
  - README, 01_PROJECT_STATE, 02_DECISION_LOG, 03_OPEN_QUESTIONS, regulatory_facts(스켈레톤), metrics_spec(스켈레톤)

---

## ✅ 방금 완료 (2026-08-13)
- **골드 평가셋 100~120 착수 — 인프라 + seed 32(AI_DRAFT).** `src/regimpact/goldset/`
  (schema·evaluate·coverage) + `docs/eval/goldset/`(dev 24 · challenge 8 · locked 스캐폴드 · README).
  브리프 §11 8필드 스키마 + 10 카테고리 + DEV/LOCKED/CHALLENGE 분리. **채점은 전부 결정적**
  (LOCKED §4 금지선: LLM이 LLM 채점 금지) — scenario 아이템은 검증된 룰엔진으로, 근거는 원문 grounding으로.
  **실측:** scenario 28/28(100%), Escalation Recall/Precision 100%, grounding 8/8(100%).
  CHALLENGE 가중 카테고리(EXCEPTION·GRANDFATHERING·EFFECTIVE_DATE·CONFLICT) 강조. `load_goldset()` 기본 DEV만
  (누수 방지). **전 항목 AI_DRAFT** — regulatory_facts(검수대기)에서 파생, claim_refs로 연결. 진척 32/115(28%).
  `examples/demo_goldset.py`. 테스트 9개(총 66) 통과. **후속:** 사용자 도메인 검수→HUMAN_CONFIRMED, DEV40/LOCKED40/CHALLENGE35까지 확대 후 freeze.
- **층화 합성 포트폴리오(Phase 2) — 룰엔진 차등검증 seed 30 → ~3,024건 확대.**
  `src/regimpact/tc_generator/portfolio.py`. 5축(scope·region_time·ownership·exception·grandfather)
  곱집합 **432 strata 전수 커버**, 판정 관련(scope=home) 셀에 가중. 결정적(seed 고정, 재현 가능).
  오라클이 기대값 유도 → 기존 `run_regression()`로 그대로 차등검증. **Pass Rate 3024/3024 (100%)**,
  카테고리별 100%(GRANDFATHERING 1227·CONFLICT 912·BOUNDARY 348·BASELINE 168·EXCEPTION 81·SCOPE 288).
  `portfolio_coverage()`로 커버리지 노출(성공 기준=규모 아닌 층화 커버리지). scale-up 결함검출력을
  mutation test로 실증(유주택 LTV 변조 시 포트폴리오가 seed보다 10배↑ 실패 검출).
  `examples/demo_portfolio_regression.py`. 테스트 5개(총 57) 통과.
- **Extractor 실제 LLM 1회 실행 (run 1) — 첫 실측 지표 확보.** 이 환경에 `ANTHROPIC_API_KEY`가
  없어 SDK 경로(api.anthropic.com) 대신 **세션 모델(claude-opus-4-8)** 이 `run_extractor`와 동일
  프롬프트+원문 3건으로 구조화 추출을 생성(`docs/eval/regchange_extraction_6_30_run1.json`, 10건).
  실제 extractor 코드 경로(`extract_regchange`의 complete 주입점)로 흘려 결정적 Assurance 채점.
  **실측:** Citation Correctness **100% (10/10 grounded)**, Unsupported Claim Rate **0%**,
  Change Completeness **100%**, Exception Recall **100%**, Effective-date/Regions OK.
  동일 추출을 `run_e2e(extraction=)`에 주입해 E2E 관통(회귀 30/30). `examples/run_extractor_session_model.py`,
  실측 요약 `docs/eval/regchange_run1_metrics.json`. run1 아티팩트 grounding을 테스트로 고정(총 52 통과).
  **한계(투명성):** 고립 API 호출이 아닌 세션 모델 in-loop + 동일 세션 gold 사전열람(오염 가능) →
  파이프라인 실배선 실증 + grounding 실측 용도이지 독립 벤치마크 아님. **후속:** 사용자 API 키로
  `run_extractor.py`(고립 claude-opus-5) 재실행 시 독립 실측치 확보.
- **Impact Matrix E2E 관통 (Walking Skeleton)** — `src/regimpact/impact/`
  (personas·matrix·anchor·proposal·pipeline·report). 04_PLAN의 최대 리스크("E2E 관통 실패")
  해소: 6·30 1건이 **Source→Before/After→Impact Matrix→Rule Change Proposal→Test/Regression
  →Assurance→Validation Report** 까지 관통(`run_e2e()`). **오프라인**(API 키 불필요) — 앵커 추출이
  원문에 grounding됨(Citation Correctness 100%, grounded 6/6). Impact Matrix 18행(무주택 70→40,
  생애최초 70→70, 서민 70→60, 유주택/다주택은 escalation). Proposal은 LOCKED §4대로 `AI_DRAFT`로
  태어나고 provenance(LLM 추출 vs 룰엔진) 분리. 환각 인용 주입 시 e2e_ok=False로 잡음. 테스트 12개(총 51) 통과.
  실행: `python examples/demo_e2e_6_30.py`.

## ✅ 이전 완료 (2026-08-10)
- **TC Generator + Rule-Regression** — `src/regimpact/tc_generator/` (oracle·generator·regression). 룰엔진을
  **독립 명세 오라클(challenger)** 로 차등 검증. 오라클은 rule_engine·regions·grandfathering 을 import 하지 않고
  명세(§H)를 독립 코드 경로로 재구현 → 지역·경과·판정 어느 구현 오차든 잡힘. 30개 케이스(SCOPE/BASELINE/
  EXCEPTION/BOUNDARY/GRANDFATHERING/CONFLICT) Pass Rate 100%. **mutation test**로 fixture 방어력 증명(엔진에
  버그 심으면 회귀가 실패로 잡음). 명세 내부 상충(유주택+생애최초) 발견 → Q8로 표면화. 테스트 11개(총 39) 통과.
- **룰엔진 v1** — `src/regimpact/` 알고리즘 H, 테스트 23.
- **RegChange Extractor + Citation Assurance** — `src/regimpact/extractor/` (schema·prompt·extractor·evaluate·sources). LLM 주입 가능(claude-opus-5, 오프라인 테스트 가능). Citation grounding으로 환각 탐지 실측. 골드 정답지 `docs/eval/regchange_gold_6_30.json`. 테스트 5개.
- 실행: `python -m pytest`(39), `python examples/demo_6_30.py`, `python examples/demo_tc_regression.py`, `python examples/run_extractor.py`(API 키 필요).

## 다음 액션 (NEXT)
- ~~**최소 Impact Matrix E2E**~~ — ✅ 완료(2026-08-13). `src/regimpact/impact/` 전체 관통, 오프라인, 테스트 51.
  - **후속(선택):** ①UI 연동 시 Stitch 하드코딩값을 `E2EReport.to_dict()` 실제 출력으로 교체
    ②`high_impact` 임계(현재 20%p 초안)를 metrics_spec high-risk 확정과 정렬 ③검증보고서 15~20쪽 서식화.
- ~~**Extractor 실제 LLM 1회 실행**~~ — ✅ 완료(2026-08-13, run1 세션 모델 경로). Citation Correctness 100%,
  Change/Exception 100%. **후속:** 사용자 API 키로 `run_extractor.py`(고립 claude-opus-5) 재실행해
  **독립 실측치**(오염 없는 run2) 확보 → run1과 대조.
- ~~**TC Generator**~~ — ✅ 완료(2026-08-10). ~~①합성 포트폴리오 확대~~ ✅ 완료(2026-08-13, ~3,024건 층화, 100%).
  - **후속(선택):** ②CFL-04(Q8) 도메인 확정 후 반영 ③포트폴리오 규모 5,000까지 확대(target_n 조정).
- ~~골드셋 100~120 작성 착수~~ — ✅ 착수(2026-08-13): 인프라+seed 32(AI_DRAFT, 32/115). **후속:** 도메인 검수→확정, 115까지 확대·freeze.
- (병행) `regulatory_facts.md` URL·hash 채우기, metrics_spec 임계값 확정.

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

- **2026-08-13** — ✅ **골드 평가셋 착수 — 인프라 + seed 32(AI_DRAFT).** `src/regimpact/goldset/`
  (schema·evaluate·coverage), `docs/eval/goldset/`(dev 24·challenge 8·locked 스캐폴드·README). 브리프 §11 8필드·10카테고리·
  DEV/LOCKED/CHALLENGE 분리. 결정적 채점(LOCKED §4 금지선): scenario→룰엔진, 근거→원문 grounding.
  실측 scenario 28/28·Escalation R/P 100%·grounding 8/8. 전 항목 AI_DRAFT(regulatory_facts claim_refs 연결).
  누수방지(load_goldset 기본 DEV만). `examples/demo_goldset.py`. 테스트 9개(총 66). 진척 32/115.
- **2026-08-13** — ✅ **층화 합성 포트폴리오(Phase 2) 구현 — 차등검증 ~3,024건 확대.**
  `tc_generator/portfolio.py`(generate_portfolio·portfolio_coverage·format_coverage). 5축 곱집합 432 strata
  전수 커버(scope=home 가중), 결정적 seed. 오라클 기대값으로 기존 run_regression 차등검증 → 3024/3024(100%),
  전 카테고리 100%. mutation test로 scale 결함검출력 실증(seed 대비 10배↑). `examples/demo_portfolio_regression.py`.
  metrics_spec §3 현재값 갱신. 테스트 5개(총 57) 통과.
- **2026-08-13** — ✅ **Extractor 실제 LLM 1회 실행(run 1) — 첫 실측 지표.** API 키 부재로 세션 모델
  (claude-opus-4-8)이 run_extractor 동일 프롬프트+원문으로 추출 10건 생성(`docs/eval/regchange_extraction_6_30_run1.json`).
  실제 extractor 코드 경로로 주입해 결정적 Assurance 채점: **Citation Correctness 100%(10/10), Unsupported 0%,
  Change Completeness 100%, Exception Recall 100%, Effective-date/Regions OK.** E2E 관통(회귀 30/30).
  `examples/run_extractor_session_model.py`, `docs/eval/regchange_run1_metrics.json`. run1 grounding 회귀 테스트 추가(총 52).
  한계: 세션 모델 in-loop + gold 사전열람(오염 가능) → 독립 벤치마크 아님. 후속: 사용자 키로 고립 재실행.
- **2026-08-13** — ✅ **Impact Matrix E2E 관통(Walking Skeleton) 구현.** `src/regimpact/impact/`
  (personas·matrix·anchor·proposal·pipeline·report·README). 04_PLAN 최대 리스크("E2E 관통 실패") 해소 —
  6·30 1건이 Source→Before/After(앵커추출)→Impact Matrix(룰엔진 2시점)→Rule Change Proposal→
  Test/Regression(독립 오라클)→Assurance(Citation grounding + Gold)→Validation Report 까지 관통.
  `run_e2e()`/`format_e2e_report()`. **오프라인**(앵커 추출이 원문 grounding, Citation Correctness 100%).
  값의 출처 분리(Impact Matrix·segment_impacts=룰엔진 deterministic, narrative_changes=LLM 추출+citation),
  LOCKED §4 코드화(Proposal `AI_DRAFT`→`.confirm()`). 환각 인용 주입 회귀 방어(`test_e2e_detects_ungrounded_injection`).
  `examples/demo_e2e_6_30.py`. 테스트 12개(총 51) 통과.
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
