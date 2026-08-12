# metrics_spec — 평가지표 정의

> **이 파일은 브리프 §13 지표에 공식·분모·임계값을 부여한다.** 코드보다 먼저 채운다.
> Model Risk 직무에서 실력이 드러나는 지점이므로 각 지표의 분모/분자를 모호하지 않게 정의한다.
>
> ✅ **임계값 확정(2026-08-12):** §0-B 정책(고위험=하드게이트, 나머지=퍼센트 하한)으로 전 지표 임계 확정.
> high-risk failure 정의도 확정. 모두 ADJUSTABLE(방법론 결정, LOCKED 아님). 실측값은 현재 전 지표 임계 충족.
> 각 지표: `정의 / 분모 / 분자 / pass-fail 임계 / high-risk 여부 / 현재값`.

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

## 0-B. 임계값 정책 (2026-08-12 확정 · ADJUSTABLE)

> 임계값은 임의의 퍼센트가 아니라 **risk tolerance의 표현**이다. 실패가 실제 차주의 여신 결정을
> 조용히 뒤바꿀 수 있으면 tolerance는 **0**이다.

- **하드 게이트(0 누락 / 100%)** — 실패가 의사결정을 뒤바꾸는 고위험 실패모드에 적용.
  단 1건이라도 위반하면 **fail**(퍼센트로 완화하지 않는다).
  → Effective-date Accuracy, Policy-version Consistency, Source Contradiction Rate,
    Rule-regression(전 카테고리), High-risk Miss Rate, 그리고 핵심 예외·경과규정의 **고위험 누락**.
- **퍼센트 하한** — 누락이 사람 검토로 포착되고 결정을 조용히 뒤바꾸지 않는 커버리지 지표에 적용.
  → Change Completeness ≥ 90%, Exception/Grandfathering Recall ≥ 95%, Citation Correctness ≥ 95%,
    Unsupported Claim Rate ≤ 5%, Escalation Recall ≥ 95%.
- **참고(임계 없음)** — 효율 지표. 방향만 본다. → Escalation Precision, Unnecessary Escalation Rate.

근거: 임의의 95%/99%보다 "고위험=0 tolerance"가 Model Risk 관점에서 방어 가능하고, 이 프로젝트의
high-risk 정의(아래)와 직접 연결된다. **표기 규칙:** 아래 표의 임계는 `퍼센트 하한` 또는 `하드게이트`.

---

## 1. RegChange / RAG 계열 (브리프 §13.1) — [DEEP] dimension ②③

> 📊 **첫 실측(2026-08-12):** Gemini(`gemini-flash-latest`)로 6·30 공문 3건 추출.
> 상세·발견은 `docs/eval/extractor_run_6_30.md`. 아래 "현재값"은 정책 n=1 seed 기준(소규모).

| 지표 | 정의 | 분모 | 분자 | 임계(확정) | high-risk | 현재값(6·30) |
|---|---|---|---|---|---|---|
| Change Completeness | 원문의 실제 변경사항 중 시스템이 포착한 비율 | 골드 변경 항목 수 | 정확 포착 수 | **≥ 90%** | 놓침=위험 | **100%** (4/4) |
| Exception Recall | 예외조건(생애최초·정책대출 등) 중 포착 비율 | 골드 예외 수 | 포착 수 | **≥ 95% + 핵심예외 0누락(하드게이트)** | ★ 높음 | **100%** (2/2) ✅ |
| Grandfathering Recall | 경과규정 적용대상 판정 중 포착 비율 | 골드 경과규정 케이스 | 정확 판정 | **≥ 95% + 고위험 0누락(하드게이트)** | ★ 높음 | 포착(정성) |
| Effective-date Accuracy | 시행일 정확 추출 비율 | 시행일 있는 케이스 | 정확 케이스 | **100%(하드게이트)** | ★ 높음 | **OK** (1/1) |
| Citation Correctness | 인용이 실제 원문 위치와 일치하는 비율 | 생성 인용 수 | 정확 인용 수 | **≥ 95%** | 중 | **100%** (12/12) |
| Policy-version Consistency | 특정 시점 유효 버전을 일관되게 반환하는 비율 | 시점 질의 수 | 정확 반환 수 | **100%(하드게이트)** | ★ 높음 | (미측정) |

