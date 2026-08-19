"""검수표 공용 렌더 요소 — 추출 골드 검수표와 QA 골드 검수표가 같은 시각 언어를 쓴다.

두 검수표의 CSS를 각자 들고 있으면 반드시 어긋난다(마크다운/HTML 두 벌 규칙과 같은 이유).
여기 있는 것은 표현(스타일·이스케이프·인용 블록)뿐이고, 데이터 조립은 각 도구가 한다.
"""
from __future__ import annotations

import html as _html

FONTS_LINK = (
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2'
    '?family=Noto+Serif+KR:wght@500;700&family=Noto+Sans+KR:wght@400;500;700'
    '&family=JetBrains+Mono:wght@400;500&display=swap">'
)

REVIEW_CSS = """
:root {
  --ground:#fcf8ff; --panel:#ffffff; --panel-2:#f5f2ff; --line:#c4c6cf;
  --ink:#1a1a2e; --ink-2:#43474e; --navy:#022448; --action:#0051d5;
  --alarm:#ba1a1a; --alarm-bg:#ffdad6; --alarm-ink:#93000a;
  --pend:#edbf7f; --pend-bg:#fff4e2; --pend-ink:#60410c;
  --ok:#0051d5;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --ground:#12121c; --panel:#1b1b28; --panel-2:#222232; --line:#3a3a4d;
    --ink:#eceaf6; --ink-2:#a9adbe; --navy:#adc8f5; --action:#8fb2ff;
    --alarm:#ff8a80; --alarm-bg:#3d1512; --alarm-ink:#ffb4ab;
    --pend:#edbf7f; --pend-bg:#3a2c14; --pend-ink:#f0d3a3;
    --ok:#8fb2ff;
  }
}
:root[data-theme="dark"] {
  --ground:#12121c; --panel:#1b1b28; --panel-2:#222232; --line:#3a3a4d;
  --ink:#eceaf6; --ink-2:#a9adbe; --navy:#adc8f5; --action:#8fb2ff;
  --alarm:#ff8a80; --alarm-bg:#3d1512; --alarm-ink:#ffb4ab;
  --pend:#edbf7f; --pend-bg:#3a2c14; --pend-ink:#f0d3a3;
  --ok:#8fb2ff;
}
*,*::before,*::after { box-sizing:border-box; }
body {
  background:var(--ground); color:var(--ink); margin:0;
  font-family:'Noto Sans KR',system-ui,sans-serif; line-height:1.7;
  padding:clamp(20px,4vw,56px) clamp(16px,5vw,40px);
}
.wrap { max-width:920px; margin:0 auto; display:flex; flex-direction:column; gap:40px; }
h1,h2,h3 { font-family:'Noto Serif KR',Georgia,serif; text-wrap:balance; margin:0; }
h1 { font-size:clamp(28px,4.5vw,40px); letter-spacing:-.02em; color:var(--navy); }
h2 { font-size:22px; letter-spacing:-.01em; padding-bottom:10px; border-bottom:2px solid var(--navy); }
p { margin:0; }
.lede { color:var(--ink-2); max-width:62ch; }
.meta { display:flex; flex-wrap:wrap; gap:8px; font-family:'JetBrains Mono',monospace; font-size:12px; }
.meta span { background:var(--panel-2); border:1px solid var(--line); padding:3px 9px; border-radius:3px; color:var(--ink-2); }
section { display:flex; flex-direction:column; gap:18px; }

.conflict { background:var(--panel); border:1px solid var(--line); border-left:5px solid var(--alarm);
  border-radius:4px; padding:22px; display:flex; flex-direction:column; gap:16px; }
.conflict header { display:flex; flex-wrap:wrap; align-items:center; gap:8px; }
.id { font-family:'JetBrains Mono',monospace; font-size:13px; font-weight:500; color:var(--alarm-ink);
  background:var(--alarm-bg); padding:3px 9px; border-radius:3px; }
.tag { font-size:11px; letter-spacing:.06em; text-transform:uppercase; color:var(--ink-2);
  border:1px solid var(--line); padding:2px 8px; border-radius:99px; }
.tag.seal::before { content:"🔒 "; }
.ask { font-family:'Noto Serif KR',serif; font-size:17px; font-weight:500; }
.face-off { display:grid; grid-template-columns:1fr auto 1fr; gap:14px; align-items:stretch; }
@media (max-width:640px) { .face-off { grid-template-columns:1fr; } .versus { justify-self:start; } }
.side { padding:14px; border-radius:4px; background:var(--panel-2); border:1px solid var(--line); }
.side.gold { border-color:var(--pend); background:var(--pend-bg); }
.side.spec { border-color:var(--action); }
.side-label { display:block; font-size:11px; letter-spacing:.06em; text-transform:uppercase;
  color:var(--ink-2); margin-bottom:6px; }
.side.gold .side-label { color:var(--pend-ink); }
.side.spec .side-label { color:var(--action); }
.side p { font-size:14px; }
.versus { align-self:center; font-family:'JetBrains Mono',monospace; font-size:12px; color:var(--ink-2); }
.verdict { border:1px dashed var(--line); border-radius:4px; padding:12px 14px; margin:0;
  display:flex; flex-wrap:wrap; gap:14px; }
.verdict legend { font-size:11px; letter-spacing:.06em; text-transform:uppercase; color:var(--ink-2); padding:0 6px; }
.verdict label { display:flex; align-items:center; gap:7px; font-size:14px; cursor:pointer; }

.conflict.resolved { border-left-color:var(--ok); }
.id.ok { color:var(--panel); background:var(--ok); }
.tag.done { border-color:var(--ok); color:var(--ok); }
.why { font-size:13.5px; color:var(--ink-2); border-left:3px solid var(--ok); padding-left:12px; }
.q { margin:0; border-left:3px solid var(--line); padding-left:12px; }
.q figcaption { font-family:'JetBrains Mono',monospace; font-size:11px; color:var(--action); margin-bottom:3px; }
.q blockquote { margin:0; font-family:'JetBrains Mono',monospace; font-size:12.5px; line-height:1.65;
  color:var(--ink-2); word-break:keep-all; }

.note { background:var(--panel-2); border:1px solid var(--line); border-radius:4px; padding:18px;
  display:flex; flex-direction:column; gap:12px; }
.note pre { margin:0; overflow-x:auto; background:var(--panel); border:1px solid var(--line);
  border-radius:3px; padding:12px; font-family:'JetBrains Mono',monospace; font-size:12px; color:var(--ink-2); }

ol.items { list-style:none; margin:0; padding:0; display:flex; flex-direction:column; gap:2px; }
.item { display:flex; gap:14px; padding:14px 12px; border-bottom:1px solid var(--line); }
.item:has(.cb:checked) { background:var(--panel-2); }
.item.confirmed { border-left:3px solid var(--ok); }
.item:has(.cb:checked) .claim { color:var(--ink-2); text-decoration:line-through; }
.check { flex-shrink:0; padding-top:3px; cursor:pointer; }
.check input { position:absolute; opacity:0; width:0; height:0; }
.check span { display:block; width:20px; height:20px; border:2px solid var(--line); border-radius:3px; }
.check input:checked + span { background:var(--ok); border-color:var(--ok); }
.check input:checked + span::after { content:"✓"; display:block; color:var(--panel); font-size:14px;
  line-height:16px; text-align:center; }
.check input:focus-visible + span { outline:2px solid var(--action); outline-offset:2px; }
.body { display:flex; flex-direction:column; gap:7px; min-width:0; }
.head { display:flex; flex-wrap:wrap; align-items:baseline; gap:10px; }
.head code { font-family:'JetBrains Mono',monospace; font-size:12.5px; color:var(--navy);
  background:var(--panel-2); padding:2px 7px; border-radius:3px; }
.claim { font-weight:500; }
.kw { display:flex; flex-wrap:wrap; gap:5px; }
kbd { font-family:'JetBrains Mono',monospace; font-size:11px; color:var(--ink-2);
  border:1px solid var(--line); border-radius:3px; padding:1px 6px; }
.hits { font-family:'JetBrains Mono',monospace; font-size:11px; color:var(--action); }

.progress { position:fixed; bottom:18px; left:50%; transform:translateX(-50%); z-index:10;
  background:var(--navy); color:var(--ground); font-family:'JetBrains Mono',monospace; font-size:13px;
  padding:9px 18px; border-radius:99px; box-shadow:0 4px 16px rgba(0,0,0,.28); }
:root[data-theme="dark"] .progress, :root:not([data-theme="light"]) .progress { color:#12121c; }
footer { color:var(--ink-2); font-size:13px; border-top:1px solid var(--line); padding-top:16px; }
@media (prefers-reduced-motion:reduce) { * { transition:none !important; animation:none !important; } }
"""


def esc(x) -> str:
    return _html.escape(str(x), quote=True)


def quote_block(cits, limit: int = 220) -> str:
    """인용 목록 → <figure> 블록. dict(json)와 dataclass 양쪽을 받는다."""
    return "".join(
        f'<figure class="q"><figcaption>{esc(c["source_doc_id"] if isinstance(c, dict) else c.source_doc_id)}</figcaption>'
        f'<blockquote>{esc(" ".join((c["quote"] if isinstance(c, dict) else c.quote).split())[:limit])}</blockquote></figure>'
        for c in cits
    )
