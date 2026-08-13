# 기능단위: Deterministic LTV 룰엔진

> **버전:** v1   **날짜:** 2026-08-13   **상태:** 유효
> **이전 버전:** 없음 — 최초 작성

## 변경 이력 (→ v1)
- 최초 작성 (신규). 이전 버전 없음. (구현 자체는 2026-08-10 커밋 `bd86d23`.)

---

## 1. 목적·책임
주택구입목적 주담대의 **적용 LTV를 결정론적으로(deterministic) 판정**한다.
**LLM이 규칙을 생성하지 않는다(LOCKED §4).** 이 엔진은 확정 명세(`docs/05_RULE_SPEC.md` v1)의
구현이며, LLM 출력(Extractor 등)을 검증하는 **기준점(ground truth)**이다.

## 2. 입력/출력 인터페이스
- 입력: `MortgageApplication` (`src/regimpact/models.py`)
  - `region_code`, `evaluation_date`(시점 해석), `house_count`, `disposal_condition_flag`,
    `first_home_buyer`, `real_demand_flag`, `policy_mortgage_flag`, `loan_purpose`,
    경과규정 이벤트일(`application_accepted_at`/`contract_signed_at`/`downpayment_paid_at`/
    `land_permit_target`/`land_permit_applied_at`).
- 출력: `LtvDecision` — `status`, `max_ltv`, `applicable_rule_id`, `grandfathering_applied`,
  `reason_codes[]`, `source_policy_ids[]`.
- 진입점: `regimpact.evaluate(app) -> LtvDecision`.

## 3. 핵심 로직·설계 결정
- **알고리즘 H (short-circuit 우선순위):** P0 스코프 → P0b 정책대출=Discovery → P1 경과규정
  → P2 지역상태(시점) → P3 다주택 → P4 유주택(비처분) → P5 생애최초 → P6 서민실수요 → P7 일반.
- **시점 해석 분리:** 지역 규제상태는 `regions.resolve_region_status(code, date)`가 버전 데이터로 해석
  (6·30 3개 지역: 2026-07-01부터 REGULATED).
- **경과규정 분리:** `grandfathering.is_grandfathered(app)` — G1(전산접수≤6.30)/G2(계약≤6.30+계약금)/
  G3(토허제 신청≤6.30).
- **정직한 escalation:** 명세에 값이 없는 경우(非규제 유주택 기준선 부재)는 임의값 대신
  `NEEDS_HUMAN_REVIEW` 반환(`OWNER_BASELINE_UNKNOWN`).
- **확정 LTV 값**(§C/regulatory_facts FAQ Q2): 규제 표준 40 / 생애최초 70 / 서민실수요 60 /
  유주택·다주택 0 / 기준선·종전 70.

## 4. 관련 파일
- `src/regimpact/rule_engine.py` (알고리즘 H), `models.py`(스키마), `regions.py`(시점),
  `grandfathering.py`(경과규정)
- `tests/test_rule_engine.py` · `examples/demo_6_30.py`
- 명세: `docs/05_RULE_SPEC.md`, `docs/regulatory_facts.md`

## 5. 검증 상태
- `tests/test_rule_engine.py` — 23건(전체 58 통과에 포함). 우선순위·경계·escalation 커버.
- TC Generator의 독립 오라클 차등검증으로 이중 확인(→ `tc-generator` 기능단위).

## 6. 알려진 제약·모호성
- **코어 출력 = LTV만.** DTI·대출한도는 참고값(코어 판정 아님).
- **Q8(OPEN_QUESTIONS):** 유주택+생애최초 모순 입력 시 §H(0%) vs §E(escalation) 상충 —
  현재 §H 권위 채택. 도메인 확정 대기.
- 정책대출은 Discovery(수동 검토)로 분리, 코어 자동판정 제외.
