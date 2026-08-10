# 05 — RULE ENGINE 규칙 명세 (주택구입목적 주담대 LTV)

> ⚠️ **LOCKED §4:** 규칙 로직은 LLM이 생성하지 않는다. **✍️ 표시 칸은 사용자(도메인 전문가)가 작성/확정**한다.
> Claude는 🔧 표시(스키마·표 구조·라벨 체계·테스트 하네스)만 스캐폴드한다.
> 이 명세가 확정되면 deterministic 코드로 구현되고, LLM 출력 검증의 기준점이 된다.
>
> - 상태: 🟡 스캐폴드 완료, ✍️ 도메인 값 입력 대기
> - 범위: Core Executable Scope (브리프 §5.1) — 주택구입목적 주담대만. 전세/신용/중도금/사업자는 Discovery(자동판정 제외).
> - 기준 시나리오: 6·30 (FSC_20260630), 기준선 = 6·30 이전 상태.

---

## A. 입력 스키마 🔧 (타입·enum은 스캐폴드, 값 의미는 ✍️ 확인)

| 필드 | 타입 | 값/enum(제안) | 비고 |
|---|---|---|---|
| `region_code` | enum | GURI, YONGIN_GIHEUNG, HWASEONG_DONGTAN, OTHER | 지역 코드 |
| `evaluation_date` | date | | 판정 기준일 (이 시점의 지역상태·정책버전 결정) |
| `region_status_as_of` | enum(derived) | REGULATED, NON_REGULATED | LTV 판정용 2값. (2026-08-10) |
| `regulated_type` | enum(derived) | SPECULATIVE_OVERHEATED(투기과열), ADJUSTMENT(조정), NONE | 🔺2026-08-10 추가: **DTI가 유형별로 다름**(투기과열40%/조정50%). 6·30 3개 지역 = 투기과열지구(+조정) → DTI 40%. LTV는 REGULATED면 동일. |
| `house_count` | int | 0, 1, 2+ | ✍️Q: 경계 정의 (0=무주택, 2+=다주택?) |
| `disposal_condition_flag` | bool | | ✅확정(2026-08-10): 별도 boolean 채택. house_count=1 + flag=true → 처분조건부 1주택. |
| `first_home_buyer` | bool | | 생애최초 여부 |
| `policy_mortgage_flag` | bool | | 정책대출 여부 |
| `loan_purpose` | enum | HOME_PURCHASE, OTHER | Core는 HOME_PURCHASE만 |
| `application_submitted_at` | datetime? | | 신청 제출 |
| `application_accepted_at` | datetime? | | 금융회사 전산 접수 완료 |
| `contract_signed_at` | datetime? | | 매매계약 체결 |
| `downpayment_paid_at` | datetime? | | 계약금 납부 |

> ✅ **Q-스키마(처분조건부/지역상태) 확정 2026-08-10.** 남은 확인: 위 필드로 충분한지, 빠진 입력(처분기한, 담보물건 종류, 소득요건 등)이 규칙에 필요한지.

## B. 출력 스키마 🔧

| 필드 | 타입 | 비고 |
|---|---|---|
| `applicable_rule_id` | string | 적용된 규칙 ID (아래 C 표의 rule_id) |
| `max_ltv` | float | 적용 최대 LTV (0.0~1.0) — **코어 판정 출력** |
| `ref_dti` | float? | DTI 참고값(코어 판정 아님). regulated_type별(투기과열0.40/조정0.50). ✅2026-08-10 코어 제외. |
| `ref_max_loan_amount` | int? | 한도 참고값(코어 판정 아님). 가격구간별 6/4/2억. ✅2026-08-10 코어 제외. |
| `grandfathering_applied` | bool | 경과규정으로 종전규정 적용 여부 |
| `reason_codes` | string[] | 판정 근거 라벨 (아래 D) |
| `source_policy_ids` | string[] | 근거 정책 (예: FSC_20260630) |
| `evaluation_status` | enum | IN_SCOPE / OUT_OF_SCOPE / NEEDS_HUMAN_REVIEW 🔧제안 |

---

## C. 의사결정표 ✍️ (핵심 — 값과 우선순위는 사용자 작성)

