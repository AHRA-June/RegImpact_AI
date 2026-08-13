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
8. `docs/features/` ← 기능단위·워크플로우 문서(버전별). 규칙: `docs/features/_VERSIONING.md`

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
| `docs/features/` | **기능단위·워크플로우 문서(버전별 관리)** — 규칙은 `docs/features/_VERSIONING.md` |
| `docs/sources/` | 공문 원본 스냅샷 + 추출 텍스트 + 해시 (SOURCES.md 레지스트리) |
| `docs/ui/stitch_prompts.md` | UI 목업용 Google Stitch 프롬프트 모음(5개 화면) |
| `src/regimpact/` | **deterministic LTV 룰엔진** (알고리즘 H 구현, 검증 기준점) |
| `src/regimpact/extractor/` | **RegChange Extractor(E) + Citation Assurance(A)** — 공문→추출→검증 |
| `src/regimpact/tc_generator/` | **TC Generator + Rule-Regression** — 독립 명세 오라클로 룰엔진 차등 검증(Assurance ④) |
| `src/regimpact/impact/` | **Impact Matrix(Before/After)** — 룰엔진 시행 전/후 temporal diff로 세그먼트별 LTV 영향 산출 + UI 렌더 |
| `src/regimpact/proposal/` | **Rule Change Proposal** — ImpactMatrix→구조화 룰변경 초안(AI초안→사람확정) |
| `src/regimpact/assurance/` | **Assurance Scorecard** — 4 dimension 12지표 + 확정 임계값(Strict) 판정 |
| `src/regimpact/validation/` | **Validation Report** — 파이프라인 산출을 검증보고서(md + 정식 HTML)로 조립 |
| `docs/eval/` | 골드 정답지 (RegChange 채점 기준) |
| `tests/` | 테스트 하네스 (pytest, 110개) |
| `examples/` | 룰엔진 / Extractor / TC 회귀·포트폴리오 / Impact Matrix / UI / E2E / Assurance 실측·스코어카드 |
| `docs/regulatory_facts.md` | 규제 사실 + 인용 (골드셋·룰엔진·Proposal 공통 기준점) |
| `docs/metrics_spec.md` | 평가지표 정의·분모·임계값·high-risk 정의 |
| `docs/prd/` | **정식 PRD (버전별)** — `regchange-ai/regchange-ai_v1.md` |
| `docs/cards/` | **Model/System Card (버전별)** — AI 거버넌스 투명성 산출물 |

## 현재 상태

🟢 **코어 완성선 도달** — 룰엔진 + Extractor + TC Generator + Impact Matrix + Rule Proposal + Assurance Scorecard + Validation Report(테스트 110개 통과). **6·30 E2E 전 노드 관통 · Assurance 4 dimension 12/12 PASS · 룰 평가셋 3계층(30 / 106 / 3,200) 전부 100% · 정식 검증보고서(약 17쪽) 완성**. PRD `docs/prd/`, 정식 보고서 `docs/reports/validation_report_6_30_full.md`. 자세한 내용은 `docs/01_PROJECT_STATE.md`.

```bash
python -m pytest                          # 110개
python examples/demo_e2e.py               # E2E 관통 → 검증보고서 md + 정식 HTML
python examples/assurance_scorecard.py    # 4 dimension 스코어카드(확정 임계값)
python examples/demo_portfolio.py         # 큐레이션 106 + 조합 격자 3,200 통계
```

## 개발 브랜치

`claude/work-in-progress-d2et38`
