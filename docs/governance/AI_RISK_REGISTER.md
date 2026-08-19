# AI Risk Register — RegImpact AI

> 생성: `python examples/build_governance_docs.py` · 정량 수치는 파이프라인 실측에서 온다.
>
> 리스크의 발생가능성·영향은 **측정값이 아니라 판단**이므로 `src/regimpact/governance/risk.py`
> 에 사람이 적는다. 대신 통제는 말로 끝나지 않게 **실재하는 코드·테스트를 가리키도록 강제**한다
> — `tests/test_governance.py` 가 참조 경로의 존재를 확인한다.

## 1. 평가 방법론

**Rating = Likelihood(1~5) × Impact(1~5)**
Low 1–4 · Medium 5–9 · High 10–15 · Critical 16–25

Impact 기준은 도메인 특수하다 — 잘못된 규제 사실·LTV 오판이 여신 의사결정과 고객 피해로
전파되는 정도로 잰다.

통제 유형: **[검증]** 결정론적 검사 · **[설계]** 아키텍처 통제 · **[프로세스]** 운영 규율
상태: ✅ 운영 · 🟡 부분 · ⬜ 계획

**잔여위험은 0으로 만들지 않는다.** 통제 후에도 남는 것을 정직하게 적고, 수용한다면 근거를 남긴다.

## 2. 요약

- 등록 리스크 **18건** / 5범주
- 고유위험: Critical 3 · High 12 · Medium 3 · Low 0
- 잔여위험: Critical 0 · High 1 · Medium 7 · Low 10
- **실제 발생 이력이 있는 리스크: R-AI-02, R-RUL-02, R-RUL-03, R-RUL-04, R-DAT-04** — 가상의 목록이 아니라는 뜻이다
- 미구현 통제:
- R-AI-04: 인젝션 탐지 필터

### 잔여위험 히트맵

| | I1 | I2 | I3 | I4 | I5 |
|---|---|---|---|---|---|
| **L5** |  |  |  |  |  |
| **L4** |  |  |  |  |  |
| **L3** |  | R-AI-05 |  |  |  |
| **L2** |  |  | R-AI-02, R-AI-03, R-AI-04, R-DAT-04, R-GOV-03 | R-AI-01 | R-RUL-02 |
| **L1** |  | R-DAT-02, R-OPS-01, R-OPS-02 | R-RUL-04, R-GOV-01 | R-RUL-01, R-RUL-03, R-DAT-01, R-DAT-03, R-GOV-02 |  |

잔여 High 는 **R-RUL-02(명세 자체의 원문 오독)** 하나다. 차등검증으로 잡을 수 없는 범주라
의도적으로 높게 유지한다 — 실제로 R-01 이 이 경로로 발생했고, 어떤 지표로도 잡히지 않았다.

## 3. 현재 실측 (검증보고서 연동)

| 통제 | 실측 |
|---|---|
| 인용 verbatim 대조 | Citation Correctness 100% (75/75) |
| 차등 검증 | Rule Regression 100% (36/36) |
| 판별력 | 9/9 지표가 오류에 반응 |
| 정책 DB ↔ 기준선 | 드리프트 없음 |
| 사람 검토 유도 | 변경안 NEEDS_REVIEW · 엔진 대조 8/10 |
| 감사로그 | 9건 · 체인 OK |

감사로그 head (외부 앵커): `7e1817f772d568c0491b2777d1c0645c3286b446fe30f953be4e93e8136be811`

## 4. 리스크 상세

### AI/LLM
#### R-AI-01 — 환각 — 원문에 없는 규제 사실 생성

LLM 이 공문에 없는 LTV·시행일·지역을 그럴듯하게 만들어 내고, 그것이 여신 판정으로 전파된다.

- **평가:** 4×5=20 (Critical) → 2×4=8 (Medium) (감소 12)
- **통제:**
  - ✅ **[검증]** 인용이 원문에 verbatim 존재하는지 결정적 대조 (LLM 자기판단 아님)<br/>근거: `src/regimpact/extractor/evaluate.py` · `tests/test_extractor.py`
  - ✅ **[검증]** 판별력 실측 — 환각을 주입하면 지표가 떨어지는지 확인<br/>근거: `src/regimpact/discrimination.py` · `tests/test_discrimination.py`
  - ✅ **[설계]** 추출은 룰엔진을 수정하지 않는다 — 변경안(DRAFT)으로만 조립<br/>근거: `src/regimpact/proposal/`
- **잔여위험 수용 근거:** 인용의 **적절성**(원문 아무 문장이나 붙이는 경우)은 미검증이라 잔여위험을 0으로 낮추지 않는다.
#### R-AI-02 — 누락 — 변경 사항을 빠뜨림