> ✅ **Exception Recall 50%→100%**(2026-08-12): 프롬프트 개선(예외 개별 분리)으로 서민·실수요 포착.
> 항목 6→12건으로 세분화돼도 Citation 100%·환각 0% 유지.
> ✅ **Regions MISS→OK**(2026-08-12): 지역명→canonical code **정규화 계층**(`regions.normalize_regions`)
> 추가. 추출은 한글명 보존, 채점 시점에만 코드로 대조. 미상 지역은 `unmapped`로 표면화. 상세 `extractor_run_6_30.md`.

## 2. Hallucination 계열 — 분리 측정 (브리프 §13.2) — [DEEP] dimension ①

> `hallucination rate` 단일 지표로 뭉뚱그리지 않는다.

| 지표 | 정의 | 분모 | 분자 | 임계(확정) | 현재값(6·30) |
|---|---|---|---|---|---|
| Unsupported Claim Rate | 원문 근거 없이 생성된 정책 주장 비율 | 생성된 정책 주장 총수 | 근거 없는 주장 수 | **≤ 5%** (목표 0%) | **0%** (0/6) |
| Source Contradiction Rate | 원문과 명시적으로 충돌하는 주장 비율 | 생성된 정책 주장 총수 | 원문 충돌 주장 수 | **0%(하드게이트)** | (미측정) |

> ⚠️ **측정 아티팩트 주의(2026-08-12 실측에서 발견):** 초기 Unsupported Claim Rate가 33%로
> 나왔으나, 이는 원문 PDF의 문장 중간 줄바꿈을 공백정규화가 공백으로 바꿔 **정확한 인용을 오탐**한
> 것이었다. grounding 비교를 공백 무관(`_squish`)으로 보정 후 0%. → 지표 신뢰성은 채점기의
> 텍스트 정규화 견고성에 의존. 상세: `docs/eval/extractor_run_6_30.md`.

## 3. Rule / Test 계열 (브리프 §13.3) — [DEEP] dimension ④

> ✅ **구현: `src/regimpact/tc_generator/`** — 룰엔진을 **독립 명세 오라클(challenger)** 로 차등 검증.
> 기대값을 엔진 자신이 아니라 명세(§H)에서 독립 유도 → 회귀가 tautology가 되지 않음.
> `run_regression()` 이 아래 지표를 카테고리별로 산출(`report.pass_rate_by_category()`).
> mutation test로 fixture 방어력 확인(엔진 버그 주입 시 회귀 실패). 현재 30 케이스 전 항목 100%.

| 지표 | 정의(초안) | 분모 | 분자 | 임계 | 현재값(seed 30) | 현재값(포트폴리오 178) |
|---|---|---|---|---|---|---|
| Rule-regression Pass Rate | 회귀 fixture 중 룰엔진 통과 비율 | 회귀 TC 수 | 통과 수 | **100%(하드게이트)** | 30/30 (100%) | **178/178 (100%)** |
| Expected vs Actual Match Rate | TC의 기대결과와 실제 판정 일치율 | 전체 TC | 일치 TC | **100%(하드게이트)** | 30/30 | **178/178** |
| Boundary-case Pass Rate | 경계 케이스 통과율 | 경계 TC | 통과 | **100%(하드게이트)** | 8/8 | **40/40** |
| Conflict-case Pass Rate | 충돌 케이스에서 올바르게 escalate/판정한 비율 | 충돌 TC | 정답 | **100%(하드게이트)** | 5/5 | **33/33** |

> **왜 하드게이트인가:** 오라클은 확정 명세(§H)에서 독립 유도되므로, 단 1건의 disagreement도
> "엔진이 명세를 틀리게 구현" 또는 "명세 모호성"을 뜻한다 — 퍼센트로 완화할 수 없다. 표본 회귀
> 5,000/5,000도 100%(`population_impact.md`).

