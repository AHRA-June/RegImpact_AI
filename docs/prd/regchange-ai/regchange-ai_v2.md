# PRD — RegChange AI (Financial Policy Impact & Assurance Lab)

> **버전:** v2   **날짜:** 2026-08-13   **상태:** 유효(현행 구현 반영)
> **이전 버전:** v1 (`regchange-ai_v1.md`)
> **버전 규칙:** `docs/features/_VERSIONING.md` (수정 시 `regchange-ai_v3.md` 신규 + 이 폴더 CHANGELOG).

## 변경 이력 (v1 → v2)
- **[범위]** RAG/retrieval: `⬜ 계획` → `✅ 구현`. `src/regimpact/retrieval/`(BM25 어휘검색·무료·결정론
  + 임베딩 주입식 + recall@k 평가 + grounding 보존). §5·§6·§13·§15 반영.
- **[문서]** 무료 LLM 제공자 지원(extractor v4)도 데이터/재현성 맥락에 반영.

## (v1 변경 이력)
- 최초 작성 (신규). 브리프 §25 필수 항목을 구체화하고, **현행 구현 상태(구현됨/부분/계획)**를 명시.

---

## 1. 개요

**한 줄 정의:** 생성형 AI 기반 **주택담보대출 규제 변경 영향분석 및 검증 시스템**
(RegChange AI — Financial Policy Impact & Assurance Lab).

**문제:** 정부의 가계대출 정책이 바뀌면 금융회사는 변경사항을 **여신정책·전산 Rule·고객 영향·
테스트케이스**로 빠르고 정확하게 변환해야 한다. LLM으로 이 작업을 하면 정확성 검증과 사람 승인
지점이 급소가 된다.

**가치 제안:** "정확한 자동화"가 아니라 **검증 가능한 초안화 + 실패의 명시적 통제.**
- **E(제품)** = 규제 변경 영향분석(RegChange / Impact Analysis)
- **A(신뢰 기반)** = AI 결과의 검증·통제(Assurance Layer)
- 챗봇이 아니라 **검증 가능한 의사결정 지원 시스템**. (LOCKED §1, §2)

**용도:** 금융권 Model Risk / 모델검증 / AI Governance / AI Assurance 직무 포트폴리오.

---

## 2. 사용자 · Use Case (브리프 §25)

- **Primary user:** 은행 여신정책·리스크·모델검증 담당(규제 변경을 내규·전산 Rule로 반영하는 실무자).
- **Trigger:** 감독당국/정부의 규제 변경 공식 원문 발표(메인 시나리오: **2026-06-30 규제지역 추가 지정**).
- **Main workflow(E2E):**
  원문 스냅샷 → 유효 정책 버전 해석 → Before/After 변경 탐지 → 고객·업무 영향 매트릭스 →
  구조화 Rule 변경 초안 → 경계·예외·충돌 Test Case → deterministic Rule 회귀 → Assurance 평가 →
  Human Review → 검증보고서.
- **Human review point:** Rule 변경은 **AI초안(PENDING_REVIEW) → 사람 확정(APPROVED/REJECTED)**.
  LLM은 규칙 로직을 생성·실행하지 않는다(LOCKED §4, §9).
- **Success criteria(제품):** 6·30 1건이 원문→검증보고서까지 **관통**되고, 각 노드 산출이
  **추적 가능(citation·reason_code·source_policy_id)**하며, Assurance 스코어카드가 **정량 PASS**.

---

## 3. 범위 (MVP)

원칙(브리프 §5): **영향 탐지는 넓게, 실행 가능한 자동판정은 좁게.**
- **자동판정 코어:** 주택구입목적 주담대 **LTV**만(코어 출력). DTI·대출한도는 참고값. (LOCKED §3)
- **넓게 탐지(초안):** 전세/신용/중도금/사업자 등 제한은 추출·표면화하되 **Discovery(수동 검토)**.
- **정책대출:** Discovery로 분리(코어 자동판정 제외).

