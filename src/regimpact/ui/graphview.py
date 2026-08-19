"""영향 지식그래프 화면 — 레이어드 DAG 를 자기완결 SVG+JS 로 그린다.

노드를 클릭하면 그 노드에서 **양방향으로 도달 가능한 경로**가 강조된다 —
"이 문서가 어떤 정책·룰·고객군까지 흘러가는가 / 이 세그먼트는 어디서 왔는가"가
이 화면의 유일한 질문이다. 엣지마다 provenance(어느 산출물에서 왔는가)를 갖고,
상세 패널이 그것을 그대로 보여준다.

레이아웃은 파이썬에서 결정적으로 계산한다(난수 없는 열 배치) — 빌드마다 같은 그림.
"""
from __future__ import annotations

import json

from ..graph import Graph
from .theme import card, chip, esc, explainer, glance, page, page_title

_COL_LABEL = {
    "doc": "원문 문서", "policy": "정책 버전", "region": "규제지역",
    "rule": "룰 (엔진 상수)", "segment": "고객 세그먼트", "tc": "룰 회귀 (검증)",
}
# 열 색 — 테마 토큰의 상태 의미를 따른다 (식별용 소수 hue, 시리즈 아님)
_COL_TONE = {
    "doc": "var(--outline)", "policy": "var(--primary)", "region": "var(--secondary)",
    "rule": "var(--tertiary-fixed-dim)", "segment": "var(--error)", "tc": "var(--inverse-primary)",
}

_NODE_W, _NODE_H, _ROW_GAP, _COL_GAP, _PAD = 178, 46, 16, 42, 24


def _layout(g: Graph) -> tuple[dict, int, int]:
    """열 배치 — x 는 열, y 는 열 내 순서(정의 순서 유지). 난수 없음."""
    cols: dict[str, list] = {c: [] for c in _COL_LABEL}
    for n in g.nodes:
        cols[n.type].append(n)
    max_rows = max(len(v) for v in cols.values())
    height = _PAD * 2 + 30 + max_rows * (_NODE_H + _ROW_GAP)
    pos = {}
    for ci, (ctype, nodes) in enumerate(cols.items()):
        x = _PAD + ci * (_NODE_W + _COL_GAP)
        # 열 안에서 세로 중앙 정렬
        y0 = _PAD + 30 + (max_rows - len(nodes)) * (_NODE_H + _ROW_GAP) / 2
        for ri, n in enumerate(nodes):
            pos[n.id] = (x, y0 + ri * (_NODE_H + _ROW_GAP), ci)
    width = _PAD * 2 + len(cols) * _NODE_W + (len(cols) - 1) * _COL_GAP
    return pos, int(width), int(height)


def _svg(g: Graph) -> str:
    pos, W, H = _layout(g)
    parts = [f'<svg id="kg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
             'font-family="\'Noto Sans\',sans-serif" role="img" '
             'aria-label="규제 영향 지식그래프">']
    # 열 헤더
    seen_cols = set()
    for n in g.nodes:
        x, _, ci = pos[n.id]
        if n.type in seen_cols:
            continue
        seen_cols.add(n.type)
        parts.append(
            f'<text x="{x + _NODE_W / 2}" y="{_PAD + 8}" text-anchor="middle" '
            f'font-size="12" font-weight="600" fill="var(--on-surface-variant)" '
            f'letter-spacing=".04em">{esc(_COL_LABEL[n.type])}</text>')
    # 엣지 (노드 아래 깔리게 먼저)
    maxw = max((e.weight for e in g.edges), default=1)
    for i, e in enumerate(g.edges):
        x1, y1, _ = pos[e.source]
        x2, y2, _ = pos[e.target]
        sx, sy = x1 + _NODE_W, y1 + _NODE_H / 2
        tx, ty = x2, y2 + _NODE_H / 2
        if x2 <= x1:   # 같은 열(타임라인) — 세로 곡선
            sx, sy = x1 + _NODE_W / 2, y1 + _NODE_H
            tx, ty = x2 + _NODE_W / 2, y2
            d = f"M{sx},{sy} C{sx},{sy + 18} {tx},{ty - 18} {tx},{ty}"
        else:
            mx = (sx + tx) / 2
            d = f"M{sx},{sy} C{mx},{sy} {mx},{ty} {tx},{ty}"
        w = 1.2 + 4.5 * (e.weight / maxw) ** 0.5
        parts.append(
            f'<path class="ke" data-i="{i}" data-s="{esc(e.source)}" data-t="{esc(e.target)}" '
            f'd="{d}" fill="none" stroke="var(--outline-variant)" stroke-width="{w:.1f}" '
            'stroke-linecap="round" opacity=".75"/>')
    # 노드
    for n in g.nodes:
        x, y, _ = pos[n.id]
        parts.append(
            f'<g class="kn" data-id="{esc(n.id)}" tabindex="0" role="button" '
            f'aria-label="{esc(n.label)}" transform="translate({x},{y})" cursor="pointer">'
            f'<rect width="{_NODE_W}" height="{_NODE_H}" rx="6" '
            f'fill="var(--surface-container-lowest)" stroke="{_COL_TONE[n.type]}" '
            'stroke-width="1.6"/>'
            f'<rect width="4" height="{_NODE_H}" rx="2" fill="{_COL_TONE[n.type]}"/>'
            f'<text x="12" y="19" font-size="11.5" font-weight="600" '
            f'fill="var(--on-surface)">{esc(n.label[:15])}</text>'
            f'<text x="12" y="35" font-size="10" '
            f'fill="var(--on-surface-variant)">{esc(n.sub[:24])}</text>'
            "</g>")
    parts.append("</svg>")
    return "".join(parts)


