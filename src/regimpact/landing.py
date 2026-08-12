"""포트폴리오 프론트도어(랜딩) 페이지 렌더러 — 자체완결 HTML.

시스템을 1분 안에 이해시키는 단일 진입점(index.html). 헤드라인 지표 타일 + 파이프라인 흐름 +
산출물 링크(임팩트 리포트·검증보고서·라이브파이어 증거) + Assurance/정직성 서사.

report.py와 동일하게 **모든 수치는 실제 파이프라인 출력에서 주입**된다(하드코딩·환각 불가).
이 모듈은 순수 렌더러이며, 값 계산은 생성기(examples/gen_index.py)가 담당한다(테스트 용이).
디자인: Institutional Navy, Noto Sans/JetBrains Mono, 라이트/다크.
"""
from __future__ import annotations

import html
from typing import Any

_PIPELINE = [
    ("공문", "PDF/HWP + sha256"),
    ("추출", "LLM structured"),
    ("인용검증", "grounding"),
    ("지역정규화", "→ code"),
    ("룰엔진", "전/후 2시점"),
    ("임팩트", "차등 매트릭스"),
    ("여력", "담보가격 밴드"),
    ("민감도", "가정 섭동"),
    ("룰변경안", "사람 확정 대조"),
    ("리포트", "감사 가능"),
]


def _esc(s: Any) -> str:
    return html.escape(str(s), quote=True)


def _tile(label: str, value: str, note: str, tone: str = "") -> str:
    return (
        f'<div class="tile {tone}"><div class="t-label">{_esc(label)}</div>'
        f'<div class="t-val">{value}</div><div class="t-note">{_esc(note)}</div></div>'
    )


def _card(a: dict[str, str]) -> str:
    tag = f'<span class="c-tag">{_esc(a["tag"])}</span>' if a.get("tag") else ""
    return (
        f'<a class="card" href="{_esc(a["href"])}">'
        f'<div class="c-head">{_esc(a["title"])}{tag}</div>'
        f'<div class="c-desc">{_esc(a["desc"])}</div>'
        f'<div class="c-go">열기 →</div></a>'
    )


