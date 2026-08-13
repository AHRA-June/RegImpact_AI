# Model & System Card — RegChange AI

> **버전:** v1   **날짜:** 2026-08-13   **상태:** 유효(현행 구현 반영)
> **이전 버전:** 없음 — 최초 작성
> **버전 규칙:** `docs/features/_VERSIONING.md` (수정 시 `regchange-ai_card_v2.md` 신규 + 이 폴더 CHANGELOG).

## 변경 이력 (→ v1)
- 최초 작성 (신규). System Card + LLM 컴포넌트(RegChange Extractor) Model Card 통합. 실측 근거 반영.

---

이 문서는 RegChange AI **시스템 전체(System Card)**와 그 안의 확률론 컴포넌트인 **RegChange
Extractor(Model Card)**를 함께 문서화한다. 시스템은 **확률론 축(LLM 추출)과 결정론 축(룰엔진)을
분리**하는 하이브리드이므로, 단일 ML 모델 카드가 아니라 시스템 카드에 모델 컴포넌트 카드를 포함하는
형태를 취한다.

---

## A. System Card

### A.1 시스템 요약
- **이름:** RegChange AI — Financial Policy Impact & Assurance Lab.
- **한 줄 정의:** 생성형 AI 기반 주택담보대출 **규제 변경 영향분석 및 검증 시스템**.
- **성격:** 챗봇이 아니라 **검증 가능한 의사결정 지원 시스템**. AI는 초안·영향분석·검토자료를
  제안하며 금융 의사결정을 직접 실행하지 않는다.
- **소유/용도:** 개인 포트폴리오(금융권 Model Risk / 모델검증 / AI Governance / AI Assurance 직무).

### A.2 시스템 구성 (컴포넌트 · 버전)
| 컴포넌트 | 성격 | 상태 | 기능단위 |
|---|---|---|---|
| RegChange Extractor | 확률론(LLM) | ✅ | extractor-assurance v3 |
| Deterministic Rule Engine | 결정론(사람 확정 명세) | ✅ | rule-engine v1 |
| Impact Matrix | 결정론(temporal diff) | ✅ | impact-matrix v1 |
| Rule Change Proposal + Human Review | 결정론 + 사람 | ✅ | rule-proposal v1 |
| TC Generator + Rule-Regression | 결정론(독립 오라클) | ✅ | tc-generator v3 |
| Assurance Scorecard | 결정론(임계값 판정) | ✅ | assurance-scorecard v1 |
| Validation Report | 조립·렌더 + authored | ✅ | validation-report v3 |
| Temporal Policy Resolver | 결정론(지역 시점) | ◐ 부분 | (rule-engine 내 regions) |
| RAG/retrieval · Audit Logger | — | ⬜ 계획 | — |

파이프라인: 원문 → 추출(E) → 영향 매트릭스 → 룰엔진 → 룰 제안 → Human Review → 회귀 →
Assurance → 검증보고서. 상세: `docs/features/workflow-e2e/`(최신 v7).

### A.3 사용 목적 (Intended Use)
- **주 사용자:** 은행 여신정책·리스크·모델검증 담당(규제 변경을 내규·전산 Rule로 반영).
- **주 용도:** 규제 변경 공식 원문에서 Before/After를 구조화 추출하고, 고객·업무 영향과 룰 변경
  **초안**을 만들며, 그 결과를 검증 가능한 방식으로 평가한다.
- **트리거:** 감독당국/정부의 규제 변경 발표(메인 앵커: 2026-06-30 규제지역 추가 지정).

### A.4 범위 외 · 오용 방지 (Out-of-scope / Misuse)
- ❌ **금융 의사결정 자동 실행.** 룰 변경은 반드시 사람 확정(AI초안→APPROVED).
- ❌ **규칙 로직의 LLM 생성.** 규칙 값·우선순위는 사람 확정 명세에서만 온다(LOCKED §4).
- ❌ **실제 회사 내부문서·고객데이터 사용.** 공개 공문·합성 데이터만 사용(LOCKED §8).
- ❌ **자동판정 코어 확장.** 코어는 주택구입목적 주담대 LTV만. DTI·한도·전세·신용은 참고/Discovery.
- ❌ **단일 앵커의 일반화 주장.** 6·30 1건 기준 관측을 전 규제 도메인으로 확대 해석하지 않는다.

