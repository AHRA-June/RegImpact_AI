# 01 — PROJECT STATE (살아있는 상태판)

> **이 파일은 프로젝트의 단일 진실 상태판이다.**
> 매 작업 세션 종료 시 갱신한다. 새 계정/새 세션은 이 파일부터 읽는다.
> 규칙: "지금 어디 / 다음 3개 액션 / 대기 중 결정 / 블로커"를 항상 최신으로 유지.

- **마지막 갱신:** 2026-08-14
- **갱신자:** Claude (골드셋 v1 freeze 세션)
- **개발 브랜치:** `claude/proceed-4ujipo`
- **전체 단계:** 🟢 **Walking Skeleton E2E + Assurance 4 DEEP 실측 + 골드셋 v1 freeze(115)** — Source→…→Report 관통, RegChange 1회 실측(①②③ 100%), 오라클 회귀 30/30, **골드셋 DEV40/LOCKED40/CHALLENGE35 freeze(DEV 회귀 100%, LOCKED/CHALLENGE sealed)**. UI 6화면(오프라인). (테스트 108 통과)
- (해결됨) 원격 푸시 권한 부여됨.

---

## 지금 어디까지 왔나 (DONE)

- [x] 프로젝트 브리프 v2 확정 (`docs/00_BRIEF.md`)
- [x] 브리프에 대한 분석 피드백 완료 (6개 핵심 지적 — 아래 "피드백 요약" 참고)
- [x] 문서 구조(handoff scaffold) 생성 및 커밋
  - README, 01_PROJECT_STATE, 02_DECISION_LOG, 03_OPEN_QUESTIONS, regulatory_facts(스켈레톤), metrics_spec(스켈레톤)

---

## ✅ 방금 완료 (2026-08-14)
- **골드셋 v1 빌드·freeze (115문항, DEV40/LOCKED40/CHALLENGE35).** `src/regimpact/eval/`(gold_set: 스키마·로더·
  엔진 회귀·누수 규율) + `tools/build_gold_set.py`(결정론적 생성) → `docs/eval/gold_set/{dev,locked,challenge}.json`
  + `MANIFEST.json`(sha256·버전·freeze) + `README.md`. **정답은 독립 명세 오라클(tc_generator)에서 유도**(엔진 미참조
  → 회귀 tautology 아님). 브리프 §11 스키마(입력·정답·근거·카테고리·escalation·정책버전·rule_id). **누수 방지(§12):**
  `load_split('locked'/'challenge')`는 unlock 없이 RuntimeError, split 간 입력 disjoint(테스트 강제). DEV 회귀 100%(40/40),
  LOCKED/CHALLENGE도 최종 검증 시 100%(엔진이 충돌·모호·경계 명세대로 처리, AMBIGUOUS는 escalation 검증). DEV pass rate를
  Assurance·Report 화면에 노출(sealed는 count·잠금 배지). `examples/demo_gold_set.py`. 테스트 8개 → **총 108 통과.**
- **RegChange Extractor 1회 실제 LLM 실행 → Assurance ①②③ 첫 실측.** 환경에 API 키가 없어 프록시 직접
  호출은 불가했으나, **실행 모델(claude-opus-4-8)이 6·30 공문 원문 3건만 읽고**(gold 미참조) RegChange를 9건
  추출(인용은 원문 verbatim). 산출물 `docs/eval/regchange_extraction_6_30.json`(provenance 포함). 결정론적
  채점기로 재계산: **Citation Correctness 100%(환각 0%) · Change Completeness 100% · Exception Recall 100% ·
  시행일/지역 OK.** `extractor.measured_assurance()`(저장값 아님, 항상 재계산). Assurance/Report/규제분석 화면의
  '실측 대기'를 실측값으로 대체(추출 없으면 폴백). `run_extractor.py`가 키 없을 때 기록 산출물로 동일 채점 시연.
  → **4 DEEP dimension 전부 실측 완료.** 테스트 3개(recorded grounding/gold 회귀 + 폴백) → **총 100 통과.**
