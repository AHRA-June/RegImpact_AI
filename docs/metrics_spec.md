# metrics_spec — 평가지표 정의

> **이 파일은 브리프 §13 지표에 공식·분모·임계값을 부여한다.** 코드보다 먼저 채운다.
> Model Risk 직무에서 실력이 드러나는 지점이므로 각 지표의 분모/분자를 모호하지 않게 정의한다.
>
> ✅ **상태: 임계값 확정(2026-08-11).** gate 철학 = **차등(tiered)**: 안전핵심 0-tolerance +
> recall 95% + 개별 miss 자동 escalate. 각 지표: `정의 / 분모 / 분자 / Gate / Target / tier / high-risk`.

---

## 0-Z. 임계값 tier 체계 (2026-08-11 확정)

gate 철학: **"완벽한 자동화"가 아니라 "검증 가능한 초안화 + 실패의 명시적 통제"**(브리프 §5).
따라서 안전을 자동판정 정확도가 아니라 **escalation**으로 보장하고, 지표 gate는 배포 판단선이다.

| tier | 성격 | Gate | 근거 |
|---|---|---|---|
| **T0 안전핵심** | 오판=regime 뒤바꿈/중대 오프라이싱 | **하드(0 또는 100%)** | deterministic 계열·고위험 자동처리·원문 충돌. n 무관. |
| **T1 고위험 recall** | 놓치면 위험하나 사람이 잡을 수 있음 | **Gate 95% / Target 100%** | 개별 miss는 **항상 자동 escalate**(silent error 불가). |
| **T2 완전성·grounding** | 초안 품질 | **Gate 90~95% / Target 100%** | 개별 실패도 escalate. |
| **T3 모니터링** | 효율성(안전 아님) | **하드 gate 없음**, 참고값 | precision·불필요 escalation 등. |

> **n 인식:** Gate는 LOCKED(n≈40) 집계 기준. 95% ≈ 최대 2건 허용이나 **개별 miss는 항상 사람 escalate**.
> deterministic 계열(§3)·Source Contradiction·High-risk Miss는 n 무관 하드(0/100%).
>
> **per-case ↔ 집계 정합:** 단일 시나리오 gate는 `assurance.AssuranceThresholds`가 구현한다. 개별 miss마다
> escalation을 쌓아 gate를 `REVIEW_REQUIRED`로 만들므로, 집계 gate 수치와 무관하게 **silent error가 불가능**하다.

---

## 0-A. 평가셋 규모·split (2026-08-10 확정)

- **총 규모: 100~120** (원안 150~200에서 축소, ADJUSTABLE). 질 우선, CHALLENGE 강화.
- **확정 split (권장, 총 ~115):**
  | Split | 규모 | 용도 |
  |---|---:|---|
  | DEV | 40 | 프롬프트·retrieval·extractor 튜닝 |
  | LOCKED TEST | 40 | 최종 성능평가 (개발 중 튜닝 금지) |
  | CHALLENGE | 35 | 예외·경계·충돌·모호 중심 적대적 평가 |
- CHALLENGE는 EXCEPTION / GRANDFATHERING / EFFECTIVE_DATE / CONFLICT 가중.
- 성공 기준: 건수 채우기가 아니라 **실패모드 카테고리 커버리지**.

## 0. 공통 원칙

- 모든 지표는 **골드셋(DEV/LOCKED/CHALLENGE)** 또는 **룰엔진 회귀 fixture** 위에서 계산.
- LOCKED TEST / CHALLENGE는 개발 중 튜닝 루프에 쓰지 않음 (브리프 §12).
- 최종 KPI 관점: 단순 정확도가 아니라 **AI Error → Decision/Operational Risk 전파**를 본다 (브리프 §13.5).

### 구현 깊이 정책 (2026-08-10 결정, `02_DECISION_LOG.md`)

Assurance 체크를 전부 동일 깊이로 만들지 않는다. 깊이 태그:

