# RegImpact AI — 검증보고서 (Validation Report)

> **생성형 AI 기반 주택담보대출 규제 변경 영향분석·검증 시스템**
> 대상 시나리오: **2026-06-30 규제지역 추가 지정**

| 항목 | 값 |
|---|---|
| 문서 유형 | 모델·시스템 검증보고서 (Model & System Validation Report) |
| 대상 정책 | 2026-06-30 규제지역 추가 지정 (policy_id `FSC_20260630`) |
| 시행일 / 경과규정 컷오프 | 2026-07-01 / 2026-06-30 |
| 전체 판정 | **REVIEW_REQUIRED** (escalation 1건 → 사람 검토) |
| 검증 파이프라인 | 8단계 End-to-End |
| 작성 방식 | AI초안 → 사람확정 (provenance 명시, LOCKED §4) |
| 값의 출처 | 전 항목 실측 산출물에서 유도 (손으로 적지 않음) |

본 보고서의 모든 수치는 코드로 산출된 실측값이다. `python examples/build_report_doc.py` 로 재현한다.

---

## 목차

- 1. Executive Summary (경영 요약)
- 2. 서론 및 검증 범위
- 3. 시스템 개요 및 아키텍처
- 4. 데이터 및 원문 무결성
- 5. 검증 방법론
- 6. 검증 결과 (컴포넌트별)
- 7. Assurance Layer — 4 DEEP dimension
- 8. 평가셋 설계 및 freeze (Gold Set)
- 9. 한계 및 알려진 이슈
- 10. 거버넌스 및 통제
- 11. 결론 및 권고
- 부록 A~E

---

## 1. Executive Summary (경영 요약)

RegImpact AI는 정부의 가계대출 규제 변경(**2026-06-30 규제지역 추가 지정**)이 공식 원문에서 무엇을 바꾸는지 탐지하고, 그 변경이 여신 Rule·고객 영향·테스트케이스로 어떻게 전파되는지를 **검증 가능한(auditable) 방식**으로 산출하는 의사결정 지원 시스템이다. 챗봇이 아니라, AI의 제안을 사람이 확정하고 그 정확성을 정량적으로 증명하는 통제 구조를 갖춘다.

본 검증에서 확인된 핵심 결과는 다음과 같다.

- **결정론적 룰엔진**은 독립 명세 오라클 차등 검증 30/30 (100%) 및 **골드셋 최종 평가(DEV·LOCKED·CHALLENGE 전 115문항 개봉) 115/115 (100%)** 를 기록했다.
- **RegChange 추출**(모델 `claude-opus-4-8`, 9건)은 인용 grounding 100%(환각 0%), 변경 완전성 100%, 예외 재현율 100%로, 4개 DEEP Assurance dimension이 전부 실측되었다.
- **영향분석**은 9개 세그먼트(Core 7)에서 하향 3·신규제한 2·Discovery 2를 산출했고, 합성 포트폴리오 2,000명 기준 영향 차주 1,340명·고위험(LTV 0%) 360명으로 규모를 정량화했다.
- **평가셋**은 115문항(DEV 40 / LOCKED 40 / CHALLENGE 35)으로 freeze되었으며, 누수 방지를 위해 LOCKED·CHALLENGE는 sealed다.

**정직성 원칙이 시스템 전반에 관철되었다.** 원문에 기준선이 없는 항목(非규제 유주택)은 값을 지어내지 않고 `OWNER_BASELINE_UNKNOWN`으로 사람 검토에 escalate했으며(현재 escalation 1건), LLM 실행이 필요한 지표는 실측 전까지 '실측 대기'로 표기했다. 전체 판정은 escalation이 존재하므로 **REVIEW_REQUIRED**이다 — 즉 시스템은 자동 승인하지 않고 사람 검토를 요구한다.

### 1.1 Model Risk 관점의 시사점

본 시스템이 Model Risk / 모델검증 관점에서 갖는 의미는 세 가지다. 첫째, **검증 독립성** — 채점 기준이 검증 대상과 독립된 경로(명세 오라클·사람 확정 골드)에서 오므로, 'LLM이 LLM을 채점'하는 순환을 구조적으로 차단한다. 둘째, **평가 무결성** — 평가셋을 개발보다 먼저 설계하고 LOCKED/CHALLENGE를 sealed로 두어 누수(overfitting to test)를 방지한다. 셋째, **재현성** — 모든 지표가 저장값이 아니라 원문·추출·골드로부터 코드로 재계산되며, 해시로 아티팩트 무결성이 고정된다. 이 세 가지는 감독기관의 모델검증 기대(독립성·문서화·재현성)와 직접 대응한다.

---

## 2. 서론 및 검증 범위

### 2.1 목적

본 보고서는 RegImpact AI의 End-to-End 파이프라인(원문 → 검증보고서)이 의도한 기능을 정확히 수행하는지, 그리고 그 정확성이 **독립적이고 재현 가능한 방식**으로 측정되는지를 검증한다. 관점은 금융권 Model Risk / 모델검증(SR 11-7 계열)의 정석 — 개발 주체와 독립된 기준(challenger)과의 대조, 평가셋의 사전 설계와 누수 방지, 한계의 명시 — 을 따른다.

### 2.2 검증 대상 범위 (Core Executable Scope)

자동 판정하는 범위는 의도적으로 좁게 제한한다:

