# 01 — PROJECT STATE (살아있는 상태판)

> **이 파일은 프로젝트의 단일 진실 상태판이다.**
> 매 작업 세션 종료 시 갱신한다. 새 계정/새 세션은 이 파일부터 읽는다.
> 규칙: "지금 어디 / 다음 3개 액션 / 대기 중 결정 / 블로커"를 항상 최신으로 유지.

- **마지막 갱신:** 2026-08-18
- **갱신자:** Claude (골드셋 작성 세션)
- **개발 브랜치:** `claude/anthropic-api-key-issue-itk27f`
- **전체 단계:** 🟢 **Phase 1 Walking Skeleton 관통 완료** — 6·30 1건이 Source→Impact Matrix→Assurance까지 E2E 연결 (테스트 158 통과)
- (해결됨) 원격 푸시 권한 부여됨.
- (해결됨) **유료 API 키 의존 제거** — 총 지출 0원으로 실행·재현 가능 (`docs/06_LLM_PROVIDER.md`).

---

## 지금 어디까지 왔나 (DONE)

- [x] 프로젝트 브리프 v2 확정 (`docs/00_BRIEF.md`)
- [x] 브리프에 대한 분석 피드백 완료 (6개 핵심 지적 — 아래 "피드백 요약" 참고)
- [x] 문서 구조(handoff scaffold) 생성 및 커밋
  - README, 01_PROJECT_STATE, 02_DECISION_LOG, 03_OPEN_QUESTIONS, regulatory_facts(스켈레톤), metrics_spec(스켈레톤)

---

## ✅ 방금 완료 (2026-08-18 · 6차)
- **★ 골드 평가셋 115문항 작성** — `docs/eval/gold/` (DEV 40 / 🔒LOCKED 40 / 🔒CHALLENGE 35).
  10개 카테고리 전부 커버, high-risk 비중 DEV·LOCKED 52% / CHALLENGE 80%.
  **튜닝 시작 전에 세 셋을 모두 작성**(브리프 §12-1·2 순서 준수).
- **봉인을 코드로 강제** — `load_split(LOCKED)`는 사유 없이 `SealedSplitError`. 해제는
  `SEAL_ACCESS_LOG.md`에 append-only 기록. `split_stats()`는 정답 없이 구성만 반환해
  일상 점검이 봉인을 소모하지 않게 했다. `src/`·`examples/`의 봉인 셋 참조를 테스트가 금지.
- **정답지 자신에게 Citation Assurance** — 115문항의 모든 인용이 원문에 verbatim 존재함을
  매 테스트마다 대조. 인용문은 손으로 옮기지 않고 `q()`가 원문에서 잘라 온다.
- **DEV/LOCKED 카테고리 분포 동일** 고정(테스트) — 최종 성능 차이가 난이도 차이로 오염되지 않게.
- 한계 명시: 작성자=개발자이므로 독립 벤치마크 아님(브리프 §12 문구 기록). 전 문항 🤖 초안.
- 테스트 129 → **158** (`tests/test_goldset.py` 29개).

## ✅ 이전 완료 (2026-08-18 · 5차)
- **★ Q10 확정(사용자 결정)** — **유주택자를 코어 스코프에 유지**하고, 기준값 없는 구간은
  추정하지 않고 escalation 유지. 모집단에 존재하는 고객군을 범위 밖으로 선언해 지표를 좋아 보이게
  하는 회피를 하지 않는다. → `03_OPEN_QUESTIONS` Q10 ✅ 해결.
- **"자동판정 불가 22.4%"가 잘못된 그림이었음을 발견** — 447건을 열어 보니 **299건(66.9%)은 이미
  판정된 건**이었다. 규제지역 유주택은 시행일 LTV가 0%로 확정되므로 **오늘 심사가 된다.**
  못 하는 것은 시행 전 기준값 부재로 인한 **변화량 비교**뿐.
- **지표를 두 축으로 분리** — `decision_coverage`(심사 판정) **91.4%** vs
  `impact_coverage`(영향 측정) **74.1%**. 진짜 판정 불가는 7.4%(148건: 경과규정 해당 유주택,
  비수도권 유주택). `Segment.IMPACT_UNKNOWN` 신설.
- **미확정을 0으로 세지 않도록 수정** — `limit_before/after/delta`가 미확정 LTV를 0원으로 대체해
  "한도가 늘었다" 같은 허구 수치를 만들 수 있었다 → `None` 반환.