여러 문서에 흩어진 예외·경과규정을 일부만 추출해, 반영해야 할 변경이 누락된다.

- **평가:** 4×4=16 (Critical) → 2×3=6 (Medium) (감소 10)
- **통제:**
  - ✅ **[검증]** 사람 확정 골드 대조 — Change Completeness / Exception Recall<br/>근거: `docs/eval/regchange_gold_6_30.json`
  - ✅ **[설계]** 문서별 추출 후 문서 간 병합 — 문서 간 열거가 서로를 가리는 문제 제거<br/>근거: `src/regimpact/extractor/merge.py`
- **잔여위험 수용 근거:** Completeness 는 recall 이지 precision 이 아니다 — 골드에 없는 변경은 측정 밖.
- **실제 발생:** D-02 — `docs/validation/VALIDATION_REPORT.md` §12
#### R-AI-03 — 모델·프롬프트 변경에 따른 드리프트

provider·모델을 교체하면 추출 품질이 조용히 달라지는데, 회귀 없이 배포되면 알 수 없다.

- **평가:** 4×3=12 (High) → 2×3=6 (Medium) (감소 6)
- **통제:**
  - ✅ **[설계]** provider 주입 — 동일 입력으로 교체 비교 가능<br/>근거: `src/regimpact/extractor/backends.py`
  - 🟡 **[검증]** 봉인된 평가셋(LOCKED/CHALLENGE)으로 교체 시 재측정<br/>근거: `docs/eval/gold/`
- **잔여위험 수용 근거:** LOCKED/CHALLENGE 는 코어 완성 시 1회만 열기로 해 상시 회귀 게이트가 아니다.
#### R-AI-04 — 프롬프트 인젝션 — 원문에 심긴 지시

공문 형식의 입력에 '이전 지시를 무시하라' 류 문구가 섞이면 추출이 조작될 수 있다.

- **평가:** 2×4=8 (Medium) → 2×3=6 (Medium) (감소 2)
- **통제:**
  - ✅ **[설계]** 입력은 공개 공문 스냅샷으로 한정 + 해시 고정<br/>근거: `docs/sources/SOURCES.md`
  - ✅ **[검증]** 출력이 룰을 바꾸지 못한다 — 변경안은 사람 승인 전 registry 미반영<br/>근거: `src/regimpact/proposal/consistency.py`
  - ⬜ **[검증]** 인젝션 탐지 필터<br/>근거: —
- **잔여위험 수용 근거:** 조작에 성공해도 룰엔진을 직접 바꿀 수 없는 구조라 영향이 제한된다.
#### R-AI-05 — 자동화 편향 — 사람이 AI 산출을 그대로 승인

검토자가 DRAFT 를 형식적으로 승인해 사실상 자동 반영이 된다.

- **평가:** 3×4=12 (High) → 3×2=6 (Medium) (감소 6)
- **통제:**
  - ✅ **[설계]** 미통과 항목을 사유와 함께 표면화 — 무엇을 봐야 하는지 지정<br/>근거: `src/regimpact/proposal/consistency.py`
  - ✅ **[설계]** 자동처리 불가 행은 사유 없이 생성 불가 (스키마가 거부)<br/>근거: `src/regimpact/impact/schema.py`
  - ✅ **[프로세스]** 승인 이력을 감사로그에 기록<br/>근거: `src/regimpact/audit/`
- **잔여위험 수용 근거:** 사람의 주의력은 시스템이 통제할 수 없다 — 잔여위험을 Low 로 낮추지 않는다.

### 규칙·판정
#### R-RUL-02 — 명세 자체가 원문을 오독

엔진과 오라클이 **같은** 오독을 공유하면 일치율 100% 로도 잡히지 않는다.

- **평가:** 3×5=15 (High) → 2×5=10 (High) (감소 5)
- **통제:**
  - ✅ **[프로세스]** 규칙 값은 사람이 원문 대조로 확정 (LOCKED §4)<br/>근거: `docs/regulatory_facts.md` · `docs/05_RULE_SPEC.md`
  - ✅ **[검증]** 골드 확정 지문 — 확정 후 수정 시 재검수 필요로 드러남<br/>근거: `src/regimpact/eval/confirmation.py`
- **잔여위험 수용 근거:** 차등검증으로 잡을 수 없는 범주다. 실제로 R-01 이 이 경로로 발생했고, 지표가 아니라 원문 재독해로 발견됐다. 잔여위험을 High 로 유지한다.
- **실제 발생:** R-01, R-01b — `docs/validation/VALIDATION_REPORT.md` §12
#### R-RUL-01 — 룰엔진 구현이 확정 명세와 어긋남

