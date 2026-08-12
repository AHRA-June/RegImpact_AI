# PRD — RegImpact AI (RegChange / Impact & Assurance)

> 브리프 §25가 요구하는 항목을 **as-built(구현 반영) 명세**로 구체화한다. 아직 안 만든 것은
> 상태로 정직하게 표기한다(✅ 구현 / 🟡 부분 / ⬜ 로드맵 / ◦ Discovery=코어 밖).
>
> - **버전:** 1.0 · **작성:** 2026-08-12 · **상태:** Phase 1~2 반영(테스트 112 통과)
> - **상위 문서:** `docs/00_BRIEF.md`(정체성·LOCKED), `docs/01_PROJECT_STATE.md`(현재 상태)
> - **원칙:** 이 PRD의 수치·모듈 경로는 실제 코드/실측에서 온다. 미확정 사실은 만들어 넣지 않는다.

---

## 1. 제품 정의 · 사용자 · Use Case

**한 문장:** 규제가 바뀌었을 때 무엇을 고쳐야 하는지 AI가 **제안**하고, 그 제안이 틀리지 않았는지
**검증 가능한 방식으로 증명**하는 시스템. (챗봇 아님 — 검증 가능한 의사결정 지원.)

| 항목 | 정의 |
|---|---|
| **Primary user** | 은행 여신정책/리스크·모델검증 담당자(규제 변경을 여신 룰·고객 영향으로 번역하는 실무자) |
| **Trigger** | 정부/감독기관의 가계대출 규제 변경 공문 발표(예: 2026-06-30 규제지역 추가 지정) |
| **Main workflow** | 공문 → 추출 → 검증 → 정규화 → 룰엔진 판정 → 임팩트 매트릭스 → 룰 변경안(초안) → **사람 검토·승인** |
| **Human review point** | ① Rule Change Proposal `approval_status=PENDING`(자동 확정 없음) ② 명세 여백/충돌은 `NEEDS_HUMAN_REVIEW`로 escalate ③ 규제 사실(claim) 최종 도메인 검수(LOCKED §4) |
| **Success criteria** | (a) 파이프라인이 실제 데이터로 E2E 관통 ✅ (b) Assurance 지표가 확정 임계 충족 ✅ (c) 고위험 실패모드를 자동처리하지 않고 escalate ✅ (d) 모든 산출이 원문 인용으로 추적 가능 ✅ |

**가치 제안(정직판):** "정확한 자동화"가 아니라 **"검증 가능한 초안화 + 실패의 명시적 통제"**.

---

## 2. 범위 (MVP) — 영향은 넓게, 자동판정은 좁게

- **Core Executable Scope(룰엔진이 실제 판정):** 주택구입목적 주담대의 **LTV**. 지역상태 × 주택수 ×
  생애최초 × 서민실수요 × 정책대출 분기 × 경과규정 × 시점. (`docs/05_RULE_SPEC.md §H`)
- **Discovery Scope(영향만 탐지, 자동판정 안 함) ◦:** 전세대출·신용대출·중도금/이주비·사업자대출·
  정책대출(디딤돌·보금자리). → "Potentially impacted — manual policy review required".
- **DTI/DSR/최대한도/전입의무 ◦:** 참고값으로 기록(코어 판정=LTV만, 2026-08-10 결정).

---

## 3. 시스템 아키텍처 · 컴포넌트

```
공문(스냅샷+hash) ─▶ [E] RegChange Extractor ─▶ [A] Citation Assurance
                                   │
                          지역명→코드 정규화
                                   ▼
   Temporal/Region Resolver ─▶ Deterministic Rule Engine(사람 확정 §H)
                                   │
                 ┌─────────────────┼───────────────────┐
                 ▼                 ▼                   ▼
          Impact Matrix     Rule Change Proposal   TC Generator + Rule-Regression
        (before/after 차등)   (초안, 엔진 대조)      (독립 명세 오라클, 골드셋)
                 │                 │                   │
                 └────────▶ HTML 리포트(UI) ◀──────────┘
                        + 가중 합성 모집단(비중)
```

