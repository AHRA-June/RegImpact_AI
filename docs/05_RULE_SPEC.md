# 05 — RULE ENGINE 규칙 명세 (주택구입목적 주담대 LTV)

> ⚠️ **LOCKED §4:** 규칙 로직은 LLM이 생성하지 않는다. **✍️ 표시 칸은 사용자(도메인 전문가)가 작성/확정**한다.
> Claude는 🔧 표시(스키마·표 구조·라벨 체계·테스트 하네스)만 스캐폴드한다.
> 이 명세가 확정되면 deterministic 코드로 구현되고, LLM 출력 검증의 기준점이 된다.
>
> - 상태: ✅ **v1 확정 (2026-08-10)** — 코어 LTV 판정 로직 확정. 엔진 코드화 준비 완료.
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
| `first_home_buyer` | bool | | 생애최초(세대원 전원 무주택 이력, 주4) |
| `real_demand_flag` | bool | | 🔺2026-08-10 추가: 서민·실수요자(주5: 연소득 9천↓·주택가격 8억↓·무주택세대주). 포트폴리오에서 파생 가능. |
| `policy_mortgage_flag` | bool | | 정책대출 여부. ✅true → **Discovery**(코어 자동판정 제외, 2026-08-10). |
| `loan_purpose` | enum | HOME_PURCHASE, OTHER | Core는 HOME_PURCHASE만 |
| `land_permit_target` | bool | | 🔺추가: 물건이 토지거래허가 대상인지 |
| `land_permit_applied_at` | datetime? | | 🔺추가: 토지거래허가 신청 접수일(G3용) |
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

> ✅ **정책대출(디딤돌·보금자리)은 Discovery로 분리(2026-08-10 확정)** — 코어 자동판정 대상 아님. `policy_mortgage_flag=true` → Discovery(수동 검토). 참고값(디딤돌70/보금자리 아파트60·비55)은 `regulatory_facts.md`에만 기록.

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
| B3 | **다주택(house_count≥2) · 수도권** | **0.00** | — | `MULTI_0` |
> 주의: MOLIT 참고1의 "非규제(수도권 外) 유주택 60%"는 **수도권 외** 맥락 → 6·30 시나리오(수도권)에는 직접 해당 안 됨. 혼동 주의.

#### C-2 보강 (2026-08-18) — 유주택 구간 정리 🤖 ✍️확정 대기

FAQ Q2 표 **주1)** 이 "무주택자(처분조건부 1주택자 포함) 기준"이라고 명시하므로, C-2의 非규제(수도권)
열에는 **유주택 값이 애초에 없다.** 그 빈칸을 다음과 같이 정리한다.

| 차주 | 非규제(수도권) LTV | 근거 | 상태 |
|---|---|---|---|
| 무주택 / 처분조건부 1주택 | **0.70** | FAQ Q2 표 非규제(수도권) 열 | ✅ 확정 |
| **다주택 (수도권)** | **0.00** | FSC p2 · FAQ Q1 ※ (아래 원문) | 🤖 초안 — ✍️ 확정 대기 |
| **비처분 1주택 (수도권)** | **없음 → escalation** | 원문 어디에도 없음 | ⛔ **미결(Q10)** |
| 다주택 (수도권 外) | 없음 → escalation | 수도권 규칙 적용 밖 | ⛔ 미결 |
| 유주택 (수도권 外) | 0.60 (참고) | MOLIT 참고1 — 6·30 시나리오 밖 | 참고값 |

**다주택 0%의 근거 (원문 verbatim):**
> "다주택자는 수도권 內 주택구입시 **규제지역 여부와 무관하게** LTV 0% 적용"
> — FSC 보도참고자료 p2, 동일 문장 FAQ Q1 ※

**시점 무관인 근거 (원문 verbatim):**
> "금번 조치로 규제지역으로 지정된 지역에 대해서는 **旣 마련된 규정**에 따라 강화된 대출규제가
> 7.1일부터 즉시 적용된다." — FSC 보도참고자료 p2

즉 6·30 지정은 **새 규칙을 만든 것이 아니라 기존 규칙을 그 지역에 발동시킨 것**이다. 수도권 다주택
0%는 지정과 무관한 상시 규칙이므로 **6.30 이전에도 동일하게 0%**이고, 경과규정으로 되돌릴 종전값도 0%다.

> ⚠️ **비처분 1주택은 여전히 미결(Q10)이다.** MOLIT의 유주택 60%는 수도권 外 값이므로 전용 금지.
> 값을 추정하면 LOCKED §4 위반 → 엔진은 `OWNER_BASELINE_UNKNOWN`으로 escalate 한다.

> ✅ **Q-값1/값2 해소(이미지 기준):** 생애최초 70%(좌동), 서민·실수요 60%, 유주택/다주택 0%, 정책대출 상품별.
> 🔺 **재설정 포인트(이전 초안 교정):** ①DTI 추가(투기과열40/조정50) → `regulated_type` 필드 필요, ②최대한도 추가(가격구간별), ③기준선을 "수도권 외"→"非규제 수도권"으로 정정, ④보금자리론 비아파트 55%·DTI 50% 반영.
> ✅ **Q-스코프 확정(2026-08-10): LTV만 코어 판정.** DTI·최대한도는 참고값(`ref_*`)으로 기록만. regulated_type은 DTI 참고 표시용으로 보관(LTV 판정엔 REGULATED 2값이면 충분).