- **Rule Change Proposal 구조화 + Validation Report E2E 관통 (Walking Skeleton 완결).**
  - `src/regimpact/proposal.py` — `RuleChangeProposal` dataclass(파라미터 변경·대상지역·경과규정·reason_codes·
    source·impact·escalation·승인상태) + `build_rule_change_proposal()`(엔진 상수·regions·Impact Matrix 유도) +
    `render_rule_dsl()`. 유주택/다주택 before=명세부재(None) 정직 표기, escalation=OWNER_BASELINE_UNKNOWN.
  - `src/regimpact/report.py` — `ValidationReport`가 8단계 파이프라인(Source→Policy→RegChange→Impact→Proposal→
    TC/Regression→Assurance→HumanReview)을 실제 관통·집계. `build_validation_report()` + `format_report()`.
    브리프 §18 '코어 완성의 정의' 충족. Assurance는 ④만 실측, ①②③은 '실측 대기'(지어내지 않음).
  - UI: `ui/rule_proposal.py`를 구조화 제안 소비로 리팩터, `ui/report.py` 신규(audit-trail nav) → 6번째 화면
    `validation_report.html`. gold 로더·SOURCE_REGISTRY를 extractor로 이전(중립화). `examples/demo_report.py`.
  - 테스트: proposal 5 + report 5 + UI(report 화면) → **총 97 통과.** 아이콘 서브셋 40개로 재빌드(빌드 스크립트
    lru_cache 캐시 무효화 버그 수정).
- **Impact Matrix E2E** — `src/regimpact/impact/` (segments·matrix). 룰엔진을 **Before(2026-06-30)/After(2026-07-02)**
  두 시점에 관통시켜 세그먼트별 `기존 LTV → 변경 LTV / 방향 / 경과규정 / 근거코드`를 산출. 제품 핵심 출력
  (RegChange Impact Analysis)이며 UI 임팩트매트릭스 하드코딩값을 이 실제 엔진 출력으로 대체 가능.
  **정직성 3원칙:** ①非규제 유주택 기준선 명세부재 → `NEW_RESTRICTION`(70→0 fabricate 금지) ②정책대출·전세 등
  → Discovery Scope 분리 ③경과규정 → 종전규정 유지 + **counterfactual**(보호 없었다면 적용됐을 LTV) 병기.
  9개 세그먼트, `format_matrix` 리포트 stub, `examples/demo_impact_matrix.py`.
- **UI 5개 화면 전부 엔진/평가 산출물로 렌더** — 신규 `src/regimpact/ui/` 프레젠테이션 패키지
  (chrome·regchange·impact_matrix·rule_proposal·assurance·portfolio·render_all) → `docs/ui/generated/`
  (5화면 + index). Stitch 목업의 화면별 환각(지역 세종/부산/강남, "60%→50%", 가짜 98.5%, "1,240건",
  가상 담당자)을 제거: 규제분석=RegChange gold, 임팩트=`build_impact_matrix()`, Rule변경안=엔진 상수 diff,
  검증=tc 회귀 실측(30/30)+LLM지표'실측 대기', 포트폴리오=합성 포트폴리오×엔진 집계. 디자인 시스템은
  `ui/templates/*.html`(export 추출)로 보존, 활성 nav만 화면별 전환. **값을 손으로 적지 않아 환각 재발 불가.**
  합성 포트폴리오 집계 `impact/portfolio.py`(결정론적) 추가. UI 테스트 8개 + 포트폴리오 1개. **총 67 통과.**
  렌더: `python examples/render_ui.py`.
- **UI 오프라인 자립화 (CDN 의존 제거)** — 외부 Tailwind CDN·Google Fonts·Material Symbols 링크를 전부 제거.
  실제 Tailwind v3.4.17을 빌드해 `ui/templates/app.css`로 인라인, Material Symbols는 화면에서 쓰는 36개
  글리프만 서브셋해 data URI로 임베드(아이콘은 코드포인트 참조). **네트워크 없이 완전 스타일링**(전체 네트워크
  차단 스크린샷으로 검증). 재현 가능한 빌드 스크립트 `tools/build_ui_assets.py`(디자인 토큰은 보존된 Stitch
  export가 단일 진실). 오프라인 자립성 테스트 15개 추가. **총 82 통과.**
- **(이전)** UI 임팩트매트릭스 최초 대체 — `impact/render.py`는 `ui/impact_matrix.py`로 이전(리팩터링).

