# 01 — PROJECT STATE (살아있는 상태판)

> **이 파일은 프로젝트의 단일 진실 상태판이다.**
> 매 작업 세션 종료 시 갱신한다. 새 계정/새 세션은 이 파일부터 읽는다.
> 규칙: "지금 어디 / 다음 3개 액션 / 대기 중 결정 / 블로커"를 항상 최신으로 유지.

- **마지막 갱신:** 2026-08-13
- **갱신자:** Claude (Impact Matrix 구현 세션)
- **개발 브랜치:** `claude/work-in-progress-d2et38`
- **전체 단계:** 🟢 Phase 1~2 진행 — 룰엔진 + Extractor + TC Generator + Impact Matrix + Rule Proposal + **Assurance Scorecard** + Validation Report(테스트 110 통과). **6·30 E2E 전 노드 관통 · Assurance 4 dimension 12지표 확정 임계값 12/12 PASS · 룰 평가셋 3계층(30/106/3,200) 전부 100%.**
- (해결됨) 원격 푸시 권한 부여됨.

---

## 지금 어디까지 왔나 (DONE)

- [x] 프로젝트 브리프 v2 확정 (`docs/00_BRIEF.md`)
- [x] 브리프에 대한 분석 피드백 완료 (6개 핵심 지적 — 아래 "피드백 요약" 참고)
- [x] 문서 구조(handoff scaffold) 생성 및 커밋
  - README, 01_PROJECT_STATE, 02_DECISION_LOG, 03_OPEN_QUESTIONS, regulatory_facts(스켈레톤), metrics_spec(스켈레톤)

---

## ✅ 방금 완료 (2026-08-13)
- **AI Risk Register v1** — `docs/risk/regchange-ai/regchange-ai_risk_register_v1.md`(+CHANGELOG·README).
  Model/System Card 리스크 요약을 정식 리스크 관리 형식으로 확장: **19건 5범주**(AI/모델·데이터·룰/의사결정·
  거버넌스·운영), 각 건 **고유위험(L×I) → 통제[유형] → 잔여위험** + 소유자·상태·모니터링/escalation 트리거.
  히트맵(Critical 잔여 없음)·Top 잔여위험 6종·리뷰 주기. 수용 리스크(단일앵커·Q8) 근거 명시. 통제는 실제
  구현(grounding·임계값·mutation·escalation·hash·결정론) 근거. 버전 규칙 적용.
- **Model/System Card v1** — `docs/cards/regchange-ai/regchange-ai_card_v1.md`(+CHANGELOG, README).
  하이브리드 특성 반영 **System Card(A) + LLM 컴포넌트 Model Card(B: RegChange Extractor)** 통합. A:
  시스템 요약·구성·사용목적·범위외·데이터(PII 없음)·정량결과(12/12 PASS·격자 3,200)·**리스크 레지스터
  8종**·공정성/윤리·거버넌스·한계. B: 모델 상세(claude-opus-5 기본, 추출 전용)·입출력·지표·factors·
  failure modes·caveats. 실측 근거·provenance(세션 수동 grounded, 자동 API 후속) 명시. 버전 규칙 적용.
- **정식 검증보고서(15~20쪽 분석 서사)** — `docs/reports/validation_report_6_30_full.md`(약 17쪽/28.8k자).
  모델검증 보고서 형식: Executive Summary·검증 범위·방법론(차등검증·grounding·임계값·mutation)·데이터/평가셋·
  Dimension별 발견사항·룰엔진 심층·영향/제안 검토·**고위험 실패 분석(예외 누락 피드백 루프)**·한계·거버넌스·
  결론/권고·부록. 모든 수치 실측 근거(스코어카드 12/12 PASS·격자 3,200/3,200), 재현 명령 포함. 브리프 §18
  코어 완성 정의 충족. validation-report **v3**·workflow-e2e **v7** 승격.