### A.5 데이터
- **원문:** 공개 공문 3건(FSC·MOLIT 보도참고자료, 관계기관 FAQ), 스냅샷+hash 보존. **PII 없음.**
- **평가셋:** 룰 3계층(seed 30·큐레이션 106·격자 3,200, 오라클 라벨), 추출 골드 n=1(6·30).
- **합성:** 차주 프로필 조합(격자). 실제 고객데이터 미사용.
- **provenance:** 현 검증의 LLM 추출은 세션 수동 grounded 추출(자동 무인 API 실행 아님). Assurance
  채점은 전부 결정론 오프라인 → 재현 가능.

### A.6 정량 평가 결과 (2026-08-13)
- **Assurance Scorecard(4 dimension, 12지표, 확정 임계값 Strict): 12/12 PASS → 종합 PASS.**
  - ① Grounding: Citation 100% · Unsupported 0% · Contradiction 0%.
  - ② Completeness: Change 100% · Exception Recall 100% · Grandfathering Recall 100%.
  - ③ Temporal: Effective-date 100% · Region 100% · Policy-version Consistency 100%.
  - ④ Regression: Rule-regression 100% · Boundary 100% · Conflict 100%.
- **룰 회귀:** 격자 3,200/3,200(100%), 큐레이션 106/106, seed 30/30. 커버리지 status 4·rule_id 6·reason_code 11.
- **방어력:** mutation(엔진 버그 주입) 시 회귀·스코어카드가 실패로 포착.
- 상세: `docs/reports/validation_report_6_30_full.md`, `assurance_scorecard.md`, `rule_grid_stats.md`.

### A.7 리스크 · 완화 (Risk Register 요약)
| 리스크 | 영향 | 완화 | 상태 |
|---|---|---|---|
| 환각 인용/값 날조 | 잘못된 규제 사실 전파 | grounding·contradiction 결정론 검증(고위험, =0% 임계) | ✅ 관측 0 |
| 예외/경과규정 누락 | LTV 과소/과대, 규제 전후 뒤바뀜 | 고위험 Recall 지표 FAIL→escalate | ✅ 포착·보완 실증 |
| 시점 오판(시행일/버전) | 규제 전후 혼동 | 시점 프로브·오라클 검증(=100%) | ✅ |
| 룰엔진↔명세 불일치 | 자동판정 오류 | 독립 오라클 차등검증(3,200) + mutation | ✅ |
| 과잉 자동화 | 사람 통제 상실 | AI초안→사람확정, escalation | ✅ 설계 |
| 평가 누수(과적합) | 성능 과대평가 | DEV/LOCKED/CHALLENGE 분리; 룰은 결정론이라 무누수 | ✅ |
| 명세 공백(유주택 기준선) | 판정 불가 | 임의값 대신 NEEDS_HUMAN_REVIEW | ◐ Q6 확정 대기 |
| 단일 앵커 | 일반화 한계 | n=1 명시, 추가 이벤트 확보 후 확대 | ⬜ 후속 |

### A.8 공정성 · 윤리 (도메인 특수)
- 본 시스템은 개인 신용평가·차별적 판정을 하지 않는다. LTV는 **차주 유형(무주택/유주택/생애최초/
  서민실수요)** 이라는 **규제가 정의한 공개 기준**으로만 결정되며, 이는 감독규정의 반영이지 시스템의
  자체 판단이 아니다.
- 고객 영향(강화/완화/검토)은 투명하게 노출되며, 불리한 판정(예: 유주택 0%)도 그 근거(reason_code)와
  출처(source_policy_id)를 동반한다.
- 판정 불가·모호 케이스는 자동 처리하지 않고 사람 검토로 escalate하여 **자동화의 과신을 방지**한다.

### A.9 거버넌스
- **Human-in-the-loop:** 룰 변경은 사람 승인(approval envelope: status·검토자·노트·시점, 본문 불변).
- **추적성:** 모든 판정에 reason_code·rule_id·source_policy_id, 추출에 citation, 소스에 hash.
- **재현성:** 결정론 파이프라인(난수 없음) → 동일 입력·동일 출력. 테스트 110개 전량 통과.
- **감사 로그:** 정식 append-only audit는 계획(현재 approval 기록·hash·결정론 재현으로 부분 대체).

### A.10 한계 · 유지보수
- 한계: n=1 문서셋 / 오라클은 challenger(제3자 벤치마크 아님) / Contradiction은 %-값 프록시(NLI 아님) /
  추출 provenance(세션 수동) / 명세 공백 escalation / LTV 코어 한정.
