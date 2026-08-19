/**
 * 룰엔진 JS 포팅본 — 브라우저에서 판정을 즉시 보여주기 위한 것.
 *
 * ⚠️ 이 파일은 **Python 엔진의 사본이 아니라 포팅본**이다. 두 구현이 갈라질 수 있으므로
 *    `tools/verify_js_port.mjs` 가 Python 엔진이 만든 픽스처와 전 케이스를 대조한다.
 *    대조 없이 이 파일만 고치면 화면이 조용히 거짓말을 하게 된다.
 *
 * 규칙 **값**은 여기 없다 — 전부 fixtures.constants 에서 읽는다. 값을 여기 적는 순간
 * 엔진 상수가 바뀌어도 화면이 안 따라온다(PR #4 에서 제거했던 하드코딩이 되살아난다).
 * 여기 있는 것은 **순서(§H 우선순위)** 뿐이고, 그 순서가 맞는지는 대조가 증명한다.
 */

export const OUT_OF_SCOPE = "OUT_OF_SCOPE";
export const DISCOVERY = "DISCOVERY";
export const DECIDED = "DECIDED";
export const NEEDS_HUMAN_REVIEW = "NEEDS_HUMAN_REVIEW";

const REGULATED = "REGULATED";
const NON_REGULATED = "NON_REGULATED";
const UNKNOWN = "UNKNOWN";

/** 'YYYY-MM-DD' 문자열 비교로 날짜를 비교한다(사전순 == 시간순). */
const lte = (a, b) => a !== null && a !== undefined && a <= b;

/** 시점 지역상태. 레지스트리에 없으면 UNKNOWN — 비규제로 간주하지 않는다. */
export function regionStatus(fx, code, asOf) {
  const entry = fx.regions[code];
  if (!entry) return UNKNOWN;
  for (const v of entry.versions) {
    const afterStart = v.effective_from === null || asOf >= v.effective_from;
    const beforeEnd = v.effective_to === null || asOf <= v.effective_to;
    if (afterStart && beforeEnd) return v.status;
  }
  return UNKNOWN;
}

export function isCapitalArea(fx, code) {
  return fx.capital_area.includes(code);
}

function grandfathering(fx, app) {
  const cutoff = fx.constants.GRANDFATHERING_CUTOFF;
  if (lte(app.application_accepted_at, cutoff)) {
    return "GRANDFATHERED_ACCEPTED_OR_CONTRACT";
  }
  if (lte(app.contract_signed_at, cutoff) && app.downpayment_paid_at) {
    return "GRANDFATHERED_ACCEPTED_OR_CONTRACT";
  }
  if (app.land_permit_target && lte(app.land_permit_applied_at, cutoff)) {
    return "GRANDFATHERED_LAND_PERMIT";
  }
  return null;
}

const isOwner = (app) =>
  app.house_count >= 2 || (app.house_count >= 1 && !app.disposal_condition_flag);

function decided(ltv, ruleId, reason, sources) {
  return {
    status: DECIDED,
    max_ltv: ltv,
    applicable_rule_id: ruleId,
    grandfathering_applied: false,
    reason_codes: [reason],
    source_policy_ids: sources,
  };
}

/**
 * §H 판정. `trace` 에 어느 규칙에서 멈췄는지 남긴다 — 화면이 "왜 이 값인지"를 보여줘야 한다.
 */