| # | 컴포넌트(브리프 §25) | 상태 | 모듈 | 핵심 계약 |
|---|---|---|---|---|
| 1 | Source ingestion | ✅ | `extractor/sources.py`, `docs/sources/` | 공개 원문 스냅샷 + sha256(무결성), doc_id 로더 |
| 2 | Temporal/Region Resolver | 🟡 | `regions.py` | 시점별 지역 규제상태(`resolve_region_status`) + 지역명→코드 정규화 |
| 3 | RAG / retrieval | ⬜ | — | 문서 3건이 컨텍스트에 들어가 현재 불필요. 코퍼스 확대 시 도입 |
| 4 | RegChange Extractor (E) | ✅ | `extractor/` (Gemini 실측) | 공문→Before/After 구조화 추출, structured output, 인용 강제 |
| 5 | Impact Analyzer | ✅ | `impact/matrix.py`,`connect.py` | 룰엔진 before/after 차등 → 세그먼트별 임팩트 |
| 6 | Rule Proposal Generator | ✅ | `rule_proposal.py` | 추출→룰 표면 매핑→엔진 대조, `approval_status=PENDING` |
| 7 | Synthetic Portfolio Simulator | ✅ | `impact/population.py`,`tc_generator/portfolio.py` | 비중 가중 모집단 + 몬테카를로 5,000명 |
| 8 | Test Case Generator | ✅ | `tc_generator/generator.py`,`portfolio.py` | 6 카테고리 층화 케이스 생성 |
| 9 | Deterministic Rule Engine | ✅ | `rule_engine.py` | §H 결정적 구현, **검증 기준점(ground truth)** |
| 10 | Assurance Evaluator (A) | ✅ | `extractor/evaluate.py`,`tc_generator/regression.py` | Citation grounding / 골드 대조 / 룰-회귀 |
| 11 | Audit Logger | 🟡 | (proposal `approval_status`+인용 provenance) | 승인상태·인용 추적 O, 전용 audit event 로거 ⬜ |
| 12 | Minimal UI | ✅ | `report.py` → `docs/ui/report_6_30.html` | 자체완결 HTML, 값은 엔진 실제 출력(환각 불가) |

---

## 4. 데이터 스키마 (브리프 §25) — 실제 구현 매핑

| 스키마 | 상태 | 구현(dataclass/파일) | 핵심 필드 |
|---|---|---|---|
| Policy document | ✅ | `docs/sources/SOURCES.md` + `regulatory_facts.md` | doc_id, 기관, 발표/시행일, source_hash, retrieved_at |
| Policy version | 🟡 | `regions.REG_EFFECTIVE`, 명세 상수 | effective_from(시행일). 다정책 버전 resolver는 로드맵 |
| Region version | ✅ | `regions.RegionVersion` | status, effective_from/to, regulated_type, source_policy_id |
| Synthetic borrower | ✅ | `impact.CustomerSegment` / `SegmentArchetype` | region_code, house_count, disposal, first_home, real_demand, policy_flag, 이벤트 날짜, weight |
| Rule registry | ✅ | `rule_engine.py` 상수 + `models.ReasonCode` | LTV_*, REG_EFFECTIVE, REGION_VERSIONS(코드=명세에서, LOCKED §4) |
| Test case | ✅ | `tc_generator.GeneratedCase` | case_id, category, app, expected(oracle), split, spec_note |
| Evaluation item | ✅ | `docs/eval/goldset_manifest.json`, `regchange_gold_6_30.json` | case_id→category→split freeze / 골드 변경·예외 |
| Audit event | 🟡 | `RuleChangeProposal.approval_status` + `RuleDelta.citation_*` | 승인상태(PENDING), 인용 doc/quote, disposition. 전용 이벤트 로그 ⬜ |

**입력/출력 코어:** `MortgageApplication`(입력) → `LtvDecision`(출력, status/max_ltv/reason_codes/
source_policy_ids). 추출 스키마: `RegChangeExtraction`/`RegChangeItem`/`Citation`.

---

## 5. 평가 (브리프 §25) — 확정

### 5.1 DEV / LOCKED / CHALLENGE 프로토콜
- **분할:** DEV(튜닝) / LOCKED TEST(개발 중 미개봉) / CHALLENGE(적대적). 결정적 해시 분할,
  `goldset_manifest.json` freeze. 현재 룰-회귀 골드셋 178건(DEV 52 / LOCKED 59 / CHALLENGE 67).
- **규율:** `cases_in_split(cases, "DEV")`로 개발 중 DEV만 열람. CHALLENGE는 하드 카테고리 45% 가중.
- **누수 방지:** 기대값은 **독립 명세 오라클**에서만 유도(엔진 미import) → tautology 아님.

### 5.2 지표 공식 · 임계 (상세: `docs/metrics_spec.md`)
| dimension | 지표 | 임계(확정) | 현재값 |
|---|---|---|---|
| ① Grounding | Citation Correctness / Unsupported / **Source Contradiction** | ≥95% / ≤5% / **0%(하드)** | 100% / 0% / (미측정) |
| ②③ Change/Temporal | Change ≥90% · **Exception/Grandfathering Recall ≥95%+고위험 0누락** · **Effective-date/Policy-version 100%(하드)** | — | 100% / 100% / OK |
| ④ Rule/Test | **Rule-regression 전 카테고리 100%(하드)** | — | 178/178, 표본 5,000/5,000 |
| Escalation(로드맵) | Escalation Recall ≥95% · **High-risk Miss 0%(하드)** | — | 정성 |

### 5.3 high-risk failure 정의(확정, `metrics_spec` §high-risk)
경과규정 오판 / 시행일 오적용 / 핵심예외 누락 / rule conflict 자동처리 — **tolerance=0(하드게이트)**.

