# 01 — PROJECT STATE (살아있는 상태판)

> **이 파일은 프로젝트의 단일 진실 상태판이다.**
> 매 작업 세션 종료 시 갱신한다. 새 계정/새 세션은 이 파일부터 읽는다.
> 규칙: "지금 어디 / 다음 3개 액션 / 대기 중 결정 / 블로커"를 항상 최신으로 유지.

- **마지막 갱신:** 2026-08-12
- **갱신자:** Claude (Impact Matrix E2E + Extractor 첫 실측 세션)
- **개발 브랜치:** `claude/work-in-progress-fmo0g8`
- **전체 단계:** 🟢 Phase 1~2 진행 — 룰엔진 v1 + Extractor(**Gemini 첫 실측**) + TC Generator/Rule-Regression + **Impact Matrix E2E**(6·30 관통) 구현(테스트 56 통과)
- (해결됨) 원격 푸시 권한 부여됨.

---

## 지금 어디까지 왔나 (DONE)

- [x] 프로젝트 브리프 v2 확정 (`docs/00_BRIEF.md`)
- [x] 브리프에 대한 분석 피드백 완료 (6개 핵심 지적 — 아래 "피드백 요약" 참고)
- [x] 문서 구조(handoff scaffold) 생성 및 커밋
  - README, 01_PROJECT_STATE, 02_DECISION_LOG, 03_OPEN_QUESTIONS, regulatory_facts(스켈레톤), metrics_spec(스켈레톤)

---

## ✅ 방금 완료 (2026-08-12)
- **Extractor 예외 recall 개선·재측정** — 프롬프트에 예외 개별 분리(규칙 6 + 체크리스트) 반영 후 2차 실측.
  **Exception Recall 50%→100%**(생애최초/서민·실수요/정책모기지 각각 분리 추출). 항목 6→12건으로 세분화돼도
  **Citation 100%(12/12)·환각 0% 유지**(recall↑가 환각↑로 안 이어지게 규칙 1 우선 통제). 다른 지표 회귀 없음.
  남은 이슈: **Regions MISS**(지역 한글명↔코드 정규화 미해결, 발견 3).
- **Extractor 첫 실측(Gemini)** — Google AI Studio(Gemini `gemini-flash-latest`, structured output)로
  6·30 공문 3건 실제 추출. **프로젝트 최초 실측 지표 확보:** Citation Correctness 100%·Unsupported 0%·
  Change Completeness 100%·Effective-date OK. 실행 중 **측정 아티팩트 발견·수정**(PDF 줄바꿈이 정확한 인용을
  환각으로 오탐 → grounding 공백무관 비교로 보정, 67%→100%). Gemini 백엔드는 SDK 없이 urllib REST(추가 dep 0).
  원시 추출 `docs/eval/extractor_run_6_30_gemini.json`, 리포트 `docs/eval/extractor_run_6_30.md`.
- **Impact Matrix E2E (Walking Skeleton 관통)** — `src/regimpact/impact/` (matrix·segments). 룰엔진을
  같은 세그먼트에 대해 **시행 전(6/30)·후(7/2) 두 시점**으로 돌려 LTV delta·상태전이·중대영향을
  표로 산출. 새 규칙을 만들지 않고 deterministic 엔진 위에서만 동작(LOCKED §4). 6·30 대표 8개
  세그먼트로 E2E 관통(`examples/demo_impact_matrix.py`). 방향(강화/완화/유지/검토) 집계 + 수치비교
  가능 행만 가중평균(제외분 리포트 명시=조용한 누락 금지). **비규제 유주택 기준선 명세 여백**을
  숨기지 않고 NEEDS_REVIEW로 표면화. tautology 방지 회귀(두 날짜를 모두 시행 전으로 두면 임팩트
  소멸)로 임팩트가 엔진 시점해석에서 나옴을 증명. 테스트 14개(총 53) 통과.

## ✅ 이전 완료 (2026-08-10)
- **TC Generator + Rule-Regression** — `src/regimpact/tc_generator/` (oracle·generator·regression). 룰엔진을
  **독립 명세 오라클(challenger)** 로 차등 검증. 오라클은 rule_engine·regions·grandfathering 을 import 하지 않고
  명세(§H)를 독립 코드 경로로 재구현 → 지역·경과·판정 어느 구현 오차든 잡힘. 30개 케이스(SCOPE/BASELINE/
  EXCEPTION/BOUNDARY/GRANDFATHERING/CONFLICT) Pass Rate 100%. **mutation test**로 fixture 방어력 증명(엔진에
  버그 심으면 회귀가 실패로 잡음). 명세 내부 상충(유주택+생애최초) 발견 → Q8로 표면화. 테스트 11개(총 39) 통과.
- **룰엔진 v1** — `src/regimpact/` 알고리즘 H, 테스트 23.
- **RegChange Extractor + Citation Assurance** — `src/regimpact/extractor/` (schema·prompt·extractor·evaluate·sources). LLM 주입 가능(claude-opus-5, 오프라인 테스트 가능). Citation grounding으로 환각 탐지 실측. 골드 정답지 `docs/eval/regchange_gold_6_30.json`. 테스트 5개.
- 실행: `python -m pytest`(53), `python examples/demo_6_30.py`, `python examples/demo_tc_regression.py`, `python examples/demo_impact_matrix.py`, `python examples/run_extractor.py`(API 키 필요).

