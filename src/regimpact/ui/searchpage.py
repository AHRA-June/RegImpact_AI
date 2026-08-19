"""규제 원문 검색 화면 — BM25 가 **브라우저에서 실제로 실행**된다.

RAG 의 검색 절반이다. 생성(LLM 답변) 절반은 정적 배포에서 실행되지 않으므로
하는 척하지 않는다 — 검색 품질을 사람 확정 인용 기준 recall@k 로 실측해 싣고,
LLM 연결은 실제 CLI 경로를 안내한다.

검색 JS 는 Python 색인의 포팅본이고 `tools/verify_search_port.mjs` 가 전 프로브를
대조한다(룰엔진 JS 포팅과 같은 통제).
"""
from __future__ import annotations

import json
from pathlib import Path

from ..retrieval.evaluate import RetrievalReport
from .theme import card, chip, esc, glance, page, page_title, table

SEARCH_JS = Path(__file__).resolve().parent / "static" / "search.js"

_PRESETS = [
    "동탄 LTV 얼마로 바뀌나",
    "생애최초 주택구입자는 강화되나",
    "잔금대출 경과규정",
    "규제지역 지정 시행일",
    "다주택자 주담대",
]


def render(index_export: dict, reports: dict[bool, RetrievalReport]) -> str:
    r_off, r_on = reports[False], reports[True]
    idx_json = json.dumps(index_export, ensure_ascii=False, separators=(",", ":"))
    engine = SEARCH_JS.read_text(encoding="utf-8")
    n_chunks = len(index_export["chunks"])
    n_docs = len({c["doc_id"] for c in index_export["chunks"]})

    top = glance(
        f"원문 {n_docs}건을 {n_chunks}개 구간으로 색인했다 — 이 화면의 검색은 "
        f"브라우저에서 실제로 실행되고, 품질은 사람 확정 인용 기준으로 "
        f"recall@5 {r_off.recall(5):.0%} / recall@10 {r_off.recall(10):.0%} 실측이다.",
        [chip(f"색인 {n_chunks}구간 · 문서 {n_docs}건", tone="primary"),
         chip(f"recall@5 {r_off.recall(5):.0%}",
              tone="good" if r_off.recall(5) >= 0.8 else "warn"),
         chip(f"못 찾은 인용 {len(r_off.misses_at_max_k)}건 (정직하게 표기)", tone="warn"),
         chip("BM25 · 외부 의존 0 · 무과금", tone="neutral")],
    )

    presets = "".join(
        f'<button type="button" class="preset-q" data-q="{esc(q)}">{esc(q)}</button>'
        for q in _PRESETS)

    search_ui = (
        '<div class="flex flex-col gap-3">'
        '<div class="flex gap-2 flex-wrap" style="align-items:center">'
        '<input id="q" type="search" placeholder="규제 원문에서 찾기 — 예: 동탄 LTV" '
        'style="flex:1;min-width:220px" class="px-4 py-2 rounded-lg border border-outline-variant" '
        'autocomplete="off">'
        '<label class="flex items-center gap-2 text-body-sm" style="cursor:pointer">'
        '<input type="checkbox" id="expand" checked> 지역 별칭 확장</label></div>'
        f'<div class="flex gap-2 flex-wrap">{presets}</div>'
        '<div id="hits" class="flex flex-col gap-3"></div></div>'
    )

    recall_rows = []
    for label, rep in (("BM25", r_off), ("BM25 + 지역 별칭 확장", r_on)):
        recall_rows.append(
            [esc(label)]
            + [chip(f"{rep.recall(k):.0%}", mono=True,
                    tone="good" if rep.recall(k) >= 0.8 else "neutral")
               for k in rep.ks])
    miss_list = "".join(
        f'<li class="flex gap-2 text-body-sm" style="line-height:20px">'
        f'{chip(m.item_id, mono=True)}<span class="text-on-surface-variant">'
        f'[{esc(m.doc_id)}] “{esc(m.quote_head)}…”</span></li>'
        for m in r_off.misses_at_max_k)

    rag_note = (
        '<ol class="flex flex-col gap-2" style="list-style:decimal;padding-left:20px;line-height:24px">'
        "<li><b>검색(이 화면)</b> — 질문과 어휘가 겹치는 원문 구간을 고른다. "
        "브라우저에서 실제 실행되며, Python 색인과 전 프로브 대조된다.</li>"
        "<li><b>생성(LLM)</b> — 고른 구간만 문맥으로 주고 인용과 함께 답하게 한다. "
        "정적 페이지에서는 실행되지 않는다 — 무과금 CLI 로:"
        '<pre class="cmd">python examples/run_retrieval_eval.py          # 검색 품질 재현\n'
        "python examples/run_goldset_eval.py --split DEV  # QA 평가 (전체 문맥 방식)</pre></li>"
        "<li><b>비교 측정(다음 단계)</b> — 전체 문맥 vs 검색 문맥의 QA 성적을 같은 "
        "골드셋으로 비교한다. 코퍼스(과거 정책 원문)가 늘면 이 차이가 의미를 갖는다.</li></ol>"
    )

    body = (
        page_title(
            "규제 원문 검색",
            "질문과 어휘가 겹치는 원문 구간을 BM25로 찾는다 — RAG의 검색 절반. "
            "품질은 골드 인용 기준 recall@k 실측.",
        )
        + top
        + card("검색 — 브라우저에서 실제 실행", search_ui,
               note="한글은 2-gram 매칭이라 조사·어미가 달라도 걸린다. "
                    "지역 별칭 확장: '동탄' ↔ '화성시 동탄구' 같은 표기 차이를 별칭 테이블(D-01)로 잇는다")
        + card(
            "검색 품질 실측 — 사람 확정 인용 기준",
            table(["방식"] + [f"recall@{k}" for k in r_off.ks], recall_rows,
                  align_center=tuple(range(1, len(r_off.ks) + 1)))
            + '<div class="mt-6"><div class="font-medium mb-2">'
            f"top-10에도 못 찾은 인용 {len(r_off.misses_at_max_k)}건</div>"
            f'<ul class="flex flex-col gap-1">{miss_list}</ul></div>',
            note=f"측정 정의: 골드 문항의 질문으로 검색해 top-k 가 그 문항 인용 구간의 "
                 f"60% 이상을 덮으면 적중. DEV {r_off.n_items}문항 · 인용 {r_off.n_citations}건 "
                 "(봉인 셋은 열지 않음)",
        )
        + card("이것이 RAG 의 어디까지인가 (정직하게)", rag_note,
               note="검색이 안 되는 걸 LLM 이 메꾸면 그게 곧 환각이다 — 그래서 검색부터 측정한다")
    )

    script = f"""<script type="module">
{engine}
const INDEX = buildIndex({idx_json});
const $q = document.getElementById("q"), $hits = document.getElementById("hits"),
      $ex = document.getElementById("expand");
function esc(s) {{ const d = document.createElement("span"); d.textContent = s; return d.innerHTML; }}
function hl(text, query) {{
  let out = esc(text);
  const words = query.split(/\\s+/).filter(w => w.length >= 2).sort((a,b) => b.length - a.length);
  for (const w of words.slice(0, 8)) {{
    out = out.split(esc(w)).join(`<mark>${{esc(w)}}</mark>`);
  }}
  return out;
}}
function run() {{
  const query = $q.value.trim();
  if (!query) {{ $hits.innerHTML = ""; return; }}
  const res = search(INDEX, query, 8, {{ expand: $ex.checked }});
  if (!res.length) {{
    $hits.innerHTML = '<div class="text-body-sm text-on-surface-variant">' +
      '일치하는 구간이 없다 — 이 코퍼스(공문 3건)에 없는 주제일 수 있다. ' +
      '없는 답을 만들지 않는 것이 이 시스템의 원칙이다.</div>';
    return;
  }}
  $hits.innerHTML = res.map(r =>
    `<div class="hit border border-outline-variant rounded-lg p-4 flex flex-col gap-2">` +
    `<div class="flex gap-2 items-center flex-wrap">` +
    `<span class="font-mono-data text-mono-data text-secondary">${{r.score.toFixed(2)}}</span>` +
    `<span class="doc-chip">${{esc(r.chunk.doc_id)}}</span>` +
    `<span class="font-mono-label text-mono-label text-on-surface-variant">${{esc(r.chunk.id)}}</span></div>` +
    `<div class="text-body-md" style="line-height:23px">${{hl(r.chunk.text, $q.value)}}</div></div>`
  ).join("");
}}
$q.addEventListener("input", run);
$ex.addEventListener("change", run);
document.querySelectorAll(".preset-q").forEach(b =>
  b.addEventListener("click", () => {{ $q.value = b.dataset.q; run(); }}));
</script>"""

    extra_css = """
.preset-q{padding:5px 12px;font-size:12px;font-family:inherit;cursor:pointer;
  border:1px solid var(--outline-variant);border-radius:99px;background:transparent;
  color:var(--on-surface-variant)}
.preset-q:hover{border-color:var(--primary);color:var(--primary)}
#q{background:var(--surface-container-lowest);color:var(--on-surface);font-size:14px}
.hit mark{background:var(--primary-fixed);color:var(--on-primary-fixed);border-radius:2px;padding:0 1px}
.doc-chip{font-family:'JetBrains Mono',ui-monospace,monospace;font-size:11px;
  background:var(--surface-variant);color:var(--on-surface-variant);padding:2px 7px;border-radius:3px}
.cmd{font-family:'JetBrains Mono',ui-monospace,monospace;font-size:12px;line-height:19px;
  background:var(--surface-container);border:1px solid var(--outline-variant);border-radius:4px;
  padding:8px 12px;margin:6px 0 2px;overflow-x:auto;white-space:pre}
"""
    return page(title="규제 원문 검색", active="search.html",
                scenario="BM25 · 브라우저 실행", status="Python ↔ JS 전 프로브 대조",
                body=body, extra_script=script, extra_css=extra_css)
