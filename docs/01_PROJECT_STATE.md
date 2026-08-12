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
- **대출 여력 영향 금액 집계(exposure)** — `src/regimpact/impact/exposure.py`. Impact Matrix의 LTV %p 변화를
  **문서화된 담보가격 밴드**(6억이하~25억초과 5밴드, 가중평균 10.12억, 시나리오 가정·실측 아님)와 결합해
  차주 1인당·포트폴리오 전체의 **대출 여력(loanable capacity) 변화 금액**으로 환산. 여력=담보가격×적용 LTV.
  **6·30 결과: 판정가능 1인당 평균 여력 7.08억 → 5.06억(Δ −2.02억, 감소율 28.6%), 산정불가 비중 23%.**
  두 경로 수렴(정확 가중 28.57% ≈ 몬테카를로 5000명 28.80%). **정직성 고지 4종**을 리포트에 노출:
  ①여력(한도)이지 실행액 아님 ②LTV 규칙만 — **가격대별 최대한도 상한(6/4/2억) 미적용**(상한 성격)
  ③담보가격 분포는 가정 ④자동판정 불가분(명세 여백=비규제 유주택 시행 전 기준선)은 **금액 산정 불가로 분리**
  (0으로 뭉개지 않음). `CustomerSegment.property_price` 필드 추가(룰 판정 무간섭). HTML 리포트에 '영향 금액'
  패널 통합(report_6_30.html 24.8KB), `examples/demo_exposure.py`·`docs/eval/exposure_impact.md`. 테스트 11개
  추가(총 122).
- **정식 PRD 작성(as-built)** — `docs/prd/PRD.md`(v1.0). 브리프 §25 전 항목(사용자·Use Case / 데이터 8스키마 /
  컴포넌트 12 / 평가 / 배포)을 **구현 반영**으로 구체화 — 각 항목에 구현상태(✅/🟡/⬜/◦)·모듈경로·실측값 매핑.
  **error taxonomy(E1~E9)** + **failure review template** 신설(`docs/prd/failure_review_template.md`, 실측 2건 예시).
  prd/README 갱신. 코드 변경 없음(테스트 112 유지).
- **metrics_spec 임계값 확정 + regulatory_facts URL 채움** — 임계값 정책(§0-B): **고위험 실패모드=하드게이트
  (0누락/100%), 커버리지=퍼센트 하한, 효율=참고**. 전 지표 임계 확정 + high-risk 정의 4종 확정
  (경과규정 오판·시행일 오적용·핵심예외 누락·rule conflict 자동처리). 실측값 전 지표 임계 충족.
  regulatory_facts: 문서 메타데이터·발행기관 공식출처(금융위 fsc.go.kr / 국토부 molit.go.kr) 확정 기입,
  **기사 permalink는 ⬜ 사용자 확인**(AI가 정부 URL 임의생성 금지 = citation integrity). DECISION_LOG 2건 기록.
- **가중 합성 모집단 — 비중 실측화 + 수천 건 확장** — `src/regimpact/impact/population.py`. 세그먼트 weight를
  **문서화된 비중 모델**(아키타입 모집단 점유율 + 지역 mix, 시나리오 가정·실측 아님)로 부여 → 가중 포트폴리오
  통계 의미화. 두 경로: `enumerate_weighted_profiles()`(정확 가중 24) / `sample_portfolio(n=5000,seed)`(몬테카를로,
  결정적). **가중 임팩트: 강화 58% · 유지 24% · 검토 18% · 가중평균 Δ −20pp · 사람검토 23%**. 5,000명 표본
  **회귀 5,000/5,000(engine⟷독립 오라클)**로 룰-회귀 분모 수천 확대. `matrix.py`에 가중 집계(direction_weight_share/
  review_weight_share). 리포트에 '비중 기준' 요약 통합. `examples/demo_population.py`·`docs/eval/population_impact.md`.
  테스트 7개 추가(총 112). **비중은 가정임을 정직 표기**(실측 확보 시 표만 교체).