def render_landing(m: dict[str, Any]) -> str:
    a = m["assurance"]
    imp = m["impact"]
    ex = m["exposure"]
    se = m["sensitivity"]
    pr = m["proposal"]
    b = m["build"]

    tiles = "".join([
        _tile("Citation 정확도", f"{a['citation']:.0%}", "인용 원문 실재", "good"),
        _tile("환각률", f"{a['unsupported']:.0%}", "근거 없는 주장", "good"),
        _tile("예외 재현율", f"{a['exception_recall']:.0%}", "핵심예외 0누락", "good"),
        _tile("룰-회귀", a["rule_regression"], "엔진↔독립 오라클", "good"),
        _tile("여력 감소율", f"{ex['pct_reduction']:.1%}",
              f"밴드 {se['band'][0]:.1%}–{se['band'][1]:.1%}"),
        _tile("사람검토 필요", f"{imp['review_weight_share']:.0%}", "명세여백 escalation", "warn"),
    ])

    steps = "".join(
        f'<div class="step"><div class="s-name">{_esc(n)}</div>'
        f'<div class="s-note">{_esc(note)}</div></div>'
        + ('<div class="arrow">→</div>' if i < len(_PIPELINE) - 1 else "")
        for i, (n, note) in enumerate(_PIPELINE)
    )

    cards = "".join(_card(c) for c in m["artifacts"])

    principles = "".join(f"<li>{_esc(p)}</li>" for p in m["principles"])

    regions = "、".join(m["regions"]) if m["regions"] else "—"

    return (
        '<!doctype html><html lang="ko"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<title>RegImpact AI — 규제 변경 영향분석·검증 시스템</title>'
        f"<style>{_CSS}</style></head><body>"
        # HERO
        '<header class="hero"><div class="inner">'
        '<div class="kicker">RegImpact AI · RegChange Impact & Assurance</div>'
        '<h1>규제 변경을, 검증 가능하게.</h1>'
        '<p class="lead">규제가 바뀌었을 때 <b>무엇을 고쳐야 하는지 AI가 초안</b>하고, '
        '그 초안이 틀리지 않았는지 <b>검증 가능한 방식으로 증명</b>하는 의사결정 지원 시스템. '
        '챗봇이 아니라, <b>사람이 확정한 결정적 룰엔진</b> 위에서 도는 Assurance 파이프라인.</p>'
        '<div class="badges">'
        f'<span class="badge">seed: {_esc(m["policy_id"])} (6·30)</span>'
        f'<span class="badge">대상지역 {_esc(regions)}</span>'
        f'<span class="badge">테스트 {_esc(b["tests"])} 통과</span>'
        '<span class="badge">런타임 의존성 0</span>'
        '</div></div></header>'
        '<main>'
        # METRICS
        '<section class="panel"><h2>한눈에 — 6·30 실측 지표</h2>'
        '<p class="sub">모든 값은 실제 파이프라인 출력에서 옵니다(하드코딩·환각 불가).</p>'
        f'<div class="tiles">{tiles}</div></section>'
        # PIPELINE
        '<section class="panel"><h2>무엇을 하는가 — 파이프라인</h2>'
        '<p class="sub">공문 한 건이 감사 가능한 영향분석·룰변경안으로 관통합니다.</p>'
        f'<div class="flow">{steps}</div></section>'
        # ARTIFACTS
        '<section class="panel"><h2>산출물 — 직접 열어보기</h2>'
        f'<div class="cards">{cards}</div></section>'
        # STORY
        '<section class="panel"><h2>왜 신뢰할 수 있는가 — Assurance 원칙</h2>'
        f'<ul class="principles">{principles}</ul>'
        '<div class="story-grid">'
        f'<div class="sbox"><div class="sb-k">가중 임팩트</div><div class="sb-v">강화 '
        f'{imp["tightened_share"]:.0%} · 유지 {imp["unchanged_share"]:.0%} · 검토 '
        f'{imp["review_share"]:.0%}</div><div class="sb-n">가중평균 Δ {imp["wmean_delta_pp"]:+.0f}pp</div></div>'
        f'<div class="sbox"><div class="sb-k">대출 여력</div><div class="sb-v">1인당 '
        f'{ex["per_unit_before"]:.2f}억 → {ex["per_unit_after"]:.2f}억</div>'
        f'<div class="sb-n">Δ {ex["per_unit_delta"]:+.2f}억 · 산정불가 {ex["undetermined_share"]:.0%}</div></div>'
        f'<div class="sbox"><div class="sb-k">견고성(민감도)</div><div class="sb-v">여력 축소 '
        f'{se["robust_shrink"]:.0%} 견고</div><div class="sb-n">강화 과반 {se["robust_tighten"]:.0%} 표본(가정 취약)</div></div>'
        f'<div class="sbox"><div class="sb-k">룰 변경안</div><div class="sb-v">반영 {pr["mapped"]} · '
        f'코어밖 {pr["oos"]} · 검토 {pr["review"]}</div><div class="sb-n">승인 {_esc(pr["status"])}'
        ' — 자동확정 없음</div></div>'
        + (f'<div class="sbox"><div class="sb-k">내규 영향도(모의)</div><div class="sb-v">수정필요 '
           f'{m["catalog"]["edits"]} · 무관 {m["catalog"]["unaffected"]}</div>'
           f'<div class="sb-n">규정 대장 매핑 — 과잉 플래그 없음</div></div>'
           if m.get("catalog") else "")
        + '</div></section>'
        '</main>'
        # FOOTER
        '<footer class="foot"><div class="inner">'
        '<p><b>정직성.</b> 변경 추출은 AI 초안이며, LTV 판정은 사람이 확정한 결정적 룰엔진 출력입니다. '
        '지표는 6·30 단일 정책 seed 기준으로 독립 3자 벤치마크가 아닙니다. 미확정 사실은 만들지 않습니다.</p>'
        f'<p class="prov">생성 {_esc(b["generated_on"])} · {_esc(b["system"])} '
        f'{_esc(b["version"])} · commit <code>{_esc(b["commit"])}</code> · '
        f'branch <code>{_esc(b["branch"])}</code></p>'
        '<p class="prov">재현: <code>python examples/gen_index.py</code> · '
        '전체: <code>python -m pytest &amp;&amp; python examples/gen_report.py</code></p>'
        '</div></footer></body></html>'
    )


