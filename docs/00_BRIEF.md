# RegImpact AI — 프로젝트 브리프 v2

> 이 문서는 PRD 작성과 개발의 기반 컨텍스트다.  
> 기존 브리프의 핵심 철학은 유지하되, 검증 엄밀성·시간축·룰 변경 통제·평가 누수 방지·MVP 범위를 명확히 하기 위해 보완한 버전이다.

---

## 0. 의사결정 원칙: LOCKED vs ADJUSTABLE

PRD 작성과 개발 과정에서 모든 결정을 같은 강도로 고정하지 않는다.

### LOCKED — 임의로 뒤집지 말 것

아래는 프로젝트의 정체성을 만드는 결정이다. 변경이 필요하다고 판단되면 먼저 사용자에게 이유를 설명하고 확인받을 것.

1. **E가 제품이고 A가 신뢰의 기반이다.**
   - E: 규제 변경 영향분석
   - A: AI 결과의 검증·통제(Assurance)
2. **챗봇이 아니라 검증 가능한 의사결정 지원 시스템을 만든다.**
3. **주택구입목적 주담대 규제의 수직 슬라이스를 유지한다.**
4. **실행 가능한 룰엔진의 규칙 로직은 LLM이 생성하지 않는다.**
5. **평가셋을 개발보다 먼저 만들고, DEV / LOCKED TEST / CHALLENGE를 분리한다.**
6. **Assurance Layer와 Test Case Generator는 일정이 밀려도 자르지 않는다.**
7. **임팩트 매트릭스의 시간축(Phase)은 삭제하지 않는다.**
8. **실제 회사 내부문서·고객데이터를 사용하지 않는다.**
9. **LLM은 금융 의사결정을 직접 실행하지 않고 변경안·영향분석·검토자료를 제안한다.**
10. **자동화 범위보다 검증 가능성과 추적 가능성을 우선한다.**

### ADJUSTABLE — 구현 과정에서 합리적으로 변경 가능

- LLM 제공자·모델
- RAG/Agent 프레임워크
- Vector DB 또는 저장소
- 로컬 DB 종류
- UI 프레임워크
- 폴더 구조
- 포트폴리오 건수(권장 2,000~5,000)
- 평가셋 세부 건수(총 150~200 범위)
- 로컬 데모 vs 웹 배포
- 공개 저장소 여부
- 대시보드 시각화 범위

---

## 1. 프로젝트 한 줄 정의

**생성형 AI 기반 주택담보대출 규제 변경 영향분석 및 검증 시스템**  
영문: **RegChange AI — Financial Policy Impact & Assurance Lab**

핵심 질문 두 개:

1. 정부의 가계대출 정책이 바뀌었을 때, 금융회사는 변경사항을 얼마나 빠르고 정확하게 **여신정책·전산 Rule·고객 영향·테스트케이스**로 변환할 수 있는가?  
   → **제품 = E**
2. 그 작업을 LLM/Agent가 수행한다면, 어떻게 정확성을 검증하고 사람이 어디에서 승인해야 하는가?  
   → **신뢰 기반 = A, Assurance Layer**

**E가 제품이고 A가 신뢰의 기반이다. 챗봇이 아니라 검증 가능한 의사결정 지원 시스템을 만든다.**

---

## 2. 왜 이 프로젝트인가 — 배경 서사

만드는 사람이 곧 이 문제의 당사자였다.

- 사용자는 금융권 개인여신 데이터분석 8년 7개월 경력자.
- CSS(신용평가모형) 개발·검증, 컷오프룰, LTV 차등 한도전략, 리스크 기반 금리 산출, 금감원·한은 대외보고 실무를 수행.
- 대표 성과: LTV 차등 전략으로 평균 불량률 5.77% → 3.16%.
- 그 이전 약 2년간 NLP 콜분석·챗봇 솔루션의 학습데이터 설계와 탐지사전 구축 담당.
- 감성분석 학습데이터 42,092문장 등 대규모 라벨링·정의 경험 보유.
- 석사 논문(2026.08): 「국내 은행 건전성 조기경보시스템 구축을 위한 시계열 특징 엔지니어링 연구」.
- 최신 LLM/RAG/Agent 실무 경험은 이번 프로젝트를 통해 보완한다.

### 실무 고충 — 이 프로젝트의 기원

정부 부동산 대출 규제가 바뀔 때마다 발표일~시행일 사이의 짧은 간격 안에 다음 작업을 완료해야 했다.

**요건정리 → IT 수정요청 → 테스트 → 전산반영 → 현업 공지**

수기운영을 피하려고 시행 전날까지 야근으로 전산 반영을 완료하곤 했다.

### 가치 제안

**“시행 전날까지 이어지던 수기 영향분석을, 발표 당일 검토 가능한 초안으로.”**

영문:

**“From regulation release to review-ready impact analysis — on the same day.”**

