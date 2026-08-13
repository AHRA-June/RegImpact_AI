# RegImpact AI

> **생성형 AI 기반 주택담보대출 규제 변경 영향분석 및 검증 시스템**
> RegChange AI — Financial Policy Impact & Assurance Lab

정부의 가계대출 정책이 바뀌었을 때, 공식 원문에서 **무엇이 달라졌는지**를 탐지하고,
그 변경이 **여신 Rule · 고객 영향 · 테스트케이스**로 어떻게 전파되는지를
**검증 가능한(auditable) 방식으로** 산출하는 의사결정 지원 시스템.

핵심 메시지:
> "규제가 바뀌었을 때 무엇을 고쳐야 하는지 AI가 제안하고,
> 그 제안이 틀리지 않았는지 검증 가능한 방식으로 증명하는 시스템."

- **제품(E)** = 규제 변경 영향분석 (RegChange / Impact Analysis)
- **신뢰 기반(A)** = AI 결과의 검증·통제 (Assurance Layer)
- 챗봇이 아니라 **검증 가능한 의사결정 지원 시스템**.

용도: 이직 포트폴리오 (금융권 Model Risk / 모델검증 / AI Governance / AI Assurance / AI Evaluation 직무).

---

## 이 저장소를 처음 보는 사람(또는 새 Claude 세션)에게

**작업을 이어받으려면 반드시 아래 순서로 읽으세요.**

1. **`docs/01_PROJECT_STATE.md`** ← 지금 어디까지 왔는지, 다음 액션이 무엇인지 (가장 먼저!)
2. `docs/00_BRIEF.md` ← 프로젝트 철학·범위·LOCKED 원칙 (정체성 문서, 원본 보존)
3. `docs/02_DECISION_LOG.md` ← 지금까지의 결정과 그 이유
4. `docs/04_PLAN.md` ← 현재 유효한 실행 계획(수직 슬라이스 우선, 9~10주)
5. `docs/03_OPEN_QUESTIONS.md` ← 사용자 확인이 필요한 대기 항목
6. `docs/regulatory_facts.md` ← 6·30 규제 사실의 단일 기준점
7. `docs/metrics_spec.md` ← 평가지표 정의

> ⚠️ 이 프로젝트는 개발 도중 Claude 계정이 교체됩니다.
> **모든 상태는 이 저장소 안에만** 존재합니다. 대화 메모리에 의존하지 마세요.
> 매 작업 종료 시 `01_PROJECT_STATE.md`를 갱신하는 것이 규칙입니다.

---

## 문서 지도

| 파일 | 역할 |
|---|---|
| `README.md` | 프로젝트 1분 요약 + 인계 안내 (이 파일) |
| `docs/00_BRIEF.md` | 프로젝트 브리프 v2 — 정체성·범위·LOCKED 원칙 (원본 보존, 임의 수정 금지) |
| `docs/01_PROJECT_STATE.md` | **살아있는 상태판** — 현재 위치, 다음 3개 액션, 블로커 |
| `docs/02_DECISION_LOG.md` | 의사결정 이력 (날짜·결정·이유·이전값) |
| `docs/03_OPEN_QUESTIONS.md` | 사용자 확인 대기 항목 |
| `docs/04_PLAN.md` | **현재 유효 실행 계획** — 수직 슬라이스 우선, 총 9~10주 |
| `docs/05_RULE_SPEC.md` | 룰엔진 규칙 명세 (LOCKED §4 — ✍️ 사용자 작성 / 🔧 스캐폴드 / 🤖 AI초안) |
| `docs/sources/` | 공문 원본 스냅샷 + 추출 텍스트 + 해시 (SOURCES.md 레지스트리) |
| `docs/ui/stitch_prompts.md` | UI 목업용 Google Stitch 프롬프트 모음(5개 화면) |
| `src/regimpact/` | **deterministic LTV 룰엔진** (알고리즘 H 구현, 검증 기준점) |
| `src/regimpact/extractor/` | **RegChange Extractor(E) + Citation Assurance(A)** — 공문→추출→검증 |
| `src/regimpact/tc_generator/` | **TC Generator + Rule-Regression + 층화 합성 포트폴리오** — 독립 명세 오라클로 룰엔진 차등 검증(Assurance ④), ~3천 규모 확대 |
| `src/regimpact/impact/` | **Impact Matrix + E2E Pipeline** — Source→…→Validation Report 관통(Walking Skeleton) |
| `src/regimpact/goldset/` | **골드 평가셋** — 브리프 §11 스키마·결정적 채점·DEV/LOCKED/CHALLENGE 분리 |
| `docs/eval/` | 골드 정답지 + `goldset/`(115문항: DEV40/LOCKED40/CHALLENGE35) + Extractor run1 실측 |
| `tests/` | 테스트 하네스 (pytest, 68개) |
| `examples/` | 룰엔진 / Extractor / TC 회귀 / **E2E 관통** / **포트폴리오 회귀** / **골드셋** 데모 |
| `docs/regulatory_facts.md` | 규제 사실 + 인용 (골드셋·룰엔진·Proposal 공통 기준점) |
| `docs/metrics_spec.md` | 평가지표 정의·분모·임계값·high-risk 정의 |
| `docs/prd/` | 정식 PRD (작성 예정) |

## 현재 상태

🟢 **Phase 1 관통 완료 → Phase 2 진행** — 룰엔진 v1 + Extractor(실측 run1) + TC Generator/Rule-Regression + **Impact Matrix E2E** + **층화 합성 포트폴리오(~3천)** + **골드셋 115문항(AI_DRAFT)**(테스트 68개 통과). 6·30 1건 Source→Report 오프라인 관통, 차등검증 수천 규모, 결정적 채점 골드셋 규모 목표 도달(사람 확정 대기). 자세한 내용은 `docs/01_PROJECT_STATE.md` 참고.

```bash
python -m pytest && python examples/demo_e2e_6_30.py && python examples/demo_portfolio_regression.py && python examples/demo_goldset.py
```

## 개발 브랜치

`claude/work-start-dq1gtz`
