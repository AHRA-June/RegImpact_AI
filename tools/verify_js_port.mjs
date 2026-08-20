/**
 * JS 포팅본 ↔ Python 엔진 대조.
 *
 * 실행:  python tools/export_fixtures.py --out site/fixtures.json
 *        node tools/verify_js_port.mjs [site/fixtures.json]
 *
 * 브라우저에서 도는 룰엔진 포팅본이 Python 엔진과 같은 판정을 내는지 전 케이스 확인한다.
 * 화면에 두 번째 룰 구현을 두는 것 자체가 위험이므로, 그 위험을 대조로 상쇄한다.
 * 하나라도 어긋나면 exit 1 — CI 가 배포를 막는다.
 */
import { readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { evaluate, regionStatus } from "../src/regimpact/ui/static/engine.js";
import { estimateAffordability } from "../src/regimpact/ui/static/affordability.js";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const fxPath = resolve(process.argv[2] ?? join(ROOT, "site", "fixtures.json"));
const fx = JSON.parse(readFileSync(fxPath, "utf8"));

const sameSet = (a, b) =>
  JSON.stringify([...(a ?? [])].sort()) === JSON.stringify([...(b ?? [])].sort());

const failures = [];

// --- 1. 판정 케이스 대조 ---
for (const c of fx.cases) {
  const js = evaluate(fx, c.input).decision;
  const py = c.engine;
  const diffs = [];
  if (js.status !== py.status) diffs.push(`status ${py.status} vs ${js.status}`);
  if ((js.max_ltv ?? null) !== (py.max_ltv ?? null)) {
    diffs.push(`max_ltv ${py.max_ltv} vs ${js.max_ltv}`);
  }
  if ((js.applicable_rule_id ?? null) !== (py.applicable_rule_id ?? null)) {
    diffs.push(`rule_id ${py.applicable_rule_id} vs ${js.applicable_rule_id}`);
  }
  if (js.grandfathering_applied !== py.grandfathering_applied) {
    diffs.push(`grandfathering ${py.grandfathering_applied} vs ${js.grandfathering_applied}`);
  }
  if (!sameSet(js.reason_codes, py.reason_codes)) {
    diffs.push(`reasons [${py.reason_codes}] vs [${js.reason_codes}]`);
  }
  if (!sameSet(js.source_policy_ids, py.source_policy_ids)) {
    diffs.push(`sources [${py.source_policy_ids}] vs [${js.source_policy_ids}]`);
  }
  if (diffs.length) failures.push({ kind: "case", id: c.case_id, diffs });
}

// --- 2. 지역 × 시점 격자 대조 (시간축 해석) ---
let probes = 0;
for (const [code, byDate] of Object.entries(fx.region_probe)) {
  for (const [asOf, expected] of Object.entries(byDate)) {
    probes += 1;
    const actual = regionStatus(fx, code, asOf);
    if (actual !== expected) {
      failures.push({ kind: "region", id: `${code}@${asOf}`,
                      diffs: [`${expected} vs ${actual}`] });
    }
  }
}

// --- 3. 참고 한도(통합 계산기) 프로브 대조 ---
let affProbes = 0;
for (const pr of fx.affordability?.probes ?? []) {
  affProbes += 1;
  const js = estimateAffordability(fx, pr.input);
  const py = pr.expected;
  const diffs = [];
  for (const k of ["LTV", "CAP", "DSR", "DTI"]) {
    if ((js.limits[k] ?? null) !== (py.limits[k] ?? null)) {
      diffs.push(`${k} ${py.limits[k]} vs ${js.limits[k]}`);
    }
  }
  if ((js.total ?? null) !== (py.total ?? null)) diffs.push(`total ${py.total} vs ${js.total}`);
  if (JSON.stringify(js.binding) !== JSON.stringify(py.binding)) {
    diffs.push(`binding [${py.binding}] vs [${js.binding}]`);
  }
  if (diffs.length) {
    failures.push({ kind: "affordability", id: `probe#${affProbes - 1}`, diffs });
  }
}

// --- 4. 값이 JS 에 하드코딩되지 않았는지 ---
for (const f of ["engine.js", "affordability.js"]) {
  const src = readFileSync(join(ROOT, "src/regimpact/ui/static", f), "utf8");
  const codeOnly = src.replace(/\/\*[\s\S]*?\*\//g, "").replace(/\/\/.*$/gm, "");
  const literals = [...codeOnly.matchAll(/(?<![\w.])0\.\d+/g)].map((m) => m[0]);
  if (literals.length) {
    failures.push({ kind: "hardcode", id: f,
                    diffs: [`규제 값 리터럴이 있다: ${[...new Set(literals)].join(", ")}`] });
  }
}

// --- 결과 ---
const total = fx.cases.length + probes + affProbes;
if (failures.length) {
  console.error(`✗ JS 포팅 대조 실패 ${failures.length}건 / ${total}건 검사\n`);
  for (const f of failures.slice(0, 20)) {
    console.error(`  [${f.kind}] ${f.id}`);
    for (const d of f.diffs) console.error(`      python vs js — ${d}`);
  }
  if (failures.length > 20) console.error(`  … 외 ${failures.length - 20}건`);
  process.exit(1);
}

console.log(`✓ JS 포팅본이 Python 엔진과 일치 — 판정 ${fx.cases.length}건 · 지역프로브 ${probes}건 · 한도계산 ${affProbes}건`);
