# 01 — PROJECT STATE (살아있는 상태판)

> **이 파일은 프로젝트의 단일 진실 상태판이다.**
> 매 작업 세션 종료 시 갱신한다. 새 계정/새 세션은 이 파일부터 읽는다.
> 규칙: "지금 어디 / 다음 3개 액션 / 대기 중 결정 / 블로커"를 항상 최신으로 유지.

- **마지막 갱신:** 2026-08-18
- **갱신자:** Claude (온라인 테스트 환경 구축 세션)
- **개발 브랜치:** `claude/online-testing-plan-8k0xmx`
- **전체 단계:** 🟢 Phase 1~2 진행 — **6·30 E2E 10/11 단계 관통** (남은 1개는 LLM 추출, API 키만 있으면 됨). 테스트 110 통과
- (해결됨) 원격 푸시 권한 부여됨.

---

## 지금 어디까지 왔나 (DONE)

- [x] 프로젝트 브리프 v2 확정 (`docs/00_BRIEF.md`)
- [x] 브리프에 대한 분석 피드백 완료 (6개 핵심 지적 — 아래 "피드백 요약" 참고)
- [x] 문서 구조(handoff scaffold) 생성 및 커밋
  - README, 01_PROJECT_STATE, 02_DECISION_LOG, 03_OPEN_QUESTIONS, regulatory_facts(스켈레톤), metrics_spec(스켈레톤)

---

## ✅ 방금 완료 (2026-08-18) — Q8 해소: 입력 무결성 게이트(P0c)
- **"상충"이 아니었다.** §E-138 이 "처분조건부 1주택 + 생애최초"를 유효 조합으로 명시하므로 §E-139 의
  "유주택"은 `is_owner()` 의미 → §E-139 는 우선순위 규칙이 아니라 **입력 유효성 규칙**이고 §H 와 층위가
  다르다. **둘 다 참**이며 §H 에 게이트를 추가하면 끝. "§E냐 §H냐" 택일 프레임 폐기.
- **0% 자동판정 → `NEEDS_HUMAN_REVIEW`.** 0%는 무해한 답이 아니라 대출 거절이고, 틀린 쪽이 생애최초
  플래그였다면 정답은 70%다. 그 70%p 격차를 데이터 오류 뒤에 숨기지 않는다.
- `src/regimpact/validation.py` 신설 · reason_code `CONTRADICTION_OWNER_FIRST_HOME` ·
  게이트 위치 P0/P0b 뒤, P1 앞 · 회귀 `CFL-04·09·10·11·12`(56 케이스, CONFLICT 12).
- **범위 절제:** 같은 부류의 다른 모순 후보는 임의 추가하지 않고 **Q12**로 표면화.

## ✅ 같은 날 완료 (2026-08-18) — Impact Matrix E2E ★코어 완성선 도달
브리프 §18 "코어 완성의 정의" 11단계 중 **10단계가 실제로 돈다.** 남은 1개는 LLM 추출뿐이고
API 키를 넣으면 바로 채워진다. 재현: `python examples/demo_impact_e2e.py --out report.md`

- **`src/regimpact/impact/`** 신설 (portfolio · customer_impact · matrix · pipeline · report)
- **층화 합성 포트폴리오 2,016건** — 난수 없는 완전요인 격자(지역군 4 × 차주 6 × 경과규정 이벤트 4 × 가격 7).
  **시장 분포 추정이 아니라 커버리지 격자**로 설계했다. 실제 고객데이터가 없는데 현실 비중을 지어내면
  그 숫자가 근거 없는 '영향 고객 수'로 둔갑한다(LOCKED §8). 분포가 생기면 `weight`만 채우면 된다.
- **고객·포트폴리오 영향** — Before(6.30)/After(7.2) 두 번 판정해 집계. 세 가지를 구분한다:
  ①실제 LTV 변화 ②경과규정 유예(+반사실로 '유예가 실제로 막아준 건' 252건 분리) ③자동판정 거부(168건, 8.3%).
  **헤드라인 영향률·세그먼트 평균은 경과규정 미해당 층에서 읽는다** — 격자에서 경과규정이 3/4를 차지해
  섞으면 "70%→63%" 같은 왜곡이 생긴다(실제는 70%→40%).
