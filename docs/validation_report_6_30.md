# RegImpact AI — 검증보고서 (Validation Report)

> **6·30 규제지역 추가지정 시나리오 · 주택구입목적 주담대 LTV 코어**
> 생성형 AI 기반 규제 변경 영향분석의 **검증 가능한(auditable)** 산출물.
>
> 생성 시각: 2026-08-13 02:12 UTC
>
> ⚠️ 이 보고서는 `regimpact.report.build_validation_report()`가 **라이브 파이프라인**에서
> 자동 생성한다. 모든 수치는 재현 가능하며, 시스템 변경 시 갱신된다.

---

## 0. 한눈에 (Executive Summary)

- **E2E 관통:** ✅ 6·30 1건이 Source→추출→Impact Matrix→Proposal→회귀→Assurance→Report까지 완결
- **룰엔진 정합성:** 층화 포트폴리오 3024/3024 = 100% (엔진 ⟷ 독립 명세 오라클)
- **Assurance(추출):** Citation Correctness 100%, Change Completeness 100%, Exception Recall 100%
- **골드 평가셋:** 115문항(DEV/LOCKED/CHALLENGE), 10 카테고리 전수 커버 — **전 항목 AI_DRAFT(사람확정 대기)**
- **하니스 판별력:** 오류 주입 시 지표가 실제 하락(§7) — 100%가 '검증 능력 없음'이 아님을 실증

> **가치 제안:** "규제가 바뀌었을 때 무엇을 고쳐야 하는지 AI가 제안하고, 그 제안이 틀리지 않았는지
> **검증 가능한 방식으로 증명**하는 시스템." 챗봇이 아니라 검증 가능한 의사결정 지원 시스템.

## 1. 범위와 방법

- **정책 버전:** `FSC_20260630` (6·30 규제지역 추가지정). 코퍼스: FSC·MOLIT 보도참고자료, 관계기관 FAQ.
- **코어 판정 범위:** 주택구입목적 주담대의 **적용 LTV**. 지역 × 주택수 × 예외 × 시점 × 경과규정.
- **Discovery(자동판정 밖):** 전세·신용·중도금·사업자대출, 정책대출(디딤돌·보금자리) — 표시만, 수동 검토.
- **값의 출처 분리:** 규칙 값·우선순위는 **사람이 확정한 명세**(`05_RULE_SPEC`, `regulatory_facts`)에서 온다.
  LLM은 규칙을 생성하지 않고, 그 출력은 **검증 대상**(Citation grounding)으로만 흐른다.

## 2. RegChange 추출 (E) + Citation Assurance (A)

공문 원문 3건에서 Before/After 변경을 구조화 추출하고, 각 인용을 원문과 대조한다.

- 추출 항목: **6건** / target_regions: GURI, YONGIN_GIHEUNG, HWASEONG_DONGTAN / effective_from: 2026-07-01
- **Citation Correctness:** 100% (원문 verbatim grounded, 환각 인용 0건)
- **Change Completeness:** 100% · **Exception Recall:** 100% · Effective-date ✅ · Regions ✅

> ⚠️ **한계(오염):** 현재 E2E 기본 추출은 원문 grounding된 **앵커**이고, 실측 run1은 세션 모델이
> gold를 이미 본 상태로 생성됐다 → **독립 성능 아님**. 독립치는 오염 없는 LLM 추출(run2)로 측정 예정.

## 3. Impact Matrix (고객 세그먼트별 영향)

시행 전(6.30)·후(7.2)를 **동일 룰엔진**으로 평가해 세그먼트별 delta를 산출한다. 총 18행(고영향 12 / escalation 6).

| 세그먼트 | 지역 | before | after | Δ |
|---|---|---:|---:|---:|
| 무주택 일반 | (규제 3지역 공통) | 70% | 40% | -30% |
| 생애최초 | (규제 3지역 공통) | 70% | 70% | +0% |
| 서민·실수요자 | (규제 3지역 공통) | 70% | 60% | -10% |
| 처분조건부 1주택 | (규제 3지역 공통) | 70% | 40% | -30% |
| 비처분 1주택 | (규제 3지역 공통) | NEEDS_HUMAN_REVIEW | 0% | - |
| 다주택 | (규제 3지역 공통) | NEEDS_HUMAN_REVIEW | 0% | - |

> 유주택/다주택의 시행 전(비규제) 값은 명세에 부재 → `NEEDS_HUMAN_REVIEW`(정직한 escalation, 값을 지어내지 않음).

## 4. Rule Change Proposal (구조화 변경 제안)

- 제안 ID: `PROP-6-30` · **상태: AI_DRAFT** (LOCKED §4: 사람 확정 전까지 초안)
- 서술 변경 6건(provenance=LLM 추출, citation 보존) · 세그먼트 영향 18건(provenance=룰엔진 deterministic)
- provenance 분리로 '무엇이 AI 판단이고 무엇이 결정적 규칙인지' 추적 가능.