이 프로젝트는 IT 배포나 내규 승인 자체를 자동 완료하는 시스템이 아니다.  
**규제 발표 직후, 사람이 검토·승인할 수 있는 수준의 영향분석·룰 변경안·테스트케이스를 빠르게 만드는 것**이 목표다.

### 용도

이직 포트폴리오.

타깃:
- 금융권 모델리스크관리 / 모델검증
- AI Governance
- AI Quality / Safety / Evaluation
- AI Model Risk / AI Assurance
- LLM/RAG 활용 금융 직무
- 금융 Risk + AI Transformation 컨설팅

면접에서 열어 보여주는 물건이므로 데모의 화려함보다 **평가·검증의 엄밀함, 도메인 설계, 실패 통제**가 우선이다.

---

## 3. 실제 업무 흐름 — 임팩트 매트릭스의 원천

규제 변경 시 실제로 일어나는 일:

```text
정부 발표
→ 무엇이 바뀌었는지 파악
→ 우리 고객 중 누가 영향받는지 파악
→ LTV / DSR / 한도 / 대상지역 / 예외 조건 정리
→ 기존 Rule 파악 및 변경 필요 부분 식별
→ 전산 요건 정리하여 IT 개발자에게 쿼리·변수 수정 요청
→ 내규 개정 프로세스 (공문 상신 + 위원회 승인)
→ 기존 신청건: 시행 전까지는 기존 시스템 그대로 진행 (경과규정)
→ 테스트: 개발자 1차 수정 완료 후 “에러 나는 테스트건”을 수작업으로 생성, 오류 없을 때까지 반복
→ 전산반영: 수기운영을 피하기 위해 시행 전날까지 야근으로 완료
→ 현업 공지

[시행 후 별도 진행]
→ 금리·한도 전략 재검토
→ 대외보고: 금감원 등에서 별도 시점에 집계기준 변경 요청이 도착
→ 모니터링: 전산반영 이상 여부 수시 체크
```

### 핵심 통찰

1. **병목은 규정 읽기가 아니라 발표~시행일 간격의 시간 압축이다.**
2. **“에러 나는 테스트건 생성”은 사용자가 수작업으로 하던 적대적 테스트 생성이다.**  
   → Test Case Generator가 자동화할 대상 그 자체.
3. **일은 두 물결로 온다.**
   - 시행일 전 필수: 룰·전산·테스트·공지
   - 시행 후: 전략 재분석·대외보고 기준 변경·모니터링
4. **대외보고 기준 변경은 별도 트리거로 나중에 도착할 수 있다.**
5. 따라서 임팩트 매트릭스에는 **시간축(Phase)** 이 반드시 필요하다.
6. 규제 변경은 문서 하나의 요약 문제가 아니라 **정책 버전·시행일·예외·경과규정·기존 룰과의 충돌** 문제다.

---

## 4. 메인 데모 시나리오

**2026년 6월 30일 규제지역 추가 지정 건**을 메인 시나리오로 사용한다.

브리프 작성 시 검증 완료로 기록된 핵심 사실:

- 6.29 국토부 주거정책심의위 의결, 6.30 발표.
- 화성시 동탄구, 용인시 기흥구, 구리시를 규제지역(조정대상지역·투기과열지구) 및 토지거래허가구역으로 신규 지정.
- **7.1부터 시행 — 발표 다음날.**
- 주담대 LTV 70% → 40% (무주택자, 처분조건부 1주택자 포함).
- 예외: 생애최초 주택구입자·정책대출은 LTV 60~70% 적용.
- 다주택자: 수도권 주택구입 시 LTV 0% (기존 규제 유지).
- 전세대출: 규제지역 내 3억 초과 아파트 취득 제한 / 3억 초과 아파트 보유 차주의 전세대출 제한.
- 1억 초과 신용대출 보유 차주: 대출 실행일로부터 1년간 규제지역 내 주택 구입 제한.
- 규제지역 내 1주택자의 재건축·재개발 중도금·이주비 대출 시 추가 주택 구입 제한.
- 주택 매매·임대사업자 외 사업자의 규제지역 내 주택구입목적 주담대 원천 차단.
- **경과규정:** 6.30까지 금융회사 전산상 대출신청 접수 완료, 또는 주택매매계약 체결 + 계약금 납부 증명 차주는 종전 규정 적용.
- 토지거래허가 대상은 6.30까지 허가 신청 시 예외.
- 신규 지정으로 해당 3개 지역은 기존 룰셋과 연결되는 매핑 문제가 발생.
- 금융위가 금융권에 창구 직원 교육, 전산시스템 점검, 고객 안내를 요청.

### 코퍼스 후보

1. 6·30 규제지역 지정 건 — **메인**
2. 6·27 대책
3. 10·15 대책
4. 필요 시 1~2건 추가

정책 사례는 **3~5건으로 제한**한다.

문서 출처는 다음 공개자료만 사용한다.

- 금융위원회
- 금융감독원
- 국토교통부
- 공식 보도자료
- 공식 FAQ