- **임팩트 매트릭스** — 브리프 §10의 업무 11행 + Discovery 4행, **Phase 3구간(LOCKED §7)**.
  각 행의 내용을 프로즈로 박지 않고 실제 산출물에서 **유도**하고, 행마다 **근거 출처(Provenance)** 를
  표시한다(결정론 엔진/사람 골드/AI 추출/확정 명세/미실행). "AI가 만들었다"와 "사람이 확정했다"가
  구분되지 않으면 감사에 못 쓴다.
- **구조화 Rule Change Proposal** — 포트폴리오에서 **실제로 관측된** rule_id 전이 2건. 전부 사람 승인 대기.
- **검증보고서** `render_report()` → 마크다운. 미실행 단계·N/A 지표를 그대로 노출.
- **표면 2곳:** 검증보고서 전용 아티팩트(`web/impact.html`) + Streamlit "임팩트 매트릭스 (E2E)" 탭.
- 테스트 27건 추가(총 108). 재현성·Phase 보존·Discovery 격리·미실행 은폐 금지를 계약으로 고정.

### 주요 결과 (6·30)
- **6·30의 영향은 경기 3곳에 국한.** 기존 규제(서울·경기)·수도권 비규제·비수도권 비규제 지역군 영향 0%.
- **생애최초는 영향 0%** — 규제지역에서도 70% 좌동이라 LTV가 안 바뀐다.
- 경과규정 미해당 층 영향률 12.5%, 한도 변화 −157.5억(LTV만 반영한 참고값).
- **자동판정 거부 8.3%는 전부 '수도권 비규제 유주택'** — 원문이 '수도권 外' 60%만 명시한 명세 공백.

## ✅ 같은 날 완료 (2026-08-18) — Q9·Q10 확정 반영 + 경과규정 버그 수정
- **Q9 확정 — 비규제 유주택 60%** (MOLIT 참고1). 원문이 "수도권 外"를 명시하므로 비수도권에만 적용,
  수도권 비규제 유주택은 근거 부재로 escalation 유지. rule_id `NONREG_OWNER_60`.
- **Q10 확정 — P3(다주택)을 지역 분기 앞으로** (FSC p2 C06). 다주택 AND (규제지역 OR 수도권) → 0%.
  비수도권 비규제 다주택은 유주택 기준 60%로 수렴.
- **Q11 (버그) — 경과규정의 '종전규정'을 70% 고정에서 컷오프 시점 재판정으로 수정.** 이미 규제지역이던
  강남에 경과규정이 붙으면 70%가 나오던 오류. 종전규정은 지역마다 다르다.
- **명세 개정:** `05_RULE_SPEC` §C-2(수도권/비수도권 2열)·§F 주석·§H 의사코드 전면 개정.
- **오라클 재작성:** docstring이 주장하던 "선언적 표 + 범용 해석기"를 실제로 구현(`_RULE_TABLE`).
  종전엔 엔진과 같은 명령형 분기여서 구조적 독립이 말뿐이었다.
- **회귀 56 케이스 100%** (EXCEPTION 10 / GRANDFATHERING 9 / CONFLICT 8), pytest 80.

## ✅ 같은 날 완료 (2026-08-18) — 지역 레지스트리 교체 (버그 수정)
- **🐛 발견·수정: 서울 강남구가 LTV 70%로 판정되던 오류.** 지역 테이블에 6·30 신규 3곳만 있었고 나머지는
  조용히 `NON_REGULATED` 기본값이었다. 실제로는 **서울 25개 자치구와 경기 12곳이 6·30 이전부터 이미 규제지역**
  (MOLIT 참고2 현황표). 사용자 지적으로 발견.
- **전국 241개 시·군·구 레지스트리** `src/regimpact/regions.py` — 시점 버전(강남4구는 조정'16.11.3 → 투기과열'17.8.3),
  `capital_area` 플래그, 구 코드 별칭. 미등록 코드는 `UNKNOWN` → `NEEDS_HUMAN_REVIEW`(추측 금지).
- **검증:** `tests/test_regions.py`가 **공문 원문의 지역 수**(추가지정 전 서울25·경기12 / 후 경기15)와 대조.
  회귀 `REGION` 분류 11건 신설 → 43 케이스 Pass 100%. 웹은 전국 241×7시점 프로브 표로 Python↔JS 대조.
- **부수 발견 → Q9·Q10 신설 → 같은 날 사용자 확정으로 해소** (위 항목 참고).