> 아래 행 조합은 🔧스캐폴드(scope 차원의 조합). **max_ltv / rule_id / grandfathering 상호작용은 ✍️ 본인이 채워주세요.**
> 값 참고용으로 regulatory_facts의 claim을 괄호에 표기했으나, **확정은 본인 검수**입니다.

> 🤖 **아래는 FAQ Q2 표(사용자 제공 이미지) 원문을 그대로 옮긴 초안 — ✍️ 사용자 최종 확정 필요.**
> 확정하면 authority가 됩니다. (workflow: `02_DECISION_LOG.md` 2026-08-10 §4 운영결정)

### C-1. 규제지역 주택구입목적 주담대 — FAQ Q2 표 원문 기준 (7.1 이후)
주1) 무주택자(처분조건부 1주택자 포함) 기준. DTI는 아파트 限. 최대한도 = 주택가격 구간별(15억↓6억/15~25억4억/25억↑2억).

| # | 차주(무주택 기준) | LTV 🤖 | DTI 🤖 | 최대한도 🤖 | rule_id |
|---|---|---|---|---|---|
| R1 | 일반 | **0.40** | 투기과열 0.40 / 조정 0.50 | 가격구간별 | `REG_STD` |
| R2 | 생애최초 | **0.70** (좌동) | 0.60 (좌동) | 가격구간별 | `REG_FIRSTHOME` |
| R3 | 서민·실수요자 | **0.60** | 0.60 (좌동) | 가격구간별 | `REG_REALDEMAND` |
| R4 | 처분조건부 1주택 | **0.40** | (R1 동일) | 가격구간별 | `REG_STD` |
| R7 | 정책대출·디딤돌 | **0.70** (좌동) | 0.60 (좌동) | 일반2.0/생초2.4/신혼3.2/신생아4.0억 | `REG_POLICY_DIDIM` |
| R8 | 정책대출·보금자리론 | 아파트 **0.60** / 비아파트 **0.55** (생초·실수요 좌동 0.70/0.65) | **0.50** (생초·실수요 좌동 0.60) | 일반3.6/생초4.2억 | `REG_POLICY_BOGEUM` |

### C-1b. 유주택·다주택 (FAQ Q2 표에는 없음 — 국토부 MOLIT 참고1 표 기준) 🔺
| # | 차주 | LTV 🤖 | rule_id | 근거 |
|---|---|---|---|---|
| R5 | 유주택(비처분 1주택 이상) · 규제지역 | **0.00** | `REG_OWNER_0` | MOLIT p3 "유주택 0%" |
| R6 | 다주택 · 수도권(규제 무관) | **0.00** | `MULTI_0` | FSC p2, C06 |

### C-2. 기준선 = 6.30 이전, 이 지역은 **非규제 수도권** (evaluation_date < 2026-07-01)
FAQ Q2 왼쪽 열. 이 3개 지역(동탄·기흥·구리)은 지정 전 수도권 非규제였음.
| # | 차주 | LTV 🤖 | DTI 🤖 | rule_id |
|---|---|---|---|---|
| B1 | 무주택 일반/생애최초/서민실수요 | **0.70** | 0.60 (아파트) | `NONREG_STD_70` |
| B2 | 정책·보금자리(아파트) | 0.70 | 0.60 | `NONREG_BOGEUM_70` |
> 주의: MOLIT 참고1의 "非규제(수도권 外) 유주택 60%"는 **수도권 외** 맥락 → 6·30 시나리오(수도권)에는 직접 해당 안 됨. 혼동 주의.

> ✅ **Q-값1/값2 해소(이미지 기준):** 생애최초 70%(좌동), 서민·실수요 60%, 유주택/다주택 0%, 정책대출 상품별.
> 🔺 **재설정 포인트(이전 초안 교정):** ①DTI 추가(투기과열40/조정50) → `regulated_type` 필드 필요, ②최대한도 추가(가격구간별), ③기준선을 "수도권 외"→"非규제 수도권"으로 정정, ④보금자리론 비아파트 55%·DTI 50% 반영.
> ✅ **Q-스코프 확정(2026-08-10): LTV만 코어 판정.** DTI·최대한도는 참고값(`ref_*`)으로 기록만. regulated_type은 DTI 참고 표시용으로 보관(LTV 판정엔 REGULATED 2값이면 충분).