### PRD 단계 검증 원칙

각 정책 문서별로 아래 메타데이터를 확정한다.

- 공식 문서명
- 기관
- 발표일
- 시행일
- 원문 URL
- 문서 ID
- 원문 저장 시점
- 원문 hash

---

## 5. MVP 범위 — 영향 탐지는 넓게, 실행 가능한 자동판정은 좁게

### 5.1 Core Executable Scope — 룰엔진이 실제 판정하는 범위

1차 MVP의 실행 가능한 룰엔진은 다음으로 제한한다.

> **주택구입목적 주담대의  
> 지역 × 주택수 × 생애최초 여부 × 정책대출 여부 × 신청/계약 이벤트 시점 × 경과규정  
> → 적용 LTV / 적용 Rule / 경과규정 여부**

즉, **주담대 LTV + 규제지역 + 예외 + 경과규정**을 수직으로 깊게 구현한다.

### 5.2 Discovery Scope — 영향 가능성만 탐지하는 범위

다음은 Impact Matrix에서 영향 가능성을 탐지하되, 1차 MVP의 deterministic rule engine으로 자동판정하지 않는다.

- 전세대출
- 1억 초과 신용대출 관련 주택구입 제한
- 중도금·이주비
- 사업자대출
- 기타 연계 정책

이 항목들은 다음 상태로 표시할 수 있다.

```text
Potentially impacted — manual policy review required
```

### 설계 원칙

**영향 범위는 넓게 발견하되, 자동판정은 신뢰 가능한 좁은 범위에서만 한다.**

이는 기능 부족이 아니라 의도적인 Governance 설계다.

---

## 6. 시스템 아키텍처

```text
정부 / 금융위 / 금감원 / 국토부
정책·규정·FAQ (공개 문서만)
        ↓
[Source Snapshot Store]
- 원문
- URL
- 기관
- retrieved_at
- source_hash
        ↓
[Policy Version DB]
- published_at
- effective_from / effective_to
- supersedes
- scope
- version
        ↓
[Temporal Policy Resolver]
- 특정 시점에 유효한 정책 버전 결정
- 신규 정책이 대체/수정하는 기존 기준선 결정
- 시행일·경과규정·지역 상태 해석
        ↓
[RegChange Agent]
- Before / After 비교
- 변경내용 / 대상 / 시행일 / 예외 / 경과규정 추출
- 근거 인용 필수
        ↓
[Impact Analyzer]
- 임팩트 매트릭스 생성
- 고객/포트폴리오 영향 분석
- 구조화된 Rule Change Proposal 생성
        ↓
[Rule Change Proposal] + [Test Case Generator]
        ↓
[Human Review / Approval]
        ↓
[Deterministic Rule Registry / Rule Engine]
        ↓
╔════════════════ ASSURANCE LAYER ════════════════╗
║ Source grounding                               ║
║ Change completeness                            ║
║ Exception detection                            ║
║ Temporal / policy-version consistency          ║
║ Rule conflict                                  ║
║ Unsupported claim detection                    ║
║ Source contradiction detection                 ║
║ Regression testing                             ║
║ Human escalation evaluation                    ║
║ Audit trail                                    ║
║ Approval status field                          ║
╚═════════════════════════════════════════════════╝
        ↓
Human Policy Owner
```

---

## 7. Temporal Policy Resolver — 변경 탐지의 기준선

RegChange AI는 새 문서 하나를 요약하는 시스템이 아니다.

핵심은:

> **“이번 정책이 시행되는 시점에, 직전까지 유효했던 정책/Rule과 무엇이 달라졌는가?”**

를 판정하는 것이다.

### 역할

- 신규 정책의 시행일 기준으로 직전 유효 정책 탐색
- 어떤 정책/룰을 수정·대체·추가하는지 연결
- `effective_from`, `effective_to` 기준으로 특정 시점의 정책 버전 반환
- 지역의 규제상태를 시점별로 해석
- 경과규정이 있으면 적용대상 이벤트 시점과 연결
- 신규 정책과 기존 룰이 중첩될 때 우선순위 검토 대상으로 표시

### 최소 메타데이터

```text
policy_id
source_document_id
title
issuer
published_at
effective_from
effective_to
supersedes_policy_id
jurisdiction
policy_scope
version
source_url
source_hash
retrieved_at
```

### 지역 버전 관리

문자열 지역명만 저장하지 않는다.

```text
region_code
region_name
region_status
effective_from
effective_to
source_policy_id
```

**지역 상태도 시점에 따라 달라지는 버전 데이터로 취급한다.**

---

## 8. 룰엔진 — 시스템의 신뢰 기준점

현행 주담대 핵심 규칙을 실행 가능한 deterministic code로 구현한다.

입력 예:

```text
region_code
region_status_as_of_date
house_count
first_home_buyer
policy_mortgage_flag
loan_purpose
application_submitted_at
application_accepted_at
contract_signed_at
downpayment_paid_at
```