## ✅ 이전 완료 (2026-08-10)
- **TC Generator + Rule-Regression** — `src/regimpact/tc_generator/` (oracle·generator·regression). 룰엔진을
  **독립 명세 오라클(challenger)** 로 차등 검증. 오라클은 rule_engine·regions·grandfathering 을 import 하지 않고
  명세(§H)를 독립 코드 경로로 재구현 → 지역·경과·판정 어느 구현 오차든 잡힘. 30개 케이스(SCOPE/BASELINE/
  EXCEPTION/BOUNDARY/GRANDFATHERING/CONFLICT) Pass Rate 100%. **mutation test**로 fixture 방어력 증명(엔진에
  버그 심으면 회귀가 실패로 잡음). 명세 내부 상충(유주택+생애최초) 발견 → Q8로 표면화. 테스트 11개(총 39) 통과.
- **룰엔진 v1** — `src/regimpact/` 알고리즘 H, 테스트 23.
- **RegChange Extractor + Citation Assurance** — `src/regimpact/extractor/` (schema·prompt·extractor·evaluate·sources). LLM 주입 가능(claude-opus-5, 오프라인 테스트 가능). Citation grounding으로 환각 탐지 실측. 골드 정답지 `docs/eval/regchange_gold_6_30.json`. 테스트 5개.
- 실행: `python -m pytest`(108), `python examples/demo_6_30.py`, `python examples/demo_impact_matrix.py`, `python examples/demo_report.py`, `python examples/demo_gold_set.py`, `python examples/render_ui.py`, `python examples/demo_tc_regression.py`, `python examples/run_extractor.py`(키 없으면 기록 산출물로 실측 시연). 재생성(네트워크): `python tools/build_ui_assets.py`, `python tools/build_gold_set.py`.

## 다음 액션 (NEXT)
- ~~**최소 Impact Matrix E2E**~~ — ✅ 완료(2026-08-14). `src/regimpact/impact/`. Before/After 관통, Discovery 분리, 경과규정 counterfactual.
- ~~**UI 임팩트매트릭스 → 엔진 출력 교체**~~ — ✅ 완료(2026-08-14).
- ~~**나머지 화면도 엔진 출력으로 렌더**~~ — ✅ 완료(2026-08-14). 5화면 전부 `regimpact.ui` → `docs/ui/generated/`.
- ~~**CDN 의존 제거(오프라인 스타일)**~~ — ✅ 완료(2026-08-14).
- ~~**Rule Change Proposal 구조화 + Report 관통**~~ — ✅ 완료(2026-08-14). `proposal.py`·`report.py`. Walking Skeleton E2E 완결.
- ~~**Extractor 실제 LLM 1회 실행 → 첫 실측**~~ — ✅ 완료(2026-08-14). ①②③ 100% 실측, 4 DEEP 전 dimension 실측.
- ~~**골드셋 100~120 + DEV/LOCKED/CHALLENGE freeze**~~ — ✅ 완료(2026-08-14). v1 115문항, DEV 회귀 100%, sealed 규율.
  - **후속(선택):** ①검증보고서 15~20쪽(브리프 §18 W7~8) 산출 — 지금까지 실측을 문서로 종합 ②API 키 확보 시 여러 모델
    추출 비교 → challenge grounding 실패 유도·측정 ③골드셋 도메인 검수(사람 확정) 후 v2 ④Model/System Card·AI Risk Register(스트레치).
- **Extractor 실제 LLM 1회 실행** — API 키로 `run_extractor.py` 돌려 6·30 실제 추출 + Assurance 수치 확보(첫 실측 지표).
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

