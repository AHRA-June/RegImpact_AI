/* 총 가능금액(참고 추정) — Python `affordability.py` 의 포팅본.
 *
 * 규제 값(최대한도 6/4/2억, DSR 40/50, DTI 40/50/60, 만기 30년)은 이 파일에 없다 —
 * 픽스처(fx.affordability.constants)에서 읽는다. 계산이 Python 과 갈라지면
 * tools/verify_js_port.mjs 의 프로브 대조가 실패하고 CI 가 배포를 막는다.
 */

export function principalFromAnnualPayment(annualPayment, annualRate, termYears) {
  if (annualPayment <= 0 || termYears <= 0) return 0;
  const n = termYears * 12;
  const pm = annualPayment / 12;
  const r = annualRate / 12;
  if (r <= 0) return Math.trunc(pm * n);
  return Math.trunc((pm * (1 - (1 + r) ** -n)) / r);
}

export function capForPrice(fx, price) {
  for (const [upper, cap] of fx.affordability.constants.max_loan_caps) {
    if (upper === null || price <= upper) return cap;
  }
  throw new Error("unreachable");
}

export function dtiRate(fx, ruleId, regulatedType) {
  const C = fx.affordability.constants;
  if (C.dti_relaxed_rules.includes(ruleId)) return C.dti_other;
  return C.dti_by_type[regulatedType] ?? C.dti_other;
}

export function estimateAffordability(fx, inp) {
  const C = fx.affordability.constants;
  const income = inp.annual_income ?? null;
  const rate = inp.annual_rate ?? null;
  const limits = {
    LTV: Math.trunc(inp.price * inp.max_ltv),
    CAP: inp.regulated ? capForPrice(fx, inp.price) : null,
    DSR: null,
    DTI: null,
  };
  if (income && rate !== null) {
    const debtAnnual = (inp.monthly_debt_service ?? 0) * 12;
    const dsrBudget = income * C.dsr_rates[inp.lender ?? "BANK"] - debtAnnual;
    limits.DSR = principalFromAnnualPayment(dsrBudget, rate, inp.term_years);
    const dtiBudget = income * dtiRate(fx, inp.rule_id, inp.regulated_type) - debtAnnual;
    limits.DTI = principalFromAnnualPayment(dtiBudget, rate, inp.term_years);
  }
  const known = Object.entries(limits).filter(([, v]) => v !== null);
  const total = known.length ? Math.min(...known.map(([, v]) => v)) : null;
  const binding = known.filter(([, v]) => v === total).map(([k]) => k).sort();
  return {
    limits, total, binding,
    dti_rate: dtiRate(fx, inp.rule_id, inp.regulated_type),
    dsr_rate: C.dsr_rates[inp.lender ?? "BANK"],
  };
}

/* 목표 역산 — Python `plan_for_target` 의 포팅본. 규제 값은 픽스처에서 읽는다. */
export function annualPaymentForPrincipal(principal, annualRate, termYears) {
  if (principal <= 0 || termYears <= 0) return 0;
  const n = termYears * 12;
  const r = annualRate / 12;
  const monthly = r <= 0 ? principal / n : (principal * r) / (1 - (1 + r) ** -n);
  return monthly * 12;
}

export function planForTarget(fx, inp) {
  const C = fx.affordability.constants;
  const now = estimateAffordability(fx, inp);
  if (now.total === null) return { target: inp.target, reachable: null, now, actions: [] };
  if (now.total >= inp.target) {
    return { target: inp.target, reachable: true, now, actions: [],
             headroom: now.total - inp.target };
  }
  const actions = [];
  const L = now.limits;
  if (L.LTV !== null && L.LTV < inp.target && inp.max_ltv > 0) {
    actions.push({ limit: "LTV", kind: "price",
      need_price: Math.trunc(inp.target / inp.max_ltv),
      detail: "담보 비율은 규제가 정한 값이라 바꿀 수 없어요. "
            + "같은 금액을 빌리려면 주택가격 기준이 더 높아야 합니다." });
  }
  if (L.CAP !== null && L.CAP < inp.target) {
    actions.push({ limit: "CAP", kind: "hard",
      detail: "규제지역 가격구간별 최대한도라 조건을 바꿔도 이 금액을 넘을 수 없어요." });
  }
  const income = inp.annual_income ?? null;
  const rate = inp.annual_rate ?? null;
  if (income && rate !== null) {
    const needAnnual = annualPaymentForPrincipal(inp.target, rate, inp.term_years);
    const debt = inp.monthly_debt_service ?? 0;
    const pairs = [["DSR", C.dsr_rates[inp.lender ?? "BANK"]],
                   ["DTI", dtiRate(fx, inp.rule_id, inp.regulated_type)]];
    for (const [key, ratio] of pairs) {
      if (L[key] === null || L[key] >= inp.target) continue;
      const allowDebtAnnual = income * ratio - needAnnual;
      const cut = debt - allowDebtAnnual / 12;
      let byTerm = null;
      if (inp.term_years < C.max_term_years) {
        const longer = principalFromAnnualPayment(
          income * ratio - debt * 12, rate, C.max_term_years);
        byTerm = { years: C.max_term_years, limit: longer, enough: longer >= inp.target };
      }
      const needIncome = Math.trunc((needAnnual + debt * 12) / ratio);
      actions.push({ limit: key, kind: "income",
        cut_monthly_debt: (cut > 0 && cut <= debt) ? Math.trunc(cut) : null,
        impossible_by_debt: cut > debt,
        by_term: byTerm,
        need_income: needIncome,
        need_income_delta: needIncome - income });
    }
  }
  return { target: inp.target, reachable: false, now, actions,
           shortfall: inp.target - now.total };
}