출력 예:

```text
applicable_rule_id
max_ltv
grandfathering_applied
reason_codes
source_policy_ids
```

### LOCKED 원칙

**룰엔진의 규칙 로직은 LLM으로 생성하지 않는다.**

- 사용자 본인이 규칙 명세를 작성한다.
- 코딩 에이전트는 인터페이스·테스트 하네스·보일러플레이트를 도울 수 있다.
- 규칙 자체는 도메인 지식의 증거물이며, LLM 출력 검증의 기준점이다.

---

## 9. Rule Change Proposal — LLM은 코드를 수정하지 않는다

LLM은 실행 코드를 생성·수정하는 대신 **구조화된 정책 변경안**만 제안한다.

예시:

```yaml
rule_id: MORTGAGE_LTV_REGULATED_REGION
change_type: MODIFY

before:
  region_status: NON_REGULATED
  max_ltv: 0.70

after:
  target_regions:
    - GURI
    - YONGIN_GIHEUNG
    - HWASEONG_DONGTAN
  region_status: REGULATED
  max_ltv: 0.40
  effective_from: 2026-07-01

exceptions:
  - FIRST_HOME_BUYER
  - POLICY_MORTGAGE

grandfathering:
  cutoff_date: 2026-06-30
  conditions:
    - APPLICATION_ACCEPTED
    - CONTRACT_SIGNED_AND_DOWNPAYMENT_PROVEN

source:
  policy_id: FSC_20260630
  evidence_span: "..."
```

### 실행 통제

```text
LLM Proposal
→ Human Review
→ Approved Rule Specification
→ Deterministic Rule Registry
→ Regression Test
→ Release-ready artifact
```

면접 핵심 답변:

> “LLM에는 금융 Rule을 직접 수정·실행할 권한을 주지 않았습니다.  
> 구조화된 변경안만 제안하게 하고, 사람 승인 후 deterministic rule registry에 반영하도록 설계했습니다.”

---

## 10. 임팩트 매트릭스 스키마

행은 사용자의 실제 업무 흐름에서 도출한다.

| 행 | 산출물 | Phase |
|---|---|---|
| 변경사항 식별·규정 해석 | 변경 요약 + 근거 인용 | D-day 전 |
| **고객·포트폴리오 영향 분석** | 영향 고객군, 예상 한도 변화, 경과규정 대상 | **D-day 전** |
| 심사 Rule 변경 | 구조화된 Rule diff 제안 | D-day 전 |
| 전산 요건 | IT 요청서 초안 — 쿼리·변수 수정 명세 | D-day 전 |
| 내규 개정 | 공문 초안 → 위원회 승인 대기 | D-day 전 |
| 경과규정 처리 | 기존 신청건 판정 기준 | D-day 전 |
| 테스트 | 경계·예외·충돌 TC 자동 생성 | D-day 전 |
| 현업 공지 | 공지문 초안 | D-day 전 |
| 금리·한도 전략 재분석 | 재분석 과제 정의 | 시행 후 |
| 대외보고 집계 기준 | 변경 대기 플래그 | 별도 트리거 |
| 사후 모니터링 | 체크 항목 | 시행 후 |

### 공통 열

- 업무영역
- 변경 내용
- 근거 문서 / evidence
- 영향 대상
- 산출물
- 우선순위: 필수 / 검토 / 회귀
- **기한(Phase)**
- 담당: 정책 / IT / 위원회 / 현업
- 승인 상태
- 자동처리 가능 여부
- Human Review 필요 사유

### LOCKED

**시간축(Phase)은 이 매트릭스의 핵심 차별점이므로 삭제하지 않는다.**

---

## 11. 평가셋 — 프로젝트의 심장

### 총 규모

**150~200문항**

각 문항에는 다음을 포함한다.

- 질문 / 입력
- 골드 정답
- 근거 문서
- 원문 위치
- 평가 카테고리
- 기대되는 human escalation 여부
- 적용 정책 버전
- 관련 rule_id

### 카테고리

```text
NORMAL
EXCEPTION
GRANDFATHERING
EFFECTIVE_DATE
REGION
BORROWER_TYPE
LOAN_PURPOSE
CONFLICT
NO_CHANGE
AMBIGUOUS
```

### 설계 철학

**금융규제에서 가장 무서운 오류는 원칙을 틀리는 것뿐 아니라 예외·경과규정·시행일을 놓치는 것이다.**

따라서 아래 카테고리 비중을 상대적으로 높인다.

- EXCEPTION
- GRANDFATHERING
- EFFECTIVE_DATE
- CONFLICT

---

## 12. 평가 누수 방지 — DEV / LOCKED TEST / CHALLENGE 분리

동일한 평가셋을 보면서 extractor를 튜닝하고 최종 성능을 보고하지 않는다.

### Split

권장 범위:

| Split | 권장 규모 | 용도 |
|---|---:|---|
| DEV | 60~70 | 프롬프트·retrieval·extractor 튜닝 |
| LOCKED TEST | 60~70 | 최종 성능평가 |
| CHALLENGE | 40~60 | 예외·경계·충돌·모호성 중심 적대적 평가 |

총합은 150~200 범위에서 조정 가능하다.

### 규율

1. 전체 골드셋을 먼저 설계한다.
2. Split을 확정하고 파일을 분리한다.
3. **LOCKED TEST / CHALLENGE는 개발 중 튜닝에 사용하지 않는다.**
4. 개발은 DEV만 사용한다.
5. 코어 기능 완성 후 LOCKED TEST를 실행한다.
6. CHALLENGE는 마지막 적대적 테스트로 실행한다.
7. 테스트 결과가 나쁘더라도 해당 세트에 맞춰 재튜닝한 성능을 같은 “최종 성능”으로 재보고하지 않는다.
8. 재개발이 필요하면 새 버전의 평가셋을 만들고 실험 버전을 명시한다.

### 보고서의 한계 명시

1인 프로젝트이므로 완전한 외부 블라인드 평가가 아님을 명시한다.

> “The locked test set was frozen before system tuning, but was authored within the project and is not an independent third-party benchmark.”

검증의 한계를 숨기지 않는 것이 오히려 신뢰성을 높인다.

---

## 13. 핵심 평가 지표

### 13.1 RegChange / RAG

- Change Completeness
- Exception Recall
- Grandfathering Recall
- Effective-date Accuracy
- Citation Correctness
- Policy-version Consistency

### 13.2 Hallucination 계열 — 더 측정 가능한 지표로 분리

`hallucination rate` 한 개로 뭉뚱그리지 않는다.

- **Unsupported Claim Rate**
  - 원문 근거 없이 생성된 정책 주장 비율
- **Source Contradiction Rate**
  - 원문과 명시적으로 충돌하는 주장 비율

### 13.3 Rule / Test

- Rule-regression Pass Rate
- Expected vs Actual Match Rate
- Boundary-case Pass Rate
- Conflict-case Pass Rate

### 13.4 Human Escalation

`human override rate` 자체를 품질지표로 사용하지 않는다.

대신:

- **Escalation Recall**
  - 사람 검토가 반드시 필요한 건을 얼마나 놓치지 않았는가
- **Escalation Precision**
  - 사람에게 넘긴 건 중 실제로 검토 필요 건 비율
- **High-risk Miss Rate**
  - 반드시 escalate해야 할 고위험 건을 자동처리한 비율
- **Unnecessary Escalation Rate**
  - 자동처리 가능한 건을 불필요하게 사람에게 넘긴 비율

### 13.5 최종 KPI 관점

단순 “답변 정확도”가 아니라 다음을 본다.

> **AI의 문서해석 오류가 Rule 오류·고객 영향분석 오류·테스트 누락으로 얼마나 전파되는가?**

즉:

**AI Error → Decision / Operational Risk**

로 연결한다.

---

## 14. 합성 포트폴리오

### 규모

**2,000~5,000건**

10만 건은 사용하지 않는다. 과시용 규모보다 검증 가능성을 우선한다.

### 설계 원칙

평가 카테고리별로 **정답이 알려진 고객을 의도적으로 층화 배치**한다.

즉 포트폴리오 자체가:

- 영향 시뮬레이션 데이터
- 회귀테스트 fixture
- 경과규정 검증셋

역할을 동시에 한다.

### 필드 예시

```text
customer_id
borrower_type
property_region_code
property_region_name
region_status_as_of_date

property_price
loan_amount
loan_purpose
house_count
first_home_buyer
policy_mortgage_flag

income
existing_debt
ltv
dsr

application_submitted_at
application_accepted_at
contract_signed_at
downpayment_paid_at
```

### 날짜 이벤트 세분화 이유

경과규정은 단순 `application_date` 하나로 판정하기 어렵다.

다음이 서로 다른 이벤트일 수 있다.

- 신청 제출
- 금융회사 전산 접수 완료
- 계약 체결
- 계약금 납부
- 정책 시행일

따라서 날짜를 분리해 저장한다.

### 공개 원칙

- 모든 산출 수치에 **“synthetic portfolio 결과”** 명시.
- 실제 회사 고객데이터 사용 금지.
- 실제 회사 내부정책 문서 사용 금지.
- 내부 여신정책 문서가 필요하면 공개 감독규정 기반의 **모의 정책 문서**를 직접 작성한다.
- 그 모의 정책 문서도 포트폴리오 산출물로 포함한다.

---

## 15. Test Case Generator — 핵심 차별점

사용자가 실제로 수작업으로 하던:

> “에러 나는 테스트건 생성”

을 자동화한다.

### 우선 생성 대상