> 주택구입목적 주담대의 **지역 × 주택수 × 생애최초 × 정책대출 여부 × 신청/계약 이벤트 시점 × 경과규정 → 적용 LTV / 적용 Rule / 경과규정 여부**

### 2.3 Discovery Scope (자동판정 제외)

다음은 영향 가능성만 탐지하고 자동 판정하지 않는다(수동 정책검토 대상): 전세대출, 1억 초과 신용대출 연계 주택구입 제한, 중도금·이주비, 사업자대출, 기타 연계 정책. **영향 범위는 넓게 발견하되 자동판정은 신뢰 가능한 좁은 범위에서만 한다** — 이는 기능 부족이 아니라 의도적 거버넌스 설계다.

---

## 3. 시스템 개요 및 아키텍처

시스템은 8단계 파이프라인으로 구성되며, 각 단계는 다음 단계의 입력을 구조화된 형태로 넘긴다. 아래는 본 검증 실행 시점의 각 단계 상태다.

| # | 단계 | 상태 | 요약 |
|---:|---|---|---|
| 1 | Source Snapshot | OK | 공식 원문 3건 해시 스냅샷 (공개 보도자료/FAQ) |
| 2 | Policy Version / Temporal | OK | 시행일 2026-07-01 · 경과규정 컷오프 2026-06-30 · 신규 규제지역 3곳 |
| 3 | RegChange (Before/After) | OK | 필수 변경 4항 · 예외 2종 (gold 확정) |
| 4 | Impact Matrix | OK | 세그먼트 9 (Core 7) · 하향 3 · 신규제한 2 · Discovery 2 |
| 5 | Rule Change Proposal | REVIEW | MORTGAGE_LTV_REGULATED_REGION · 파라미터 변경 4건 · 승인상태 REVIEW_REQUIRED |
| 6 | Test Cases / Rule Regression | MEASURED | 오라클 회귀 30/30 · Gold Set 최종 115/115 (DEV·LOCKED·CHALLENGE 개봉 2026-08-14) |
| 7 | Assurance | MEASURED | 4 DEEP dimension 실측 4/4 · 전 dimension 실측 완료 |
| 8 | Human Review | REVIEW | escalation 1건 → 사람 검토 필요 |

데이터 흐름을 도식화하면 다음과 같다.

```text
공식 원문(FSC·MOLIT·FAQ)  ──►  Source Snapshot (해시 무결성)
        │
        ▼
  Temporal Policy Resolver (시점별 유효 버전·지역 상태·경과규정)
        │
        ▼
  RegChange Extractor (LLM 초안·인용 강제)  ──►  Assurance: Citation Grounding
        │
        ▼
  Impact Matrix (Before/After 세그먼트별 LTV)
        │
        ▼
  Rule Change Proposal (구조화)  ──►  Human Review / Approval
        │
        ▼
  Deterministic Rule Engine  ◄──  독립 명세 오라클 (차등 검증) + Gold Set
        │
        ▼
  Validation Report (본 문서)
```

핵심 설계 원칙은 **검증 독립성**이다. LLM(추출·제안)은 초안을 만들고, 결정론적 룰엔진과 독립 명세 오라클은 그 초안과 무관하게 사람이 확정한 명세에서 유도된다. 따라서 'LLM이 LLM을 채점'하는 순환이 발생하지 않는다.

### 3.1 판정 알고리즘 (우선순위 §H)

룰엔진은 다음 우선순위로 short-circuit 판정한다. 상위 규칙이 적용되면 하위는 평가하지 않는다.

| # | 조건 | 결과 |
|---|---|---|
| P0 | 주택구입목적 아님 | OUT_OF_SCOPE (자동판정 밖) |
| P0b | 정책대출 | DISCOVERY (수동 정책검토) |
| P1 | 경과규정 충족(접수/계약+계약금/토허 신청 ≤ 6.30) | 종전규정 — 무주택 70%, 유주택은 기준선 부재→검토 |
| P2 | 非규제(시행 전/미등록) | 무주택 70%, 유주택 기준선 부재→검토 |
| P3 | 규제·다주택(≥2) | LTV 0% |
| P4 | 규제·비처분 1주택(유주택) | LTV 0% |
| P5 | 규제·생애최초(무주택 취급) | LTV 70% |
| P6 | 규제·서민실수요 | LTV 60% |
| P7 | 규제·무주택 일반/처분조건부 1주택 | LTV 40% |

### 3.2 확정 LTV 규칙값 (사람 확정 명세)

규칙 값은 원문에서 사람이 확정한 명세에서만 온다(LLM이 생성하지 않는다).

| 차주 유형 | 비규제 기준선 | 규제지역 지정 후 |
|---|---:|---:|
| 무주택 표준 / 처분조건부 1주택 | 70% | 40% |
| 생애최초 | 70% | 70% (좌동) |
| 서민·실수요자 | 70% | 60% |
| 유주택(비처분 1주택) | 명세부재(검토) | 0% |
| 다주택 | 명세부재(검토) | 0% |

---

## 4. 데이터 및 원문 무결성

검증의 기준점은 공개된 공식 원문뿐이다(실제 회사 내부문서·고객데이터 미사용, LOCKED §8). 각 원문은 스냅샷으로 저장하고 SHA-256 해시로 무결성을 고정한다.