## 5. 룰엔진 검증 — 독립 명세 오라클 차등 테스트 (Assurance ④)

엔진 출력을 스스로 채점하지 않는다. 명세(§H)에서 **독립 유도**한 오라클(엔진을 import 하지 않음)과
대조해 회귀가 tautology가 되지 않게 한다.

- **seed 케이스:** 30/30 = 100%
- **층화 합성 포트폴리오:** 3024/3024 = 100% (432 strata 중 432 커버)

| 카테고리 | 통과/전체 | 비율 |
|---|---|---:|
| SCOPE | 288/288 | 100% |
| BASELINE | 168/168 | 100% |
| EXCEPTION | 81/81 | 100% |
| BOUNDARY | 348/348 | 100% |
| GRANDFATHERING | 1227/1227 | 100% |
| CONFLICT | 912/912 | 100% |

> **이빨 증거(mutation test):** 엔진에 버그를 심으면 회귀가 실패로 잡는다(§7). 100%는 '드리프트 없음'이지
> '명세==현실'은 아니다 — 그 방어선은 사람의 명세·골드 확정이다.

## 6. 골드 평가셋 (DEV / LOCKED / CHALLENGE)

- 규모: **115문항** (DEV 40 / LOCKED 40 / CHALLENGE 35). 10 카테고리 전수 커버, CHALLENGE 가중 카테고리 66건.
- **결정적 채점(LOCKED §4 금지선: LLM이 LLM 채점 금지):** scenario 86/86 = 100% (룰엔진 대조), 근거 grounding 34/34 = 100% (원문 verbatim).
- **Escalation Recall/Precision:** 100% / 100% (tp=13 fp=0 fn=0).
- **상태:** 전 115문항 **AI_DRAFT** — regulatory_facts(검수대기) 파생. 사람 확정 후 freeze.

| 카테고리 | 문항수 |
|---|---:|
| GRANDFATHERING ★ | 20 |
| CONFLICT ★ | 18 |
| EXCEPTION ★ | 14 |
| EFFECTIVE_DATE ★ | 14 |
| BORROWER_TYPE | 11 |
| AMBIGUOUS | 9 |
| LOAN_PURPOSE | 8 |
| NORMAL | 7 |
| NO_CHANGE | 7 |
| REGION | 7 |

## 7. 판별력 (Negative Control) — "왜 계속 100%인가"

정상 데이터의 100%만으로는 하니스에 이빨이 있는지 알 수 없다. **의도적으로 오류를 주입**하고
각 지표가 100%에서 떨어지는지 실측한다. 정상=100%, 오류=<100%면 → 동적 범위가 있다는 증거다.

| 지표 | 정상 | 오류 주입 | 감지 |
|---|---:|---:|:---:|
| Citation Correctness | 100% | 50% | ✅ |
| Change Completeness | 100% | 50% | ✅ |
| Exception Recall | 100% | 0% | ✅ |
| Effective-date OK | 100% | 0% | ✅ |
| Regions OK | 100% | 0% | ✅ |
| E2E 종합(e2e_ok) | True | False | ✅ |
| 골드셋 scenario(엔진 변조) | 100% | 73% | ✅ |

> **결론:** 모든 지표가 오류에 반응한다. 100%는 '오류 없음'을 뜻하지 '검증 능력 없음'을 뜻하지 않는다.
> 각 100%의 강도·한계는 `docs/eval/VALIDATION_LIMITS.md` 참조.

## 8. 검증의 한계 (정직성 — 브리프 §12)

- **rule-regression 100%** = 엔진 ⟷ 독립 오라클 일치(mutation 실증). "엔진==명세"이지 "명세==현실" 아님.
- **골드셋 scenario 100%** = 작성자가 엔진 기준으로 기입 → 거의 순환(QA 게이트, 독립 성능 아님).
- **Extractor run1 100%** = 세션 모델·gold 사전열람으로 **오염** → 독립 벤치마크 아님.
- **독립 성능치는 아직 미측정.** 확보 경로: (1) 오염 없는 LLM 추출 run2(API 키), (2) 골드셋 human-confirm 후 LOCKED/CHALLENGE 1회 실행, (3) regulatory_facts claim 원문 서명.

> "The locked test set was frozen before system tuning, but was authored within the project and is
> not an independent third-party benchmark." — 한계를 숨기지 않는 것이 신뢰성을 높인다.

## 9. 사람 검토 · 감사 추적 (LOCKED §4)

- **운영 방식:** AI 초안 → **사람 확정**. 확정 전 초안은 authority 없음.
- **현재 확정 대기:** Rule Change Proposal(AI_DRAFT), 골드셋 115문항(AI_DRAFT), regulatory_facts claim(검수대기).
- **Escalation:** 명세가 값을 정의하지 않으면 지어내지 않고 `NEEDS_HUMAN_REVIEW`/`DISCOVERY`로 넘긴다
  (골드셋 escalation recall 100%).