- 시행일 전날 / 당일 경계
- 금융회사 접수 완료 시점 경계
- 계약일 경계
- 계약금 납부 증명 여부
- 생애최초 + 규제지역
- 정책대출 + 규제지역
- 다주택 + 수도권
- 신규 규제지역 + 기존 룰셋 연결
- 원칙과 예외 동시 충족
- 서로 다른 정책 Rule 우선순위 충돌
- 경과규정 기준 이벤트 해석
- 정상 건 회귀 테스트

### TC 태그

```text
BOUNDARY
EXCEPTION
CONFLICT
GRANDFATHERING
NEGATIVE
REGRESSION
```

### 예시

```text
TC001
지역: 구리시
주택수: 1
생애최초: N
정책대출: N
접수완료: 2026-07-02

Expected:
- 신규 규제 적용
- 적용 LTV: 40%
- grandfathering: false
```

```text
TC002
지역: 구리시
생애최초: Y
접수완료: 2026-07-02

Expected:
- 일반 LTV 40% 직접 적용 금지
- 생애최초 예외 Rule 검토
- source_policy_id 기록
```

```text
TC003
지역: 구리시
계약일: 2026-06-29
계약금 납부 증빙: Y
접수완료: 2026-07-01

Expected:
- 경과규정 검토
- 종전규정 적용 가능 여부 판정
```

### 자동 실행

```text
Generated TC
→ Deterministic Rule Engine
→ Expected vs Actual
→ Regression Result
```

Test Case Generator는 단순 생성형 기능이 아니라  
**AI + Software Testing + 금융 Model Validation 사고방식**을 연결하는 핵심 컴포넌트다.

---

## 16. Human Review / Approval 설계

복잡한 엔터프라이즈 승인 워크플로 UI는 만들지 않는다.

필요한 것은 다음 상태 필드와 audit trail 정도다.

```text
DRAFT
REVIEW_REQUIRED
APPROVED
REJECTED
SUPERSEDED
```

### 반드시 사람에게 넘겨야 하는 예

- 근거 인용이 없는 변경 주장
- 예외조건 해석이 불확실
- 서로 다른 정책 간 Rule conflict
- 경과규정 이벤트 해석이 모호
- 새로운 상품영역 — MVP rule engine 범위 밖
- Source Contradiction 발생
- Temporal Policy Resolver가 유효 버전을 단일하게 결정하지 못함

---

## 17. Audit Trail

모든 주요 판정에는 최소 다음을 남긴다.

```text
event_id
timestamp
policy_id
source_hash
system_version
model_name
prompt_version
input_hash
output
citation
decision_status
reviewer
reviewed_at
```

목표는 규정 변경 분석 결과를:

**언제 / 어떤 원문 / 어떤 모델·프롬프트 / 어떤 Rule 버전으로 만들었는지 재현 가능하게 하는 것**이다.

---

## 18. 주간 계획 — 6주 코어 + 2주 스트레치

| 주 | 작업 | 완료 기준 |
|---|---|---|
| **1주** | 메인 정책 3건 확정 + Temporal Policy 스키마 + 룰엔진 v0 + 6·30 건 수기 Impact 정답 작성 | Before/After 기준선과 실행 가능한 LTV Rule 확보 |
| **2주** | Gold 평가셋 150~200 설계 + DEV/LOCKED/CHALLENGE freeze + 문서 ingest·버전 코퍼스 | 개발 전 평가 기준 확정 |
| **3주** | Temporal Policy Resolver + RegChange Extractor 개발 | DEV 세트로만 튜닝 |
| **4주** | Impact Analyzer + 고객 영향 행 + 구조화 Rule Change Proposal | 영향매트릭스 E2E |
| **5주** | 층화 합성 포트폴리오 + TC Generator + Rule regression test | 고객영향·경계테스트 자동화 |
| **6주** | Assurance Layer + LOCKED TEST / CHALLENGE 실행 + 검증보고서 15~20쪽 | **코어 완성선** |
| **7주** | 스트레치: 정책 버전 타임라인 + 최소 대시보드 + Model/System Card + AI Risk Register | 밀리면 일부 삭제 가능 |
| **8주** | 스트레치: 배포·README·5분 데모·공개 글·지원자료 정리 | Live Fire 준비 |

### 코어 완성의 정의

**6·30 시나리오 1건이 다음 순서로 End-to-End 완결되어야 한다.**

```text
Source Snapshot
→ Policy Version Resolution
→ Before / After Change Extraction
→ Impact Matrix
→ Customer Impact
→ Structured Rule Proposal
→ Test Cases
→ Deterministic Rule Regression
→ Assurance Evaluation
→ Human Review
→ Validation Report
```

### 일정이 밀릴 때

잘라야 하는 것:
- 화려한 UI
- 대시보드 고도화
- 웹 배포
- 추가 정책 사례
- Model/System Card 일부
- 공개 글

자르면 안 되는 것:
- 평가셋 split
- Temporal Policy Resolver
- Rule Engine
- Test Case Generator
- Assurance Layer
- 검증보고서