- 매트릭스·UI 재생성(커버리지 2축 표시). 테스트 124 → **129**.

## ✅ 이전 완료 (2026-08-18 · 4차)
- **★ Q10 부분 해결 — 자동판정 불가 33.3% → 22.4%** (666건 → 447건).
- **원인은 명세 공백이 아니라 구현 결함이었다.** 확정 사실 C06("다주택자는 수도권 內 주택구입시
  **규제지역 여부와 무관하게** LTV 0%")이 이미 있었는데 엔진이 REGULATED 분기 **안에서만** 적용해
  "무관"을 좁혀 구현하고 있었다 → `§E P0c` 신설, `regions.is_capital_area()` 추가.
- **시점 무관 근거도 원문에 있었다(C14 신설)** — "旣 마련된 규정에 따라 ... 7.1일부터 즉시 적용"(FSC p2).
  6·30 지정은 새 규칙 생성이 아니라 기존 규칙의 발동 → 시행 전(6.30)에도 수도권 다주택 0%.
- **변이 테스트가 내 주석을 반증** — "P0c 순서 무관"이라고 적었으나 경과규정보다 뒤로 옮기면
  escalation 447→480. 주석 정정 + 회귀 `GF-MULTI-01`로 순서 고정.
- **잔여 미결(⛔ Q10):** 非규제 수도권 **비처분 1주택** 397건(19.9%) — FAQ Q2 주1)이 열 전체를
  무주택 기준으로 한정하므로 값이 원문에 **없다**(C15). MOLIT 유주택 60%는 수도권 **外** 값이라 전용 불가.
  추정 대신 escalation 유지 → **자동화율 상한 약 78%**를 문서·화면에 상시 노출.
- 오라클도 독립 재유도(수도권 집합 별도 기입), TC 34케이스로 확대(Pass 100%). 테스트 119 → **124**.

## ✅ 이전 완료 (2026-08-18 · 3차)
- **★ Stitch UI 하드코딩 → 엔진 실제 출력으로 교체** — `src/regimpact/ui/`(theme·pages·site).
  5개 화면(규제 변경 분석 / 임팩트 매트릭스 / Rule 변경안 / 검증 / 고객·포트폴리오 영향)을
  **코드에서 렌더**한다. 산출물 `docs/ui/generated/`. 생성: `python examples/build_ui.py`(0원).
- **Stitch 재생성 대신 코드 생성 채택** — 정정 프롬프트로 다시 만들면 데이터가 바뀔 때마다 또 환각한다.
  디자인 토큰은 export에서 verbatim 가져오고(테스트로 고정), 값은 전부 실제 객체에서 온다.
- **UI grounding 테스트 23개** — 2026-08-10 Stitch 사고를 회귀로 고정: 환각 지역명 / `60%→50%` /
  경과규정 부등호 반전 / **값 하드코딩(양방향 검사)** / CSS 미정의 클래스 / CDN 재도입.
  전부 **변이 테스트로 방어력 확인**(각 사고를 주입하면 해당 테스트가 실패).
- **자기완결 HTML** — `cdn.tailwindcss.com` 런타임 JIT과 아이콘 폰트 제거, 같은 토큰에서 만든
  정적 CSS 인라인 + 인라인 SVG. 네트워크 없이 열어도 디자인 유지(스크린샷 검증).
- 테스트 96 → **119**.

## ✅ 이전 완료 (2026-08-18 · 2차)
- **★ Impact Matrix E2E 관통** — `src/regimpact/impact/`(schema·portfolio·customer·builder·report).
  `examples/demo_impact_e2e.py`가 브리프 §18 "코어 완성의 정의" 10단계를 **전부 ✅로 관통**한다
  (LLM 호출 0회 — 저장된 추출 기록 재생, 비용 0원).
- **§10 매트릭스 16행 생성** — Phase 3축(D-day 전 13 / 시행 후 2 / 별도 트리거 1) 유지.
  자동처리 50%, Human Review 8행(전부 사유 명시). 산출물 `docs/eval/impact_matrix_6_30.md`.
- **고객 영향 실계산** — 층화 합성 포트폴리오 2,000건을 6.30 vs 7.1 두 시점으로 룰엔진 평가.
  한도 감소 638건(31.9%), 총 −1,549억원, 건당 평균 −2.43억원, 경과규정 보호 134건.