| 기관 | 문서 | doc_id | 발표일 | source_hash |
|---|---|---|---|---|
| 금융위원회 | 규제지역 추가 지정 관련 긴급 가계부채 점검회의 (보도참고자료) | `FSC_PRESS_20260630` | 2026-06-30 | `#403fb8fb…e8f39d23` |
| 국토교통부 | 투기과열지구 및 조정대상지역 추가 지정 (보도참고자료) | `MOLIT_PRESS_20260630` | 2026-06-30 | `#6115271b…66c11edd` |
| 관계기관 합동 | 규제지역 추가 지정 관련 FAQ | `FAQ_20260630` | 2026-06-30 | `#ef3dad7b…14ea7c9a` |

규제 사실(claim)은 실제 감독규정·보도자료(사실)와 은행 내규(모의 문서)의 경계를 명확히 구분해 관리한다. 룰엔진의 규칙 값은 이 원문에서 사람이 확정한 명세(`docs/05_RULE_SPEC.md`, `docs/regulatory_facts.md`)에서만 온다.

---

## 5. 검증 방법론

### 5.1 차등 검증 (Differential Testing)

룰엔진의 출력을 스스로 채점하면 회귀는 tautology(항상 통과)가 되어 무의미하다. 따라서 명세(§H)에서 **독립적으로 유도한 오라클(challenger)** 을 별도 코드 경로로 구현하고, 엔진 출력과 대조한다. 오라클은 `rule_engine`·`regions`·`grandfathering`을 import하지 않으므로 어느 구현의 오차든 disagreement로 드러난다.

오라클의 독립성은 구조적이다: (1) 지역 규제상태를 `regions.py` 없이 날짜 비교로 직접 판정하고, (2) 경과규정을 `grandfathering.py` 없이 G1/G2/G3로 직접 판정하며, (3) 판정 로직을 엔진의 명령형 short-circuit과 달리 선언적 데이터 표로 재구현한다. 서로 다른 구현 스타일이므로 전사(轉寫) 오류가 상관되지 않는다. fixture 방어력은 **mutation test**로 증명한다 — 엔진에 의도적으로 버그를 주입하면 회귀가 실패로 이를 잡아낸다. 즉 회귀가 '항상 통과하는 껍데기'가 아님을 실증한다.

### 5.2 인용 Grounding (Citation Grounding)

RegChange 추출의 각 항목은 원문에서 그대로 복사한 인용(verbatim quote)을 반드시 포함한다. 인용이 정규화된 원문에 substring으로 실제 존재하는지를 **완전 결정론적으로** 검사해, 모델이 원문을 지어냈는지(환각) 실측한다. 이 검사는 API·비용 없이 오프라인에서 재현된다.

### 5.3 골드 대조 및 평가셋 누수 방지

완전성·재현율은 사람이 확정한 골드 정답지와 대조한다. 평가셋은 개발보다 먼저 설계하고 DEV / LOCKED / CHALLENGE로 분리(freeze)한다. **LOCKED·CHALLENGE는 개발 중 열지 않으며**(sealed), split 간 입력이 겹치지 않음을 테스트로 강제해 누수를 방지한다. 골드 정답은 독립 명세 오라클에서 유도하므로 엔진 회귀가 순환이 되지 않는다.

### 5.4 지표 정의 (공식)

각 지표는 분모·분자·임계를 명시한다. 모든 지표는 골드셋 또는 룰엔진 회귀 fixture 위에서 계산된다.

| 지표 | 분모 | 분자 | 공식 |
|---|---|---|---|
| Citation Correctness | 생성 인용 총수 | 원문에 verbatim 존재하는 인용 수 | grounded / total |
| Unsupported Claim Rate | 생성 인용 총수 | 원문 미확인 인용 수 | ungrounded / total |
| Change Completeness | 골드 필수 변경 수 | 추출이 포착한 변경 수 | hit / required |
| Exception Recall | 골드 예외 수 | 추출이 포착한 예외 수 | hit / exceptions |
| Rule-regression Pass Rate | 회귀 TC 수 | 엔진=오라클 일치 수 | pass / total |
| Gold Set Pass Rate (split) | split 문항 수 | 엔진=골드 정답 일치 수 | pass / total |

룰엔진 회귀의 일치 판정은 status·max_ltv·applicable_rule_id·grandfathering_applied·reason_codes(부분집합)·escalation 플래그를 모두 대조한다 — 어느 한 필드라도 다르면 불일치로 집계한다.

### 5.5 정직성 통제 (LOCKED §4·§12)

- 원문에 기준이 없는 값은 지어내지 않고 사람 검토로 escalate.
- LLM 실행이 필요한 지표는 실측 전까지 '실측 대기'로 표기(가짜 수치 금지).
- 합성 데이터는 화면·보고서에 'synthetic — 실데이터 아님'으로 명시.
- 모든 산출물에 provenance(모델·날짜·출처)를 남긴다.
- 정답지는 사람(또는 독립 명세 오라클)이 원문과 독립 대조로 확정하며, LLM이 LLM을 채점하지 않는다.

---

## 6. 검증 결과 (컴포넌트별)

### 6.1 결정론적 룰엔진 (Deterministic Rule Engine)