---

## 19. 라이브 파이어 계획 — 완성 후 최강 증거

시스템 완성 후 다음 실제 부동산·가계대출 대책 발표 시 사용한다.

### 실행

1. 공식 원문 snapshot 저장
2. source hash 기록
3. 새 정책을 Policy Version DB에 등록
4. 기존 유효 버전과 비교
5. Impact Matrix 생성
6. Rule Change Proposal 생성
7. Test Case 생성
8. Assurance 결과 생성
9. Git commit
10. README에 공개 기록

### 증거 패키지

```text
official source snapshot
+
source hash
+
analysis timestamp
+
Git commit hash
+
system version
+
output artifact
```

복잡한 “사후 조작 불가 시스템”을 별도 구현하는 데 시간을 쓰지 않는다.

### README 표기 예

```text
Live Fire #1 — YYYY-MM-DD Policy Update

- Official release: HH:MM
- RegChange analysis created: HH:MM
- Commit: <hash>
- Source hash: <hash>
- Result: <artifact link>
```

핵심 메시지:

> **“이 도구는 실제 신규 규제를 발표 당일 처리했다.”**

시연이 아닌 실적을 남긴다.

---

## 20. 산출물 목록

### Core

1. 작동 데모 — 6·30 시나리오 End-to-End
2. 공식 문서 기반 Policy Version DB
3. Temporal Policy Resolver
4. 골드 평가셋 150~200문항
5. DEV / LOCKED TEST / CHALLENGE split
6. Evaluation pipeline
7. deterministic 주담대 LTV Rule Engine
8. 층화 합성 포트폴리오 2,000~5,000건
9. 고객·포트폴리오 영향 시뮬레이션
10. 임팩트 매트릭스 자동 생성
11. 구조화 Rule Change Proposal
12. Test Case Generator
13. Rule regression test
14. Assurance Layer
15. Audit trail
16. 검증보고서 15~20쪽

### Stretch

17. 정책 버전 Timeline
18. 최소 Dashboard
19. Model/System Card
20. AI Risk Register
21. 공개 글 / 기술 블로그
22. 웹 배포
23. Live Fire 기록

---

## 21. 하지 않을 것 — Non-goals

- 승인 워크플로 UI
- 복잡한 권한관리
- 10만 건 포트폴리오
- CSS/신용점수 모델 통합
- 모든 금융규정 자동판정
- 전세대출·신용대출·사업자대출의 실행 가능한 Rule Engine
- 룰엔진 규칙 로직의 LLM 생성
- LLM의 직접 코드 배포
- LLM의 금융 의사결정 자동실행
- 실제 회사 문서·고객데이터
- 모든 금융규정으로 범위 확장
- 완성도 높은 프론트엔드
- Kubernetes
- 과도한 Cloud pipeline
- GPU serving 최적화
- 복잡한 Multi-Agent
- Fine-tuning
- 최신 프레임워크 자체를 보여주기 위한 기능

Streamlit 수준의 UI면 충분하다.

---

## 22. 핵심 면접 스토리라인

### Opening

> “제가 개인여신 업무를 하면서 가장 반복적으로 큰 비용이 발생한다고 느낀 업무 중 하나가 부동산 대출 규제 변경 대응이었습니다.”

> “정책이 변경되면 단순히 문서를 읽는 것이 아니라 영향상품 식별, LTV·DSR·한도 Rule 변경, 예외·경과규정 검토, 전산 반영, 테스트, 고객 안내까지 연결해야 했습니다.”

> “특히 발표 다음날 시행 같은 경우에는 수기운영을 피하려고 시행 전날까지 테스트와 전산 반영을 반복하며 야근하곤 했습니다.”

### Why AI?

> “그래서 생성형 AI가 정책 변경을 탐지하고 고객·Rule·전산 영향과 테스트케이스까지 검토 가능한 초안으로 만드는 시스템을 설계했습니다.”

### 공격 질문 — “LLM이 잘못 해석하면요?”

> **“그래서 이 시스템의 핵심은 Agent가 아니라 Assurance Layer입니다.”**

이어 보여줄 것:

- Exception Recall
- Grandfathering Recall
- Change Completeness
- Citation Correctness
- Policy-version Consistency
- Unsupported Claim Rate
- Source Contradiction Rate
- Rule-regression Pass Rate
- Escalation Recall / High-risk Miss Rate

### 공격 질문 — “LLM이 금융 Rule을 직접 바꾸나요?”

> “아닙니다. LLM에는 실행권한을 주지 않았습니다. 구조화된 변경안만 제안하게 하고, 사람 승인 후 deterministic rule registry에 반영하도록 설계했습니다.”

### 차별화 문장

> “규정을 잘 읽는 챗봇이 아니라, 규제 변경이 실제 금융 의사결정 시스템에 미치는 영향을 추적하고 검증하는 시스템을 만들었습니다.”