> ✅ **골드셋 확대(2026-08-12):** 층화 합성 포트폴리오 **178건**(DEV 52 / LOCKED 59 / CHALLENGE 67,
> CHALLENGE 하드 카테고리 가중)으로 분모 확대. 기대값은 독립 명세 오라클에서 유도(tautology 방지),
> 결정적 생성 + `docs/eval/goldset_manifest.json` freeze(LOCKED §0-5 3분할). mutation test로 이빨 확인.
> 상세: `docs/eval/goldset_portfolio.md`.
>
> ✅ **수천 건 확장 + 비중 실측화(2026-08-12):** 문서화된 비중 모델에서 **5,000명 몬테카를로 표본**을
> 뽑아 룰-회귀 분모를 수천으로 확대 → **5,000/5,000 100%**(engine ⟷ 독립 오라클). 동시에 **가중
> 포트폴리오 임팩트**(강화 58% · 유지 24% · 검토 18% · 가중평균 Δ −20pp · 사람검토 23%) 산출.
> 비중은 실측 아닌 문서화된 가정. 상세: `docs/eval/population_impact.md`.

## 4. Human Escalation 계열 (브리프 §13.4) — [ROADMAP]

> 2026-08-10 결정에 따라 이 계열은 MVP에서 "정의+루브릭+소규모 예시"로 둔다(정량 딥다이브 아님).
> escalation을 [DEEP] 4번으로 승격하려면 `03_OPEN_QUESTIONS.md` Q2 여백 참고.
>
> `human override rate` 자체를 품질지표로 쓰지 않는다.

| 지표 | 정의 | 분모 | 분자 | 임계(확정) | high-risk |
|---|---|---|---|---|---|
| Escalation Recall | 반드시 사람 검토 필요한 건 중 escalate한 비율 | 검토 필수 건 | escalate된 건 | **≥ 95%** | ★ 최고 |
| Escalation Precision | 사람에게 넘긴 건 중 실제 검토 필요 비율 | escalate된 건 | 실제 필요 건 | 참고(임계 없음) | 중 |
| High-risk Miss Rate | 반드시 escalate해야 할 고위험 건을 자동처리한 비율 | 고위험 건 | 자동처리된 고위험 건 | **0%(하드게이트)** | ★ 최고 |
| Unnecessary Escalation Rate | 자동처리 가능 건을 불필요하게 넘긴 비율 | 자동처리 가능 건 | 넘긴 건 | 참고(임계 없음) | 낮음 |

---

## high-risk failure 정의 (2026-08-12 확정 · ADJUSTABLE)

> "High-risk Miss Rate"·하드게이트 임계의 기준. **아래 4종은 실패 시 여신 결정을 조용히 뒤바꾸므로
> tolerance = 0**(자동처리로 덮으면 fail). 위 §0-B 하드게이트와 1:1 대응.

**high-risk = 아래 중 하나에 해당하는 실패:**
1. **경과규정 오판** — 종전/신규 규정을 뒤바꿔 LTV를 뒤집는 경우. (↔ Grandfathering Recall 하드게이트)
2. **시행일 오적용** — 규제 전/후를 뒤바꾸는 경우(효력일 경계 ±1일). (↔ Effective-date / Policy-version)
3. **핵심 예외 누락** — 생애최초·서민실수요·정책대출을 놓쳐 LTV를 과소/과대 적용. (↔ Exception Recall 하드게이트)
4. **rule conflict 자동처리** — 우선순위 충돌·명세 여백(비규제 유주택 등)을 escalate하지 않고 자동 판정.

> 룰엔진은 이미 이 원칙을 구현: 명세 여백(비규제 유주택 기준선)은 `NEEDS_HUMAN_REVIEW`로 escalate하고,
> 자동 확정하지 않는다(정직한 실패 통제). CHALLENGE 골드셋이 이 4종을 집중 커버(`goldset_portfolio.md`).

---

## 보고서의 한계 명시 (브리프 §12)

> "The locked test set was frozen before system tuning, but was authored within the project and is not an independent third-party benchmark."

n 규모는 통계적 검정력이 아니라 **실패모드 층화 커버리지**를 목표로 함을 명시.