_CSS = """
:root{
  --surface:#fcf8ff; --card:#ffffff; --container:#f5f2ff; --container-2:#efecff;
  --ink:#1a1a2e; --ink-soft:#43474e; --outline:#c4c6cf; --line:#e2e0fc;
  --primary:#022448; --secondary:#0051d5;
  --good:#2e6b4f; --good-bg:#cde6d8; --warn:#7a5300; --warn-bg:#ffddb2;
  --sans:"Noto Sans","Malgun Gothic",system-ui,-apple-system,"Segoe UI",sans-serif;
  --mono:"JetBrains Mono",ui-monospace,"SF Mono",Menlo,monospace;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --surface:#111421; --card:#1a1f30; --container:#171b2b; --container-2:#1c2133;
  --ink:#e9e9f4; --ink-soft:#b6bac6; --outline:#3a3f52; --line:#2a3047;
  --primary:#adc8f5; --secondary:#8ab0ff;
  --good:#8fd6ac; --good-bg:#123322; --warn:#edbf7f; --warn-bg:#33260f;
}}
:root[data-theme="dark"]{
  --surface:#111421; --card:#1a1f30; --container:#171b2b; --container-2:#1c2133;
  --ink:#e9e9f4; --ink-soft:#b6bac6; --outline:#3a3f52; --line:#2a3047;
  --primary:#adc8f5; --secondary:#8ab0ff;
  --good:#8fd6ac; --good-bg:#123322; --warn:#edbf7f; --warn-bg:#33260f;
}
*{box-sizing:border-box}
body{margin:0;background:var(--surface);color:var(--ink);font-family:var(--sans);
  line-height:1.65;font-size:15.5px;-webkit-font-smoothing:antialiased}
.hero{background:var(--primary);color:#fff}
:root[data-theme="dark"] .hero,:root:not([data-theme="light"]) .hero{color:#0b1220}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]) .hero{color:#0b1220}}
.hero .inner{max-width:960px;margin:0 auto;padding:52px 24px 46px}
.kicker{font-family:var(--mono);font-size:.74rem;letter-spacing:.14em;text-transform:uppercase;opacity:.72}
.hero h1{margin:14px 0 0;font-size:clamp(2rem,1.4rem+3vw,3.1rem);font-weight:780;letter-spacing:-.03em;line-height:1.08}
.lead{margin:16px 0 0;font-size:1.02rem;max-width:64ch;opacity:.92}
.lead b{font-weight:720}
.badges{margin-top:22px;display:flex;flex-wrap:wrap;gap:9px}
.badge{font-family:var(--mono);font-size:.72rem;padding:5px 11px;border-radius:20px;
  background:rgba(255,255,255,.14);border:1px solid rgba(255,255,255,.22)}
:root:not([data-theme="light"]) .badge{background:rgba(0,0,0,.10);border-color:rgba(0,0,0,.16)}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]) .badge{background:rgba(0,0,0,.10);border-color:rgba(0,0,0,.16)}}
main{max-width:960px;margin:0 auto;padding:28px 24px}
.panel{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:24px;margin-bottom:20px}
.panel h2{margin:0;font-size:1.22rem;font-weight:700;letter-spacing:-.01em}
.sub{margin:6px 0 18px;color:var(--ink-soft);font-size:.86rem}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:13px}
.tile{background:var(--container);border:1px solid var(--line);border-radius:13px;padding:16px 17px}
.t-label{font-size:.78rem;color:var(--ink-soft)}
.t-val{font-family:var(--mono);font-weight:780;font-size:1.7rem;margin-top:6px;letter-spacing:-.02em}
.tile.good .t-val{color:var(--good)} .tile.warn .t-val{color:var(--warn)}
.t-note{font-size:.72rem;color:var(--ink-soft);opacity:.82;margin-top:4px}
.flow{display:flex;flex-wrap:wrap;align-items:stretch;gap:8px}
.step{background:var(--container);border:1px solid var(--line);border-radius:11px;padding:10px 13px;min-width:96px;flex:1}
.s-name{font-weight:660;font-size:.9rem}
.s-note{font-family:var(--mono);font-size:.66rem;color:var(--ink-soft);margin-top:3px}
.arrow{display:flex;align-items:center;color:var(--outline);font-weight:700;font-family:var(--mono)}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px}
.card{display:flex;flex-direction:column;text-decoration:none;color:inherit;
  background:var(--container);border:1px solid var(--line);border-radius:13px;padding:18px;transition:.15s}
.card:hover{border-color:var(--secondary);transform:translateY(-2px)}
.c-head{font-weight:700;font-size:1rem;display:flex;align-items:center;gap:9px;flex-wrap:wrap}
.c-tag{font-family:var(--mono);font-size:.6rem;font-weight:700;letter-spacing:.05em;padding:3px 8px;
  border-radius:6px;background:var(--container-2);color:var(--secondary)}
.c-desc{color:var(--ink-soft);font-size:.85rem;margin:8px 0 14px;flex:1}
.c-go{font-family:var(--mono);font-size:.78rem;color:var(--secondary);font-weight:660}
.principles{margin:0 0 18px;padding-left:20px;color:var(--ink-soft);font-size:.9rem}
.principles li{margin:6px 0}
.story-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:13px}
.sbox{background:var(--container);border:1px solid var(--line);border-radius:12px;padding:15px}
.sb-k{font-size:.74rem;color:var(--ink-soft);text-transform:uppercase;letter-spacing:.04em;font-family:var(--mono)}
.sb-v{font-weight:700;font-size:1.02rem;margin-top:6px}
.sb-n{font-size:.76rem;color:var(--ink-soft);margin-top:4px}
.foot{border-top:1px solid var(--line);margin-top:10px}
.foot .inner{max-width:960px;margin:0 auto;padding:22px 24px 44px;color:var(--ink-soft);font-size:.8rem}
.foot b{color:var(--ink)} .foot code{font-family:var(--mono);font-size:.94em;background:var(--container-2);padding:1px 6px;border-radius:5px}
.prov{font-size:.72rem;opacity:.85;margin:8px 0 0}
"""
