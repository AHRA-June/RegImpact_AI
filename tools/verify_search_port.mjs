// BM25 JS 포팅본 ↔ Python 대조 — 룰엔진 verify_js_port 와 같은 원칙.
//
// 사용: node tools/verify_search_port.mjs <search_fixtures.json>
// 픽스처는 build_site 가 만든다: {index: 색인 원재료, probes: [{query, expand,
// expected: [{id, score}]}]}. expected 는 Python BM25Index 실행 결과다.
// 하나라도 어긋나면 exit 1 — CI 가 배포를 막는다.
import { readFileSync } from "node:fs";
import { buildIndex, search } from "../src/regimpact/ui/static/search.js";

const path = process.argv[2];
if (!path) {
  console.error("사용법: node tools/verify_search_port.mjs <search_fixtures.json>");
  process.exit(2);
}
const fx = JSON.parse(readFileSync(path, "utf-8"));
const index = buildIndex(fx.index);

let failures = 0;
for (const probe of fx.probes) {
  const got = search(index, probe.query, probe.expected.length || 10,
                     { expand: probe.expand, docIds: probe.doc_ids ?? null });
  const exp = probe.expected;
  if (got.length !== exp.length) {
    failures++;
    console.error(`✗ [${probe.query}] 결과 수 ${got.length} ≠ ${exp.length}`);
    continue;
  }
  for (let i = 0; i < exp.length; i++) {
    const idOk = got[i].chunk.id === exp[i].id;
    const scoreOk = Math.abs(got[i].score - exp[i].score) < 1e-9;
    if (!idOk || !scoreOk) {
      failures++;
      console.error(
        `✗ [${probe.query}] #${i}: JS ${got[i].chunk.id}(${got[i].score.toFixed(6)})` +
        ` ≠ PY ${exp[i].id}(${exp[i].score.toFixed(6)})`);
      break;
    }
  }
}

const n = fx.probes.length;
if (failures) {
  console.error(`검색 포팅 대조 실패: ${failures}/${n} 프로브 불일치`);
  process.exit(1);
}
console.log(`✓ 검색 JS 포팅본이 Python 과 일치 — 프로브 ${n}건 (top-k id·점수 전건)`);