- **⚠ E2E가 드러낸 명세 공백** — **포트폴리오의 33.3%(666건)가 자동 판정 불가**, 사유 전부
  `OWNER_BASELINE_UNKNOWN`(非규제 유주택 기준선 부재). 유닛 테스트 30건에서는 "1케이스"였던 것이
  포트폴리오 규모에서는 1/3이었다 → **Q10 신설(영향 큼)**. 자동화율 상한이 구조적으로 67%로 묶인다.
- Stitch 하드코딩값 대체 준비 완료 — 매트릭스 모든 수치가 엔진·추출기·회귀의 실제 출력에서 나온다.
- 테스트 66 → **94** (`tests/test_impact.py` 28개 추가).

## ✅ 이전 완료 (2026-08-18 · 1차)
- **무과금 LLM provider 레이어** — `src/regimpact/extractor/backends.py`. `cli`(Claude Code 구독 포함,
  유료 키 불필요·기본값) / `gemini`(무료 티어) / `manual`(사람 중계) / `replay`(호출 0회 재생) / `anthropic`(선택).
  서버측 structured output이 없는 경로를 위해 JSON 정규화 + 스키마 검증 + 1회 교정 재시도 구현.
  → **Anthropic API 키 없이도 전 기능 동작.** 결정 근거·한계는 `docs/06_LLM_PROVIDER.md`.
- **Extractor 첫 실제 LLM 실측** — 6·30 공문 3건 실행. sonnet-5: 19건 추출, **Citation Correctness 100% /
  Unsupported Claim Rate 0% / Change Completeness 100% / Exception Recall 50%**.
  실행 기록 `docs/eval/runs/run_*.json`(`--provider replay`로 재현), 리포트 `docs/eval/EXTRACTOR_RUN_REPORT.md`.
- **실측으로 결함 3건 확인** — D-01 지역 어휘 불일치(✅해결: 결정적 정규화 `postprocess.normalize_regions`),
  D-02 열거 병합에 의한 예외 누락(⚠미해결·Q9로 등록, Phase 2 1순위), D-03 모델별 인용 환각
  (haiku-4-5 Unsupported 25% vs sonnet-5 0% → 코어 모델은 sonnet-5 이상).
- 테스트 39 → **66** (`tests/test_backends.py` 27개 추가, 전부 오프라인).

## ✅ 이전 완료 (2026-08-10)
- **TC Generator + Rule-Regression** — `src/regimpact/tc_generator/` (oracle·generator·regression). 룰엔진을
  **독립 명세 오라클(challenger)** 로 차등 검증. 오라클은 rule_engine·regions·grandfathering 을 import 하지 않고
  명세(§H)를 독립 코드 경로로 재구현 → 지역·경과·판정 어느 구현 오차든 잡힘. 30개 케이스(SCOPE/BASELINE/
  EXCEPTION/BOUNDARY/GRANDFATHERING/CONFLICT) Pass Rate 100%. **mutation test**로 fixture 방어력 증명(엔진에
  버그 심으면 회귀가 실패로 잡음). 명세 내부 상충(유주택+생애최초) 발견 → Q8로 표면화. 테스트 11개(총 39) 통과.
- **룰엔진 v1** — `src/regimpact/` 알고리즘 H, 테스트 23.
- **RegChange Extractor + Citation Assurance** — `src/regimpact/extractor/` (schema·prompt·extractor·evaluate·sources). LLM 주입 가능(claude-opus-5, 오프라인 테스트 가능). Citation grounding으로 환각 탐지 실측. 골드 정답지 `docs/eval/regchange_gold_6_30.json`. 테스트 5개.
- 실행: `python -m pytest`(158), `python examples/validate_goldset.py`(골드셋 무결성), `python examples/demo_impact_e2e.py`(**E2E 관통**),
  `python examples/build_ui.py`(**5개 화면 생성**),
  `python examples/demo_6_30.py`, `python examples/demo_tc_regression.py`,
  `python examples/run_extractor.py --provider cli`(**API 키 불필요**) 또는 `--provider replay --run docs/eval/runs/run_cli_sonnet5_v2.json`(호출 0회).

