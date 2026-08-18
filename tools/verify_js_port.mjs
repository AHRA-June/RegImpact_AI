/**
 * JS 포팅본 ↔ Python 엔진 대조 (CI/커밋 전 검증용).
 *
 * web/sandbox.template.html 에서 룰엔진 포팅 구간만 떼어내 Node 에서 실행하고,
 * web/fixtures.json(= 실제 Python 엔진 출력)과 전 케이스를 비교한다.
 * 브라우저를 띄우지 않고도 포팅 드리프트를 잡기 위한 것.
 *
 * 실행:  node tools/verify_js_port.mjs
 */
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const html = readFileSync(join(ROOT, "web/sandbox.template.html"), "utf8");
const fixtures = JSON.parse(readFileSync(join(ROOT, "web/fixtures.json"), "utf8"));

const START = "/* ===================== 룰엔진 JS 포팅";
const END = "/* ===================== 폼 상태";
const body = html.slice(html.indexOf(START), html.indexOf(END));
if (!body) throw new Error("엔진 구간을 찾을 수 없음 — 템플릿의 구분 주석이 바뀌었는지 확인");

const evaluate = new Function(`${body}; return evaluate;`)();

const sortedEq = (a, b) => JSON.stringify([...a].sort()) === JSON.stringify([...b].sort());
const failures = [];

for (const c of fixtures.cases) {
  const js = evaluate(c.input).decision;
  const py = c.engine;
  const ok =
    js.status === py.status &&
    (js.max_ltv ?? null) === (py.max_ltv ?? null) &&
    (js.applicable_rule_id ?? null) === (py.applicable_rule_id ?? null) &&
    js.grandfathering_applied === py.grandfathering_applied &&
    sortedEq(js.reason_codes, py.reason_codes) &&
    sortedEq(js.source_policy_ids, py.source_policy_ids);
  if (!ok) failures.push({ case_id: c.case_id, python: py, js });
}

if (failures.length) {
  console.error(`✕ ${failures.length}/${fixtures.cases.length} 불일치`);
  for (const f of failures) console.error(JSON.stringify(f, null, 2));
  process.exit(1);
}
console.log(`✓ JS 포팅본이 Python 엔진과 ${fixtures.cases.length}/${fixtures.cases.length} 일치`);