명세는 맞는데 코드가 다르게 동작해 판정이 틀린다.

- **평가:** 3×5=15 (High) → 1×4=4 (Low) (감소 11)
- **통제:**
  - ✅ **[검증]** 차등 검증 — 명세를 독립 재구현한 오라클과 전 케이스 대조<br/>근거: `src/regimpact/tc_generator/oracle.py` · `tests/test_tc_generator.py`
  - ✅ **[검증]** 변이 테스트 — 상수를 변조하면 회귀가 잡는지 확인<br/>근거: `tests/test_discrimination.py`
#### R-RUL-03 — 지역 데이터 누락이 관대한 판정으로 전파

레지스트리에 없는 지역을 비규제로 간주하면, 데이터 공백이 완화된 LTV 로 새어나간다.

- **평가:** 4×5=20 (Critical) → 1×4=4 (Low) (감소 16)
- **통제:**
  - ✅ **[설계]** 미등록 지역은 UNKNOWN → 사람 검토 (P0d). 비규제로 간주하지 않는다<br/>근거: `src/regimpact/regions.py` · `tests/test_regions.py`
  - ✅ **[검증]** 정책 DB ↔ 기준선 양방향 드리프트 검사<br/>근거: `src/regimpact/policy/consistency.py`
- **실제 발생:** R-01 — `docs/validation/VALIDATION_REPORT.md` §12
#### R-RUL-04 — 원문에 값이 없는 구간을 추정으로 메움

기준값이 없는 세그먼트에 그럴듯한 값을 넣으면 근거 없는 판정이 만들어진다.

- **평가:** 3×5=15 (High) → 1×3=3 (Low) (감소 12)
- **통제:**
  - ✅ **[설계]** 기준값 부재는 escalate — 추정 금지 (LOCKED §4)<br/>근거: `src/regimpact/rule_engine.py`
  - ✅ **[설계]** 세그먼트 값 충돌 시 동률이면 아무것도 고르지 않는다<br/>근거: `src/regimpact/proposal/builder.py`
- **잔여위험 수용 근거:** 대가로 영향 측정 커버리지에 상한이 생긴다 — 이는 의도된 트레이드오프다.
- **실제 발생:** P-01, P-02 — `docs/validation/VALIDATION_REPORT.md` §12

### 데이터
#### R-DAT-04 — 평가셋 오염 — 골드를 보고 모델을 맞춤

골드를 반복해서 보며 프롬프트를 조정하면 측정이 성능이 아니라 암기가 된다.

- **평가:** 4×3=12 (High) → 2×3=6 (Medium) (감소 6)
- **통제:**
  - ✅ **[설계]** DEV / LOCKED / CHALLENGE 분리 + 봉인을 코드로 강제 (20자 이상 사유 없이는 로드 거부)<br/>근거: `src/regimpact/eval/goldset.py` · `tests/test_goldset.py`
  - ✅ **[프로세스]** 봉인 접근을 append-only 로그에 기록<br/>근거: `docs/eval/gold/SEAL_ACCESS_LOG.md`
- **잔여위험 수용 근거:** DEV 셋은 반복 사용하므로 그 성능은 낙관적으로 읽어야 한다.
- **실제 발생:** G-01 — `docs/validation/VALIDATION_REPORT.md` §12
#### R-DAT-01 — 원문 스냅샷 변조·교체

검증 근거가 된 원문이 사후에 바뀌면 모든 인용 검증이 무의미해진다.

- **평가:** 2×5=10 (High) → 1×4=4 (Low) (감소 6)
- **통제:**
  - ✅ **[프로세스]** 원문 sha256 고정 + 저장소 보관<br/>근거: `docs/sources/SOURCES.md`
  - ✅ **[검증]** 해시 체인 감사로그로 파이프라인 이벤트 고정<br/>근거: `src/regimpact/audit/` · `tests/test_audit.py`
- **잔여위험 수용 근거:** 해시 체인은 끝에서 잘라낸 로그를 혼자 잡지 못한다 — head 해시를 검증보고서에 외부 앵커로 남긴다.
#### R-DAT-03 — 실제 고객 데이터 유입

개인정보가 저장소·프롬프트에 들어가면 되돌릴 수 없다.

- **평가:** 2×5=10 (High) → 1×4=4 (Low) (감소 6)
- **통제:**
  - ✅ **[설계]** 합성 데이터만 사용 — 실 고객 데이터 경로 없음 (LOCKED §0-8)<br/>근거: `src/regimpact/impact/portfolio.py`
  - ✅ **[프로세스]** 입력은 공개 보도자료·FAQ 로 한정<br/>근거: `docs/sources/SOURCES.md`