## 다음 액션 (NEXT)
- ~~**Extractor 실제 LLM 1회 실행**~~ — ✅ 완료(2026-08-18 1차).
- ~~**최소 Impact Matrix E2E**~~ — ✅ **완료(2026-08-18 2차). Phase 1 Walking Skeleton 관통.**
- ~~**Q10**~~ — ✅ **확정(2026-08-18): 유주택자 스코프 유지 + 공백은 escalation 유지.**
- ~~**P0c 도메인 검수**~~ — ✅ **확정(2026-08-18): 시행 전에도 0%.** 🤖 초안 → ✅ 전환 완료.
- ~~**골드셋 100~120 작성**~~ — ✅ **완료(2026-08-18): 115문항, 봉인 완료.**
- **✍️ 골드셋 도메인 검수(사용자)** — 전 문항 🤖 `ai_draft`. 확정분은 `authored_by`를
  `human_confirmed`로 전환. DEV부터 검수하면 튜닝을 바로 시작할 수 있다.
- **metrics_spec 임계값 확정** — 현재 대부분 TBD. DEV 실측치가 나오면 근거를 갖고 정할 수 있다.
- **Extractor 튜닝(DEV 40 기준)** — Q9/D-02(서민·실수요자 누락) 해소. Phase 2 본체.
- **Q9 / D-02 대책** — Extractor 예외 누락(서민·실수요자). 앵커 1건이 아니라 DEV 40건 기준으로. Phase 2.
- ~~**Stitch UI를 엔진 실제 출력으로 교체**~~ — ✅ **완료(2026-08-18 3차).**
- **골드셋 100~120 작성 착수 + metrics_spec 임계값 확정** (Phase 2 진입 조건).
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

- **2026-08-18 (7차)** — ✅ **골드 평가셋 115문항 작성.** `src/regimpact/eval/`(schema·goldset·validate),
  `docs/eval/gold/`(dev 40 / locked 40 / challenge 35 + README + SEAL_ACCESS_LOG),
  `tools/gold_*.py`(작성 도구), `examples/validate_goldset.py`. 튜닝 전에 세 셋을 모두 작성해
  브리프 §12 순서를 지켰고, **봉인을 코드로 강제**(사유 없는 LOCKED/CHALLENGE 로드 거부 +
  append-only 접근 기록 + 정답 없이 구성만 보는 `split_stats()`). 인용은 `q()`가 원문에서 잘라 와
  verbatim을 보장하고, 검증기가 115문항 전체를 매번 원문 대조한다. DEV/LOCKED 분포 동일 고정.
  작성 직후 커버리지 집계로 봉인을 한 번 열었고 그 기록을 지우지 않은 채 API를 고쳤다. 테스트 129→158.
- **2026-08-18 (6차)** — ✅ **P0c 확정.** 사용자 도메인 검수 완료("시행 전에도 0% 맞다") →
  수도권 다주택 0%가 지역상태·시점·경과규정 무관임을 확정. `05_RULE_SPEC §C-2 보강`·§E P0c,
  `regulatory_facts` C06·C14 모두 🤖/🔺 → **✅확정** 전환. 코드는 이미 해당 규칙으로 동작 중이라
  변경 없음. **AI초안→사람확정 워크플로(LOCKED §4 운영방식)가 처음으로 한 바퀴 완주**했다.
- **2026-08-18 (5차)** — ✅ **Q10 확정.** 사용자 결정: 유주택자를 코어 스코프에 유지(실제 고객
  모집단에 존재), 기준값 없는 구간은 추정 없이 escalation 유지. 이 결정을 검증하려고 447건을
  열어 보니 **299건(66.9%)이 이미 판정된 건**이었다 — 규제지역 유주택은 시행일 0%로 확정되어
  심사가 된다. "자동판정 불가 22.4%"는 심사 불가와 변화량 미상을 한 통에 담은 잘못된 그림.
  `Segment.IMPACT_UNKNOWN` 신설, 지표를 `decision_coverage`(91.4%)/`impact_coverage`(74.1%)로
  분리. 진짜 판정 불가 7.4%(148건). `limit_*`가 미확정 LTV를 0원으로 대체하던 것도 `None`로 수정
  (허구 수치 방지). 매트릭스·UI 재생성. 테스트 124→129.
- **2026-08-18 (4차)** — ✅ **Q10 부분 해결.** 원문 재검토 결과 다주택 구간은 **이미 확정 사실(C06)이었고
  엔진이 범위를 좁게 구현**하고 있었다 — "규제지역 여부와 무관"인데 REGULATED 분기 안에서만 적용.
  `§E P0c` 신설(수도권 다주택 → 0%, 경과규정보다 앞), `regions.is_capital_area()`, 오라클 독립 재유도,
  TC 30→34. 시점 무관 근거 C14, 공백 확인 C15를 regulatory_facts에 신설. 자동판정 불가
  33.3%→22.4%(666→447). **변이 테스트가 "P0c 순서 무관" 주석을 반증**해 정정(뒤로 옮기면 447→480,
  `GF-MULTI-01`이 고정). 잔여 미결은 비처분 1주택 397건 — FAQ Q2 주1)이 열을 무주택 기준으로
  한정하므로 원문에 값이 없다. 추정 대신 escalation 유지, 자동화율 상한 78%를 명시. 테스트 119→124.
