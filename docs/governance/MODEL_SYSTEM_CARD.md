# Model & System Card — RegImpact AI

> 생성: `python examples/build_governance_docs.py` · 생성 시각 2026-08-19 12:18 UTC
> 정량 수치는 파이프라인 실측(`docs/eval/runs/run_perdoc_sonnet5.json`, provider `replay`)에서 온다.

---

# A. System Card

## A.1 요약

주택담보대출 규제 변경(공문)을 읽어 **무엇이 달라졌는지 추출하고, 그 변경이 여신 룰·고객
영향·테스트케이스로 어떻게 전파되는지 산출하며, 각 단계 산출물을 독립 기준과 대조**하는
시스템이다.

**LLM 을 규제 판정에 쓰는 시스템이 아니다.** LLM 은 인용 근거가 붙은 사실만 추출하고,
판정은 사람이 확정한 명세를 구현한 결정적 엔진이 수행한다. 이 경계 덕분에 엔진이 LLM 출력의
검증 기준이 될 수 있다.

## A.2 구성

| 컴포넌트 | 성격 | 역할 |
|---|---|---|
| RegChange Extractor | LLM | 공문 → 구조화 변경 사실 (인용 필수) |
| Citation Assurance | 결정적 | 인용이 원문에 verbatim 존재하는지 대조 |
| Policy Version DB / Resolver | 데이터 | 정책의 시점 해석 · 직전 정책 대비 diff |
| Rule Engine | 결정적 | 확정 명세(§H)의 구현 — LTV 판정 |
| TC Generator / Oracle | 결정적 | 명세 독립 재구현 → 차등 검증 |
| Rule Change Proposal | 결정적 조립 | 추출 → 구조화 변경안(DRAFT) → 엔진 교차검증 |
| Impact Matrix | 결정적 | 포트폴리오 영향 · 업무영역별 조치 |
| Audit Trail | 결정적 | 해시 체인 감사로그 |
| Discrimination Harness | 결정적 | 오류 주입 후 지표 반응 측정 |

## A.3 사용 목적 (Intended Use)

- 규제 변경 1건에 대한 **초안 영향분석**과 그 근거 제시
- 사람 검토가 필요한 지점을 **사유와 함께** 표면화
- 검증 산출물(보고서·감사로그·테스트케이스) 생성

## A.4 범위 외 · 오용 (Out-of-scope / Misuse)

- ❌ **사람 승인 없는 룰 반영** — 변경안은 항상 DRAFT 로 생성되며 registry 에 자동 반영되지 않는다
- ❌ **실제 고객 심사 판정** — 합성 포트폴리오 기반이며 실 시스템 연동이 없다
- ❌ **전세대출·신용대출·중도금·사업자대출·정책대출 판정** — Discovery 로 분리, 코어 밖
- ❌ **법률 자문** — 원문 해석의 최종 책임은 사람에게 있다

## A.5 데이터

- **입력:** 공개 보도자료·FAQ 3건 (sha256 고정). 실제 회사 문서·고객 데이터 없음
- **지역 레지스트리:** 42곳, 시점 버전 데이터. 값 출처는 공문 현황표
- **포트폴리오:** 층화 합성 2,000건 (seed `0`) — **커버리지 측정 전용**
- **평가셋:** DEV 40문항 · LOCKED 40문항 · CHALLENGE 35문항 · TEMPORAL 12문항 (LOCKED/CHALLENGE 봉인)

## A.6 정량 평가 결과

| 지표 | 값 |
|---|---|
| Citation Correctness | 100% (75/75) |
| Unsupported Claim Rate | 0% |
| Change Completeness | 100% |
| Exception Recall | 100% |
| Rule Regression (독립 오라클) | 100% (36/36) |
| Proposal ↔ Engine Consistency | 8/10 |
| 심사 판정 커버리지 | 91.4% |
| 영향 측정 커버리지 | 74.1% |
| 코어 자동처리 비율 | 67% |

### 판별력 (negative control)

정상값 100% 는 하니스가 오류에 둔감해도 나온다. 오류를 주입하고 다시 잰 결과다.

| 지표 | 정상 | 오류 주입 | 반응 |
|---|---|---|---|
| Citation Correctness | 100% | 98% | ✅ |
| Unsupported Claim Rate | 0% | 2% | ✅ |
| Change Completeness | 100% | 94% | ✅ |
| Exception Recall | 100% | 50% | ✅ |
| Effective-date Correct | 100% | 0% | ✅ |
| Regions Correct | 100% | 0% | ✅ |
| Rule Regression (LTV 40%→50% 변조) | 100% | 75% | ✅ |
| Rule Regression (기준선 70%→65% 변조) | 100% | 75% | ✅ |
| Proposal Consistency | 80% | 50% | ✅ |