---

## 23. 타깃 채용시장 컨텍스트

관찰된 공고 유형:

- 은행·금융사 LLM/RAG 활용 서비스
- 모델 성능 평가·실험 설계
- AI Quality / Safety
- AI Governance
- AI Transformation
- Digital Audit / AI Risk
- 금융권 규제 이해 + RAG / Agent / AI Evaluation

### 포지셔닝

사용자는 이미 다음 강점을 보유한다.

- 금융 도메인
- 개인여신
- 신용모형
- 정책·Rule
- 검증
- 규제 대응
- NLP 학습데이터 설계
- Python / SQL / R

이번 프로젝트의 역할은:

> **금융 도메인·규제·검증 경험을 버리고 LLM 개발자로 재출발하는 것이 아니라,  
> LLM/RAG/Agent와 AI Evaluation 역량의 ‘실증 증거’를 기존 경력 위에 추가하는 것.**

프로젝트 하나가 “LLM 실무 경력 수년”을 대체한다고 주장하지 않는다.

대신 다음을 증명한다.

- LLM/RAG 시스템을 직접 설계·구현해봤다.
- 금융 규정을 AI가 처리할 때 생기는 실패모드를 정의할 수 있다.
- 평가셋을 먼저 설계하고 locked test로 검증할 수 있다.
- AI 결과를 deterministic rule engine과 연결해 검증할 수 있다.
- Human-in-the-loop와 auditability를 기술적으로 설계할 수 있다.
- 규제 변경을 실제 고객/운영 리스크로 연결해 볼 수 있다.

---

## 24. PRD 작성 시 코딩 에이전트에게

1. 이 브리프의 **LOCKED 결정사항**을 임의로 변경하지 말 것.
2. 구현 세부사항은 **ADJUSTABLE 범위**에서 단순하고 합리적으로 제안할 것.
3. 룰엔진 규칙 명세는 사용자에게 입력을 요청할 것.
4. 임팩트 매트릭스의 메인 시나리오 수기 정답도 사용자에게 확인받을 것.
5. Gold evaluation 정답은 사용자의 도메인 검토를 거칠 것.
6. Python 기반 1인 개발·로컬 실행 중심으로 설계할 것.
7. 과한 인프라를 제안하지 말 것.
8. 사용자의 LLM/RAG 실무 경험은 이번이 처음이므로 구현 단계에서 개념 설명을 병행할 것.
9. 모든 AI 출력은 가능한 한 구조화된 schema로 정의할 것.
10. source / policy version / rule version / prompt version / model version을 추적 가능하게 설계할 것.
11. Locked test는 개발 중 튜닝 루프에 사용하지 않을 것.
12. 전세대출·신용대출 등 Discovery Scope 항목은 Impact Matrix에만 표시하고, Core Rule Engine에 억지로 포함하지 말 것.
13. UI보다 Evaluation / Rule / Test / Audit를 우선할 것.

---

## 25. PRD에서 반드시 정의해야 할 세부 항목

PRD는 최소 다음을 구체화해야 한다.

### 사용자·Use Case
- Primary user
- Trigger
- Main workflow
- Human review point
- Success criteria

### 데이터
- Policy document schema
- Policy version schema
- Region version schema
- Synthetic borrower schema
- Rule registry schema
- Test case schema
- Evaluation item schema
- Audit event schema

### 컴포넌트
- Source ingestion
- Temporal Policy Resolver
- RAG / retrieval
- RegChange Extractor
- Impact Analyzer
- Rule Proposal Generator
- Synthetic Portfolio Simulator
- Test Case Generator
- Deterministic Rule Engine
- Assurance Evaluator
- Audit Logger
- Minimal UI

### 평가
- DEV / LOCKED / CHALLENGE protocol
- metric formula
- pass/fail threshold
- high-risk failure definition
- error taxonomy
- failure review template

### 배포
- local first
- optional web deployment
- secrets management
- reproducibility

---

## 26. 최종 프로젝트 정의

RegChange AI는:

> **금융 규제 변경을 읽어주는 챗봇이 아니다.**

정부의 가계대출 정책 변화가 발생했을 때,

```text
공식 원문
→ 유효 정책 버전 해석
→ Before / After 변경 탐지
→ 고객·업무 영향 분석
→ 구조화된 Rule 변경안
→ 경계·예외·충돌 Test Case
→ deterministic Rule 검증
→ AI 결과 Assurance
→ Human Review
```

까지 연결하는 **검증 가능한 금융 규제변경 의사결정 지원 시스템**이다.

핵심 제품은 **RegChange / Impact Analysis**이고,  
핵심 차별점은 **Assurance / Testing / Temporal Versioning**이다.

---

## 27. 한 문장 요약

> **“규제가 바뀌었을 때 무엇을 고쳐야 하는지 AI가 제안하고, 그 제안이 틀리지 않았는지 검증 가능한 방식으로 증명하는 시스템.”**
