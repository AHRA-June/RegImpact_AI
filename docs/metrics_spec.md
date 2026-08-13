# metrics_spec — 평가지표 정의

> **이 파일은 브리프 §13 지표에 공식·분모·임계값을 부여한다.** 코드보다 먼저 채운다.
> Model Risk 직무에서 실력이 드러나는 지점이므로 각 지표의 분모/분자를 모호하지 않게 정의한다.
>
> ⚠️ **상태: 스켈레톤.** 아래 정의는 초안이며 사용자 도메인 검수·확정 필요.
> 각 지표: `정의 / 분모 / 분자 / pass-fail 임계 / high-risk 여부 / 산출 데이터원`.

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

| 지표 | 정의(초안) | 분모 | 분자 | 임계(초안) | high-risk |
|---|---|---|---|---|---|
| Change Completeness | 원문의 실제 변경사항 중 시스템이 포착한 비율 | 골드 변경 항목 수 | 정확 포착 수 | TBD | 놓침=위험 |
| Exception Recall | 예외조건(생애최초·정책대출 등) 중 포착 비율 | 골드 예외 수 | 포착 수 | TBD | ★ 높음 |
| Grandfathering Recall | 경과규정 적용대상 판정 중 포착 비율 | 골드 경과규정 케이스 | 정확 판정 | TBD | ★ 높음 |
| Effective-date Accuracy | 시행일 정확 추출 비율 | 시행일 있는 케이스 | 정확 케이스 | TBD | ★ 높음 |
| Citation Correctness | 인용이 실제 원문 위치와 일치하는 비율 | 생성 인용 수 | 정확 인용 수 | TBD | 중 |
| Policy-version Consistency | 특정 시점 유효 버전을 일관되게 반환하는 비율 | 시점 질의 수 | 정확 반환 수 | TBD | ★ 높음 |

## 2. Hallucination 계열 — 분리 측정 (브리프 §13.2) — [DEEP] dimension ①

> `hallucination rate` 단일 지표로 뭉뚱그리지 않는다.

| 지표 | 정의(초안) | 분모 | 분자 | 임계 |
|---|---|---|---|---|
| Unsupported Claim Rate | 원문 근거 없이 생성된 정책 주장 비율 | 생성된 정책 주장 총수 | 근거 없는 주장 수 | 낮을수록 좋음, TBD |
| Source Contradiction Rate | 원문과 명시적으로 충돌하는 주장 비율 | 생성된 정책 주장 총수 | 원문 충돌 주장 수 | 0에 가까울수록, TBD |

### ✅ 실측 결과 (2026-08-13) — dimension ①②③

> 6·30 원문 3건 grounded 추출(`docs/eval/regchange_extracted_6_30.json`)을 결정론 채점 하네스에
> 통과시킨 실측. 재현: `python examples/measure_assurance_6_30.py` → `docs/reports/assurance_6_30.md`.
> provenance: Claude Code 세션 수동 grounded 추출(자동 claude-opus-5 API 무인 실행은 키 확보 후). n=1 문서셋.

| 지표 | dimension | v1(1차) | v2(반복 후) | 비고 |
|---|---|---|---|---|
| Citation Correctness | ① | 100% (9/9) | **100%** (10/10) | 인용 전부 원문 verbatim |
| Unsupported Claim Rate | ① | 0% | **0%** | 환각 인용 0 |
| Change Completeness | ② | 100% (4/4) | **100%** (4/4) | 골드 필수 변경 전부 포착 |
| Exception Recall | ② | 50% (1/2) | **100%** (2/2) | v1: 서민·실수요 누락 → Assurance 포착 → v2 보완 |
| Effective-date Accuracy | ③ | OK | **OK** | 2026-07-01 정확 |
| Policy/Region Consistency | ③ | OK | **OK** | 3개 지역 정확 |

> **해석(Assurance 피드백 루프):** v1은 저환각(0%)/완전한 인용(100%)을 달성한 대신 보수적 추출이
> 서민·실수요 예외를 놓쳐 **Exception Recall 50%** — 이를 **Assurance가 고위험 예외 miss로 포착**
> (프롬프트 "완전성보다 저환각 우선" tradeoff). v2에서 FAQ Q2 원문 근거(verbatim)로 해당 예외를
> 보완 → **Exception Recall 100%**, 인용 무결성(0% 환각)은 유지. **측정 → 결함 포착 → 보완**의
> 검증 루프가 실제로 한 바퀴 돈 사례(이 프로젝트의 핵심 가치제안).

## 3. Rule / Test 계열 (브리프 §13.3) — [DEEP] dimension ④