엔진은 알고리즘 §H(우선순위 P0~P7 short-circuit)를 구현한다. 독립 오라클 차등 검증에서 **30/30 (100%)**, 카테고리별로 다음과 같다.

| 카테고리 | 통과 | Pass Rate |
|---|---:|---:|
| SCOPE | 3/3 | 100% |
| BASELINE | 3/3 | 100% |
| EXCEPTION | 5/5 | 100% |
| BOUNDARY | 8/8 | 100% |
| GRANDFATHERING | 6/6 | 100% |
| CONFLICT | 5/5 | 100% |

추가로 골드셋 DEV split(40문항)에서 **40/40 (100%)** 통과했다. 두 독립 경로(오라클 회귀·골드셋)가 일치해 엔진이 명세를 정확히 구현함을 이중으로 확인한다.

### 6.2 RegChange 추출 (Extraction)

모델 `claude-opus-4-8`이 공식 원문 3건만 읽고(골드 미참조) 9건의 Before/After 변경을 추출했다. 결정론적 채점 결과:

| 지표 | 실측 | 임계(초안) |
|---|---:|---|
| Citation Correctness (인용 grounding) | 100% | ≥ 95% |
| Unsupported Claim Rate (환각) | 0% | 낮을수록 |
| Change Completeness (변경 완전성) | 100% | ≥ 95% |
| Exception Recall (예외 재현율) | 100% | ≥ 95% |
| Effective-date / Region 정확 | OK / OK | 정확 |

모든 인용이 원문에 verbatim으로 존재해 환각이 0%로 측정되었다. 추출 전체 목록은 부록 A 참조.

### 6.3 영향분석 (Impact Matrix)

동일 세그먼트를 시행 전(Before)/후(After) 두 시점에 룰엔진으로 관통시켜 LTV 변화를 산출한다. 규칙을 새로 만들지 않고 두 판정의 차이를 구조화한다.

| 지역 | 차주유형 | 기존 | 변경 | 방향 |
|---|---|---:|---:|---|
| 용인 기흥 | 무주택 일반 | 70% | 40% | DOWNGRADE |
| 화성 동탄 | 생애최초 | 70% | 70% | UNCHANGED |
| 구리 | 서민·실수요 | 70% | 60% | DOWNGRADE |
| 용인 기흥 | 유주택(비처분 1주택) | 명세부재 | 0% | NEW_RESTRICTION |
| 구리 | 처분조건부 1주택 | 70% | 40% | DOWNGRADE |
| 구리 | 다주택 | 명세부재 | 0% | NEW_RESTRICTION |
| 화성 동탄 | 무주택 일반(경과규정) | 70% | 70% (미보호 시 40%) | UNCHANGED |

Discovery(자동판정 제외, 수동 정책검토): 정책대출(디딤돌), 전세자금대출.

### 6.4 Rule Change Proposal (구조화 변경 제안)

규제 변경이 여신 룰(`MORTGAGE_LTV_REGULATED_REGION`)에 요구하는 변경을 구조화 제안으로 정식화한다. LLM은 실행 코드를 직접 수정하지 않으며, 제안은 사람 승인 후에만 결정론적 rule registry에 반영된다. LTV 계층별 변경:

| 차주 계층 | 종전 | 변경 | 근거코드 |
|---|---:|---:|---|
| 무주택 표준 | 70% | 40% | `LTV_REGULATED_40` |
| 생애최초 | 70% | 70% | `EXCEPTION_FIRST_HOME` |
| 서민·실수요 | 70% | 60% | `EXCEPTION_REAL_DEMAND` |
| 유주택(비처분 1주택) | 명세부재 | 0% | `LTV_OWNER_0` |
| 다주택 | 명세부재 | 0% | `LTV_MULTI_HOME_0` |

승인 상태: **REVIEW_REQUIRED**. 근거 정책: FSC_20260630, MOLIT_20260630.

### 6.5 포트폴리오 영향 (합성)

⚠️ 합성 데이터(2,000명, 실데이터 아님). 각 차주의 LTV는 엔진 실제 판정이며, 집계는 다음과 같다.

| 지표 | 값 |
|---|---:|
| 영향 차주 (하향+신규제한) | 1,340 (67%) |
| 경과규정 보호 | 140 |
| 고위험 (LTV 0%) | 360 |
| Discovery (수동검토) | 240 |

Before/After LTV 분포:

| 버킷 | Before | After |
|---|---:|---:|
| 70% | 1,400 | 420 |
| 60% | 0 | 200 |
| 40% | 0 | 780 |
| 0% | 0 | 360 |
| 명세부재 | 360 | 0 |
| Discovery | 160 | 160 |
| 범위외 | 80 | 80 |

---

## 6b. 대표 사례 심층 (Worked Examples)

검증의 구체성을 위해, 실제 산출물에서 뽑은 네 가지 대표 사례를 입력부터 판정·근거까지 서술한다. 모든 값은 엔진 실제 출력이다.

### 사례 1 — 표준 하향 (무주택 일반)

- **입력:** 용인 기흥, 무주택(house_count=0), 주택구입목적, 시행 후(2026-07-02).
- **Before(2026-06-30):** 非규제 기준선 → LTV 70%.
- **After(2026-07-02):** 규제지역 지정 → LTV 40%.
- **방향/근거:** DOWNGRADE · `LTV_REGULATED_40`.
- **해석:** 규제지역 지정만으로 자동 강화되는 표준 경로. 원문(FAQ)의 '70→40%'와 일치한다.