**Non-goals(브리프 §21):** 실제 회사 내부문서·고객데이터 사용(LOCKED §8), 전체 규제 도메인 커버,
LLM의 직접 의사결정·코드 자동수정, 챗봇 UX, 프로덕션 배포.

---

## 4. 시스템 아키텍처 · 파이프라인

노드 = 데이터 계약. 상세·현황은 `docs/features/workflow-e2e/`(최신 v6).

```
[1] Source Snapshot → [2] RegChange Extractor → [3] Impact Matrix → [R] Rule Engine
  → [4] Rule Change Proposal → [7] Human Review → [5] TC/Rule-Regression
  → [6] Assurance Scorecard → [8] Validation Report
```

- 결정론 축(룰엔진)과 확률론 축(LLM 추출)을 **분리**하고, 룰엔진을 LLM 출력의 **검증 기준점**으로 쓴다.
- 모든 AI 출력은 **구조화 스키마**로 정의(§5).

---

## 5. 데이터 스키마 (브리프 §25) — 구현 상태 명시

| 스키마 | 구현 | 위치 |
|---|---|---|
| 룰엔진 입력(Mortgage Application) | ✅ | `models.MortgageApplication` |
| 룰엔진 출력(Rule Decision) | ✅ | `models.LtvDecision` (status·max_ltv·rule_id·reason_codes·source_policy_ids) |
| Region version | ✅ | `regions.RegionVersion` (status·effective_from/to·regulated_type·source) |
| Policy document / version | ◐ | 추출 산출 `extractor.schema.RegChangeExtraction`(policy_id·effective_from·target_regions·changes). 정식 Temporal Policy 스키마는 계획 |
| RegChange item(Before/After) | ✅ | `extractor.schema.RegChangeItem`(+`Citation`) |
| Impact matrix | ✅ | `impact.matrix.Segment/ImpactRow/ImpactMatrix` |
| Rule change proposal | ✅ | `proposal.schema.RuleChangeProposal/RuleChangeLine/ReviewDecision` |
| Test case | ✅ | `tc_generator.GeneratedCase`(case_id·category·app·expected·split) |
| Evaluation item(gold) | ✅ | `docs/eval/regchange_gold_6_30.json`, 추출 산출 `regchange_extracted_6_30.json` |
| Synthetic borrower | ✅ | `tc_generator.portfolio`(격자 3,200, MortgageApplication 조합) |
| Audit event | ⬜ 계획 | approval envelope(`ReviewDecision`)는 존재; 정식 audit log는 미구현 |

---

## 6. 컴포넌트 명세 (브리프 §25) — 구현 상태

| 컴포넌트 | 상태 | 모듈 / 기능단위 |
|---|---|---|
| Source ingestion | ✅ 수동 | `docs/sources/`(원문 스냅샷+hash), `extractor.sources` |
| Temporal Policy Resolver | ◐ 부분 | `regions.resolve_region_status`(지역 시점 버전). 정식 정책 리졸버는 계획 |
| RAG / retrieval | ✅ | `retrieval/` — BM25 어휘검색(무료·결정론) + 임베딩 주입식 + recall@k 평가 + grounding 보존. 기본 파이프라인은 전량 컨텍스트, 검색은 스케일 대비 선택 경로 |
| RegChange Extractor | ✅ | `extractor/` (structured output, LLM 주입 가능) → `features/extractor-assurance` |
| Impact Analyzer(Matrix) | ✅ | `impact/` → `features/impact-matrix` |
| Rule Proposal Generator | ✅ | `proposal/` → `features/rule-proposal` |
| Synthetic Portfolio Simulator | ✅ | `tc_generator/portfolio`(격자 3,200) |
| Test Case Generator | ✅ | `tc_generator/`(독립 오라클 차등검증) → `features/tc-generator` |
| Deterministic Rule Engine | ✅ | `rule_engine.py`(알고리즘 H) → `features/rule-engine` |
| Assurance Evaluator | ✅ | `assurance/`(4 dimension 스코어카드) → `features/assurance-scorecard` |
| Audit Logger | ⬜ 계획 | approval 기록은 있음, 정식 audit trail 미구현 |
| Minimal UI | ◐ 부분 | Impact Matrix·Validation Report **데이터바인딩 HTML**(`render_*_html`). Stitch 목업은 참고 디자인 |