- **[DEEP]** — 정량 측정하는 4개 dimension. 골드셋/회귀로 숫자가 나오고 보고서의 핵심.
  1. Source Grounding & Citation → §2 + Citation Correctness
  2. Change & Exception Completeness → Change Completeness, Exception Recall, Grandfathering Recall
  3. Temporal / Policy-Version Consistency → Policy-version Consistency, Effective-date Accuracy
  4. Rule Regression & Conflict → §3 전체
- **[ROADMAP]** — 정의+루브릭+소규모 예시만. Human Escalation 계열(§4).
- **[INFRA]** — metric이 아니라 항상 켜지는 인프라. Audit trail, Approval status field. (§13 밖, `docs/00_BRIEF.md` §16~17)

각 지표 표의 맨 앞에 깊이 태그를 붙인다.

---

## 1. RegChange / RAG 계열 (브리프 §13.1) — [DEEP] dimension ②③

| 지표 | 정의 | 분모 | 분자 | Gate | Target | tier | high-risk |
|---|---|---|---|---|---|---|---|
| Change Completeness | 원문의 실제 변경사항 중 시스템이 포착한 비율 | 골드 변경 항목 수 | 정확 포착 수 | **≥90%** | 100% | T2 | 놓침=위험(escalate) |
| Exception Recall | 예외조건(생애최초·정책대출 등) 중 포착 비율 | 골드 예외 수 | 포착 수 | **≥95%** | 100% | T1 | ★ 높음 |
| Grandfathering Recall | 경과규정 적용대상 판정 중 포착 비율 | 골드 경과규정 케이스 | 정확 판정 | **≥95%** | 100% | T1 | ★ 높음 |
| Effective-date Accuracy | 시행일 정확 추출 비율 | 시행일 있는 케이스 | 정확 케이스 | **≥95%** | 100% | T1 | ★ 높음 |
| Citation Correctness | 인용이 실제 원문 위치와 일치하는 비율 | 생성 인용 수 | 정확 인용 수 | **≥95%** | 100% | T2 | 중 |
| Policy-version Consistency | 특정 시점 유효 버전을 일관되게 반환하는 비율 | 시점 질의 수 | 정확 반환 수 | **≥95%** | 100% | T1 | ★ 높음 |

## 2. Hallucination 계열 — 분리 측정 (브리프 §13.2) — [DEEP] dimension ①

> `hallucination rate` 단일 지표로 뭉뚱그리지 않는다.

| 지표 | 정의 | 분모 | 분자 | Gate | Target | tier |
|---|---|---|---|---|---|---|
| Unsupported Claim Rate | 원문 근거 없이 생성된 정책 주장 비율 | 생성된 정책 주장 총수 | 근거 없는 주장 수 | **≤5%** | 0% | T2 |
| Source Contradiction Rate | 원문과 명시적으로 충돌하는 주장 비율 | 생성된 정책 주장 총수 | 원문 충돌 주장 수 | **=0 (하드)** | 0% | T0 |

> Unsupported Claim Rate = 1 − Citation Correctness(이진 grounding 가정) → `check_citation_grounding`이 실측.
> Source Contradiction은 원문과 **명시적 충돌**(단순 미근거보다 강함)이므로 0-tolerance(T0).

## 3. Rule / Test 계열 (브리프 §13.3) — [DEEP] dimension ④

> ✅ **구현: `src/regimpact/tc_generator/`** — 룰엔진을 **독립 명세 오라클(challenger)** 로 차등 검증.
> 기대값을 엔진 자신이 아니라 명세(§H)에서 독립 유도 → 회귀가 tautology가 되지 않음.
> `run_regression()` 이 아래 지표를 카테고리별로 산출(`report.pass_rate_by_category()`).
> mutation test로 fixture 방어력 확인(엔진 버그 주입 시 회귀 실패). 현재 30 케이스 전 항목 100%.