## ✅ 같은 날 완료 (2026-08-18) — 온라인 테스트 환경
- **온라인 테스트 환경 2종 구축** — 사용자가 브라우저에서 직접 조건을 바꿔가며 판정을 확인할 수 있게 됨.
  1. **정적 샌드박스** `web/sandbox.html` — 룰엔진을 JS로 포팅한 자체완결 1파일(Artifact/GitHub Pages 어디든).
     조건 조작 → LTV·reason_code 즉시 갱신, **우선순위 트레이스**(P0~P7 중 어디서 short-circuit 됐는지 시각화),
     시행 전 대비 델타(Impact Matrix 1행의 원형), 회귀 30케이스 표(행 클릭 → 그 조건 로드).
     **포팅 드리프트 방어:** 표의 골든 값은 사람이 적은 게 아니라 `tools/export_fixtures.py`가 실제 Python 엔진을
     돌려 만든 `web/fixtures.json`이고, 페이지가 브라우저 계산값과 실시간 대조해 어긋나면 배지가 붉어진다.
     추가로 `node tools/verify_js_port.mjs`가 커밋 전 헤드리스 대조(현재 30/30 일치).
  2. **Streamlit 검증 콘솔** `app/streamlit_app.py` — 포팅본이 아니라 **저장소 Python 엔진 그대로**.
     3탭: LTV 판정 / 회귀 콘솔(Pass Rate·카테고리별·미결항목) / Extractor(LLM, 키 있으면 실제 추출+Assurance 수치).
     AppTest 스모크 테스트 5개 추가(`tests/test_streamlit_app.py`) — UI가 엔진을 잘못 호출하면 테스트가 잡음.
  - 배포 가이드 `docs/ui/DEPLOY.md`. **사용자 액션 필요:** Streamlit Community Cloud 배포 버튼은 사용자가 눌러야 함.
  - 두 표면 모두 전국 지역 선택 지원(샌드박스=시도별 optgroup+검색, Streamlit=검색형 selectbox).

## ✅ 이전 완료 (2026-08-10)
- **TC Generator + Rule-Regression** — `src/regimpact/tc_generator/` (oracle·generator·regression). 룰엔진을
  **독립 명세 오라클(challenger)** 로 차등 검증. 오라클은 rule_engine·regions·grandfathering 을 import 하지 않고
  명세(§H)를 독립 코드 경로로 재구현 → 지역·경과·판정 어느 구현 오차든 잡힘. 30개 케이스(SCOPE/BASELINE/
  EXCEPTION/BOUNDARY/GRANDFATHERING/CONFLICT) Pass Rate 100%. **mutation test**로 fixture 방어력 증명(엔진에
  버그 심으면 회귀가 실패로 잡음). 명세 내부 상충(유주택+생애최초) 발견 → Q8로 표면화. 테스트 11개(총 39) 통과.
- **룰엔진 v1** — `src/regimpact/` 알고리즘 H, 테스트 23.
- **RegChange Extractor + Citation Assurance** — `src/regimpact/extractor/` (schema·prompt·extractor·evaluate·sources). LLM 주입 가능(claude-opus-5, 오프라인 테스트 가능). Citation grounding으로 환각 탐지 실측. 골드 정답지 `docs/eval/regchange_gold_6_30.json`. 테스트 5개.
- 실행: `python -m pytest`(80), `python examples/demo_6_30.py`, `python examples/demo_tc_regression.py`, `python examples/run_extractor.py`(API 키 필요).

## 다음 액션 (NEXT)
- **[사용자] E2E 3단계(LLM 추출) 1회 실행** — 키 넣고 `python examples/demo_impact_e2e.py --llm`
  (또는 Streamlit Extractor 탭). 그러면 **11/11 완결** + Citation Correctness·Change Completeness 실측이 채워지고,
  매트릭스의 근거 출처가 "사람 확정(골드)"→"AI 추출(검증 대상)"으로 바뀐다.
- **[사용자] Streamlit Cloud 배포** — `docs/ui/DEPLOY.md` 절차대로. 저장소 연결 + main file `app/streamlit_app.py`.
- **[사용자] ANTHROPIC_API_KEY를 Secrets에 등록** → Extractor 탭에서 실제 LLM 1회 실행 → 첫 실측 Assurance 수치 확보.
  (로컬로 하려면 `python examples/run_extractor.py`.)
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