### 사례 2 — 경과규정 보호 (종전규정 유지)

- **입력:** 화성 동탄, 무주택, 컷오프(6.30) 이전 계약+계약금, 시행 후 평가.
- **판정:** LTV 70% 유지(방향 UNCHANGED), 경과규정 해당.
- **counterfactual:** 경과규정이 없었다면 40%로 하향됐을 것 — 보호 효과를 정량화한다.
- **해석:** 경과규정(P1)이 지역상태(P2)보다 우선한다. 시스템은 보호와 미보호 값을 함께 노출해 감사 가능성을 높인다.

### 사례 3 — 신규 제한 · 명세부재 (유주택)

- **입력:** 용인 기흥, 비처분 1주택(유주택), 주택구입목적.
- **Before:** 非규제 유주택 기준선이 원문에 없음 → '명세부재'(사람 검토).
- **After:** 규제지역 유주택 → LTV 0% (`LTV_OWNER_0`).
- **방향:** NEW_RESTRICTION. Before 값을 70%로 지어내지 않고 '명세부재'로 정직하게 표기한다.
- **해석:** 이 사례가 시스템의 핵심 차별점이다 — 근거 없는 값을 만들지 않는다.

### 사례 4 — 사람 검토 escalation

- **사유코드:** `OWNER_BASELINE_UNKNOWN`.
- **설명:** 非규제 유주택 기준선이 원문에 정의되지 않아 룰엔진이 자동판정하지 않고 사람 검토로 escalate.
- **동작:** 엔진은 `NEEDS_HUMAN_REVIEW` 상태를 반환하고 LTV를 산출하지 않는다. Rule Change Proposal과 검증보고서 전체 판정이 이 escalation 때문에 사람 검토를 요구한다.
- **해석:** '자동화 범위보다 검증 가능성·추적 가능성을 우선한다'(LOCKED §10)는 원칙의 실행이다.

### 사례 5 — 우선순위 충돌: 유주택 + 생애최초

- **입력:** GURI, house_count=1, first_home_buyer=True, 시행 후.
- **판정:** status `DECIDED`, LTV 0%, 근거 `LTV_OWNER_0`.
- **해석:** 두 예외 조건이 충돌하지만 §H는 유주택(P4)을 생애최초(P5)보다 먼저 평가한다. 따라서 생애최초 70%가 아니라 유주택 0%로 판정된다 — 완화가 아닌 제한이 우선한다.

### 사례 6 — 우선순위 충돌: 정책대출 + 다주택

- **입력:** GURI, house_count=2, policy_mortgage_flag=True, 시행 후.
- **판정:** status `DISCOVERY`, LTV -, 근거 `DISCOVERY_POLICY_LOAN`.
- **해석:** 정책대출(P0b)이 최상위에 가까워, 다주택(P3)보다 먼저 Discovery로 분리된다. 정책대출은 코어 자동판정 대상이 아니므로 LTV를 산출하지 않고 수동 정책검토로 넘긴다.

이 충돌 사례들은 CHALLENGE split의 핵심 검증 대상이며, 엔진이 §H 우선순위를 정확히 따름을 보인다.

---

## 7. Assurance Layer — 4 DEEP dimension

Assurance는 폭이 아니라 깊이로 4개 dimension을 정량 측정한다. 본 검증 시점에 4개 전부 실측되었다.

| dimension | 실측 | 임계 | 상태 |
|---|---:|---|---|
| ① Citation/Source grounding | 100% (환각 0%) | ≥ 95%(초안) | 실측 |
| ② Change Completeness | 100% | ≥ 95%(초안) | 실측 |
| ③ Exception · GF Recall | 100% | ≥ 95%(초안) | 실측 |
| ④ Rule-regression | 100% (30/30) | 100% | 실측 |

### 7.1 dimension별 정의와 해석

**① Citation / Source grounding.** 추출된 각 변경의 인용이 원문에 verbatim으로 존재하는 비율. LLM이 원문을 지어냈는지(환각)를 완전 결정론적으로 실측한다. 본 검증에서 모든 인용이 원문에 존재해 환각률이 0으로 측정되었다. 이 지표는 API·비용 없이 오프라인에서 재현된다.

**② Change Completeness.** 사람이 확정한 골드의 필수 변경(LTV·시행일·경과규정·지역 지정) 중 추출이 포착한 비율. 규제에서 '원칙은 맞췄으나 시행일·경과규정을 놓치는' 실패를 잡기 위한 지표다.

**③ Exception · Grandfathering Recall.** 예외(생애최초·서민실수요)와 경과규정 포착 비율. 금융규제에서 가장 위험한 오류 유형이므로 임계를 높게(≥95%) 둔다.

**④ Rule-regression.** 룰엔진이 독립 명세 오라클과 일치하는 비율. 엔진이 명세를 정확히 구현했는지를 차등 검증으로 측정하며, 골드셋 회귀가 이를 다른 경로로 재확인한다.

① Citation/Source grounding, ② Change Completeness, ③ Exception·GF Recall은 RegChange 추출 1회 실측을 결정론적으로 재계산한 값이고, ④ Rule-regression은 독립 오라클 차등 검증값이다. 지표는 저장값이 아니라 (추출 + 원문 + gold)에서 항상 재계산되므로 재현 가능하다.