---

## D. reason_codes 라벨 체계 🔧 (라벨은 스캐폴드, 어떤 코드가 실제 존재하는지는 ✍️ 확정)

✅ **알고리즘(H)에서 실제 방출되는 코드 (확정):**
`LTV_REGULATED_40`, `EXCEPTION_FIRST_HOME`, `EXCEPTION_REAL_DEMAND`, `LTV_OWNER_0`, `LTV_MULTI_HOME_0`,
`GRANDFATHERED_ACCEPTED_OR_CONTRACT`, `GRANDFATHERED_LAND_PERMIT`, `OWNER_BASELINE_UNKNOWN`,
`MULTI_HOME_BASELINE_UNKNOWN`(🤖 2026-08-18 신설 — 비수도권 다주택 기준값 부재),
`OUT_OF_SCOPE_PRODUCT`, `DISCOVERY_POLICY_LOAN`, `NEEDS_HUMAN_REVIEW`.
> 각 판정은 최소 1개 reason_code + source_policy_id 방출.

---

## E. 예외 우선순위 (precedence) — ✅ 확정 (2026-08-10)

한 차주가 여러 조건을 동시에 만족할 때 **위에서부터 먼저 매칭되는 규칙이 이김**(short-circuit).

```
P0.  loan_purpose != HOME_PURCHASE          → OUT_OF_SCOPE
P0b. policy_mortgage_flag == true           → DISCOVERY (정책대출: 수동 검토, 코어 자동판정 제외)
P0c. house_count>=2 AND 수도권               → 0% (MULTI_0), STOP   ★2026-08-18 추가
     ("규제지역 여부와 무관" — 지역상태·시점·경과규정 모두 무관)
P1.  경과규정 해당(F의 G1|G2|G3)             → 종전규정(非규제 수도권 LTV) 적용, STOP
P2.  region_status == NON_REGULATED         → 기준선 표(C-2) 적용, STOP
     (이하 REGULATED 확정)
P3.  다주택(house_count>=2)                  → 0% (R6), STOP
P4.  유주택(house_count>=1 AND NOT 처분조건부) → 0% (R5), STOP
     (처분조건부 1주택 = house_count==1 & disposal_flag=true → 무주택 기준으로 통과)
P5.  first_home_buyer == true               → 70% (R2), STOP
P6.  real_demand_flag == true               → 60% (R3), STOP
P7.  else (무주택 일반 / 처분조건부 1주택)    → 40% (R1/R4), STOP
```

**복합 조건 처리(확정 근거):**
- **경과규정 AND 생애최초:** 경과규정(P1) 최우선 → 종전규정 70%. (생애최초도 종전 70%라 수렴)
- **처분조건부 1주택 AND 생애최초:** P4 통과(처분조건부=무주택 기준) → P5에서 생애최초 70%.
- **유주택 AND 생애최초:** 논리상 불가(생애최초=세대원 전원 무주택 이력). 데이터 충돌 시 → `NEEDS_HUMAN_REVIEW`.
- **정책대출:** P0b에서 Discovery로 조기 분리 → 코어 LTV 자동판정 안 함.
- **수도권 다주택 AND 경과규정:** P0c가 P1보다 **앞**이므로 0%. 이 순서는 필수다 — P1의 경과규정
  분기는 유주택 전체를 '종전 기준값 부재'로 escalate 하므로, P0c를 뒤로 옮기면 경과규정에 해당하는
  수도권 다주택이 0%를 받지 못하고 사람 검토로 샌다(변이 테스트로 확인, 회귀 `GF-MULTI-01`이 고정).
- **비수도권 다주택:** P0c 미적용. 규제지역이면 P3에서 0%, 非규제면 기준값 부재 → escalation.

---

## F. 경과규정(grandfathering) 판정 — ✅ 확정 (2026-08-10) (C11)

종전규정(6·30 이전 LTV) 적용 조건. **확정된 경계 의미:**
- 날짜 경계 = **`<= 2026-06-30`** (그 날 자정까지 포함, 날짜 단위 비교).
- 계약금: **납부 사실이 증명되면 일부 납부도 인정** (`downpayment_paid_at` 존재 = 증빙으로 간주).
- **토허제 G3 포함** (코어). 토허제 효력일 7.5와 지역상태 판정 상호작용은 아래 주의.