---

## D. reason_codes 라벨 체계 🔧 (라벨은 스캐폴드, 어떤 코드가 실제 존재하는지는 ✍️ 확정)

제안 라벨(예시): `LTV_REGULATED_40`, `LTV_BASELINE_70`, `LTV_MULTI_HOME_0`, `EXCEPTION_FIRST_HOME`, `EXCEPTION_POLICY_LOAN`, `GRANDFATHERED_ACCEPTED`, `GRANDFATHERED_CONTRACT_PAID`, `OUT_OF_SCOPE_PRODUCT`, `NEEDS_REVIEW_AMBIGUOUS`.
> ✍️ 실제 사용할 코드 목록은 C·E·F 확정 후 정리.

---

## E. 예외 우선순위 (precedence) ✍️

규제지역에서 한 차주가 여러 조건을 동시에 만족할 때 어떤 규칙이 이기는지 **순서**를 정의.

예시 뼈대(값 ✍️):
```
1. ⬜ (예: 경과규정 해당 → 종전규정 우선?)
2. ⬜ (예: 생애최초 예외 > 일반 규제?)
3. ⬜ (예: 정책대출 예외 위치?)
4. ⬜ (다주택 0% 위치?)
```
> ✍️ **Q-우선순위:** 예) 생애최초 AND 정책대출 동시 충족 시? 경과규정 AND 생애최초 동시 시? 처분조건부 1주택 + 생애최초?

---

## F. 경과규정(grandfathering) 판정 ✍️ (C11)

종전규정(6·30 이전 LTV) 적용 조건 — **날짜 경계 의미를 정확히** 정의해야 함.

🤖 **FAQ 참고표 원문 기준 초안 (일반 주담대):**
```
조건 G1 (전산 접수 완료):
  application_accepted_at <= 2026-06-30   → 종전규정
조건 G2 (계약 + 계약금):
  contract_signed_at <= 2026-06-30  AND  downpayment_paid_at 증빙  → 종전규정
조건 G3 (토허제 주택):
  토지거래허가 신청 접수 <= 2026-06-30  → 이후 계약 체결해도 종전규정
G1|G2|G3 중 하나라도 만족 → grandfathering_applied=true. 아니면 신규규정.
(집단대출 G4: 입주자모집공고/착공/관리처분인가 <= 6.30 → 별도 분기, 코어 밖 검토)
```
> ✍️ **Q-경과1:** "6.30까지"의 정확한 경계 = `<= 2026-06-30`(날짜, 자정 포함)로 볼지, 시각까지 볼지. (원문은 "전일(6.30일)까지"라 날짜 경계로 해석 — 확정 필요)
> ✍️ **Q-경과2:** 계약금 "일부 납부"도 증명으로 인정? `downpayment_paid_at`만으로 충분한지, 별도 증빙 플래그가 필요한지.
> ✍️ **Q-경과3:** G3 토허제(신청접수일 기준)를 룰엔진에 포함할지. 토허제 효력일이 7.5라 지역상태 판정과 상호작용 주의.
> 🤖 근거: `sources/raw/faq_20260630.txt` "참고: 규제지역 지정에 따라 강화되는 대출규제 적용 예외사유" 표.

---

## G. 미결 질문 요약 (✍️ 사용자 입력 대기)

- ~~Q-스키마: 처분조건부 표현~~ ✅ 별도 boolean flag (2026-08-10) / 남은: 추가 필드 필요성
- ~~Q-지역: region_status 세분화~~ ✅ REGULATED/NON_REGULATED 2값 (2026-08-10)
- Q-값1: 생애최초·정책대출 정확 LTV
- Q-값2: 비처분 1주택 처리
- Q-우선순위: 복합 조건 precedence
- Q-경과1~3: 날짜 경계·증빙·토허제

> 답이 채워지면 이 문서를 확정하고, Claude가 deterministic 코드 + 테스트 하네스(🔧)로 구현한다.