---

## 7. 룰 로직 (LOCKED §4)

- 룰엔진의 규칙 값·우선순위는 **사람이 확정한 명세**(`docs/05_RULE_SPEC.md` v1, `regulatory_facts.md`)에서 온다.
  LLM이 규칙을 생성하지 않는다. 알고리즘 H(P0~P7 short-circuit)의 결정론 구현.
- 확정 LTV(규제지역, 시행 후): 무주택 일반/처분조건부 40 · 생애최초 70 · 서민실수요 60 · 유주택/다주택 0 ·
  경과규정 종전 70 · 정책대출 Discovery. 명세에 값 없는 경우(非규제 유주택 등)는 **정직한 escalation**.

---

## 8. 평가 프로토콜 (브리프 §11~13, §25)

- **누수 방지(LOCKED §5):** DEV / LOCKED TEST / CHALLENGE 분리. LLM 추출용 골드셋의 LOCKED/CHALLENGE는
  튜닝 종료 전까지 봉인. **룰엔진 평가셋은 결정론이라 전량 측정해도 누수 없음**(04_PLAN §0-5).
- **3계층 룰 평가셋:** seed 30 / 큐레이션 106(split DEV 36·LOCKED 35·CHALLENGE 35) / **격자 3,200**.
  정답은 독립 명세 오라클이 유도(차등검증) → 손라벨 없이 확장. 전부 Pass Rate 100%(engine=명세).
- **metric formula·threshold:** `docs/metrics_spec.md` §0-C(확정 임계값 표), 코드 `assurance/thresholds.py`.
- **high-risk failure 정의:** 경과규정·시행일 오판(규제 전후 뒤바뀜), 예외(생애최초·서민실수요·정책대출) 누락,
  rule conflict 자동처리 덮음. 이들 지표는 ★로 태그, FAIL 시 종합 FAIL.
- **error taxonomy(초안):**
  - E-EXT(추출): 환각 인용/값 날조(Unsupported·Contradiction), 변경 누락(Completeness), 예외 누락(Recall)
  - E-TMP(시점): 시행일 오추출, 시점 버전 불일치
  - E-RULE(룰): 엔진↔명세 불일치, 경계·충돌 오판
  - E-ESC(에스컬레이션): 고위험 자동처리 miss, 불필요 escalation
- **failure review template:** 각 FAIL은 (지표·값·임계·재현 입력·원인분류·조치) 6요소로 기록(스코어카드 FAIL 목록 + 향후 리뷰 문서화).

---

## 9. Assurance — 깊은 4 dimension + 확정 임계값 (2026-08-13)

`assurance/`가 12지표를 확정 임계값(**Strict**)으로 판정. 종합 = **고위험(★) FAIL → 전체 FAIL**.

| dim | 지표(★=고위험) | 임계 |
|---|---|---|
| ① Source Grounding | Citation ≥95% · Unsupported★ ≤5% · Source Contradiction★ =0% |
| ② Completeness | Change★ ≥90% · Exception Recall★ ≥95% · Grandfathering Recall★ ≥95% |
| ③ Temporal | Effective-date★ · Region★ · Policy-version Consistency★ =100% |
| ④ Rule Regression | Rule-regression★ · Boundary · Conflict★ =100% |

- **6·30 실측: 12/12 PASS → 종합 PASS.** 가드레일 검증(예외 누락→FAIL, 값 날조→Contradiction 포착).
- 한계: n=1 문서셋, 오라클은 challenger(제3자 벤치마크 아님).

---

## 10. Human Review · Approval · Audit (브리프 §16~17)