## 다음 액션 (NEXT)
- ~~**Extractor 실제 LLM 1회 실행**~~ — ✅ 완료(2026-08-12, Gemini). 첫 실측 지표 확보. `docs/eval/extractor_run_6_30.md`.
  - ~~①**서민·실수요 예외 recall 개선**~~ — ✅ 완료(2026-08-12). 50%→100%. 재측정 반영.
  - **후속:** ②**지역명→canonical code 매핑 계층** 추가 → Regions match 정상화 + Impact Matrix 연동 전제(다음 우선)
    ③Anthropic 백엔드로 교차 실측(모델 간 비교) ④골드셋 확대 후 분모 키워 신뢰구간 확보.
- ~~**최소 Impact Matrix E2E**~~ — ✅ 완료(2026-08-12). `src/regimpact/impact/`, 8세그먼트 6·30 관통.
  - **후속(선택):** ①세그먼트 → 층화 합성 포트폴리오(2,000~5,000)로 확대 + 비중 실측/시나리오화
    ②고객영향 행·구조화 Rule Change Proposal 연동 ③UI(Stitch) 하드코딩값을 이 매트릭스 실제 출력으로 교체.
- ~~**TC Generator**~~ — ✅ 완료(2026-08-10). Rule-regression Pass Rate 100%(30 케이스), mutation test 방어력 확인.
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

- **2026-08-12** — ✅ **예외 recall 개선·재측정.** 1차 실측의 Exception Recall 50%(서민·실수요 놓침) 대응 — 프롬프트에 규칙 6(여러 예외를 한 항목으로 뭉치지 말고 개별 EXCEPTION 항목으로 분리, summary에 예외명 명시) + EXCEPTION 체크리스트(생애최초/서민·실수요/정책모기지) 추가, 규칙 1(원문에 없으면 생략) 유지로 환각 통제. 2차 재측정: **Exception Recall 50%→100%**(세 예외 각각 분리 추출), 추출 6→12건 세분화(다주택 LTV 0%·중도금→잔금 경과규정·사업자대출 제한 추가 포착)에도 **Citation 100%(12/12)·환각 0% 유지**. metrics_spec 현재값·리포트(`extractor_run_6_30.md` 1차→2차) 갱신. 남은 이슈: Regions 한글명↔코드(발견 3). 오프라인 테스트 56 통과(프롬프트 변경은 텍스트라 회귀 없음).
- **2026-08-12** — ✅ **Extractor 첫 실측(Gemini) + Gemini 백엔드 추가.** Google AI Studio(Gemini `gemini-flash-latest`, responseSchema structured output)로 6·30 공문 3건 실제 추출 — **프로젝트 최초 실측 지표.** Citation Correctness 100%(6/6)·Unsupported 0%·Change Completeness 100%(4/4)·Effective-date OK·Exception Recall 50%(⚠️서민실수요 놓침)·Regions MISS(⚠️한글명↔코드). 실행 중 **측정 아티팩트 발견·수정**: 원문 PDF 문장중간 줄바꿈을 공백정규화가 공백으로 바꿔 정확한 인용을 환각 오탐(초기 Citation 67%) → grounding을 공백무관(`_squish`) 비교로 보정(100%), 회귀 테스트 추가. Gemini 백엔드는 SDK(google-genai)가 환경 cryptography와 충돌해 **의존성 없는 urllib REST**로 구현(`gemini_completion`+`to_gemini_schema`). `run_extractor.py` 백엔드 자동선택(GEMINI_API_KEY 우선). 원시추출 `docs/eval/extractor_run_6_30_gemini.json`, 리포트 `docs/eval/extractor_run_6_30.md`, metrics_spec 현재값 반영. 테스트 3개 추가(총 56) 통과.
- **2026-08-12** — ✅ **Impact Matrix E2E 구현(Walking Skeleton 관통).** `src/regimpact/impact/`(matrix·segments·README). 룰엔진을 같은 세그먼트에 대해 시행 전(6/30)·후(7/2) 두 시점으로 차등 평가 → LTV delta·방향(강화/완화/유지/검토)·상태전이·중대영향 표 산출. **새 규칙 없이 deterministic 엔진 위에서만 동작**(LOCKED §4). 6·30 대표 8세그먼트로 파이프라인 끝까지 관통(`examples/demo_impact_matrix.py`). 집계는 수치비교 가능 행만 가중평균하고 제외분을 리포트에 명시(조용한 누락 금지). 비규제 유주택 기준선 명세 여백을 NEEDS_REVIEW로 표면화(정직한 escalation). tautology 방지 회귀(두 날짜를 모두 시행 전으로 두면 임팩트 소멸)로 임팩트가 엔진 시점해석에서 나옴을 증명. 각 행에 before/after status·reason_codes 보존(감사 추적). 테스트 14개(총 53) 통과. `regimpact.__init__` 에 analyze_impact/format_report 노출.
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