- **Rule Change Proposal 구조화 산출** — `src/regimpact/rule_proposal.py` (`build_proposal`→`RuleChangeProposal`).
  파이프라인 마지막 조각: 공문→추출→**룰 변경안(초안)**→사람 확정 룰 대조. 추출된 각 변경을 룰엔진 실제 룰
  표면(LTV 상수·지역 버전·경과규정 컷오프·시행일)에 매핑하고 **엔진 현재값과 교차 대조**. disposition:
  MAPPED_CONSISTENT(반영)/DIVERGENT(불일치검토)/OUT_OF_SCOPE(Discovery)/NEEDS_REVIEW. **approval_status는 항상
  PENDING**(자동 확정 없음, LOCKED §4). 6·30: 12건 중 **반영 7 · 코어밖 4 · 검토 1 · 불일치 0**. HTML 리포트에
  섹션 통합, `examples/demo_rule_proposal.py`. provenance(인용) 전건 보존. 테스트 15개 추가(총 105).
- **골드셋 확대 — 층화 합성 포트폴리오** — `src/regimpact/tc_generator/portfolio.py`. seed 30건을 넘어
  입력 차원(지역/시점·소유·예외·경과규정·스코프)을 체계적으로 층화 스윕해 **178건** 결정적 생성.
  metrics_spec §3 분모 확대(Rule-regression **178/178 100%**, Boundary 40/40, Conflict 33/33). 기대값은
  **독립 명세 오라클**에서 유도(엔진 미import → tautology 방지). LOCKED §0-5 **DEV 52/LOCKED 59/CHALLENGE 67**
  3분할(hashlib 결정적, CHALLENGE 하드 카테고리 가중) + `docs/eval/goldset_manifest.json` freeze. mutation test로
  큰 골드셋의 이빨 확인. `examples/demo_portfolio.py`, `docs/eval/goldset_portfolio.md`. 테스트 9개 추가(총 90).
  **Anthropic 교차 실측은 보류**(사용자: 유료 API 미사용) — 백엔드 코드는 준비됨(`2dfc6cd`).
- **UI 연동 — HTML 리포트 생성기** — `src/regimpact/report.py` (`render_report`). 파이프라인 실제 출력
  (추출 + 정규화 + Impact Matrix + Assurance 지표)을 자체완결 HTML 대시보드로 렌더. **모든 값이 엔진/추출에서만
  오므로 Stitch 목업의 도메인 환각(세종·부산, LTV 60→50) 문제가 구조적으로 불가능.** DESIGN.md 디자인 언어
  (Institutional Navy, Noto Sans/JetBrains Mono, 라이트/다크). 지역 그룹핑, 추출 변경+인용, 임팩트 표, Assurance 타일.
  `examples/gen_report.py`로 저장 추출→오프라인 실제 리포트 생성(`docs/ui/report_6_30.html`, 24행·전 지표 녹색).
  테스트 6개(실제값 존재·환각값 부재 회귀 포함, 총 81). 다음: Anthropic 교차 실측 / 골드셋 확대.
- **추출 → Impact Matrix 실제 연결 (E2E 진짜 데이터 관통)** — `src/regimpact/impact/connect.py`
  (`impact_from_extraction`, `PolicyImpact`). 추출의 policy_id·effective_from·target_regions(한글명)를
  Impact Matrix 입력으로 흘려보냄: effective_from→before/after 시점 유도, 지역명→코드 정규화,
  각 지역×대표 유형(archetype 8종)→세그먼트→룰엔진 차등. 저장 추출로 오프라인 E2E: 3지역×8=24행,
  가중평균 Δ -20pp. LOCKED §4: LLM은 '좌표(정책·지역·시점)'만, LTV 판정은 deterministic 룰. segments를
  archetype으로 리팩터(지역 주입 가능), extractor 런타임 import 없이 duck typing. `examples/demo_extractor_to_impact.py`.
  테스트 5개 추가(총 75). 다음: Anthropic 교차 실측 / 골드셋 확대 / UI 연동.