- 유지보수: 시스템 변경 시 재실행(재현 명령은 검증보고서 §13.5). 카드·PRD·기능단위 문서는 버전 규칙으로 갱신.

---

## B. Model Card — RegChange Extractor (LLM 컴포넌트)

### B.1 모델 상세
- **역할:** 공식 공문 원문에서 주담대 규제의 Before/After 변경을 **구조화 추출**(structured output).
- **기반 모델:** Anthropic Claude, 기본 `claude-opus-5`(ADJUSTABLE — 비용/성능 따라 교체). 규칙 로직
  생성에는 사용하지 않음(추출·초안화 전용).
- **인터페이스:** LLM 호출 주입 가능(dependency injection) → API 키 없이 오프라인 테스트·채점.
  출력은 JSON Schema(`additionalProperties:false`) 강제.
- **provenance(현 검증):** 세션 수동 grounded 추출. 자동 `claude-opus-5` API 무인 실행 1회는 키 확보 후 후속.

### B.2 입력 · 출력
- **입력:** 원문 텍스트(doc_id별) + 프롬프트(원문 verbatim 인용·추론 금지 강제).
- **출력:** `RegChangeExtraction` — policy_id, effective_from, target_regions, changes[
  {category, summary, before, after, citation{source_doc_id, quote}, confidence}].
- 카테고리: LTV·EXCEPTION·GRANDFATHERING·EFFECTIVE_DATE·REGION·SCOPE_LIMIT.

### B.3 사용 목적 · 범위 외
- **목적:** 사람이 검토할 **초안** 생성. "정확한 인용·낮은 환각"이 "정확한 완전성"보다 우선.
- **범위 외:** 규칙 값 생성·LTV 자동판정(룰엔진 담당), 금융 의사결정.

### B.4 평가 지표 · 결과 (6·30)
| 지표 | 값 | 임계(Strict) | 판정 |
|---|---|---|---|
| Citation Correctness | 100% (10/10) | ≥95% | ✅ |
| Unsupported Claim Rate | 0% | ≤5% | ✅ |
| Source Contradiction Rate | 0% | =0% | ✅ |
| Change Completeness | 100% | ≥90% | ✅ |
| Exception Recall | 100% | ≥95% | ✅ |
| Grandfathering Recall | 100% | ≥95% | ✅ |
| Effective-date / Region | 100% | =100% | ✅ |

- **관측:** 이 단계에서 환각 없음. Exception Recall은 1차 50%(서민실수요 누락)를 Assurance가 포착 →
  원문 근거 보완 → 100%(인용 무결성 유지). 상세 서사: `validation_report_6_30_full.md §9`.

### B.5 Factors · 알려진 실패 모드
- **성능 좌우 요인:** 원문 품질(PDF→txt 추출 시 줄바꿈으로 인한 인용 경계), 예외 조항의 분산(FSC vs FAQ),
  표 형식 규제값의 파싱.
- **실패 모드:** 보수적 추출로 인한 예외 누락(관측·완화됨), 표·각주 값의 부분 포착. 이들은 Assurance
  Recall·Completeness 지표로 포착된다.

### B.6 Caveats
- 지표는 n=1 문서셋 관측. 모델 버전·프롬프트 변경 시 재측정 필요.
- 인용 grounding은 결정론이지만, 의미론적 모순(원문과 반대 주장)은 %-값 프록시로만 부분 탐지.

---

## C. 참조
- 검증보고서(정식): `docs/reports/validation_report_6_30_full.md`
- PRD: `docs/prd/regchange-ai/regchange-ai_v1.md`
- 지표·임계값: `docs/metrics_spec.md`(§0-C) · 임계값 코드: `src/regimpact/assurance/thresholds.py`
- 규칙 명세: `docs/05_RULE_SPEC.md` · 규제 사실: `docs/regulatory_facts.md`
- 기능단위·워크플로우: `docs/features/` · 결정 이력: `docs/02_DECISION_LOG.md` · 미해결: `docs/03_OPEN_QUESTIONS.md`

> 본 카드는 현행 구현 기준 point-in-time 문서다. 컴포넌트·지표·임계값·provenance가 바뀌면
> `_VERSIONING.md` 규칙에 따라 `regchange-ai_card_v2.md`를 신규 생성하고 변경 이력을 기록한다.