- **Approval envelope:** `proposal.record_decision`(PENDING_REVIEW→APPROVED/REJECTED/CHANGES_REQUESTED),
  검토자·노트·시점 기록. 본문 불변(감사 친화). (INFRA — 항상 켜짐)
- **Escalation:** 명세 공백·모순 입력은 `NEEDS_HUMAN_REVIEW`로 자동 판정 대신 사람 검토(정직성).
- **Audit trail:** 정식 audit log는 계획(현재 approval 기록·소스 hash·결정론 재현으로 부분 대체).

---

## 11. 배포 · 재현성 (브리프 §25)

- **Local-first:** Python 패키지 + pytest(110). 외부 서비스 의존 없이 오프라인 테스트(LLM 주입 가능).
- **Secrets:** API 키는 환경변수(`ANTHROPIC_API_KEY`), 저장소에 커밋 금지(`.gitignore`).
- **Reproducibility:** 룰엔진·오라클·포트폴리오·격자·스코어카드 전부 **결정론**(난수 없음, 안정 case_id).
  추출 산출물은 provenance 명시(수동 grounded; 자동 claude-opus-5 API 무인 실행은 키 확보 후).
- **Web 배포:** 선택(ADJUSTABLE). 현재 산출물은 self-contained HTML(`docs/reports/*.html`).

---

## 12. 성공 기준 · KPI

- **관통:** 6·30 E2E `is_pipeline_complete=True` (달성).
- **Assurance:** 4 dimension 12지표 확정 임계값 종합 PASS (달성: 12/12).
- **룰 신뢰:** 3계층 평가셋 Pass Rate 100%(engine=명세) + mutation 방어력(달성).
- **추적성:** 모든 판정에 reason_code·source_policy_id·citation(달성).
- **정직성:** 실패·escalation·한계를 산출물에 명시(달성).

---

## 13. 현재 구현 상태 (요약)

- ✅ **완료:** 룰엔진, Extractor+Citation Assurance(무료 LLM 제공자 지원), **RAG/retrieval(BM25+recall@k)**,
  Impact Matrix(+UI), Rule Proposal+Human Review, TC Generator+3계층 회귀, Assurance 4 dimension 스코어카드+
  임계값, Validation Report(md+HTML+**정식 17쪽 서사**), Model/System Card, AI Risk Register.
- ◐ **부분:** Temporal Policy Resolver(지역만), Minimal UI(2화면 데이터바인딩), Audit(approval만).
- ⬜ **계획:** 정식 Audit Logger, 임베딩 검색 라이브 실행(무료 로컬), 다문서 골드셋 확대, 자동 LLM 실행,
  추가 실제 규제이벤트 확보 시 추출 골드셋 확대.

---

## 14. 리스크 · 미해결

- `docs/03_OPEN_QUESTIONS.md`: Q5(6·30 수기 Impact 앵커 확인), Q6(규제사실 검수), Q8(유주택+생애최초 §E/§H).
- 최대 리스크(브리프): 1인·단기 E2E 관통 실패 — **수직 슬라이스로 이미 관통 달성**(완화됨).
- LLM 추출 골드셋 n=1(실제 규제문서 1건) — 가짜 문서 생성은 LOCKED §8 위반이므로 추가 이벤트 확보 후 확대.

---

## 15. 로드맵 (Phase 3~스트레치, `docs/04_PLAN.md`)

- Phase 3: 정식 검증보고서(15~20쪽) 서사, LOCKED/CHALLENGE 최초 실행, Assurance escalation 계열 정량화(선택).
- 스트레치: 정책 버전 타임라인, 대시보드, Model/System Card, AI Risk Register, 라이브 파이어, 공개글.

---

> 이 PRD는 현행 구현을 반영한 v1이다. 컴포넌트 상태·지표·임계값이 바뀌면 `_VERSIONING.md` 규칙에 따라
> `regchange-ai_v2.md`를 신규 생성하고 변경 이력을 기록한다.