## A.7 리스크 요약

등록 **18건** / 5범주 · 통제 38/40 운영 중.
잔여위험: High 1 · Medium 7 · Low 10 · Critical 0.

| ID | 리스크 | 고유 → 잔여 |
|---|---|---|
| R-RUL-02 | 명세 자체가 원문을 오독 | 15 → 10 (High) |
| R-AI-01 | 환각 — 원문에 없는 규제 사실 생성 | 20 → 8 (Medium) |
| R-AI-02 | 누락 — 변경 사항을 빠뜨림 | 16 → 6 (Medium) |
| R-AI-03 | 모델·프롬프트 변경에 따른 드리프트 | 12 → 6 (Medium) |
| R-AI-04 | 프롬프트 인젝션 — 원문에 심긴 지시 | 8 → 6 (Medium) |

상세: `docs/governance/AI_RISK_REGISTER.md`

## A.8 거버넌스

- **규칙 값은 LLM 이 만들지 않는다** — 사람이 원문 대조로 확정한 명세에서 온다
- **AI 초안 → 사람 확정** — DRAFT 는 판정 경로에 들어가지 않는다
- **평가셋 봉인** — LOCKED/CHALLENGE 는 사유 없이 로드 자체가 거부되고 접근이 기록된다
- **감사추적** — 해시 체인, head 해시를 검증보고서에 외부 앵커로 남긴다

## A.9 한계

검증보고서 §11 과 `docs/eval/VALIDATION_LIMITS.md` 참조. 요약하면 —
인용의 **적절성**은 미검증(존재만 확인), 집계 비율은 단건 오류에 둔감, 합성 포트폴리오는
성능 주장의 근거가 아니며, 영향 측정 커버리지는 원문의 값 공백 때문에
74.1% 에서 상한에 걸린다.

---

# B. Model Card — RegChange Extractor (LLM 컴포넌트)

## B.1 모델

- **역할:** 공문 텍스트 → 구조화된 변경 사실 (JSON, 인용 필수)
- **provider 주입식** — 특정 모델에 묶이지 않는다. 무과금 경로 우선
  (`cli` → `gemini` → `anthropic` → `manual`), 재현은 `replay`
- **이번 측정:** provider `replay` (원본 `docs/eval/runs/run_perdoc_sonnet5.json`)

## B.2 입력 · 출력

- 입력: 공문 원문 텍스트 (문서별로 분리 호출)
- 출력: `policy_id` · `effective_from` · `target_regions` · `changes[]`
  (각 change 는 category · summary · before · after · **citation** 필수)
- 이번 실행 산출: 변경 **75건** — EFFECTIVE_DATE 9 · EXCEPTION 21 · GRANDFATHERING 12 · LTV 10 · REGION 5 · SCOPE_LIMIT 18

## B.3 사용 목적 · 범위 외

LLM 은 **사실 추출만** 한다. 규칙 값 결정, LTV 판정, 승인 결정은 하지 않는다.
출력은 룰엔진을 수정할 수 없고, 결정적 조립을 거쳐 변경안(DRAFT)이 된다.

## B.4 알려진 실패 모드

| 실패 모드 | 탐지 | 발생 이력 |
|---|---|---|
| 인용 환각 | Citation grounding (verbatim 대조) | 없음 (D-03 은 오진으로 철회) |
| 항목 누락 | 골드 대조 Change Completeness / Exception Recall | D-02 |
| 문서 간 열거 가림 | 문서별 추출 + 병합으로 구조 해소 | D-02 |
| 카테고리 오분류 | 변경안 조립 시 `unmapped` 로 표면화 | P-02 |
| 세그먼트 값 혼동 | 변경안 `conflicts` 로 표면화 | P-01 |

## B.5 Caveats

- **`replay` 는 벤치마크가 아니다.** 실제 실행 기록의 재생이며 결정적 재현이 목적이다
- 골드 대조는 **recall** 이지 precision 이 아니다 — 골드에 없는 변경은 측정 대상 밖이다
- DEV 셋은 반복 사용하므로 그 성능은 낙관적으로 읽어야 한다

---

## C. 참조

| 문서 | 내용 |
|---|---|
| `docs/validation/VALIDATION_REPORT.md` | 시스템 검증보고서 (발견사항 포함) |
| `docs/governance/AI_RISK_REGISTER.md` | AI 리스크 레지스터 |
| `docs/eval/VALIDATION_LIMITS.md` | 검증 한계 상세 |
| `docs/05_RULE_SPEC.md` | 확정 룰 명세 |
| `docs/regulatory_facts.md` | 사람 확정 규제 사실 |
