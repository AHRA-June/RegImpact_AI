# 검증보고서 (Validation Report) — 2026-06-30 규제지역 추가 지정

- 정책: `FSC_20260630`
- 시행일: `2026-07-01`
- 대상지역: `GURI`, `YONGIN_GIHEUNG`, `HWASEONG_DONGTAN`

## 1. 파이프라인 관통 현황
- ✅ [2] RegChange Extractor
- ✅ [3] Impact Matrix
- ✅ [4] Rule Change Proposal
- ✅ [5] TC / Rule-Regression
- ✅ [6] Assurance

**판정: 관통(핵심 노드 완결).**

## 2. 규제 변경 요약 (원문 추출)
- 추출 변경 항목: 9건
  - `LTV` 규제지역 내 주담대 LTV 70%→40% 강화
  - `LTV` 유주택자 규제지역 LTV 0%, 무주택(처분조건부 1주택 포함) 40%
  - `EXCEPTION` 생애최초·정책모기지 등은 완화된 LTV(60~70%) 적용
  - `EXCEPTION` 다주택자는 수도권 내 주택구입시 규제지역 여부 무관 LTV 0%
  - `GRANDFATHERING` 6.30까지 접수완료 또는 계약체결+계약금 증명시 종전규정 적용
  - `GRANDFATHERING` 토지거래허가 대상 주택은 6.30까지 허가 신청 접수시 이후 계약해도 종전규정
  - `EFFECTIVE_DATE` 규제지역 지정효력 2026-07-01 발생
  - `REGION` 화성 동탄·용인 기흥·구리 3곳 투기과열지구·조정대상지역 신규 지정
  - `SCOPE_LIMIT` 1억원 초과 신용대출 보유 차주 1년간 규제지역 주택구입 제한

## 3. 시행 전/후 영향 매트릭스
- 지역 `GURI` · 전 `2026-06-30` → 후 `2026-07-03`

| 세그먼트 | 시행 전 | 시행 후 | Δ | 방향 |
|---|---|---|---|---|
| 무주택 일반 | 70% | 40% | -30pp | TIGHTENED |
| 생애최초 | 70% | 70% | 0pp | UNCHANGED |
| 서민·실수요 | 70% | 60% | -10pp | TIGHTENED |
| 비처분 1주택 | — | 0% | — | REVIEW |
| 처분조건부 1주택 | 70% | 40% | -30pp | TIGHTENED |
| 다주택 | — | 0% | — | REVIEW |

요약: 강화 3 · 완화 0 · 동일 1 · 검토 2

## 4. 룰 변경 제안 (AI초안 → 사람확정)
- 제안 ID: `FSC_20260630::GURI`
- 승인 상태: **APPROVED** (검토자 심사역)
  - 검토 노트: 6·30 표준 변경 확인
- 제안 행: 6건 (사람 검토 필요 2건)

| 세그먼트 | rule_id | 전→후 | reason_code | 검토 |
|---|---|---|---|---|
| 무주택 일반 | `REG_STD` | 70%→40% | `LTV_REGULATED_40` |  |
| 생애최초 | `REG_FIRSTHOME` | 70%→70% | `EXCEPTION_FIRST_HOME` |  |
| 서민·실수요 | `REG_REALDEMAND` | 70%→60% | `EXCEPTION_REAL_DEMAND` |  |
| 비처분 1주택 | `REG_OWNER_0` | —→0% | `LTV_OWNER_0` | ⚠ |
| 처분조건부 1주택 | `REG_STD` | 70%→40% | `LTV_REGULATED_40` |  |
| 다주택 | `MULTI_0` | —→0% | `LTV_MULTI_HOME_0` | ⚠ |

## 5. 룰 회귀 검증 (엔진 ⟷ 독립 오라클)
- Rule-regression Pass Rate: 30/30 = 100.0%
  - SCOPE: 3/3 (100%)
  - BASELINE: 3/3 (100%)
  - EXCEPTION: 5/5 (100%)
  - BOUNDARY: 8/8 (100%)
  - GRANDFATHERING: 6/6 (100%)
  - CONFLICT: 5/5 (100%)

## 6. Assurance (부분 측정)
- Citation Correctness: 100%
- Unsupported Claim Rate: 0%
- Change Completeness: 100%
- Exception Recall: 50% (놓침 ['real_demand'])
- Effective-date: OK
- Region: OK

## 7. 한계 (정직성)
- 이 보고서는 6·30 단일 앵커 기준 stub 이다(정식 15~20쪽 아님).
- 사람 검토 필요 세그먼트 2건 — 자동 확정 보류(escalation).