#### R-DAT-02 — 합성 포트폴리오로 성능을 주장

합성 데이터에서 나온 수치를 실제 성능처럼 제시하면 순환 논증이 된다.

- **평가:** 3×3=9 (Medium) → 1×2=2 (Low) (감소 7)
- **통제:**
  - ✅ **[프로세스]** 합성 포트폴리오는 커버리지 측정 전용 — 정확도 주장 금지<br/>근거: `src/regimpact/impact/portfolio.py`
  - ✅ **[프로세스]** 검증보고서 한계 절에 명시 (L4)<br/>근거: `docs/eval/VALIDATION_LIMITS.md`

### 거버넌스
#### R-GOV-03 — 검증 하니스가 오류에 둔감해짐

지표가 항상 100% 인데 실은 아무것도 잡지 못하는 상태가 될 수 있다.

- **평가:** 3×4=12 (High) → 2×3=6 (Medium) (감소 6)
- **통제:**
  - ✅ **[검증]** 판별력(negative control) — 오류 주입 후 지표 반응 측정<br/>근거: `src/regimpact/discrimination.py` · `tests/test_discrimination.py`
  - ✅ **[검증]** 집계 지표의 둔감성을 테스트로 고정 — 성질이 바뀌면 문서도 고치라고 실패<br/>근거: `docs/eval/VALIDATION_LIMITS.md`
- **잔여위험 수용 근거:** 집계 비율은 단건 오류에 둔감하다는 성질 자체는 제거할 수 없다.
#### R-GOV-02 — AI 초안이 확정 없이 판정에 사용됨

DRAFT 상태의 정책·변경안이 사람 승인 없이 실제 판정 경로에 들어간다.

- **평가:** 3×5=15 (High) → 1×4=4 (Low) (감소 11)
- **통제:**
  - ✅ **[설계]** CONFIRMED 만 지역 상태에 반영 — DRAFT 는 미리보기만<br/>근거: `src/regimpact/policy/resolver.py` · `tests/test_policy.py`
  - ✅ **[설계]** 변경안은 항상 DRAFT 로 생성 — APPROVED 로 태어나지 않는다<br/>근거: `src/regimpact/proposal/builder.py`
#### R-GOV-01 — 변경 이력·승인 근거 부재

무엇이 언제 왜 바뀌었는지 재구성할 수 없으면 검증 결과를 신뢰할 수 없다.

- **평가:** 3×4=12 (High) → 1×3=3 (Low) (감소 9)
- **통제:**
  - ✅ **[검증]** 해시 체인 감사로그 — 변조·재정렬·중간삭제 탐지<br/>근거: `src/regimpact/audit/log.py` · `tests/test_audit.py`
  - ✅ **[프로세스]** 정책 버전을 git 안 JSON 으로 관리 — 이력이 곧 승인 기록<br/>근거: `docs/policies/`
  - ✅ **[프로세스]** 의사결정 로그<br/>근거: `docs/02_DECISION_LOG.md`

### 운영
#### R-OPS-01 — 비용·자격증명 문제로 재현 불가

리뷰어가 API 키가 없어 결과를 재현하지 못하면 검증 주장이 확인되지 않는다.

- **평가:** 4×2=8 (Medium) → 1×2=2 (Low) (감소 6)
- **통제:**
  - ✅ **[설계]** replay provider — 실제 실행 기록 재생, LLM 호출 0회<br/>근거: `src/regimpact/extractor/backends.py`
  - ✅ **[설계]** 무과금 경로 우선 (cli → gemini → anthropic → manual)<br/>근거: `docs/06_LLM_PROVIDER.md`
#### R-OPS-02 — 검증보고서가 코드보다 낡아짐

손으로 쓴 수치가 시스템 변경 후에도 남아 조용히 거짓말이 된다.

- **평가:** 4×3=12 (High) → 1×2=2 (Low) (감소 10)
- **통제:**
  - ✅ **[설계]** 보고서를 라이브 실행 결과에서 생성<br/>근거: `src/regimpact/report/evidence.py`
  - ✅ **[검증]** 실측 절에 수치 리터럴 금지 — 테스트가 강제<br/>근거: `tests/test_validation_report.py`

## 5. 이 레지스터의 한계

- 발생가능성·영향은 **1인 작성자의 판단**이며 외부 검증을 받지 않았다
- 통제의 **존재**는 테스트로 강제하지만, 통제의 **충분성**은 판단 영역이다
- 운영 이력이 없어 발생 빈도는 사후 데이터가 아니라 사전 추정이다