- **PRD v1 작성** — `docs/prd/regchange-ai/regchange-ai_v1.md`(+CHANGELOG). 브리프 §25 필수 항목
  (사용자·Use Case / 데이터·컴포넌트 스키마 / 평가 프로토콜 / 배포)을 구체화하고, **각 컴포넌트·스키마의
  현행 구현 상태(구현됨/부분/계획)를 매트릭스로 명시.** error taxonomy·성공기준·리스크·로드맵 포함.
  버전 규칙 적용(PRD도 vN + CHANGELOG). `docs/prd/README.md`·top README 문서지도 갱신.
- **Assurance 4 dimension 완성 + 임계값 확정(Strict)** — `src/regimpact/assurance/`(thresholds·metrics·scorecard).
  누락 3지표 추가(**Source Contradiction Rate**·**Grandfathering Recall**·**Policy-version Consistency**) →
  12지표 완비. 사용자 확정: 프로파일 **Strict**, 종합 판정 **고위험 FAIL→전체 FAIL**. 6·30 스코어카드
  **12/12 PASS(종합 PASS)**. 가드레일 확인(예외 누락→Exception Recall FAIL→전체 FAIL, 값 날조→Contradiction 포착).
  `examples/assurance_scorecard.py`→`docs/reports/assurance_scorecard.md`, E2E [6] 차원 요약 연동.
  metrics_spec §0-C 임계값 확정, DECISION_LOG·OPEN_QUESTIONS Q2 마감. 신규 기능단위 assurance-scorecard v1,
  workflow-e2e **v6** 승격. 테스트 96→110.
- **Validation Report 정식 HTML 보고서** — `src/regimpact/validation/render_html.py`(`render_report_html`).
  DESIGN.md 디자인 시스템(Institutional Navy·Noto Sans·JetBrains Mono) 기반 self-contained HTML, 7개 섹션
  (관통현황·추출·영향매트릭스·룰제안·회귀·Assurance·한계) 데이터바인딩(하드코딩 0). demo_e2e가 md+html
  동시 생성→`docs/reports/validation_6_30.html`. 정식 15~20쪽 분석 서사는 Phase 3(프레젠테이션은 완료).
  HTML 렌더 테스트 4건. validation-report **v2**·workflow-e2e **v5** 승격. 테스트 92→96.
- **룰 평가셋 수천 건 확대(조합 격자 3,200건)** — `generate_grid()` 결정론 cartesian(지역·시점·house_count·
  처분·생애최초·서민실수요·경과규정 6-way + 스코프). 정답은 오라클 유도(손라벨 없음). **Pass Rate 3,200/3,200
  100%**, split 전량 측정 각 100%, 생성+회귀 ≈0.05s. `docs/reports/rule_grid_stats.md`. mutation(경과규정
  무력화) 격자 포착 확인. temporal 축 과표집(균형은 큐레이션 106이 보완). tc-generator **v3** 승격. 테스트 +6(총 92).
- **룰엔진 평가셋 100~120 확대·통계화** — 층화 합성 포트폴리오 **106건**(`generate_portfolio()`, seed 30→확대).
  정답은 독립 오라클 유도(차등검증, 손라벨 없음). **Pass Rate 106/106 100%**, split(DEV 36/LOCKED 35/
  CHALLENGE 35) **전량 측정** 각 100%, 커버리지 status 4·rule_id 6·reason_code 11. mutation 방어력 확인.
  `examples/demo_portfolio.py`→`docs/reports/rule_portfolio_stats.md`. split 전량 측정 정당성: 결정론 엔진
  (튜닝 루프 없음)→누수 위험 없음(04_PLAN §0-5). tc-generator **v2** 승격. 테스트 +11(총 86).
- **Assurance 실측 + 피드백 루프 1회 완결** — 6·30 grounded 추출(`docs/eval/regchange_extracted_6_30.json`)을
  결정론 채점 하네스로 측정. 1차: **Citation 100%·Unsupported 0%·Completeness 100%·Exception Recall 50%
  (서민·실수요 누락)** — Assurance가 고위험 예외 miss 포착. 2차 반복: FAQ Q2 원문 근거(verbatim)로 서민·실수요
  예외 보완 → **Exception Recall 100%**(인용 무결성 0% 환각 유지). **측정→포착→보완** 루프 실증(핵심 가치제안).
  `examples/measure_assurance_6_30.py`→`docs/reports/assurance_6_30.md`, E2E 보고서 [6]에 연결. 회귀 고정
  테스트 3건, metrics_spec v1/v2 비교 블록, extractor-assurance **v3**·workflow-e2e **v4** 승격.
  provenance: 세션 수동 grounded 추출(자동 claude-opus-5 API 무인 실행은 키 확보 후).