- **2026-08-18** — ✅ **Q8 해소: 입력 무결성 게이트(P0c) 신설.** §E-138이 '처분조건부 1주택+생애최초'를 유효 조합으로 명시하므로 §E-139의 '유주택'은 is_owner() 의미 → §E-139는 우선순위 규칙이 아니라 **입력 유효성 규칙**이고 §H와 층위가 다르다(둘 다 참). 0% 자동판정을 폐기하고 NEEDS_HUMAN_REVIEW로 전환 — 0%는 대출 거절이고 틀린 쪽이 생애최초 플래그였다면 정답은 70%다. `validation.py` 신설, 게이트는 P0/P0b 뒤·P1 앞. 오라클은 규칙표 상단에 조건 독립 재기입. 다른 모순 후보는 임의 추가하지 않고 Q12로 표면화. 회귀 56 케이스 100%, pytest 110, JS 56/56.
- **2026-08-18** — ✅ **Impact Matrix E2E 구현 (코어 완성선 도달).** `src/regimpact/impact/` (portfolio·customer_impact·matrix·pipeline·report). 브리프 §18 11단계 중 10단계 실제 실행 — 남은 1개는 LLM 추출(키만 있으면 됨). 층화 합성 포트폴리오 2,016건(난수 없는 완전요인 커버리지 격자, 시장 분포 추정 아님), Before/After 2회 판정 집계, 경과규정 반사실 분리, 업무 11행+Discovery 4행 매트릭스(Phase 3구간, LOCKED §7), 행별 근거 출처(Provenance) 표기, 관측 기반 Rule Change Proposal, 검증보고서 렌더러. 표면: 검증보고서 아티팩트 + Streamlit E2E 탭. 테스트 27건 추가(총 108). 결과: 6·30 영향은 경기 3곳 국한, 생애최초 영향 0%, 자동판정 거부 8.3%는 전부 수도권 비규제 유주택 명세 공백.
- **2026-08-18** — ✅ **Q9·Q10 사용자 확정 반영 + 경과규정 버그(Q11) 수정.** 비규제 유주택 60%(비수도권 한정, 수도권은 근거 부재로 escalation 유지), 다주택 판정을 지역 분기 앞으로 이동(수도권이면 규제 무관 0%, 비수도권 비규제는 유주택 기준 60%). 반영 중 경과규정의 '종전규정'을 70%로 하드코딩한 버그 발견 — 이미 규제지역이던 강남에 경과규정이 붙으면 70%가 나왔다 → 컷오프 시점 재판정으로 정정. `05_RULE_SPEC` §C-2·§F·§H 개정. 오라클을 선언적 규칙표+범용 해석기로 재작성(구조적 독립 실현). 회귀 56 케이스 100%, pytest 80, JS 52/52 + 지역 241×7 일치.
- **2026-08-18** — 🐛 **지역 판정 버그 수정 + 전국 레지스트리.** 사용자 지적("서울 강남은 원래 40 제한 걸려야 되는 거 아냐?")으로 발견 — 지역표에 6·30 신규 3곳만 있고 나머지는 조용히 非규제 기본값이라 이미 투기과열지구인 강남구가 70%로 판정됐다. MOLIT 참고2 현황표를 근거로 전국 241곳을 시점 버전과 함께 등록(`regions.py`), 미등록 코드는 `UNKNOWN`→사람 검토로 전환. 오라클 독립성 계약을 심볼 단위로 정밀화(데이터 공유·해석 로직 독립, `tests/test_regions.py`가 원문 지역 수와 대조). 웹은 241×7시점 프로브로 Python↔JS 대조. 회귀 REGION 11건 신설(43 케이스 100%), pytest 71 통과. 부수로 명세 상충 2건 발견 → Q9(비규제 유주택 60%)·Q10(수도권 비규제 다주택 0%) 신설, 룰 값은 임의 변경하지 않고 표면화.
- **2026-08-18** — ✅ **온라인 테스트 환경 2종.** ①정적 샌드박스 `web/sandbox.html`(엔진 JS 포팅, 우선순위 트레이스 시각화, 회귀 30케이스 인터랙티브 표) + 빌드 파이프라인 `tools/export_fixtures.py`→`tools/build_sandbox.py`, 헤드리스 대조 `tools/verify_js_port.mjs`(30/30). 골든 기대값을 사람이 적지 않고 Python 엔진 실행으로 생성해 포팅 드리프트를 구조적으로 탐지. ②Streamlit 검증 콘솔 `app/streamlit_app.py`(실제 Python 엔진, 3탭) + AppTest 스모크 5개. 배포 가이드 `docs/ui/DEPLOY.md`. 테스트 44 통과.
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