> ✅ **구현: `src/regimpact/tc_generator/`** — 룰엔진을 **독립 명세 오라클(challenger)** 로 차등 검증.
> 기대값을 엔진 자신이 아니라 명세(§H)에서 독립 유도 → 회귀가 tautology가 되지 않음.
> `run_regression()` 이 아래 지표를 카테고리별로 산출. **층화 합성 포트폴리오 106건**(seed 30 → 확대,
> `generate_portfolio()`)로 통계화 — split(DEV/LOCKED/CHALLENGE) 전량 측정, `format_portfolio_stats()`.
> mutation test로 fixture 방어력 확인(엔진 버그 주입 시 회귀 실패, seed·포트폴리오 양쪽).

| 지표 | 정의(초안) | 분모 | 분자 | 임계 | seed(30) | 포트폴리오(106) |
|---|---|---|---|---|---|---|
| Rule-regression Pass Rate | 회귀 fixture 중 룰엔진 통과 비율 | 회귀 TC 수 | 통과 수 | 100% 목표 | 30/30 (100%) | **106/106 (100%)** |
| Expected vs Actual Match Rate | TC의 기대결과와 실제 판정 일치율 | 전체 TC | 일치 TC | 100% | 30/30 | **106/106** |
| Boundary-case Pass Rate | 경계 케이스 통과율 | 경계 TC | 통과 | 100% | 8/8 | **19/19** |
| Conflict-case Pass Rate | 충돌 케이스에서 올바르게 escalate/판정한 비율 | 충돌 TC | 정답 | 100% | 5/5 | **10/10** |

**층화 포트폴리오 통계 (2026-08-13, `docs/reports/rule_portfolio_stats.md`):**
- N=106, Pass Rate 100%. split: DEV 36 / LOCKED 35 / CHALLENGE 35(전량 측정, 각 100%).
- 카테고리: SCOPE 18 / BASELINE 25 / EXCEPTION 21 / BOUNDARY 19 / GRANDFATHERING 13 / CONFLICT 10.
- 커버리지: status 4종 전부 / rule_id 6 / reason_code 11.
- **split 전량 측정 정당성:** 룰엔진은 결정론(성능 튜닝 루프 없음)이라 LOCKED/CHALLENGE를 열어도
  누수 위험이 없다(`04_PLAN.md` §0-5 정합). LLM 추출용 골드셋의 LOCKED/CHALLENGE 봉인 원칙과 별개.

> 주: n=106은 통계적 검정력이 아니라 **실패모드 층화 커버리지 + 넓은 입력공간에서의 명세 일치**가 목표.
> 정답은 독립 오라클이 유도(차등검증) → 손라벨 없이 확장. 추가 확대(수천 건)는 후속.

## 4. Human Escalation 계열 (브리프 §13.4) — [ROADMAP]

> 2026-08-10 결정에 따라 이 계열은 MVP에서 "정의+루브릭+소규모 예시"로 둔다(정량 딥다이브 아님).
> escalation을 [DEEP] 4번으로 승격하려면 `03_OPEN_QUESTIONS.md` Q2 여백 참고.
>
> `human override rate` 자체를 품질지표로 쓰지 않는다.

| 지표 | 정의(초안) | 분모 | 분자 | high-risk |
|---|---|---|---|---|
| Escalation Recall | 반드시 사람 검토 필요한 건 중 escalate한 비율 | 검토 필수 건 | escalate된 건 | ★ 최고 |
| Escalation Precision | 사람에게 넘긴 건 중 실제 검토 필요 비율 | escalate된 건 | 실제 필요 건 | 중 |
| High-risk Miss Rate | 반드시 escalate해야 할 고위험 건을 자동처리한 비율 | 고위험 건 | 자동처리된 고위험 건 | ★ 최고 (0 목표) |
| Unnecessary Escalation Rate | 자동처리 가능 건을 불필요하게 넘긴 비율 | 자동처리 가능 건 | 넘긴 건 | 낮음 |

---

## high-risk failure 정의 (초안 — 확정 필요)

> "High-risk Miss Rate" 등을 측정하려면 **어떤 케이스가 high-risk인지**를 먼저 정의해야 한다.

high-risk 후보 (사용자 검수 필요):
- 경과규정 오판으로 종전/신규 규정을 뒤바꾸는 케이스
- 시행일을 잘못 적용해 규제 전/후를 뒤바꾸는 케이스
- 예외(생애최초·정책대출)를 놓쳐 LTV를 과소/과대 적용하는 케이스
- 서로 다른 정책 간 rule conflict를 자동처리로 덮는 케이스

---

## 보고서의 한계 명시 (브리프 §12)

> "The locked test set was frozen before system tuning, but was authored within the project and is not an independent third-party benchmark."

n 규모는 통계적 검정력이 아니라 **실패모드 층화 커버리지**를 목표로 함을 명시.