| 지표 | 정의 | 분모 | 분자 | Gate | tier | 현재값 |
|---|---|---|---|---|---|---|
| Rule-regression Pass Rate | 회귀 fixture 중 룰엔진 통과 비율 | 회귀 TC 수 | 통과 수 | **=100% (하드)** | T0 | 30/30 (100%) |
| Expected vs Actual Match Rate | TC의 기대결과와 실제 판정 일치율 | 전체 TC | 일치 TC | **=100% (하드)** | T0 | 30/30 |
| Boundary-case Pass Rate | 경계 케이스 통과율 | 경계 TC | 통과 | **=100% (하드)** | T0 | 8/8 |
| Conflict-case Pass Rate | 충돌 케이스에서 올바르게 escalate/판정한 비율 | 충돌 TC | 정답 | **=100% (하드)** | T0 | 5/5 |

> §3은 deterministic 룰엔진 회귀이므로 n 무관 **하드 100%**. 실패는 명세↔구현 불일치(회귀)이며
> 사람 튜닝이 아니라 코드 수정으로만 해소한다. Proposal→TC fidelity(engine⟷proposal)도 같은 하드 기준.

> 주: 현재값은 6·30 시나리오 소규모 seed 케이스 기준. 층화 합성 포트폴리오(2,000~5,000, `04_PLAN.md` Phase 2)로 확대 예정.

## 4. Human Escalation 계열 (브리프 §13.4) — [ROADMAP]

> 2026-08-10 결정에 따라 이 계열은 MVP에서 "정의+루브릭+소규모 예시"로 둔다(정량 딥다이브 아님).
> escalation을 [DEEP] 4번으로 승격하려면 `03_OPEN_QUESTIONS.md` Q2 여백 참고.
>
> `human override rate` 자체를 품질지표로 쓰지 않는다.

| 지표 | 정의 | 분모 | 분자 | Gate | tier | high-risk |
|---|---|---|---|---|---|---|
| Escalation Recall | 반드시 사람 검토 필요한 건 중 escalate한 비율 | 검토 필수 건 | escalate된 건 | **≥95%** (Target 100%) | T1 | ★ 최고 |
| Escalation Precision | 사람에게 넘긴 건 중 실제 검토 필요 비율 | escalate된 건 | 실제 필요 건 | 모니터링(참고 ≥70%) | T3 | 중 |
| High-risk Miss Rate | 반드시 escalate해야 할 고위험 건을 자동처리한 비율 | 고위험 건 | 자동처리된 고위험 건 | **=0 (하드)** | T0 | ★ 최고 |
| Unnecessary Escalation Rate | 자동처리 가능 건을 불필요하게 넘긴 비율 | 자동처리 가능 건 | 넘긴 건 | 모니터링(참고 ≤20%) | T3 | 낮음 |

> [ROADMAP] 계열이라 값은 확정하되 정량 딥다이브는 Phase 3. **High-risk Miss Rate=0은 하드**(안전핵심):
> 고위험 건을 자동처리로 덮으면 즉시 fail. Escalation Precision/불필요 escalation은 효율성 지표로 gate 없음.

---

## high-risk failure 정의 (2026-08-11 확정)

> "High-risk Miss Rate" 등을 측정하려면 **어떤 케이스가 high-risk인지**를 먼저 정의해야 한다.
> 공통 성격: **오판이 regime(종전/신규·규제전후)을 뒤바꾸거나 LTV를 중대하게 오프라이싱**하는 것.

확정된 high-risk 케이스 (모두 T0 — 자동처리 금지, escalate 필수):
- **경과규정 오판** — 종전/신규 규정을 뒤바꾸는 케이스 (컷오프 경계 ±1일 포함)
- **시행일 오판** — 규제 전/후를 뒤바꾸는 케이스 (효력일 경계)
- **예외 누락** — 생애최초·서민실수요·정책대출을 놓쳐 LTV를 과소/과대 적용
- **정책 간 rule conflict를 자동처리로 덮음** — 우선순위 충돌·상충 명세를 escalate 없이 판정
- **유주택 '기존 LTV' 기준부재를 임의값으로 채움** — 명세 부재를 escalate하지 않고 자동판정 (Impact Matrix `BASELINE_GAP` 참고)

---

## 보고서의 한계 명시 (브리프 §12)

> "The locked test set was frozen before system tuning, but was authored within the project and is not an independent third-party benchmark."

n 규모는 통계적 검정력이 아니라 **실패모드 층화 커버리지**를 목표로 함을 명시.