- **E2E 파이프라인 핵심 관통** — [4] Rule Change Proposal(`src/regimpact/proposal/`) + [7] Human Review
  (approval envelope) + [8] Validation Report(`src/regimpact/validation/`, stub) 구현. 이제
  [2]Extractor→[3]Impact Matrix→[R]룰엔진→[4]Proposal→[7]Review→[5]Regression→[8]Report 가 관통
  (`is_pipeline_complete=True`). `examples/demo_e2e.py`→`docs/reports/validation_6_30.md`. 제안·보고서
  값은 ImpactMatrix에서만 유도(하드코딩 0), 제안은 AI초안(PENDING_REVIEW). 테스트 +14(총 72).
  workflow-e2e 문서 **v2**로 승격(v1 보존, before→after 기록).
- **Impact Matrix (Before/After)** — `src/regimpact/impact/` (matrix·segments·report). Walking Skeleton의
  **Before/After → Impact Matrix 노드.** 룰엔진을 시행 전/후 두 시점으로 **차등 실행(temporal diff)** 해
  세그먼트별 LTV 변화를 산출. 규칙값을 자체 보유하지 않음(LOCKED §4 준수). 6·30 6개 세그먼트: 무주택
  70→40%(강화), 생애최초 70→70%(예외 보호=동일), 서민실수요 70→60%, 처분조건부 70→40%, **유주택은
  종전 기준값 부재 → REVIEW로 정직 표면화**(억지 델타 금지). `analyze_from_extraction`으로 Extractor
  (effective_from) → Impact Matrix **E2E 연결.** 테스트 14개(총 53). `examples/demo_impact_matrix.py`.

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
- ~~**Extractor Assurance 실측 + Recall 보완**~~ — ✅ 완료(2026-08-13). Citation 100%/Exception Recall 50%→100%.
  - **후속:** ①**자동 LLM 실행 1회** — 이제 **무료 경로 지원**(로컬 Ollama 권장, 또는 Groq/Gemini 무료 키;
    `REGIMPACT_LLM_PROVIDER=ollama python examples/run_extractor.py`). 사용자 환경에서 실행해 수동 추출 수치와
    비교·재현 → provenance 갱신 ②골드셋 다문서 확대(실제 규제이벤트 확보 시) ③Assurance 임계값 도메인 재검토.
- ~~**TC Generator + 층화 포트폴리오 + 격자**~~ — ✅ 완료(2026-08-13). 3계층: seed 30 / 큐레이션 106 /
  **조합 격자 3,200** 전부 Pass Rate 100%, split 전량 측정, 커버리지 status4/rule_id6/reason_code11. mutation 방어력.
  - **후속(선택):** ①더 큰 격자(원한다면) ②CFL-04(Q8) 도메인 확정 후 반영.
- **(구분 주의) LLM 추출용 골드셋 100~120** — 룰 평가셋(위)과 별개. 실제 규제문서가 6·30 1건뿐이라
  확대는 **추가 규제이벤트 확보 후**(가짜 규제문서 생성은 LOCKED 원칙 위반). regulatory_facts URL·임계값 병행.
- ~~**최소 Impact Matrix E2E**~~ — ✅ 완료(2026-08-13). `src/regimpact/impact/` Before/After 매트릭스.
  - **후속:** ①UI(Stitch) 연동 시 하드코딩값을 `format_matrix`/`ImpactMatrix` 실제 산출로 교체
    ②고객영향 행(가격구간·대출한도) 추가 ③Report stub → 검증보고서 골격 연결(파이프라인 완주).
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