### 5.4 Error taxonomy (신설)
| 코드 | 오류 | 지표 | high-risk |
|---|---|---|---|
| E1 | 변경 누락 | Change Completeness | 전파 위험 |
| E2 | 예외 누락(생애최초·서민실수요·정책대출) | Exception Recall | ★ (LTV 과소/과대) |
| E3 | 근거 없는 주장 / 원문 충돌 | Unsupported / Contradiction | ★(충돌=하드) |
| E4 | 인용 불일치 | Citation Correctness | 중 |
| E5 | 시점 오류(시행일/버전) | Effective-date / Policy-version | ★(규제 전후 뒤바꿈) |
| E6 | 경과규정 오판 | Grandfathering Recall | ★(종전/신규 뒤바꿈) |
| E7 | 지역 매핑 오류 | Regions match | 영향 누락 |
| E8 | 룰엔진 ⟷ 명세 불일치 | Rule-regression | ★(하드, 구현 버그) |
| E9 | escalation 누락(고위험 자동처리) | High-risk Miss | ★ 최고 |

### 5.5 Failure review template
실패 1건 기록 양식은 `docs/prd/failure_review_template.md`. 필드: case_id·dimension·metric·
expected·actual·error_class(E#)·high_risk·root_cause·disposition(프롬프트/엔진/채점기/명세 수정)·citation.

---

## 6. Assurance 원칙 (핵심 차별점)

1. **역할 분리:** LLM은 '정책·지역·시점' 좌표를 **초안**으로 제공. **LTV 판정은 사람 확정 결정적 룰엔진**
   (LOCKED §4). LLM이 룰 값을 만들지 않는다.
2. **검증 독립성(tautology 방지):** 룰-회귀 오라클은 rule_engine/regions/grandfathering을 import하지
   않고 명세를 재구현 → 어느 구현 오차든 disagreement로 드러남. mutation test로 이빨 확인.
3. **채점기 자체를 검증:** 실측 중 발견한 "PDF 줄바꿈이 정확한 인용을 환각으로 오탐"을 채점기 정규화로
   보정(67%→100%) → 지표 신뢰성이 채점 인프라에 의존함을 사례화.
4. **정직한 실패 통제:** 명세 여백(비규제 유주택 기준선)을 자동 확정하지 않고 `NEEDS_HUMAN_REVIEW`로
   escalate. 룰 변경안은 항상 `PENDING`.
5. **조용한 누락 금지:** 미매핑 지역·수치비교 불가 행·가정 비중을 리포트에 표면화.

---

## 7. 배포 · 재현 · 보안 (브리프 §25)

- **Local first:** 순수 Python(표준 라이브러리), 런타임 의존성 0. `python -m pytest`(112) + 데모 스크립트.
- **오프라인 재현:** 저장된 추출(`extractor_run_6_30_gemini.json`)·골드셋 매니페스트로 **API 키 없이**
  파이프라인/리포트 재현. 골드셋·모집단은 결정적 생성(seed/hash).
- **LLM 백엔드:** Gemini(Google AI Studio, 실측)·Anthropic(claude-opus-5) 모두 **SDK 없이 REST**,
  키만 있으면 됨. 백엔드/모델은 `REGIMPACT_LLM`/`REGIMPACT_MODEL`로 교체.
- **Secrets:** API 키는 환경변수만(저장소 커밋 금지). 프록시/CA는 환경 존중.
- **웹 배포(선택):** HTML 리포트는 정적 파일 → 어디든 호스팅 가능.

---

## 8. 현재 상태 · 로드맵 · Non-goals

**구현 완료(✅):** 룰엔진 v1, Extractor(Gemini 실측), Citation Assurance, TC Generator + 층화 골드셋
(178 + 5,000 표본), Impact Matrix E2E, 지역 정규화, 추출→임팩트 연결, Rule Change Proposal, HTML 리포트,
가중 합성 모집단, 확정 임계값. **테스트 112 통과.**

**로드맵(⬜/🟡):** 다정책 Temporal Policy Resolver 정식, RAG(코퍼스 확대 시), 전용 Audit event 로거,
Anthropic 교차 실측(사용자 유료 API 결정 대기), 대출액/가격대 밴드 '영향 금액' 집계.

**사용자 확정 대기(LOCKED §4):** regulatory_facts claim C01~C13 최종 도메인 검수, 기사 permalink.

**Non-goals:** 실제 은행 내규/고객데이터 사용 금지(LOCKED §8, 모의 문서로 대체), LLM의 룰 직접 수정
금지(§4), "완전 자동 승인" 아님(항상 사람 확정).

---

## 9. 추적성 (문서 맵)

| 목적 | 문서 |
|---|---|
| 정체성·LOCKED 원칙 | `docs/00_BRIEF.md` |
| 현재 상태·다음 액션 | `docs/01_PROJECT_STATE.md` |
| 의사결정 이력 | `docs/02_DECISION_LOG.md` |
| 규제 사실 단일 출처 | `docs/regulatory_facts.md` |
| 룰 명세 §H | `docs/05_RULE_SPEC.md` |
| 지표·임계·high-risk | `docs/metrics_spec.md` |
| 골드셋·실측 리포트 | `docs/eval/` |
| 실패 기록 양식 | `docs/prd/failure_review_template.md` |
