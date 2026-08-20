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