그 밖의 Assurance 항목(Source Contradiction, Temporal Consistency, Human Escalation Recall 등)은 로드맵/인프라로 정의되어 있으며, Audit Trail과 Approval Status는 항상 켜지는 인프라 통제다. 이는 폭을 넓히기보다 신뢰 가능한 4개 dimension을 깊게 측정한다는 설계 선택이다.

---

## 8. 평가셋 설계 및 freeze (Gold Set)

평가셋은 개발보다 먼저 설계하고 v1 총 115문항으로 freeze했다. 각 문항은 입력·골드 정답·근거 문서·카테고리·escalation 기대·정책 버전·rule_id를 포함한다. 정답은 독립 명세 오라클에서 유도한다.

| split | 규모 | 용도 | 상태 | 최종 결과 |
|---|---:|---|---|---|
| DEV | 40 | 상시 회귀·튜닝 | 개방 | 100% (40/40) |
| LOCKED TEST | 40 | 최종 성능평가 | **개봉** | 100% (40/40) |
| CHALLENGE | 35 | 예외·경계·충돌·모호 적대 | **개봉** | 100% (35/35) |

**최종 평가(개봉일 2026-08-14): 전체 115/115 (100%).** LOCKED·CHALLENGE는 이번이 최초·최종 개봉이며, 이후 엔진/명세를 바꿔도 동일 세트로 재튜닝·재보고하지 않는다(§12). CHALLENGE의 충돌·모호 사례까지 전부 통과해, 엔진이 명세 우선순위를 정확히 따르고 기준 부재 시 escalate함을 확인했다.

DEV split 카테고리 분포 및 회귀 결과:

| 카테고리 | 문항 | Pass Rate |
|---|---:|---:|
| BORROWER_TYPE | 5 | 100% |
| EFFECTIVE_DATE | 3 | 100% |
| EXCEPTION | 8 | 100% |
| GRANDFATHERING | 6 | 100% |
| LOAN_PURPOSE | 7 | 100% |
| NORMAL | 8 | 100% |
| REGION | 3 | 100% |

누수 방지 규율(§12): `load_split('locked'/'challenge')`는 명시적 unlock 없이는 열리지 않으며, split 간 입력이 disjoint임을 테스트로 강제한다. LOCKED·CHALLENGE는 코어 완성 후 최종 1회만 실행한다.

### 8.1 카테고리 설계 근거

금융규제에서 가장 무서운 오류는 원칙을 틀리는 것뿐 아니라 **예외·경과규정·시행일을 놓치는 것**이다. 따라서 CHALLENGE split은 EXCEPTION·GRANDFATHERING·EFFECTIVE_DATE·CONFLICT·AMBIGUOUS를 가중한다. 특히 CONFLICT(복수 조건 동시 충족 시 우선순위)와 AMBIGUOUS(기준 부재 → escalation 기대)는 이 시스템의 진짜 차별점을 검증한다 — 잘 만든 충돌·모호 사례 하나가 평범한 정상 사례 여럿보다 검증 가치가 크다. AMBIGUOUS 문항은 정답이 '특정 LTV'가 아니라 '사람 검토(escalation)'이며, 엔진이 값을 지어내지 않고 escalate하는지를 직접 검증한다.

---

## 9. 한계 및 알려진 이슈

**9.1 단일 시나리오.** 현 검증은 6·30 규제 변경 1건에 대한 것이다. 다른 정책·시점으로 일반화하려면 골드셋과 지역 버전을 확장해야 한다.

**9.2 非규제 유주택 기준선 부재.** 원문에 非규제지역 유주택 LTV 기준선이 명시되지 않아, 엔진은 값을 지어내지 않고 `OWNER_BASELINE_UNKNOWN`으로 사람 검토에 escalate한다(현재 1건). 이는 결함이 아니라 의도된 정직한 통제이나, 해당 케이스는 자동 판정되지 않는다.

**9.3 골드 정답의 출처.** 골드 정답은 독립 명세 오라클(사람 확정 명세에서 결정론적으로 유도)이다. 도메인 전문가의 최종 검수를 거친 v2가 아직 아니며, 이 한계는 부록·MANIFEST에 명시된다.

**9.4 LLM 추출 1회·단일 모델.** RegChange 추출 지표는 모델 1종(claude-opus-4-8) 1회 실행에 기반한다. 분산·모델 간 비교, CHALLENGE 세트로의 grounding 실패 유도 측정은 향후 과제다.

**9.5 합성 포트폴리오.** 포트폴리오 규모·분포는 가정된 합성 데이터다. 실데이터가 아니므로 절대 규모는 예시이며, 각 차주 LTV 판정만 엔진 실제 출력이다.

**9.6 §E vs §H 알려진 모호성.** 유주택+생애최초 동시 충족 시 §E 주석과 §H 알고리즘이 상충한다. 판정 권위는 §H(P4 우선, 유주택 0%)로 두되 CHALLENGE·OPEN_QUESTIONS(Q8)에 표면화했다.

---

## 10. 거버넌스 및 통제

