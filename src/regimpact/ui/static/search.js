/* BM25 검색 — Python `retrieval/bm25.py` 의 포팅본.
 *
 * 파라미터(k1, b)와 지역 별칭 테이블은 이 파일에 없다 — 내보낸 색인 원재료에서
 * 읽는다. 토크나이저·점수식이 Python 과 갈라지면 화면이 조용히 다른 결과를
 * 보여주므로, tools/verify_search_port.mjs 가 전 프로브 질의의 top-k 를
 * Python 실행 결과와 대조하고 CI 가 배포를 막는다.
 */

const RUN = /[0-9a-z]+|[가-힣]+/g;

export function tokenize(text) {
  const out = [];
  for (const run of text.toLowerCase().match(RUN) ?? []) {
    if (run[0] < "가") out.push(run);
    else if (run.length === 1) out.push(run);
    else for (let i = 0; i < run.length - 1; i++) out.push(run.slice(i, i + 2));
  }
  return out;
}

export function expandQuery(query, regionNames) {
  const extra = [];
  for (const code of Object.keys(regionNames).sort()) {
    const names = regionNames[code];
    if (names.some((n) => query.includes(n))) {
      extra.push(...names.filter((n) => !query.includes(n)));
    }
  }
  if (!extra.length) return query;
  return query + " " + [...new Set(extra)].sort().join(" ");
}

export function buildIndex(exported) {
  const { chunks, params } = exported;
  const tfs = [], df = new Map();
  for (const c of chunks) {
    const tf = new Map();
    for (const t of tokenize(c.text)) tf.set(t, (tf.get(t) ?? 0) + 1);
    tfs.push(tf);
    for (const t of tf.keys()) df.set(t, (df.get(t) ?? 0) + 1);
  }
  const n = chunks.length;
  const idf = new Map();
  for (const [t, d] of df) idf.set(t, Math.log(1 + (n - d + 0.5) / (d + 0.5)));
  const lens = tfs.map((tf) => [...tf.values()].reduce((a, b) => a + b, 0));
  const avg = n ? lens.reduce((a, b) => a + b, 0) / n : 0;
  return { chunks, tfs, idf, lens, avg, k1: params.k1, b: params.b,
           regionNames: exported.region_names };
}

export function search(index, query, k, { expand = false } = {}) {
  if (expand) query = expandQuery(query, index.regionNames);
  const qTerms = [...new Set(tokenize(query))].sort();
  const scored = [];
  for (let i = 0; i < index.chunks.length; i++) {
    const tf = index.tfs[i], dl = index.lens[i];
    let s = 0;
    for (const t of qTerms) {
      const f = tf.get(t);
      if (!f) continue;
      const idf = index.idf.get(t) ?? 0;
      s += (idf * f * (index.k1 + 1)) /
           (f + index.k1 * (1 - index.b + (index.b * dl) / index.avg));
    }
    if (s > 0) scored.push({ chunk: index.chunks[i], score: s });
  }
  scored.sort((a, b) => b.score - a.score || (a.chunk.id < b.chunk.id ? -1 : 1));
  return scored.slice(0, k);
}