- **2026-08-13** — ✅ **무료 LLM 제공자 지원(anthropic 불필요).** 사용자 요청: "무료만 쓸 것". Extractor가 완성 함수 주입식이라 제공자 교체가 자연스러움을 활용 → `src/regimpact/extractor/providers.py` 추가: OpenAI 호환 범용 어댑터(`openai_compatible_completion`)로 **Ollama(로컬·완전 무료·가입 불필요)·Groq·OpenRouter·Gemini(무료 티어)** 를 base_url·model·키 환경변수만으로 커버. **외부 SDK 불필요 — 표준 라이브러리 urllib만.** 견고 JSON 파서(`extract_json_object`), env 구성(`completion_from_env`), 무료 프리셋(`FREE_PROVIDERS`). `run_extractor.py`를 제공자-불문으로 재작성(무료 옵션 안내). 어댑터 오프라인 테스트 10건(총 120). extractor-assurance **v4** 승격. 주: 라이브 실행은 사용자 환경에서(로컬 Ollama 권장); 현 검증 환경은 키·egress 정책상 미수행이라 provenance는 세션 수동 grounded 추출 유지.
- **2026-08-13** — ✅ **README·데모 정리(포트폴리오 첫인상).** README를 재구성: 인계 안내가 맨 위였던 것을 **핵심 결과(E2E 관통·Assurance 12/12·룰 3계층 100%·110 테스트) → 30초 Quickstart → 파이프라인(mermaid) → 데모 카탈로그 → 포트폴리오 산출물 → 저장소 구조** 순으로 임팩트를 앞세우고, 인계 안내·LOCKED 요약·버전 규칙은 보존해 하단 배치. `demo_tc_regression.py`가 `sys.path` 부트스트랩 누락으로 pip 미설치 시 실패하던 것 수정 → **8개 무-API 데모 전부 실행 확인**. `docs/reports/README.md` 산출물 인덱스 추가. (코드 로직 무변경, 테스트 110 유지.)
- **2026-08-13** — ✅ **AI Risk Register v1 작성.** `docs/risk/regchange-ai/regchange-ai_risk_register_v1.md`(+CHANGELOG·README). Model/System Card 리스크 요약(8종)을 정식 리스크 관리 형식으로 확장 — 19건 5범주(R-AI 5·R-DAT 4·R-RUL 4·R-GOV 3·R-OPS 3). 평가 척도(L×I 1~5, Low/Med/High/Critical), 각 건 고유위험→통제[검증/설계/프로세스/계획]→잔여위험 + 소유자·상태·모니터링/escalation 트리거. 리스크 히트맵(Critical 잔여 없음, 대부분 Low~Medium), Top 잔여위험 6종, 리뷰 주기·수용 리스크(R-DAT-04 단일앵커·R-RUL-04 Q8) 근거. 통제는 실제 구현(grounding·임계값 스코어카드·mutation·escalation·hash·결정론 재현) 근거. 버전 규칙 적용. README·STATE 갱신. (코드 무변경, 테스트 110 유지.)
- **2026-08-13** — ✅ **Model/System Card v1 작성.** `docs/cards/regchange-ai/regchange-ai_card_v1.md`(+CHANGELOG·README). 하이브리드(LLM 추출+결정론 룰엔진) 특성상 **System Card(A) + LLM 컴포넌트 Model Card(B)** 통합. A: 시스템 요약·컴포넌트 상태표·사용목적·범위외/오용방지·데이터(공개 공문·합성, PII 없음)·정량 결과(Assurance 12/12 PASS·격자 3,200/3,200)·**리스크 레지스터 8종**·공정성/윤리(규제 공개기준만·차별 판정 없음)·거버넌스·한계. B(RegChange Extractor): 모델 상세(claude-opus-5 기본·추출 전용)·입출력 스키마·지표(6·30)·factors·failure modes·caveats. 실측 근거 + provenance(세션 수동 grounded 추출, 자동 무인 API는 키 확보 후) 명시. 버전 규칙 적용. README·STATE 갱신. (코드 무변경, 테스트 110 유지.)
- **2026-08-13** — ✅ **정식 검증보고서(15~20쪽 분석 서사) 작성.** `docs/reports/validation_report_6_30_full.md`(약 17쪽/28.8k자, 14개 대섹션). 모델검증 보고서 형식의 authored 분석 문서 — Executive Summary·검증 범위·목적·대상 시스템 개요·방법론(차등검증·오라클·인용 grounding·시점 프로브·임계값·mutation)·데이터/평가셋(3계층·DEV/LOCKED/CHALLENGE 정당성·골드셋 n=1 한계)·Assurance Dimension별 발견사항·룰엔진 심층(우선순위·커버리지·방어력·escalation)·영향 매트릭스/룰 제안 검토·**고위험 실패 분석(서민실수요 예외 누락 → Assurance 포착 → 보완 피드백 루프)**·한계 6종·거버넌스/Human Review/감사추적·결론/권고 5종·부록(스코어카드 전문·임계값·평가셋 통계·error taxonomy·재현 명령). 모든 수치 실측 근거(12/12 PASS·3,200/3,200·106/106). 브리프 §18 코어 완성 정의 충족. validation-report **v3**·workflow-e2e **v7** 승격. (코드 변경 없음, 테스트 110 유지.)
- **2026-08-13** — ✅ **PRD v1 작성.** `docs/prd/regchange-ai/regchange-ai_v1.md`(+CHANGELOG). 브리프 §25 필수 항목(사용자·Use Case·데이터/컴포넌트 스키마·평가·배포)을 구체화하고 **현행 구현 상태(구현됨/부분/계획)를 매트릭스로 명시**(과대약속 금지). 데이터 스키마 11종·컴포넌트 12종 상태표, 평가 프로토콜(3계층·DEV/LOCKED/CHALLENGE·error taxonomy 4종), Assurance 4 dimension 확정 임계값, Human Review·Audit, 배포·재현성, 성공기준·리스크·로드맵. PRD도 버전 규칙 적용. `docs/prd/README.md`·top README 갱신.
- **2026-08-13** — ✅ **Assurance 4 dimension 완성 + 임계값 확정(Strict).** `src/regimpact/assurance/`(thresholds·metrics·scorecard). 누락 3지표 추가: ①Source Contradiction Rate(인용 grounded지만 %값 원문 부재=날조 프록시) ②Grandfathering Recall(경과규정 항목 포착, 고위험 분리) ③Policy-version Consistency(효력일 경계 시점질의 정합, 오라클 검증). 12지표 완비. 사용자 확정: 프로파일 **Strict**, 종합 판정 **고위험(★) FAIL→전체 FAIL**. 6·30 스코어카드 **12/12 PASS→종합 PASS**. 가드레일 테스트(서민실수요 누락→Exception Recall FAIL→전체 FAIL, LTV 33% 날조→Contradiction 1.0 포착). `build_scorecard`/`format_scorecard_md`, `examples/assurance_scorecard.py`→`docs/reports/assurance_scorecard.md`. E2E [6]에 `dimension_summary()` 연동. metrics_spec §0-C 임계값 표 확정, DECISION_LOG 2026-08-13, OPEN_QUESTIONS Q2 마감. 신규 기능단위 **assurance-scorecard v1**, workflow-e2e **v6** 승격. 테스트 96→110.
- **2026-08-13** — ✅ **Validation Report 정식 HTML 보고서.** `src/regimpact/validation/render_html.py`(`render_report_html`) — DESIGN.md 디자인 시스템 기반 self-contained HTML(외부 스크립트 없음), 7개 섹션(파이프라인 관통현황 배지·규제변경 요약·영향 매트릭스·룰 변경 제안+승인상태·룰 회귀·Assurance 타일·정직성 한계) 전부 ValidationReport 실데이터 바인딩(하드코딩 0). 관통 verdict 배지, escalation/초안 미승인/오라클 challenger 한계 노출. demo_e2e가 md+html 동시 산출→`docs/reports/validation_6_30.html`. 정식 15~20쪽 분석 서사는 Phase 3(프레젠테이션 골격 완료). HTML 렌더 테스트 4건. validation-report **v2**·workflow-e2e **v5** 승격. 테스트 92→96.
- **2026-08-13** — ✅ **룰 평가셋 수천 건 확대(조합 격자 3,200건).** `generate_grid()` — 결정론 cartesian(지역4·시점4·house_count4·처분2·생애최초2·서민실수요2·경과규정6 + 스코프 격자). 정답은 독립 오라클 유도(손라벨 없음). **Pass Rate 3,200/3,200 100%**, split 전량 측정(DEV 1200/LOCKED 1088/CHALLENGE 912 각 100%), 생성+회귀 ≈0.05s. 커버리지 status 4·rule_id 6·reason_code 11. mutation(경과규정 무력화)로 격자 방어력 확인(GRANDFATHERING 실패 포착). temporal 축 의도적 과표집 → GRANDFATHERING 다수(카테고리 균형은 큐레이션 106이 보완). `format_portfolio_stats(title=...)`, `demo_portfolio.py`가 106+3,200 동시 산출→`docs/reports/rule_grid_stats.md`. tc-generator **v3** 승격. 테스트 86→92.
- **2026-08-13** — ✅ **룰엔진 평가셋 100~120 확대·통계화(층화 합성 포트폴리오 106건).** `src/regimpact/tc_generator/portfolio.py` — 입력 차원(지역·시점·house_count·예외·경과규정·스코프)을 중첩 루프로 층화, 결정론(난수 없음)·case_id 안정. 정답은 독립 오라클 유도(차등검증)→손라벨 없이 확장. **Pass Rate 106/106 100%**, split(DEV 36/LOCKED 35/CHALLENGE 35) 전량 측정 각 100%, 커버리지 status 4·rule_id 6·reason_code 11. `GeneratedCase.split` 필드, `pass_rate_by_split()`·`format_portfolio_stats()`·`coverage()` 추가. mutation test 포트폴리오 적용(LTV 상수·유주택 규칙 변조 시 실패 포착). split 전량 측정 정당성: 결정론 엔진(튜닝 루프 없음)→누수 위험 없음(04_PLAN §0-5), LLM 골드셋 봉인과 별개. `examples/demo_portfolio.py`→`docs/reports/rule_portfolio_stats.md`. metrics_spec §3 seed/포트폴리오 비교, tc-generator **v2** 승격. 테스트 75→86.
- **2026-08-13** — ✅ **Assurance Exception Recall 50%→100% 보완(피드백 루프 완결).** v1 추출이 놓친 서민·실수요 예외를 FAQ Q2 원문 근거(verbatim, line 52 "규제지역에서도 금융권 생애최초 주담대*, 금융권 서민·실수요자 주담대*, 정책모기지 등에 대해서는 완화된 LTV가 적용됨")로 보완(추출 9→10건). Citation Correctness 10/10·Unsupported 0% 유지, Exception Recall 100% 달성. **측정→결함 포착→보완**의 Assurance 검증 루프가 실제로 한 바퀴 돈 사례. `regchange_extracted_6_30.json` `_meta.iteration` 기록, measure 리포트·metrics_spec에 v1/v2 비교·서사 반영. test_assurance_measure 기대값 갱신(75 통과 유지). extractor-assurance **v3**·workflow-e2e **v4**(지표 디커플링) 승격.
- **2026-08-13** — ✅ **첫 Assurance 실측 확보.** 6·30 원문 3건(FSC/MOLIT 보도참고자료, 관계기관 FAQ)에서 SYSTEM_PROMPT 규칙(verbatim 인용)대로 grounded 추출 → `docs/eval/regchange_extracted_6_30.json`. 결정론 채점 하네스(`extractor/evaluate.py`)로 실측: **Citation Correctness 100%(9/9)·Unsupported 0%·Change Completeness 100%(4/4)·Exception Recall 50%(서민·실수요 누락)·Effective-date/Region OK.** 보수적 저환각 추출이 서민·실수요 예외를 놓쳐 **Assurance가 고위험 예외 miss를 실제 포착**(프롬프트 tradeoff 입증). `examples/measure_assurance_6_30.py`→`docs/reports/assurance_6_30.md`. demo_e2e가 [6] Assurance 실측 수치를 검증보고서에 연결(전 노드 관통). 회귀 고정 `test_assurance_measure`(3). metrics_spec 실측 블록, extractor-assurance **v2**·workflow-e2e **v3** 승격. provenance: 세션 수동 grounded 추출(자동 claude-opus-5 API 무인 실행은 키 확보 후). 테스트 72→75.
- **2026-08-13** — ✅ **E2E 파이프라인 완주(핵심 관통).** [4] Rule Change Proposal(`src/regimpact/proposal/`: build_proposal + record_decision) + [7] Human Review(approval envelope, LOCKED §4 AI초안→사람확정) + [8] Validation Report(`src/regimpact/validation/`: build_report + format_report_md, stub) 구현. 6·30 1건이 [2]Extractor→[3]Impact Matrix→[R]룰엔진→[4]Proposal→[7]Review→[5]Rule-Regression→[8]Report 관통(`is_pipeline_complete=True`). 제안·보고서 값은 ImpactMatrix 실제 산출에서만 유도(하드코딩 0), 회귀 30/30 100% 포함. `examples/demo_e2e.py`→`docs/reports/validation_6_30.md`. 기능단위 문서 rule-proposal·validation-report v1 신규, **workflow-e2e v2 승격**(v1 보존, 변경이력 기록), features/README·README·STATE 갱신. 테스트 +14(총 72).
- **2026-08-13** — ✅ **기능단위·워크플로우 문서 + 버전관리 규칙 도입.** `docs/features/` 신설. 규칙 `_VERSIONING.md`(시맨틱 vN, 새 파일=전체 스냅샷·이전 보존, 각 버전파일 상단 before→after + 폴더 CHANGELOG 누적, PRD 동일 적용). 구현된 5개 기능단위(rule-engine·extractor-assurance·tc-generator·impact-matrix·ui-render) + E2E 워크플로우(workflow-e2e) 각 v1 작성(폴더별 `_v1.md`+`CHANGELOG.md`), `features/README.md` 인덱스. README 문서지도·인계순서 반영.
- **2026-08-13** — ✅ **Impact Matrix UI 렌더 구현.** `src/regimpact/impact/render_html.py`(`render_matrix_html`/`render_6_30`). Stitch 목업(`_1`)의 하드코딩·환각값("60%→50%", 세종·부산 등)을 **룰엔진 실제 산출(ImpactMatrix)에 바인딩된 self-contained HTML로 교체.** DESIGN.md 디자인 토큰 인라인, 근거(reason_code·출처) 표시, REVIEW 세그먼트 별도 노출. `examples/render_impact_ui.py`→`docs/ui/generated/impact_matrix.html`. 렌더 테스트 5건(환각값 부재 단언 포함, 총 58).
- **2026-08-13** — ✅ **Impact Matrix (Before/After) 구현.** `src/regimpact/impact/`(matrix·segments·report·README). Walking Skeleton(04_PLAN Phase 1)의 **Before/After → Impact Matrix 노드.** 룰엔진(`evaluate`)을 시행 전(2026-06-30)/후(2026-07-02) 두 시점으로 **차등 실행(temporal diff)** 해 세그먼트별 LTV 변화를 산출. 규칙값을 자체 보유하지 않음(temporal diff만) → **LOCKED §4 준수.** 6·30 6개 표준 세그먼트: 무주택 70→40%(강화), 생애최초 70→70%(예외 보호=동일), 서민실수요 70→60%, 처분조건부1주택 70→40%, **유주택(비처분1주택·다주택)은 非규제 유주택 기준값이 명세에 없어 시행 전이 escalation → 델타를 억지로 만들지 않고 `REVIEW`로 정직 표면화**(브리프 §12 가치제안). `analyze_from_extraction(extraction, …)`으로 RegChange Extractor(effective_from) → Impact Matrix **E2E 연결**(before=효력일 전일, after=효력일+2). 테스트 14개(총 53) 통과. `examples/demo_impact_matrix.py`.
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