**FAQ 참고표 원문 기준 (일반 주담대):**
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
🤖 **종전규정 = 무엇?** 이 3개 지역은 6.30 이전 **非규제 수도권**이므로, grandfathered 시 **기준선 표 C-2**(무주택 70% 등)를 적용.
> ⚠️ 엣지: 非규제 수도권 **유주택** LTV는 원문에 명시 없음 → grandfathered 유주택은 `NEEDS_HUMAN_REVIEW`로 escalate (초안).
> ✅ **Q-경과1 확정:** 경계 = `<= 2026-06-30` (날짜 단위, 그 날 자정까지 포함).
> ✅ **Q-경과2 확정:** 계약금 일부 납부도 인정 (`downpayment_paid_at` 존재 = 증빙).
> ✅ **Q-경과3 확정:** G3 토허제 코어 포함. (효력 7.5 vs 7.1 상호작용은 지역상태 해석에서 처리)
> 근거: `sources/raw/faq_20260630.txt` "참고: 규제지역 지정에 따라 강화되는 대출규제 적용 예외사유" 표.

---

## H. 통합 판정 알고리즘 — ✅ 확정 (2026-08-10) · 엔진 구현의 기준

```python
def evaluate_mortgage_ltv(inp) -> Result:
    # P0. 스코프
    if inp.loan_purpose != "HOME_PURCHASE":
        return Result(status="OUT_OF_SCOPE", reasons=["OUT_OF_SCOPE_PRODUCT"])
    # P0b. 정책대출 → Discovery (코어 자동판정 제외)
    if inp.policy_mortgage_flag:
        return Result(status="DISCOVERY", reasons=["DISCOVERY_POLICY_LOAN"])

    # P0c. 수도권 다주택 → 0% (규제 여부·시점·경과규정 무관) — C-2 B3, ★2026-08-18 추가
    #      P1보다 앞이어야 한다(아래 P1이 유주택 전체를 escalate 하므로).
    if inp.house_count >= 2 and is_capital_area(inp.region_code):
        return Result(max_ltv=0.00, rule_id="MULTI_0", reasons=["LTV_MULTI_HOME_0"])

    # P1. 경과규정 — F 참조. 경계 <= 2026-06-30
    if is_grandfathered(inp):          # G1 | G2 | G3
        if is_owner(inp):              # 유주택 & 非규제수도권 baseline 부재
            return Result(status="NEEDS_HUMAN_REVIEW",
                          reasons=["GRANDFATHERED", baseline_gap_reason(inp)])
        return Result(max_ltv=0.70, grandfathering_applied=True,   # 非규제수도권 무주택
                      rule_id="NONREG_STD_70",
                      reasons=["GRANDFATHERED_ACCEPTED_OR_CONTRACT"])

    # P2. 지역상태
    if inp.region_status_as_of == "NON_REGULATED":
        return baseline_rule(inp)      # C-2

    # --- 이하 REGULATED ---
    # P3. 다주택
    if inp.house_count >= 2:
        return Result(max_ltv=0.00, rule_id="MULTI_0", reasons=["LTV_MULTI_HOME_0"])
    # P4. 유주택(비처분)
    if inp.house_count >= 1 and not inp.disposal_condition_flag:
        return Result(max_ltv=0.00, rule_id="REG_OWNER_0", reasons=["LTV_OWNER_0"])
    # (처분조건부 1주택 = 무주택 기준으로 계속)

    # P5~P7. 무주택 기준 예외 계층
    if inp.first_home_buyer:
        return Result(max_ltv=0.70, rule_id="REG_FIRSTHOME", reasons=["EXCEPTION_FIRST_HOME"])
    if inp.real_demand_flag:
        return Result(max_ltv=0.60, rule_id="REG_REALDEMAND", reasons=["EXCEPTION_REAL_DEMAND"])
    return Result(max_ltv=0.40, rule_id="REG_STD", reasons=["LTV_REGULATED_40"])
```
> ✅ 확정. `is_grandfathered`(G1|G2|G3), `is_owner`, `is_capital_area`, `baseline_rule`(C-2),
> `baseline_gap_reason`(다주택→`MULTI_HOME_BASELINE_UNKNOWN` / 그 외→`OWNER_BASELINE_UNKNOWN`)은
> 하위함수. 이 알고리즘 그대로 deterministic 코드로 구현.

## G. 미결 질문 요약 (✍️ 사용자 입력 대기)

- ~~Q-스키마: 처분조건부 표현~~ ✅ 별도 boolean flag (2026-08-10)
- ~~Q-지역: region_status 세분화~~ ✅ REGULATED/NON_REGULATED 2값 (2026-08-10)
- ~~Q-값1/값2: LTV 값·비처분 1주택~~ ✅ FAQ Q2 이미지로 확정 (2026-08-10)
- ~~Q-스코프: DTI/한도~~ ✅ LTV만 코어 (2026-08-10)
- ✅ Q-우선순위(E): precedence P0~P7 확정 (2026-08-10)
- ✅ Q-경과1~3(F): 날짜경계 `<=2026-06-30`·계약금 일부인정·토허제 G3 포함 확정
- ✅ Q-알고리즘(H): 통합 판정 pseudocode 확정
- ✅ 정책대출 → Discovery 분리 확정
- house_count: 0=무주택 / 1=1주택 / 2+=다주택 (처분조건부는 1+flag). 확정.

> **✅ v1 확정 완료.** 다음: Claude가 이 알고리즘(H)을 deterministic 코드 + 테스트 하네스(🔧)로 구현 → Phase 1 Walking Skeleton 착수.