def render(g: Graph, *, portfolio_size: int) -> str:
    data = json.dumps(g.to_dict(), ensure_ascii=False, separators=(",", ":"))
    n_by = {}
    for n in g.nodes:
        n_by[n.type] = n_by.get(n.type, 0) + 1

    top = glance(
        f"노드 {len(g.nodes)}개 · 관계 {len(g.edges)}개 — 전부 검증된 산출물"
        f"(정책 DB · 룰엔진 diff · 고객 영향 실측 · 룰 회귀)에서 조립했다. "
        "LLM 이 만든 그래프가 아니라서 관계마다 출처(provenance)가 있다.",
        [chip(f"정책 {n_by.get('policy', 0)}건 타임라인", tone="primary"),
         chip(f"룰 → 세그먼트 연결은 합성 {portfolio_size:,}건 실측", tone="good"),
         chip("전 관계 provenance 보유", tone="neutral")],
    )

    legend = "".join(
        f'<span class="lg"><i style="background:{_COL_TONE[c]}"></i>{esc(l)}</span>'
        for c, l in _COL_LABEL.items())

    body = (
        page_title(
            "영향 지식그래프",
            "문서 → 정책 → 지역 → 룰 → 고객까지, 규제 변경이 흘러가는 경로. "
            "노드를 클릭하면 그 노드와 연결된 경로가 양방향으로 강조된다.",
        )
        + explainer(
            "규제 변경이 문서 → 정책 → 지역 → 규칙 → 고객으로 어떻게 번져가는지 "
            "연결 지도로 보는 화면입니다.",
            "이 사이트의 다른 화면들이 이미 계산·검증해 둔 데이터(정책 이력, 규칙 변경, "
            "고객 영향 계산, 검산 결과)를 이어 붙인 것. AI가 상상으로 그린 그림이 아니라서 "
            "연결선마다 \"어느 데이터에서 왔는지\" 출처가 있습니다.",
            "상자(노드)를 클릭하면 그것과 연결된 경로만 밝게 남습니다. 아래 패널에서 "
            "각 연결의 출처를 확인할 수 있습니다.",
        )
        + top
        + card(
            "그래프",
            f'<div class="lgs">{legend}</div>'
            f'<div class="kg-wrap" style="overflow-x:auto">{_svg(g)}</div>',
            note="레이아웃은 빌드 시 결정적으로 계산 — 난수 없음. 넓은 화면에서는 전체가, "
                 "좁은 화면에서는 가로 스크롤로 보인다",
        )
        + card(
            "선택한 노드",
            '<div id="detail" class="text-body-md text-on-surface-variant">'
            "노드를 클릭하면 연결된 관계와 각 관계의 출처(provenance)가 여기 표시된다.</div>",
        )
    )

    script = """<script>
const G = __DATA__;
const OUT = {}, IN = {};
G.edges.forEach((e, i) => {
  (OUT[e.source] = OUT[e.source] || []).push(i);
  (IN[e.target] = IN[e.target] || []).push(i);
});
function reach(id) {
  const nodes = new Set([id]), edges = new Set();
  const walk = (start, adj, dir) => {
    const q = [start];
    while (q.length) {
      const cur = q.pop();
      (adj[cur] || []).forEach(i => {
        if (edges.has(i)) return;
        edges.add(i);
        const nxt = dir === "out" ? G.edges[i].target : G.edges[i].source;
        if (!nodes.has(nxt)) { nodes.add(nxt); q.push(nxt); }
      });
    }
  };
  walk(id, OUT, "out"); walk(id, IN, "in");
  return { nodes, edges };
}
const svg = document.getElementById("kg"), detail = document.getElementById("detail");
const nodeEls = [...svg.querySelectorAll(".kn")], edgeEls = [...svg.querySelectorAll(".ke")];
const byId = {}; G.nodes.forEach(n => byId[n.id] = n);
let selected = null;
function esc(s) { const d = document.createElement("span"); d.textContent = s; return d.innerHTML; }
function paint() {
  if (!selected) {
    nodeEls.forEach(el => el.style.opacity = 1);
    edgeEls.forEach(el => { el.style.opacity = .75; el.style.stroke = "var(--outline-variant)"; });
    detail.innerHTML = "노드를 클릭하면 연결된 관계와 각 관계의 출처(provenance)가 여기 표시된다.";
    return;
  }
  const r = reach(selected);
  nodeEls.forEach(el => el.style.opacity = r.nodes.has(el.dataset.id) ? 1 : .18);
  edgeEls.forEach(el => {
    const hit = r.edges.has(Number(el.dataset.i));
    el.style.opacity = hit ? .95 : .08;
    el.style.stroke = hit ? "var(--secondary)" : "var(--outline-variant)";
  });
  const n = byId[selected];
  const rows = [...r.edges].map(i => G.edges[i])
    .filter(e => e.source === selected || e.target === selected)
    .map(e => {
      const other = e.source === selected ? e.target : e.source;
      const arrow = e.source === selected ? "→" : "←";
      return `<li><b>${arrow} ${esc(byId[other].label)}</b>` +
        (e.label ? ` — ${esc(e.label)}` : "") +
        `<div class="prov">출처: ${esc(e.provenance)}</div></li>`;
    }).join("");
  detail.innerHTML =
    `<div class="dt-head"><b>${esc(n.label)}</b> <span>${esc(n.sub)}</span></div>` +
    `<div class="dt-sum">양방향 도달: 노드 ${r.nodes.size}개 · 관계 ${r.edges.size}개</div>` +
    `<ul class="dt-list">${rows}</ul>`;
}
nodeEls.forEach(el => {
  const pick = () => { selected = selected === el.dataset.id ? null : el.dataset.id; paint(); };
  el.addEventListener("click", pick);
  el.addEventListener("keydown", ev => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); pick(); } });
});
svg.addEventListener("click", ev => { if (ev.target === svg) { selected = null; paint(); } });
paint();
</script>""".replace("__DATA__", data)

    extra_css = """
.lgs{display:flex;flex-wrap:wrap;gap:14px;margin-bottom:10px}
.lg{display:inline-flex;align-items:center;gap:6px;font-size:12px;color:var(--on-surface-variant)}
.lg i{display:inline-block;width:10px;height:10px;border-radius:3px}
.kn:focus-visible rect:first-child{outline:2px solid var(--secondary);outline-offset:2px}
#detail .dt-head span{color:var(--on-surface-variant);font-size:13px;margin-left:8px}
#detail .dt-sum{font-size:12px;color:var(--on-surface-variant);margin:6px 0 10px}
#detail .dt-list{display:flex;flex-direction:column;gap:8px}
#detail .dt-list li{line-height:21px;font-size:13.5px}
#detail .prov{font-family:'JetBrains Mono',ui-monospace,monospace;font-size:11px;
  color:var(--secondary)}
"""
    return page(title="영향 지식그래프", active="graph.html",
                scenario="규제 변경의 전파 경로", status="검증된 산출물에서 조립",
                body=body, extra_script=script, extra_css=extra_css)