## 10. 결론 및 남은 일

- ✅ **코어 E2E 관통 달성**(6·30 1건), 룰엔진 정합성 100%(~3024건), 골드셋 규모 목표 도달, 하니스 판별력 실증.
- ⏳ **남은 것(사람/독립성):** 골드셋·제안·규제사실 **사람 확정** → 독립 성능 측정(run2, LOCKED/CHALLENGE).
- 이 보고서는 라이브 생성물이다. `python examples/gen_validation_report.py`로 재생성한다.

---

### 부록 A — E2E 상세 리포트

```
========================================================================
RegImpact — E2E Validation Report : 6·30 규제지역 추가지정
========================================================================

[1] Source Snapshot   : FAQ_20260630, FSC_PRESS_20260630, MOLIT_PRESS_20260630

[2] RegChange 추출    : policy=FSC_20260630  effective=2026-07-01
    target_regions    : GURI, YONGIN_GIHEUNG, HWASEONG_DONGTAN
    변경 항목(6):
      • [LTV] 규제지역 내 주담대 LTV 강화 (비규제 70% → 규제 40%)  (비규제지역 70% → 규제지역 40%)
      • [EFFECTIVE_DATE] 강화된 대출규제 시행일 = 2026-07-01 (7.1일)  (- → 2026-07-01)
      • [REGION] 규제지역 추가 지정: 동탄구·기흥구·구리시 (투기과열지구·조정대상지역)  (비규제지역(수도권) → 규제지역(투기과열지구·조정대상지역))
      • [EXCEPTION] 생애최초·서민실수요·정책모기지는 완화 LTV(60~70%) 유지  (70% → 생애최초 70% / 서민·실수요 60% (완화 유지))
      • [EXCEPTION] 다주택자는 수도권 주택구입시 규제지역 여부 무관 LTV 0%  (- → LTV 0%)
      • [GRANDFATHERING] 경과규정: 전산접수 완료 또는 계약+계약금 증명시 종전규정 적용  (- → 종전규정 적용(경과규정))

[3] Impact Matrix     : 18행 (고영향 12 / escalation 6)
  세그먼트           지역                   before    after       Δ
  --------------------------------------------------------------
  무주택 일반         GURI                    70% →      40%    -30%  [고영향]
  생애최초           GURI                    70% →      70%     +0%
  서민·실수요자        GURI                    70% →      60%    -10%
  처분조건부 1주택      GURI                    70% →      40%    -30%  [고영향]
  비처분 1주택        GURI               NEEDS_HUMAN_REVIEW →       0%          [고영향/escalation]
  다주택            GURI               NEEDS_HUMAN_REVIEW →       0%          [고영향/escalation]
  무주택 일반         YONGIN_GIHEUNG          70% →      40%    -30%  [고영향]
  생애최초           YONGIN_GIHEUNG          70% →      70%     +0%
  서민·실수요자        YONGIN_GIHEUNG          70% →      60%    -10%
  처분조건부 1주택      YONGIN_GIHEUNG          70% →      40%    -30%  [고영향]
  비처분 1주택        YONGIN_GIHEUNG     NEEDS_HUMAN_REVIEW →       0%          [고영향/escalation]
  다주택            YONGIN_GIHEUNG     NEEDS_HUMAN_REVIEW →       0%          [고영향/escalation]
  무주택 일반         HWASEONG_DONGTAN        70% →      40%    -30%  [고영향]
  생애최초           HWASEONG_DONGTAN        70% →      70%     +0%
  서민·실수요자        HWASEONG_DONGTAN        70% →      60%    -10%
  처분조건부 1주택      HWASEONG_DONGTAN        70% →      40%    -30%  [고영향]
  비처분 1주택        HWASEONG_DONGTAN   NEEDS_HUMAN_REVIEW →       0%          [고영향/escalation]
  다주택            HWASEONG_DONGTAN   NEEDS_HUMAN_REVIEW →       0%          [고영향/escalation]

[4] Rule Change Proposal : PROP-6-30  상태=🟡 AI초안(사람확정 대기)
    서술 변경 6 · 세그먼트 영향 18

[5] Rule Regression   : Pass Rate 30/30 = 100% (engine ⟷ 독립 명세 오라클)
      SCOPE            3/3  100%
      BASELINE         3/3  100%
      EXCEPTION        5/5  100%
      BOUNDARY         8/8  100%
      GRANDFATHERING   6/6  100%
      CONFLICT         5/5  100%

[6] Assurance (검증)
    ① Citation Correctness : 100% (grounded 6/6, unsupported 0)
    ② Change Completeness  : 100%
    ③ Exception Recall     : 100%
    ③ Effective-date/Region: date=✓ region=✓

[7] 종합 판정         : ✅ E2E 관통 성공
    (회귀 100% + 인용 환각 0 + 추출·매트릭스 산출 = 배관 관통 확인)
========================================================================
```