- **AI초안 → 사람확정.** LLM은 변경안·영향분석·검토자료를 제안할 뿐 금융 의사결정을 직접 실행하지 않는다. 룰 명세·골드 정답은 사람이 확정한다.
- **승인 통제.** Rule Change Proposal은 승인 상태 필드를 가지며, 현재 **REVIEW_REQUIRED**로 사람 검토를 대기한다.
- **Escalation.** 자동 판정 불가 시 지어내지 않고 사람 검토로 escalate한다. 현재 escalation:

  - `OWNER_BASELINE_UNKNOWN` — 非규제 유주택 기준선이 원문에 정의되지 않아 룰엔진이 자동판정하지 않고 사람 검토로 escalate.

- **Provenance & Audit Trail.** 원문 해시, 추출 모델·날짜, 골드셋 버전·해시, 규칙 값의 출처를 모든 산출물에 남긴다.
- **전체 판정.** escalation이 존재하므로 시스템 전체 판정은 **REVIEW_REQUIRED** — 자동 승인하지 않고 사람 검토를 요구한다.

### 10.1 감사 추적 아티팩트

재현·감사를 위해 다음 산출물이 저장소에 고정되어 있다.

| 아티팩트 | 경로 | 무결성/provenance |
|---|---|---|
| 원문 스냅샷 | `docs/sources/` | SHA-256 해시 (SOURCES.md) |
| RegChange 골드 정답 | `docs/eval/regchange_gold_6_30.json` | 사람 확정 |
| RegChange 추출 산출물 | `docs/eval/regchange_extraction_6_30.json` | 모델·날짜 `_meta` |
| 골드셋(freeze) | `docs/eval/gold_set/` | split별 SHA-256 (MANIFEST) |
| 룰 명세 | `docs/05_RULE_SPEC.md` | AI초안→사람확정 |
| 의사결정 이력 | `docs/02_DECISION_LOG.md` | 날짜·결정·이유 |
| 본 검증보고서 | `docs/VALIDATION_REPORT.md` | 코드 생성(재현 가능) |

모든 지표는 저장된 숫자가 아니라 이 아티팩트들로부터 코드로 재계산된다. 따라서 아티팩트가 바뀌면 지표도 즉시 따라가며, 숫자를 손으로 조작할 여지가 없다.

---

## 11. 결론 및 권고

6·30 규제 변경 시나리오 1건이 Source Snapshot부터 Validation Report까지 End-to-End로 완결되었고, 각 단계의 정확성이 독립적·재현 가능한 방식으로 측정되었다. 결정론적 룰엔진은 오라클 차등 검증(30/30)과 **골드셋 최종 평가 115/115 개봉**에서 100% 통과했고, RegChange 추출은 4개 DEEP dimension 전부 실측(인용 100%)되었다. 시스템은 모르는 값을 지어내지 않고 사람 검토로 넘기는 통제를 일관되게 보였다.

### 권고 (다음 단계)

1. ~~LOCKED / CHALLENGE 최종 실행~~ — **완료(2026-08-14 개봉, 전체 115/115).** 이후 재튜닝·재보고 금지.
2. **골드셋 도메인 검수(v2).** 오라클 유도 정답을 도메인 전문가가 최종 확정한다.
3. **다중 모델·challenge grounding.** API 키 확보 시 여러 모델로 추출을 비교하고, CHALLENGE 원문으로 grounding 실패를 유도·측정한다.
4. **정책 일반화.** 지역 버전·골드셋을 확장해 6·30 외 시나리오로 넓힌다.

---

## 부록 A. RegChange 추출 전체 목록 (인용 포함)

**A.1 [LTV]** 규제지역 내 주택구입목적 주담대 LTV를 무주택 기준 70%에서 40%로 강화  (70% → 40%, conf 0.98)
  - 인용 `FAQ_20260630`: "규제지역 내 주담대 취급시 강화된 LTV(70→40%) 적용"

**A.2 [REGION]** 화성시 동탄구·용인시 기흥구·구리시 3곳을 투기과열지구 및 조정대상지역으로 신규 지정  (- → 투기과열지구 및 조정대상지역, conf 0.97)
  - 인용 `MOLIT_PRESS_20260630`: "구리시 등 3곳을 투기과열지구 및 조정대상지역으로 신규 지정한다"

**A.3 [EFFECTIVE_DATE]** 강화된 대출규제 시행일 7.1일(2026-07-01)  (- → 2026-07-01, conf 0.98)
  - 인용 `FSC_PRESS_20260630`: "강화된 대출규제가 7.1일부터 즉시 적용된다"

**A.4 [GRANDFATHERING]** 6.30일까지 전산 접수 완료 또는 매매계약+계약금 증명 시 종전규정 적용  (- → 종전규정 적용, conf 0.95)
  - 인용 `FAQ_20260630`: "금융회사 전산상 대출 신청 접수가 완료되거나, 주택매매계약을 체결하고 계약금 납부 사실 증명시 종전규정 적용 가능"

**A.5 [EXCEPTION]** 생애최초 주택구입은 완화된 LTV 70% 유지  (70% → 70%, conf 0.90)
  - 인용 `MOLIT_PRESS_20260630`: "생애최초 LTV 70% + 전입의무(6개월 이내)"

**A.6 [EXCEPTION]** 금융권 서민·실수요자 주담대는 완화된 LTV 적용(60%)  (- → 60%, conf 0.88)
  - 인용 `FAQ_20260630`: "금융권 서민·실수요자 주담대*, 정책모기지 등에 대해서는 완화된 LTV가 적용됨"

