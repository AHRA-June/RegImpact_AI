# RegImpact — Validation Report (Walking Skeleton)

- **시나리오:** 6·30 규제지역 추가지정 (LTV 70%→40%)
- **정책 시점:** before `2026-06-15` → after `2026-07-02`
- **추출 경로:** 오프라인 stub(API 키 없이 관통)
- **E2E 상태:** ✅ 관통 성공

> 브리프 §18 코어라인: Source → Policy Version → Before/After → Impact Matrix → Rule Proposal → Test Cases → Rule Regression → Assurance → Human Review → Report. 각 노드가 실제 산출물을 냈는지 한 문서로 관통 확인.

## 1. Source Snapshot (원문 무결성)

| doc_id | chars | raw_sha256 (앞 16) |
|---|---:|---|
| FAQ_20260630 | 4307 | `625bf53e9084ff9e…` |
| FSC_PRESS_20260630 | 2943 | `2063e336c60b9f1c…` |
| MOLIT_PRESS_20260630 | 4249 | `67a40543914f1957…` |

> raw_sha256 = extractor가 실제 소비한 추출 텍스트의 지문. 원본(PDF/HWP) 해시는 `docs/sources/SOURCES.md`.

## 2. Policy Version Resolution (지역 규제상태 전환)

| region | before | after | 신규규제 |
|---|---|---|:---:|
| GURI | NON_REGULATED | REGULATED | 🔺 |
| YONGIN_GIHEUNG | NON_REGULATED | REGULATED | 🔺 |
| HWASEONG_DONGTAN | NON_REGULATED | REGULATED | 🔺 |

## 3. Before/After — RegChange 추출

- policy_id: `FSC_20260630`  ·  effective_from: `2026-07-01`  ·  target_regions: GURI, YONGIN_GIHEUNG, HWASEONG_DONGTAN

| category | 변경 | before | after |
|---|---|---|---|
| LTV | 규제지역 주담대 LTV 70% → 40% | 70% | 40% |
| EFFECTIVE_DATE | 시행일 2026-07-01 | — | 2026-07-01 |
| REGION | 구리·용인기흥·화성동탄 규제지역 지정 | — | REGULATED |
| GRANDFATHERING | 6.30까지 접수/계약+계약금은 종전규정(경과규정) | — | 종전규정 |
| EXCEPTION | 생애최초·서민실수요는 완화 LTV | — | 생애최초 70% / 서민실수요 60% |

## 4. Impact Matrix (Before/After · 룰엔진 실측)

포트폴리오 n=10 · 변경영향 6(60%) · 강화 6 · 경과규정보호 1 · **고임팩트 5**

| 세그먼트 | n | 변화 | before | after | Δ | 고위험 |
|---|---:|---:|---:|---:|---:|---:|
| NEWLY_REGULATED · NO_HOME · GENERAL | 4 | 2 | 70% | 50% | -20% | 2 |
| NEWLY_REGULATED · OWNER_1HOME · GENERAL | 1 | 1 | — | 0% | — | 1 |
| NEWLY_REGULATED · MULTI_HOME · GENERAL | 1 | 1 | — | 0% | — | 1 |
| NEWLY_REGULATED · DISPOSAL_1HOME · GENERAL | 1 | 1 | 70% | 40% | -30% | 1 |
| NEWLY_REGULATED · NO_HOME · REAL_DEMAND | 1 | 1 | 70% | 60% | -10% | 0 |
| NEWLY_REGULATED · NO_HOME · FIRST_HOME | 1 | 0 | 70% | 70% | 0% | 0 |
| NON_REGULATED · NO_HOME · GENERAL | 1 | 0 | 70% | 70% | 0% | 0 |

## 5. Structured Rule Change Proposal (승인 대기)

- 상태: **PENDING_HUMAN_APPROVAL** (§4 AI초안→사람확정)
- 경과규정: 6.30까지 접수/계약+계약금은 종전규정(경과규정)

| 차주 유형 | before LTV | after LTV | rule_id | 비고 |
|---|---:|---:|---|---|
| 무주택 일반 / 처분조건부 1주택 | 70% | 40% | `REG_STD` |  |
| 생애최초 | 70% | 70% | `REG_FIRSTHOME` | 예외 — 변동 없음(좌동) |
| 서민·실수요자 | 70% | 60% | `REG_REALDEMAND` |  |
| 유주택(비처분 1주택 이상) | 70% | 0% | `REG_OWNER_0` | 사실상 대출 거절 |
| 다주택 | 70% | 0% | `MULTI_0` | 사실상 대출 거절 |

## 6. Deterministic Rule Regression (엔진 ⟷ 명세 오라클)

- Rule-regression Pass Rate: **30/30 = 100%**

| 카테고리 | 통과/전체 |
|---|---:|
| SCOPE | 3/3 |
| BASELINE | 3/3 |
| EXCEPTION | 5/5 |
| BOUNDARY | 8/8 |
| GRANDFATHERING | 6/6 |
| CONFLICT | 5/5 |

## 7. Assurance (Citation Grounding + Gold)

- Citation Correctness: **100%** (5/5)  ·  Unsupported Claim Rate: 0%
- Change Completeness: **100%**  ·  Exception Recall: **100%**  ·  Effective-date: ✅  ·  Regions: ✅

## 8. Human Review 게이트

자동판정으로 종결하지 않고 **사람 검토로 넘기는 6건**:

| 출처 | 대상 | 사유 |
|---|---|---|
| IMPACT | C01 | 고임팩트(TIGHTENED) — 검토 권장 |
| IMPACT | C02 | 고임팩트(TIGHTENED) — 검토 권장 |
| IMPACT | C05 | 고임팩트(TIGHTENED) — 검토 권장 |
| IMPACT | C06 | 고임팩트(TIGHTENED) — 검토 권장 |
| IMPACT | C07 | 고임팩트(TIGHTENED) — 검토 권장 |
| IMPACT | C10 | 엔진 자동판정 불가 → DISCOVERY |

## 9. 한계 (정직한 명시)

- **Walking Skeleton stub.** 각 노드는 관통 확인용 최소 구현. 포트폴리오는 소규모 대표 표본.
- 추출은 오프라인 stub(환각 없음). 실제 LLM 추출 시 Assurance 수치가 첫 실측 지표가 됨.
- 룰엔진 LTV 값은 확정 명세(FAQ Q2)에서만 옴(LOCKED §4). 이 보고서는 값을 만들지 않음.
- 규칙 변경안은 **승인 대기** 상태 — 사람 확정 전에는 운영 반영 금지(§4).

---

_E2E 상태: ✅ 관통 성공 · 생성: RegImpact report node (stub)_