- **지역명→canonical code 정규화 계층** — `regions.py`에 `resolve_region_code`/`normalize_regions` 추가
  (distinctive token 매칭, code에 idempotent, 미상은 None/unmapped로 표면화). 채점(`score_against_gold`)이
  추출 원본을 훼손하지 않고 **비교 시점에만** 코드로 정규화. 저장된 2차 추출 오프라인 재채점: **Regions MISS→OK**.
  발견 3 해결. 테스트 14개 추가(총 70). 다음: 추출→Impact Matrix 실제 연결.
- **Extractor 예외 recall 개선·재측정** — 프롬프트에 예외 개별 분리(규칙 6 + 체크리스트) 반영 후 2차 실측.
  **Exception Recall 50%→100%**(생애최초/서민·실수요/정책모기지 각각 분리 추출). 항목 6→12건으로 세분화돼도
  **Citation 100%(12/12)·환각 0% 유지**(recall↑가 환각↑로 안 이어지게 규칙 1 우선 통제). 다른 지표 회귀 없음.
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
  - ~~②**지역명→canonical code 매핑 계층**~~ — ✅ 완료(2026-08-12). Regions MISS→OK. `regions.normalize_regions`.
  - ~~③**추출→Impact Matrix 실제 연결**~~ — ✅ 완료(2026-08-12). `impact_from_extraction`. 공문→추출→임팩트 관통.
  - ~~④**UI 연동**~~ — ✅ 완료(2026-08-12). `report.py` HTML 리포트 생성기. 하드코딩값→엔진 실제 출력.
  - ~~⑥**골드셋 확대**~~ — ✅ 완료(2026-08-12). 층화 합성 포트폴리오 178건 + DEV/LOCKED/CHALLENGE 3분할.
  - ~~⑦**Rule Change Proposal 구조화 산출·리포트 통합**~~ — ✅ 완료(2026-08-12). `rule_proposal.py`.
  - ~~⑧**포트폴리오 수천까지 확장·비중 실측화**~~ — ✅ 완료(2026-08-12). `population.py`(5000명 표본·가중 임팩트).
  - ~~⑨**metrics_spec 임계값 확정 · regulatory_facts URL**~~ — ✅ 완료(2026-08-12). 하드게이트 정책 + 발행기관 URL.
  - **보류** ⑤Anthropic 교차 실측 — 사용자 유료 API 미사용. 백엔드 코드는 준비(`REGIMPACT_LLM=anthropic`).
  - **사용자 확정 대기(LOCKED §4):** claim C01~C13 최종 도메인 검수 · 기사 permalink(발행기관 게시판에서 검색).
  - ~~⑩**정식 PRD 작성**~~ — ✅ 완료(2026-08-12). `docs/prd/PRD.md`(as-built) + failure review template.
  - ~~⑪대출액/가격대 밴드 '영향 금액' 집계~~ — ✅ 완료(2026-08-12). `impact/exposure.py`(여력 변화 금액, 정직성 4고지).
  - **후속:** ⑫(선택) 비중/가격 민감도 분석 ⑬(선택) 라이브파이어(브리프 §19).
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