export function evaluate(fx, app) {
  const C = fx.constants;
  const SRC = C.SOURCE_POLICY_IDS;
  const trace = [];
  const step = (id, label, hit, note) => trace.push({ id, label, hit, note });

  // P0. 스코프
  if (app.loan_purpose !== "HOME_PURCHASE") {
    step("P0", "주택구입목적인가", true, "아니다 → 코어 판정 대상 아님");
    return {
      decision: {
        status: OUT_OF_SCOPE, max_ltv: null, applicable_rule_id: null,
        grandfathering_applied: false, reason_codes: ["OUT_OF_SCOPE_PRODUCT"],
        source_policy_ids: [],
      }, trace,
    };
  }
  step("P0", "주택구입목적인가", false, "예 → 계속");

  // P0b. 정책대출
  if (app.policy_mortgage_flag) {
    step("P0b", "정책대출인가", true, "예 → Discovery(수동 검토)");
    return {
      decision: {
        status: DISCOVERY, max_ltv: null, applicable_rule_id: null,
        grandfathering_applied: false, reason_codes: ["DISCOVERY_POLICY_LOAN"],
        source_policy_ids: [],
      }, trace,
    };
  }
  step("P0b", "정책대출인가", false, "아니다 → 계속");

  // P0c. 수도권 다주택 — 규제지역 여부와 무관
  const capital = isCapitalArea(fx, app.region_code);
  if (app.house_count >= 2 && capital) {
    step("P0c", "수도권 다주택인가", true, "예 → 규제지역 여부와 무관하게 0%");
    return { decision: decided(C.LTV_MULTI, "MULTI_0", "LTV_MULTI_HOME_0", SRC), trace };
  }
  step("P0c", "수도권 다주택인가", false, capital ? "수도권이지만 다주택 아님" : "수도권 아님");

  // P0d. 지역 미상
  const status = regionStatus(fx, app.region_code, app.evaluation_date);
  if (status === UNKNOWN) {
    step("P0d", "지역을 아는가", true, "레지스트리에 없다 → 사람 검토 (비규제로 간주하지 않는다)");
    return {
      decision: {
        status: NEEDS_HUMAN_REVIEW, max_ltv: null, applicable_rule_id: null,
        grandfathering_applied: false, reason_codes: ["REGION_UNKNOWN"],
        source_policy_ids: [],
      }, trace,
    };
  }
  step("P0d", "지역을 아는가", false, `${app.region_code} → ${status}`);

  // P1. 경과규정
  const gf = grandfathering(fx, app);
  if (gf) {
    if (isOwner(app)) {
      const reason = app.house_count >= 2
        ? "MULTI_HOME_BASELINE_UNKNOWN" : "OWNER_BASELINE_UNKNOWN";
      step("P1", "경과규정 해당인가", true, "예 — 단 유주택 종전 기준값이 원문에 없다 → 사람 검토");
      return {
        decision: {
          status: NEEDS_HUMAN_REVIEW, max_ltv: null, applicable_rule_id: null,
          grandfathering_applied: true, reason_codes: [gf, reason],
          source_policy_ids: SRC,
        }, trace,
      };
    }
    step("P1", "경과규정 해당인가", true, "예 → 종전규정 적용");
    return {
      decision: {
        status: DECIDED, max_ltv: C.LTV_BASELINE, applicable_rule_id: "NONREG_STD_70",
        grandfathering_applied: true, reason_codes: [gf], source_policy_ids: SRC,
      }, trace,
    };
  }
  step("P1", "경과규정 해당인가", false, `컷오프 ${C.GRANDFATHERING_CUTOFF} 까지의 접수·계약·토허 없음`);

  // P2. 지역상태
  if (status === NON_REGULATED) {
    step("P2", "규제지역인가", false, "비규제 → 기준선 표");
    if (isOwner(app)) {
      const reason = app.house_count >= 2
        ? "MULTI_HOME_BASELINE_UNKNOWN" : "OWNER_BASELINE_UNKNOWN";
      step("P2b", "비규제 유주택 기준값이 있는가", true, "원문에 없다 → 사람 검토");
      return {
        decision: {
          status: NEEDS_HUMAN_REVIEW, max_ltv: null, applicable_rule_id: null,
          grandfathering_applied: false, reason_codes: [reason], source_policy_ids: [],
        }, trace,
      };
    }
    step("P2b", "비규제 무주택", true, "기준선 적용");
    // source_policy_ids 를 비워 둔다. 이 70% 는 6·30 이 만든 값이 아니라 종전부터
    // 있던 기준선이므로, 6·30 문서를 출처로 다는 것은 잘못된 인용이다.
    // (P1 경과규정은 다르다 — 종전규정 적용 자체가 6·30 이 정한 것이라 출처를 단다.)
    return {
      decision: {
        status: DECIDED, max_ltv: C.LTV_BASELINE, applicable_rule_id: "NONREG_STD_70",
        grandfathering_applied: false, reason_codes: ["LTV_BASELINE_70"],
        source_policy_ids: [],
      }, trace,
    };
  }
  step("P2", "규제지역인가", true, "규제지역 → 이하 강화 규정");

  // P3. 다주택 (비수도권 규제지역)
  if (app.house_count >= 2) {
    step("P3", "다주택인가", true, "예");
    return { decision: decided(C.LTV_MULTI, "MULTI_0", "LTV_MULTI_HOME_0", SRC), trace };
  }
  step("P3", "다주택인가", false, "아니다");

  // P4. 유주택(비처분)
  if (app.house_count >= 1 && !app.disposal_condition_flag) {
    step("P4", "비처분 1주택인가", true, "예");
    return { decision: decided(C.LTV_OWNER, "REG_OWNER_0", "LTV_OWNER_0", SRC), trace };
  }
  step("P4", "비처분 1주택인가", false,
       app.house_count >= 1 ? "처분조건부 → 무주택 기준으로 계속" : "무주택");

  // P5. 생애최초
  if (app.first_home_buyer) {
    step("P5", "생애최초인가", true, "예 → 좌동");
    return { decision: decided(C.LTV_FIRST_HOME, "REG_FIRSTHOME", "EXCEPTION_FIRST_HOME", SRC), trace };
  }
  step("P5", "생애최초인가", false, "아니다");

  // P6. 서민·실수요자
  if (app.real_demand_flag) {
    step("P6", "서민·실수요자인가", true, "예");
    return { decision: decided(C.LTV_REAL_DEMAND, "REG_REALDEMAND", "EXCEPTION_REAL_DEMAND", SRC), trace };
  }
  step("P6", "서민·실수요자인가", false, "아니다");

  // P7. 일반
  step("P7", "규제지역 무주택 일반", true, "표준 적용");
  return { decision: decided(C.LTV_REGULATED_STANDARD, "REG_STD", "LTV_REGULATED_40", SRC), trace };
}