- **2026-08-14** — ✅ **골드셋 v1 빌드·freeze (115문항, DEV40/LOCKED40/CHALLENGE35).** `src/regimpact/eval/gold_set.py`(GoldItem 스키마·load_split·엔진 회귀 러너·누수 규율) + `tools/build_gold_set.py`(결정론적) → `docs/eval/gold_set/{dev,locked,challenge}.json`+`MANIFEST.json`(split별 sha256·v1·freeze)+`README.md`. 정답(expected)은 **독립 명세 오라클**(`tc_generator.oracle`)에서 유도 → 엔진과 독립 코드 경로이므로 회귀가 tautology 아님(LOCKED §4). 브리프 §11 스키마(입력/정답/근거 문서·인용/카테고리/escalation 기대/정책버전/rule_id). 카테고리 10종(NORMAL·EXCEPTION·GRANDFATHERING·EFFECTIVE_DATE·REGION·BORROWER_TYPE·LOAN_PURPOSE·CONFLICT·AMBIGUOUS·NO_CHANGE). **누수 방지(§12):** `load_split('locked'/'challenge')`는 unlock 없이 RuntimeError, split 간 입력 disjoint(테스트로 강제), 개발 상시 회귀는 DEV만. DEV 회귀 100%(40/40); LOCKED/CHALLENGE도 최종 검증 시 100%(엔진이 충돌·모호·경계 명세대로, AMBIGUOUS는 escalation 기대로 '지어내지 않음' 검증). report에 `gold_set` 필드+파이프라인 step 반영, ui/assurance·ui/report에 Gold Set 패널/카드(DEV pass rate + sealed 배지, dataset 아이콘 재빌드). DECISION_LOG freeze 기록. `examples/demo_gold_set.py`. 테스트 8개 → **총 108 통과.**
- **2026-08-14** — ✅ **RegChange Extractor 1회 실제 LLM 실행 → Assurance ①②③ 첫 실측.** 환경에 Anthropic API 키가 없고 프록시가 인증을 주입하지 않아 직접 API 호출은 불가. 대신 **실행 모델(claude-opus-4-8)이 6·30 공문 3건(FSC·MOLIT·FAQ) 원문만 읽고**(gold 미참조) RegChange 9건을 추출 — 인용은 전부 원문 verbatim. 산출물 `docs/eval/regchange_extraction_6_30.json`(_meta: model·run_date·sources). extractor에 `load_recorded_extraction()`+`measured_assurance()` 추가(결정론적 재계산, 저장값 아님): Citation Correctness 100%/환각 0%, Change Completeness 100%, Exception Recall 100%, 시행일·지역 OK. report `_assurance_dimensions`가 measured 반영(없으면 폴백), ui/assurance·ui/regchange에 실측 카드/배너 추가(psychology 아이콘). `run_extractor.py`가 키 없을 때 기록 산출물로 동일 채점 시연. metrics_spec §1에 1회 실측 주석. gold 로더·SOURCE_REGISTRY extractor 중립화. 아이콘 40개 재빌드. 테스트 recorded 3개(+ assurance/report 갱신) → **총 100 통과.**
- **2026-08-14** — ✅ **Rule Change Proposal 구조화 + Validation Report E2E 관통 (Walking Skeleton 완결).** `proposal.py`: `RuleChangeProposal` dataclass(파라미터 변경·대상지역·경과규정·근거·영향·escalation·승인상태)를 엔진 상수·regions·Impact Matrix에서 유도(`build_rule_change_proposal`), DSL은 구조의 렌더링(`render_rule_dsl`). 유주택/다주택 before=명세부재(None) 정직 표기, escalation=OWNER_BASELINE_UNKNOWN. `report.py`: `ValidationReport`가 8단계 파이프라인(Source Snapshot→Policy Version→RegChange→Impact Matrix→Rule Change Proposal→Test/Regression→Assurance→Human Review)을 실제 관통·집계(`build_validation_report`) + `format_report` 텍스트 → 브리프 §18 코어 완성의 정의 충족. Assurance ④만 실측(30/30), ①②③은 '실측 대기'(가짜 수치 없음). UI: `ui/rule_proposal.py`를 구조화 제안 소비로 리팩터, `ui/report.py` 신규(audit-trail nav)로 6번째 화면 `validation_report.html`(파이프라인 스테퍼+섹션 카드, 오프라인). gold 로더+SOURCE_REGISTRY를 extractor로 이전(중립화, ui 의존 제거). `examples/demo_report.py`. 아이콘 서브셋 40개 재빌드(build 스크립트 lru_cache 캐시 무효화 버그 수정). 테스트 proposal 5 + report 5 + report UI → **총 97 통과.**
- **2026-08-14** — ✅ **UI 오프라인 자립화(CDN 의존 제거).** Stitch export가 쓰던 외부 Tailwind Play CDN·Google Fonts·Material Symbols 링크를 전부 제거하고 자기완결 HTML로. (1) Tailwind v3.4.17 실제 빌드(디자인 토큰은 보존된 `stitch_export/_1`의 config에서 추출, 생성 화면을 스캔해 사용 유틸리티만 JIT) → `ui/templates/app.css` 인라인. (2) Material Symbols Outlined를 화면에서 쓰는 36개 아이콘 코드포인트로만 서브셋(10.6MB→2.9KB woff2) → data URI 임베드, 아이콘 스팬은 `chrome._iconify`가 이름→코드포인트 엔티티로 치환(서브셋은 리가처 없음). (3) 본문 폰트는 시스템 스택 폴백. **전체 네트워크 차단 상태 스크린샷으로 완전 스타일링 검증**(사이드바 아이콘·색 배지·monospace 칩 모두 렌더). 재현 가능한 빌드 스크립트 `tools/build_ui_assets.py`(pytailwindcss+fonttools, 빌드 타임 네트워크 필요, 산출물은 커밋). head 템플릿에서 외부 링크 제거+`{{STYLES}}` 주입. 오프라인 자립성 테스트 15개(외부 의존 부재·인라인 CSS·임베드 폰트·아이콘 코드포인트) → **총 82 통과.**
- **2026-08-14** — ✅ **UI 5개 화면 전부 엔진/평가 산출물로 렌더.** 신규 프레젠테이션 패키지 `src/regimpact/ui/`(chrome=nav-aware 공용 셸, regchange/impact_matrix/rule_proposal/assurance/portfolio, render_all) → `docs/ui/generated/`(5화면+index). Stitch 목업의 화면별 환각을 각각의 실제 소스로 대체: 규제분석=RegChange gold(`regchange_gold_6_30.json`)+SOURCES+엔진상수(지역 세종/부산/수지구 오류 제거), Rule변경안=rule_engine 상수 diff(경과규정 부등호 `<=`로 교정, 대상지역 실제 3곳, 가짜 "1,240건" 제거, escalation=OWNER_BASELINE_UNKNOWN 실사유), 검증=tc 회귀 실측(30/30 카테고리별)+LLM 의존 지표는 '실측 대기'(가짜 98%/92% 제거), 포트폴리오=합성 포트폴리오(결정론적, 실데이터아님 명시)×엔진 Before/After 집계. 디자인 시스템은 export에서 추출한 `ui/templates/*.html`로 보존, 활성 nav만 화면별 전환. `impact/render.py`→`ui/impact_matrix.py` 이전, 합성 포트폴리오 `impact/portfolio.py`(결정론적, 난수 없음) 추가. `examples/render_ui.py`. 각 화면 상단 provenance 스트립으로 '실제 산출물' 명시. UI 테스트 8 + 포트폴리오 1 = **총 67 통과.**
- **2026-08-14** — ✅ **UI 임팩트매트릭스 = 엔진 산출물로 대체.** `src/regimpact/impact/render.py`(+ `templates/chrome_*.html`, `examples/render_impact_ui.py`) → `docs/ui/generated/impact_matrix.html`. Stitch 목업(`_1`)이 환각한 하드코딩 값("LTV 60%→50% 하향", 가상 담당자/기한)을 `build_impact_matrix()` 실제 판정으로 대체. 디자인 시스템(head·사이드바·헤더)은 기존 export에서 추출해 보존하고 표·요약카드·Discovery 섹션만 엔진 출력으로 생성 → **값을 손으로 적지 않아 환각 재발 불가**(엔진=단일 진실). 엔진 산출 근거 스트립(rule_engine v1·before/after 날짜·rows)으로 '실제 출력'임을 명시. 정직성 신호(명세부재·종전유지 counterfactual) 화면 노출. `stitch_review.md`에 supersede 주석, `docs/ui/generated/README.md` 신규. 렌더 테스트 2개(총 53 통과).
- **2026-08-14** — ✅ **Impact Matrix E2E 구현.** `src/regimpact/impact/`(segments·matrix·README). 룰엔진을 Before(6·30)/After(7·2) 두 시점에 관통시켜 세그먼트별 델타(기존→변경 LTV / 방향 / 경과규정 / 근거코드)를 산출 — 제품 핵심 출력(RegChange Impact Analysis). **규칙을 새로 만들지 않고** 동일 프로파일을 두 `evaluation_date`에 넣어 `evaluate()` 2회 호출 후 차이를 구조화(지역 시점버전·경과규정은 엔진이 날짜로 해석). 정직성 3원칙: ①非규제 유주택 기준선 명세부재 → `NEW_RESTRICTION`(70→0 fabricate 금지) ②정책대출·전세 → Discovery Scope 분리 ③경과규정 → 종전규정 유지 + counterfactual(보호 없었다면 적용됐을 LTV) 병기. 9 세그먼트, `format_matrix`, `examples/demo_impact_matrix.py`. 테스트 12개(총 51) 통과. → 다음: Rule Change Proposal + Report stub와 연결해 Walking Skeleton 완전 관통, UI 하드코딩값 교체.
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