- **2026-08-12** — ✅ **대출 여력 영향 금액 집계(exposure).** `src/regimpact/impact/exposure.py`. Impact Matrix의 LTV %p 변화를 문서화된 담보가격 밴드(PRICE_BANDS: 6억이하 30%@4.5 / 6~9억 28%@7.5 / 9~15억 25%@12 / 15~25억 13%@19 / 25억초과 4%@30, 가중평균 10.12억 — 시나리오 가정)와 결합해 **대출 여력(loanable capacity)=담보가격×적용 LTV** 변화 금액으로 환산. before/after LTV는 가격 무관이라 세그먼트당 1회 평가 후 (weight×share×price)로 배분. `compute_exposure`→`ExposureReport`(밴드별/세그먼트별/집계, per-unit 여력). **6·30: 판정가능 1인당 평균 여력 7.08억→5.06억(Δ −2.02억, 감소율 28.6%), 산정불가 23%.** 두 경로 수렴(정확 가중 28.57% ≈ 몬테카를로 5000명+담보가격 몬테카를로 부여 28.80%). **정직성 4고지**(여력≠실행액 / LTV만·최대한도 상한 6·4·2억 미적용=상한 성격 / 담보가격 분포=가정 / 자동판정 불가분=금액 산정 불가로 분리, 조용한 누락 금지). `CustomerSegment.property_price` 필드 추가(exposure 전용, `.application()`에 미전달 → 룰 판정 무간섭·테스트로 확인). `report.py`에 '영향 금액 — 대출 여력(가정)' 패널 통합 + `gen_report.py` 연결(report_6_30.html 24.8KB). `examples/demo_exposure.py`·`docs/eval/exposure_impact.md`. 테스트 11개 추가(총 122) 통과.
- **2026-08-12** — ✅ **정식 PRD 작성(as-built).** `docs/prd/PRD.md`(v1.0). 브리프 §25 전 항목을 구현 반영으로 구체화: 사용자·Use Case(primary user/trigger/workflow/human review point/success criteria), 데이터 8스키마(실제 dataclass 매핑 + 구현상태), 컴포넌트 12(모듈경로+상태), 평가(DEV/LOCKED/CHALLENGE·지표공식·확정임계·high-risk 정의·**error taxonomy E1~E9**·failure review template), 배포(local first·오프라인 재현·secrets·재현성). 아키텍처 다이어그램, Assurance 원칙 5, 로드맵/Non-goals, 문서 추적맵 포함. `docs/prd/failure_review_template.md` 신설(실측 실패 2건 예시=grounding 오탐·예외 recall). prd/README·STATE 갱신. 코드 변경 없음(테스트 112 유지).
- **2026-08-12** — ✅ **metrics_spec 임계값 확정 + regulatory_facts URL 채움.** 임계값 정책 §0-B 신설: 실패가 여신 결정을 조용히 뒤바꾸는 **고위험 실패모드=하드게이트(0누락/100%)**, 커버리지 지표=퍼센트 하한(Change ≥90%·Exception/Grandfathering Recall ≥95%·Citation ≥95%·Unsupported ≤5%·Escalation Recall ≥95%), 효율 지표=참고(임계 없음). 하드게이트: Effective-date·Policy-version·Source Contradiction·Rule-regression 전 카테고리·High-risk Miss·핵심예외/경과규정 고위험 누락. **high-risk 정의 4종 확정**(경과규정 오판·시행일 오적용·핵심예외 누락·rule conflict 자동처리) — §0-B 하드게이트와 1:1. 실측값 전 지표 임계 충족. metrics_spec §1~4 임계 컬럼·헤더 갱신. regulatory_facts: 문서 메타데이터(문서명·기관·발표/시행일·hash·retrieved_at) + **발행기관 공식출처**(금융위 www.fsc.go.kr / 국토부 www.molit.go.kr 보도자료) 확정 기입, **기사 permalink는 ⬜ 사용자 확인**(AI가 정부 URL 임의생성 금지 = citation integrity, LOCKED §8 정합). SOURCES.md 비고 갱신. DECISION_LOG 2건 기록. (코드 변경 없음 → 테스트 112 유지)
- **2026-08-12** — ✅ **가중 합성 모집단: 비중 실측화 + 수천 건 확장.** `src/regimpact/impact/population.py`. 세그먼트 weight를 문서화된 비중 모델(아키타입 모집단 점유율=DEFAULT_ARCHETYPES.weight, 지역 mix GURI35/YONGIN35/HWASEONG30 — 시나리오 가정·실측 아님)로 부여. `enumerate_weighted_profiles()`(아키타입×지역 24, weight=결합확률 합1) / `sample_portfolio(n=5000,seed=42)`(몬테카를로, 결정적 `random.Random`). `matrix.py`에 가중 집계 `direction_weight_share`/`review_weight_share`/`total_weight` 추가. **가중 임팩트(가정 기준): 강화 58% · 유지 24% · 검토 18% · 가중평균 Δ −20pp · 사람검토 필요 23%** — 몬테카를로 5000명이 정확 가중값에 수렴(테스트로 확인). **표본 회귀 5000/5000(engine⟷독립 오라클)** → metrics_spec §3 분모 수천 확대. `report.py` 임팩트 섹션에 '비중 기준' 요약 통합(report_6_30.html 갱신). `examples/demo_population.py`·`docs/eval/population_impact.md`(정직성 고지: 비중=가정, 실측 확보 시 표만 교체). 테스트 7개 추가(총 112) 통과.
- **2026-08-12** — ✅ **Rule Change Proposal 구조화 산출 + 리포트 통합.** `src/regimpact/rule_proposal.py`(`build_proposal`→`RuleChangeProposal`/`RuleDelta`). 파이프라인 마지막 조각: 추출된 각 변경을 룰엔진 실제 룰 표면(LTV_REGULATED_STANDARD·LTV_FIRST_HOME·LTV_REAL_DEMAND·LTV_MULTI·REG_EFFECTIVE·GRANDFATHERING_CUTOFF·REGION_VERSIONS)에 매핑하고 **사람 확정 엔진 현재값과 교차 대조**. 값 파싱(퍼센트/범위) + 키워드 매핑(생애최초/서민실수요/정책모기지/다주택/유주택). disposition 4종. **approval_status 항상 PENDING**(자동 확정 없음, LOCKED §4). 6·30 실제 추출(12건): 반영 7·코어밖 4(정책모기지+전세/신용/사업자→Discovery)·검토 1(중도금→잔금 미묘 룰)·**불일치 0**(AI 추출이 확정 엔진과 충돌 안 함) → "AI 초안이 사람 확정 룰과 일치/코어밖" Assurance 스토리. provenance(인용) 전건 보존. `report.py`에 '제안된 룰 변경(초안)' 섹션 통합(report_6_30.html 23KB), `examples/demo_rule_proposal.py`, `gen_report.py`에 연결. 테스트 15개 추가(총 105) 통과.
- **2026-08-12** — ✅ **골드셋 확대: 층화 합성 포트폴리오 + 3분할.** `tc_generator/portfolio.py`. 입력 차원(시나리오5·소유5·예외4·경과규정6·스코프)을 체계적 층화 스윕해 **178건** 결정적 생성(경과규정을 전용 층에 가두어 카테고리 균형; 초안 500/610→균형). 기대값은 독립 명세 오라클(`expected_outcome`, 엔진 미import)에서만 유도 → 대량에서도 tautology 아님. metrics_spec §3 분모 확대: **Rule-regression 178/178(100%)**, Boundary 40/40, Conflict 33/33. LOCKED §0-5: **DEV 52/LOCKED 59/CHALLENGE 67** 결정적 해시 분할(CHALLENGE 하드 카테고리 45% 가중), `cases_in_split()`로 개발중 DEV만 열람 강제 가능. `docs/eval/goldset_manifest.json`에 freeze(생성기와 정합성 테스트). regression에 `pass_rate_by_split()` + split×category 교차표. mutation test(엔진 상수 오염→회귀 실패)로 큰 골드셋의 이빨 확인. `examples/demo_portfolio.py`·`docs/eval/goldset_portfolio.md`. 테스트 9개 추가(총 90) 통과. **Anthropic 교차 실측은 사용자 결정으로 보류**(유료 API 미사용) — REST 백엔드는 준비 완료(`2dfc6cd`).
- **2026-08-12** — ✅ **UI 연동: HTML 리포트 생성기.** `src/regimpact/report.py`(`render_report`). PolicyImpact + 추출 + Assurance(grounding/gold)를 자체완결 HTML 대시보드로 렌더. **모든 값이 엔진/추출 실제 출력에서만** 오므로 Stitch 목업의 도메인 환각(세종·부산·LTV 60→50, `docs/ui/stitch_review.md`) 문제가 구조적으로 불가능 — 이게 "UI 연동"의 본질. DESIGN.md 디자인 언어(Institutional Navy #022448, Noto Sans/JetBrains Mono, 라이트/다크 대응). 섹션: 헤더밴드(정책·시행일·지역·비교시점) / Assurance 타일(Citation·환각·완전성·예외재현·지역) / 무엇이 달라졌나(추출 변경+원문 인용) / 누가 영향받나(지역 그룹핑 임팩트 표). `examples/gen_report.py`로 저장 추출→오프라인 실제 리포트 생성(`docs/ui/report_6_30.html` 18KB, 24행, 전 지표 녹색). `regions.py`에 REGION_DISPLAY_NAME 추가. 테스트 6개(실제값 존재·환각값 부재 회귀 포함, 총 81) 통과.
- **2026-08-12** — ✅ **추출 → Impact Matrix 실제 연결(E2E 진짜 데이터 관통).** `src/regimpact/impact/connect.py`(`impact_from_extraction`→`PolicyImpact`). LLM 추출의 policy_id·effective_from·target_regions(한글명)를 Impact Matrix 입력으로 연결: effective_from에서 before(−1일)/after(+1일) 유도, 지역명→코드 정규화(미상은 unmapped로 표면화), 각 정규화 지역 × 대표 고객유형(archetype 8종) → 세그먼트 → 룰엔진 before/after 차등. 저장 추출(`extractor_run_6_30_gemini.json`)로 오프라인 E2E 관통: 3지역×8=24행, 강화 9·유지 9·검토 6, 가중평균 Δ −20pp. LOCKED §4: LLM은 '정책·지역·시점' 좌표만 제공, LTV 판정은 deterministic 룰. `segments.py`를 archetype(지역 무관 템플릿)+`segments_for_region`으로 리팩터(하위호환 SIX_THIRTY_SEGMENTS 유지). connect는 extractor를 런타임 import하지 않음(레이어 독립, duck typing). ImpactMatrix에 regions/unmapped provenance, format_report에 노출. `examples/demo_extractor_to_impact.py`. 테스트 5개 추가(총 75) 통과.
- **2026-08-12** — ✅ **지역명→canonical code 정규화 계층.** 6·30 실측의 Regions MISS(발견 3: 추출이 지역을 한글명 "화성시 동탄구"로 반환, 룰엔진·골드는 code GURI 등) 대응. `regions.py`에 `resolve_region_code`(distinctive token '구리'·'기흥'·'동탄' 매칭 → 접두 '경기도'·'시'·'구'에 견고, code에 idempotent, 미상은 None) + `normalize_regions`((코드목록, 매핑실패목록) 반환 → 조용한 누락 금지) 추가. LOCKED §4: 지역 도메인 사전은 사람 확정. 채점(`score_against_gold`)은 추출 원본을 훼손하지 않고 비교 시점에만 코드로 정규화, `normalized_regions`/`unmapped_regions` 필드로 표면화. 저장된 2차 추출 오프라인 재채점 → **Regions MISS→OK**. `run_extractor.py` 출력에 정규화 지역 노출, 상위 패키지 export. 테스트 14개 추가(총 70) 통과. 다음: 추출→Impact Matrix 실제 연결.
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