**A.7 [LTV]** 다주택자는 수도권 내 주택구입시 LTV 0% 적용  (- → 0%, conf 0.95)
  - 인용 `FSC_PRESS_20260630`: "다주택자는 수도권 內 주택구입시 규제지역 여부와 무관하게 LTV 0% 적용"

**A.8 [LTV]** 규제지역 유주택자 주택구입목적 주담대 LTV 0%  (- → 0%, conf 0.93)
  - 인용 `MOLIT_PRESS_20260630`: "무주택(처분조건부 1주택 포함) 40%, 유주택 0%"

**A.9 [SCOPE_LIMIT]** 전세대출 보유자의 규제지역 내 3억원 초과 APT 취득시 전세대출 회수  (- → 전세대출 회수, conf 0.85)
  - 인용 `FAQ_20260630`: "전세대출 보유자가 투기·투과지역 내 3억원 초과 APT 취득*시 전세대출 회수"

## 부록 B. Impact Matrix 전체 행

| key | 지역 | 차주유형 | 기존 | 변경 | 방향 | 경과규정 | 근거코드 |
|---|---|---|---:|---:|---|---|---|
| NO_HOME_STANDARD | 용인 기흥 | 무주택 일반 | 70% | 40% | DOWNGRADE | - | LTV_REGULATED_40 |
| FIRST_HOME | 화성 동탄 | 생애최초 | 70% | 70% | UNCHANGED | - | EXCEPTION_FIRST_HOME |
| REAL_DEMAND | 구리 | 서민·실수요 | 70% | 60% | DOWNGRADE | - | EXCEPTION_REAL_DEMAND |
| OWNER_1_NON_DISPOSAL | 용인 기흥 | 유주택(비처분 1주택) | 명세부재 | 0% | NEW_RESTRICTION | - | LTV_OWNER_0 |
| DISPOSAL_1_HOME | 구리 | 처분조건부 1주택 | 70% | 40% | DOWNGRADE | - | LTV_REGULATED_40 |
| MULTI_HOME | 구리 | 다주택 | 명세부재 | 0% | NEW_RESTRICTION | - | LTV_MULTI_HOME_0 |
| GRANDFATHERED_CONTRACT | 화성 동탄 | 무주택 일반(경과규정) | 70% | 70% | UNCHANGED | 해당 | GRANDFATHERED_ACCEPTED_OR_CONTRACT |
| POLICY_LOAN | 구리 | 정책대출(디딤돌) | 명세부재 | - | DISCOVERY | - | DISCOVERY_POLICY_LOAN |
| JEONSE_LOAN | 구리 | 전세자금대출 | 명세부재 | - | DISCOVERY | - | OUT_OF_SCOPE_PRODUCT |

## 부록 C. 골드셋 카테고리 분포 & split

| category | DEV | LOCKED | CHALLENGE |
|---|---:|---:|---:|
| AMBIGUOUS | 0 | 0 | 10 |
| BORROWER_TYPE | 5 | 4 | 0 |
| CONFLICT | 0 | 0 | 13 |
| EFFECTIVE_DATE | 3 | 3 | 6 |
| EXCEPTION | 8 | 7 | 0 |
| GRANDFATHERING | 6 | 5 | 6 |
| LOAN_PURPOSE | 7 | 7 | 0 |
| NORMAL | 8 | 8 | 0 |
| NO_CHANGE | 0 | 3 | 0 |
| REGION | 3 | 3 | 0 |

## 부록 D. reason_code 사전

| code | 의미 |
|---|---|
| `LTV_REGULATED_40` | 규제지역 무주택 표준 LTV 40% |
| `EXCEPTION_FIRST_HOME` | 생애최초 예외 — LTV 70% 유지 |
| `EXCEPTION_REAL_DEMAND` | 서민·실수요자 예외 — LTV 60% |
| `LTV_OWNER_0` | 규제지역 유주택(비처분 1주택) LTV 0% |
| `LTV_MULTI_HOME_0` | 다주택 LTV 0% |
| `LTV_BASELINE_70` | 非규제 무주택 기준선 70% |
| `GRANDFATHERED_ACCEPTED_OR_CONTRACT` | 경과규정 — 접수/계약+계약금으로 종전규정 |
| `GRANDFATHERED_LAND_PERMIT` | 경과규정 — 토지거래허가 신청으로 종전규정 |
| `OWNER_BASELINE_UNKNOWN` | 非규제 유주택 기준선 원문 부재 → 사람 검토 |
| `OUT_OF_SCOPE_PRODUCT` | 주택구입목적 아님 → 자동판정 범위 밖 |
| `DISCOVERY_POLICY_LOAN` | 정책대출 → Discovery(수동 정책검토) |

## 부록 E. 재현 방법

```bash
python -m pytest                     # 전체 테스트
python examples/demo_report.py       # 검증 보고서 요약(텍스트)
python examples/build_report_doc.py  # 본 문서(마크다운) 생성
python examples/demo_gold_set.py     # 골드셋 DEV 회귀
python examples/run_extractor.py     # RegChange 추출 + Assurance
python examples/render_ui.py         # 6개 화면(오프라인)
```

본 문서의 모든 수치는 위 코드 실행 결과와 일치한다(손으로 적지 않음).