- **2026-08-18 (3차)** — ✅ **★ Stitch UI 하드코딩 → 엔진 실제 출력 교체.** `src/regimpact/ui/` 신규
  (theme: Stitch 토큰 verbatim + 정적 CSS 생성 / pages: 5개 화면, 리터럴 도메인 수치 금지 /
  site: 렌더·기록). `examples/build_ui.py` → `docs/ui/generated/`. **Stitch 재생성 대신 코드 생성**
  채택(재생성은 데이터 변경 때마다 재환각). **UI grounding 테스트** 신설 — Citation Assurance가
  인용을 원문에 대조하듯 화면 값을 엔진 출력에 대조하고, 2026-08-10 사고(환각 지역명/60%→50%/
  부등호 반전)를 회귀로 고정. Rule 화면 LTV는 양방향 검사(단방향은 하드코딩을 통과시킴 — 변이로 확인).
  **자기완결 HTML**로 전환(CDN JIT·아이콘 폰트 제거 → 정적 CSS 인라인 + 인라인 SVG), 오프라인
  스크린샷으로 검증. 포트폴리오 대조군 지역을 SEJONG→CHEONGJU로 변경(환각 금지어와 충돌 회피).
  `stitch_review.md`에 해결 배너 추가(사고 기록은 보존). 테스트 96→119.
- **2026-08-18 (2차)** — ✅ **★ Impact Matrix E2E 관통 (Phase 1 Walking Skeleton 완료).**
  `src/regimpact/impact/` 신규 — `portfolio`(층화 합성 2,000건, 비율을 상수로 노출·시드 고정),
  `customer`(같은 신청건을 6.30/7.1 두 시점으로 룰엔진 평가 → 6개 세그먼트 분류),
  `builder`(§10 행/열 조립, 수치는 전부 실제 컴포넌트 출력에서), `report`(Phase별 마크다운/텍스트).
  `demo_impact_e2e.py`가 브리프 §18 10단계를 전부 ✅ 관통(LLM 호출 0회, 0원).
  매트릭스 16행 — Phase 3축 유지, 자동처리 50%, Human Review 8행(전부 사유 명시),
  Discovery 4행은 표시만 하고 코어 룰엔진 미포함(§24-12). 고객영향: 한도 감소 638건(31.9%),
  총 −1,549억원. **E2E가 명세 공백을 정량화**: 33.3%가 `OWNER_BASELINE_UNKNOWN`으로 자동판정 불가
  → Q10 신설(자동화율 상한 67% 구조적 고정). `ImpactRow`는 사유 없는 비자동 행을 생성 시 거부.
  산출물 `docs/eval/impact_matrix_6_30.md`. 테스트 66→94.
- **2026-08-18 (1차)** — ✅ **무과금 LLM provider 레이어 + Extractor 첫 실측.** 사용자 제약("Anthropic API 키 발급
  어려움, 프로젝트에 비용 지출 안 함")을 설계로 흡수: `backends.py`에 `cli`/`gemini`/`manual`/`replay`/
  `anthropic` provider 추가, `resolve_completion("auto")`가 무과금 경로를 우선. structured output 부재는
  JSON 정규화+스키마 검증+1회 교정 재시도로 대체. 6·30 공문 3건 **실제 LLM 실행**(0원) — sonnet-5
  Citation Correctness 100%/Unsupported 0%/Completeness 100%/Exception Recall 50%. 결함 3건 확인:
  D-01 지역 어휘 불일치(해결 — 결정적 별칭 테이블 `normalize_region_name`, 프롬프트에 코드 어휘 주는
  대안은 정답 누설이라 거부), D-02 예외 누락(미해결·Q9 등록, 앵커 과적합 방지 위해 튜닝 중단),
  D-03 haiku-4-5 인용 환각 25%(모델 선택=리스크 선택 실증). `docs/06_LLM_PROVIDER.md`,
  `docs/eval/EXTRACTOR_RUN_REPORT.md`, `docs/eval/runs/*.json` 신규. 테스트 39→66.
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
