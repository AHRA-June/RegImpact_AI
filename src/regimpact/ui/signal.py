"""내 한도 시그널 — 고객용 개인화 시뮬레이터 (Tomorrow Challenge 제안 화면).

지원서(APPLY_TOMORROW_CHALLENGE)의 4단 콘텐츠를 한 화면에 담는다:
  ① 영향 알림(시뮬레이션) → ② 변경 전/후 한도 비교 → ③ 경과규정 체크 → ④ 근거 우선 Q&A.

기존 사이트(검증·포트폴리오, B2B 시선)와 성격이 달라 **별도의 고객용 화면**으로 둔다.
금융앱 웹뷰 탑재형이므로 모바일 우선이고, 데스크톱에서는 폰 프레임 안에 담아
"웹뷰에 이렇게 실린다"를 그대로 보여준다.

원칙은 본편과 같다 — 시연 화면이라고 예외가 아니다:
  - 판정은 검증된 JS 엔진 포팅본(플레이그라운드와 동일). 별도 데모 로직을 두지 않는다.
  - 근거 인용은 전부 추출 파이프라인이 원문 대조를 통과한 verbatim 인용에서 온다.
  - Q&A 는 RAG 의 검색 절반(BM25 포팅본·시점 필터)까지만 — 답변 문장 생성(LLM 연결)은
    PoC 배선 목표라고 화면에 그대로 적는다. 근거를 못 찾으면 지어내지 않고 상담을 안내한다.
  - 한도 = 주택가격 × LTV (코어 판정). DSR·가격구간별 최대한도 등 부가 규제는
    미반영임을 명시한다.

⚠️ 신한·슈퍼SOL 의 로고·UI 를 흉내 내지 않는다 — 제품 자체 아이덴티티로 만들고,
"금융앱 웹뷰 탑재형 제안"이라는 맥락만 텍스트로 밝힌다 (실 브랜드 사칭 금지).
"""
from __future__ import annotations

import json
import re
from datetime import date, timedelta
from pathlib import Path

from ..extractor.sources import SOURCE_FILES, load_corpus
from ..report.evidence import ValidationEvidence
from ..retrieval import BM25Index, chunk_sources
from .intake import load_snapshots
from .theme import CSS, FONTS, esc, explainer

ENGINE_JS = Path(__file__).resolve().parent / "static" / "engine.js"
SEARCH_JS = Path(__file__).resolve().parent / "static" / "search.js"
AFFORD_JS = Path(__file__).resolve().parent / "static" / "affordability.js"

_SIGNAL_CSS = """
html{scroll-behavior:smooth}
body.sg{margin:0;background:var(--surface-container-low);color:var(--on-surface)}
.dlink{color:inherit;font-weight:700;text-decoration:underline;text-underline-offset:2px}
.dock{display:flex;justify-content:center;align-items:flex-start;gap:44px;
  padding:0;min-height:100vh}
.pitch{display:none}
@media(min-width:1020px){
  .dock{padding:48px 24px}
  .pitch{display:block;width:380px;position:sticky;top:48px}
  .phone{border:1px solid var(--outline-variant);border-radius:28px;
    box-shadow:0 24px 60px rgba(15,23,42,.14);overflow:hidden}
}
.pitch .kicker{font-family:'JetBrains Mono',ui-monospace,monospace;font-size:11px;
  letter-spacing:.09em;text-transform:uppercase;color:var(--primary);font-weight:600}
.pitch h1{font-size:30px;line-height:1.2;letter-spacing:-.02em;margin:12px 0 12px;word-break:keep-all}
.pitch .lede{font-size:14.5px;line-height:1.6;color:var(--on-surface-variant);word-break:keep-all}
.pitch ul{margin:18px 0 0;padding:0;list-style:none;display:flex;flex-direction:column;gap:9px}
.pitch li{font-size:13px;line-height:1.5;color:var(--on-surface-variant);display:flex;gap:8px}
.pitch li b{color:var(--on-surface)}
.pitch .vbadge{margin-top:20px;padding:12px 14px;border:1px solid var(--outline-variant);
  border-radius:10px;background:var(--surface-container-lowest);font-size:12.5px;line-height:1.55;
  color:var(--on-surface-variant)}
.pitch .links{margin-top:14px;display:flex;flex-wrap:wrap;gap:8px}
.pitch .links a{font-size:12px;color:var(--primary);text-decoration:none;
  border:1px solid var(--outline-variant);border-radius:99px;padding:5px 11px}
/* ---- 폰(앱 컬럼) ---- */
.phone{width:100%;max-width:430px;background:var(--background);min-height:100vh;
  display:flex;flex-direction:column}
@media(min-width:1020px){.phone{min-height:0;max-height:calc(100vh - 96px);overflow-y:auto}}
.appbar{position:sticky;top:0;z-index:3;display:flex;align-items:center;gap:10px;
  padding:14px 18px;background:color-mix(in srgb,var(--background) 92%,transparent);
  backdrop-filter:blur(6px);border-bottom:1px solid var(--outline-variant)}
.appbar .logo{width:28px;height:28px;border-radius:8px;background:var(--primary);
  color:#fff;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:14px}
.appbar .t{font-size:15px;font-weight:700}
.appbar .s{font-size:11px;color:var(--on-surface-variant)}
.body{padding:16px 16px 40px;display:flex;flex-direction:column;gap:14px}
.sec-t{font-size:12px;font-weight:700;letter-spacing:.05em;color:var(--on-surface-variant);
  text-transform:uppercase;margin:8px 2px 0}
/* 알림 카드 */
.push{border:1px solid var(--outline-variant);border-radius:14px;overflow:hidden;
  background:var(--surface-container-lowest)}
.push .head{display:flex;align-items:center;gap:8px;padding:10px 14px;font-size:11px;
  color:var(--on-surface-variant);border-bottom:1px solid var(--outline-variant)}
.push .dot{width:7px;height:7px;border-radius:99px;background:var(--error)}
.push .bd{padding:13px 14px;font-size:13.5px;line-height:1.5;word-break:keep-all}
.push .bd b{display:block;font-size:14px;margin-bottom:3px}
/* 입력 */
.panel{background:var(--surface-container-lowest);border:1px solid var(--outline-variant);
  border-radius:14px;padding:16px}
.f{margin-bottom:12px}
.f:last-child{margin-bottom:0}
.f label{display:block;font-size:12px;color:var(--on-surface-variant);margin-bottom:5px}
.f select,.f input[type=date],.f input[type=number]{width:100%;padding:10px 11px;font-size:14px;
  font-family:inherit;border:1px solid var(--outline-variant);border-radius:9px;
  background:var(--background);color:var(--on-surface);box-sizing:border-box}
.seg{display:grid;grid-template-columns:repeat(4,1fr);gap:6px}
.seg button{padding:9px 4px;font-size:12px;font-family:inherit;border:1px solid var(--outline-variant);
  border-radius:9px;background:var(--background);color:var(--on-surface-variant);cursor:pointer;
  word-break:keep-all}
.seg button.on{border-color:var(--primary);color:var(--primary);font-weight:700;
  box-shadow:0 0 0 1px var(--primary) inset}
.chk{display:flex;align-items:flex-start;gap:9px;font-size:13.5px;margin-bottom:9px;cursor:pointer}
.chk small{display:block;color:var(--on-surface-variant);font-size:11px;line-height:15px}
.gfbox{border-top:1px dashed var(--outline-variant);margin-top:13px;padding-top:13px;
  scroll-margin-top:74px}  /* 앵커 점프 시 고정 헤더에 가리지 않게 */
.gfbox .hint{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px}
.gfbox .hint button{padding:5px 10px;font-size:11.5px;border-radius:99px;font-family:inherit;
  border:1px solid var(--outline-variant);background:transparent;color:var(--on-surface-variant);cursor:pointer}
.gfbox .hint button:hover{border-color:var(--primary);color:var(--primary)}
/* 결과 */
.cmp{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.vc{border:1px solid var(--outline-variant);border-radius:14px;padding:14px;
  background:var(--surface-container-lowest)}
.vc .when{font-size:11px;color:var(--on-surface-variant);
  font-family:'JetBrains Mono',ui-monospace,monospace}
.vc .ltv{font-family:'JetBrains Mono',ui-monospace,monospace;font-size:30px;font-weight:700;
  margin-top:8px;line-height:1}
.vc .amt{font-size:13px;margin-top:7px;font-weight:600}
.vc .why{font-size:11px;color:var(--on-surface-variant);margin-top:6px;line-height:1.45;word-break:keep-all}
.vc.after{border-color:var(--primary)}
.vc .ltv.zero{color:var(--error)}
.vc .ltv.review{font-size:16px;line-height:1.3;color:var(--on-tertiary-fixed-variant);word-break:keep-all}
.delta{border-radius:12px;padding:12px 14px;font-size:13.5px;line-height:1.5;word-break:keep-all}
.delta.bad{background:color-mix(in srgb,var(--error) 9%,var(--surface-container-lowest));
  border:1px solid color-mix(in srgb,var(--error) 35%,transparent)}
.delta.good{background:var(--surface-container-low);border:1px solid var(--outline-variant)}
.delta b{font-weight:700}
.gfbadge{display:inline-block;padding:3px 9px;border-radius:99px;font-size:11px;font-weight:700;
  background:var(--primary-fixed,#dbe1ff);color:var(--on-primary-fixed,#00174b);margin-right:6px}
/* 총 가능금액(참고 추정) — 한도 4개를 나란히, binding 규제를 짚는다 */
.aff-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.aff-total{margin-top:13px;padding:13px 14px;border-radius:12px;border:1px solid var(--primary);
  background:color-mix(in srgb,var(--primary) 5%,var(--surface-container-lowest));
  word-break:keep-all}
.aff-total .amt{font-family:'JetBrains Mono',ui-monospace,monospace;font-size:26px;
  font-weight:700;line-height:1.15}
.aff-total .bind{font-size:12.5px;margin-top:5px;line-height:1.5}
.aff-total .bind b{color:var(--error)}
.aff-rows{margin-top:11px;display:flex;flex-direction:column;gap:8px}
.aff-r{font-size:12px}
.aff-r .hd{display:flex;justify-content:space-between;gap:8px;margin-bottom:3px}
.aff-r .nm{color:var(--on-surface-variant)}
.aff-r .vv{font-family:'JetBrains Mono',ui-monospace,monospace;font-weight:600}
.aff-r .bar{height:7px;border-radius:99px;background:var(--surface-container-highest);
  overflow:hidden}
.aff-r .bar i{display:block;height:100%;border-radius:99px;background:var(--primary);opacity:.55}
.aff-r.bind .bar i{background:var(--error);opacity:.85}
.aff-r.bind .nm,.aff-r.bind .vv{color:var(--error);font-weight:700}
.aff-r.na .vv{color:var(--on-surface-variant);font-weight:400;font-size:11px}
.aff-r .rt{font-size:11px;color:var(--on-surface-variant);margin-top:3px;
  font-family:'JetBrains Mono',ui-monospace,monospace}
.aff-r.bind .rt{color:var(--error)}
/* 규정 한도 대비 내 비율 — "한도 40%인데 당신은 58%" */
.gauge{margin-top:10px;border:1px solid var(--outline-variant);border-radius:10px;
  padding:12px 14px;background:var(--surface-container-lowest)}
.gauge .g-t{font-size:12px;color:var(--on-surface-variant);margin-bottom:10px;
  word-break:keep-all;line-height:1.5}
.g-row{margin-bottom:11px}
.g-row:last-child{margin-bottom:0}
.g-hd{display:flex;justify-content:space-between;gap:10px;font-size:12.5px;margin-bottom:4px}
.g-hd .gn{color:var(--on-surface-variant)}
.g-hd .gv{font-family:'JetBrains Mono',ui-monospace,monospace;font-weight:700}
.g-bar{position:relative;height:9px;background:var(--surface-container-highest);
  border-radius:99px;overflow:visible}
.g-bar i{display:block;height:100%;border-radius:99px;background:var(--secondary);opacity:.7}
.g-bar .lim{position:absolute;top:-3px;bottom:-3px;width:2px;background:var(--on-surface)}
.g-row.over .g-bar i{background:var(--error);opacity:.9}
.g-row.over .gv{color:var(--error)}
.g-note{font-size:11.5px;color:var(--on-surface-variant);margin-top:4px;line-height:1.5;
  word-break:keep-all}
.g-row.over .g-note b{color:var(--error)}
/* 내게 가능한 상품 찾기 — 추천이 아니라 자격 판정 */
.pr{display:flex;flex-direction:column;gap:8px;margin-top:10px}
.pr-i{border:1px solid var(--outline-variant);border-radius:10px;padding:12px 14px;
  background:var(--surface-container-lowest)}
.pr-i .top{display:flex;align-items:baseline;gap:8px;justify-content:space-between}
.pr-i .nm{font-size:13.5px;font-weight:700;word-break:keep-all}
.pr-i .st{font-size:10.5px;font-weight:700;padding:3px 9px;border-radius:99px;flex:none;
  font-family:'JetBrains Mono',ui-monospace,monospace}
.pr-i.ok{border-color:var(--secondary)}
.pr-i.ok .st{background:var(--surface-container-low);color:var(--secondary)}
.pr-i.no .st{background:var(--surface-container-low);color:var(--error)}
.pr-i.un .st{background:var(--surface-container-low);color:var(--on-surface-variant)}
.pr-i .rs{font-size:12.5px;color:var(--on-surface-variant);margin-top:6px;line-height:1.55;
  word-break:keep-all}
/* 목표 역산 — 진단(무엇에 막혔나)에서 행동(그래서 얼마)으로 잇는 다리 */
.goal-row{display:flex; gap:8px; align-items:flex-end; flex-wrap:wrap; margin-top:4px}
.goal-row .f{flex:1; min-width:150px; margin-bottom:0}
.goal-row button{padding:10px 16px; font-family:inherit; font-size:13px; font-weight:700;
  border-radius:9px; border:1px solid var(--primary); background:var(--primary); color:#fff;
  cursor:pointer; white-space:nowrap}
.rx{margin-top:12px; display:flex; flex-direction:column; gap:9px}
.rx-hd{font-size:13.5px; line-height:1.55; word-break:keep-all; padding:12px 14px;
  border-radius:10px; background:var(--surface-container-low);
  border:1px solid var(--outline-variant)}
.rx-hd.ok{border-color:var(--secondary)}
.rx-hd b{color:var(--error)}
.rx-hd.ok b{color:var(--secondary)}
.rx-item{border:1px solid var(--outline-variant); border-radius:10px; padding:12px 14px;
  background:var(--surface-container-lowest)}
.rx-item .lb{font-size:11px; font-family:'JetBrains Mono',ui-monospace,monospace;
  color:var(--primary); font-weight:700; letter-spacing:.04em}
.rx-item .ways{margin-top:8px; display:flex; flex-direction:column; gap:7px}
.rx-item .way{font-size:13px; line-height:1.55; word-break:keep-all; display:flex; gap:8px}
.rx-item .way b{font-family:'JetBrains Mono',ui-monospace,monospace; color:var(--on-surface)}
.rx-item .way .mk{color:var(--secondary); flex:none; font-weight:700}
.rx-item .no{font-size:12.5px; color:var(--on-surface-variant); line-height:1.55;
  word-break:keep-all}
/* 한도 타임라인 — '시그널'이 규제일에만 쓰는 도구가 아님을 보여준다 */
.tl{margin-top:12px; border-left:2px solid var(--outline-variant); padding-left:16px;
  display:flex; flex-direction:column; gap:14px}
.tl .ev{position:relative}
.tl .ev::before{content:""; position:absolute; left:-21px; top:5px; width:8px; height:8px;
  border-radius:99px; background:var(--outline-variant); border:2px solid var(--background)}
.tl .ev.hit::before{background:var(--error)}
.tl .dt{font-family:'JetBrains Mono',ui-monospace,monospace; font-size:11px;
  color:var(--on-surface-variant)}
.tl .ti{font-size:13.5px; font-weight:700; margin-top:2px; word-break:keep-all}
.tl .ds{font-size:12px; color:var(--on-surface-variant); margin-top:3px; line-height:1.5;
  word-break:keep-all}
.tl .ev.hit .ti{color:var(--error)}
.sub-cta{margin-top:12px; padding:13px 15px; border-radius:10px; border:1px dashed var(--primary);
  font-size:13px; line-height:1.6; word-break:keep-all; color:var(--on-surface-variant)}
.sub-cta b{color:var(--on-surface)}
/* 두 사람 비교 — 계산기가 구조적으로 답 못 하는 질문을 10초 안에 보여준다 */
.duo-wrap{padding:12px 14px}
.duo{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.pc{border:1px solid var(--outline-variant);border-radius:12px;padding:12px;
  background:var(--surface-container-low)}
.pc .who{font-size:12px;font-weight:700;word-break:keep-all}
.pc .cond{font-size:11px;color:var(--on-surface-variant);margin-top:3px;line-height:1.45;
  word-break:keep-all}
.pc .ltv{font-family:'JetBrains Mono',ui-monospace,monospace;font-size:24px;font-weight:700;
  margin-top:8px}
.pc .ltv.zero{color:var(--error)}
.pc .ltv.review{font-size:14px;color:var(--on-tertiary-fixed-variant)}
.pc .amt{font-size:12.5px;font-weight:600;margin-top:4px}
.duo-note{margin-top:11px;font-size:12.5px;line-height:1.55;word-break:keep-all;
  padding:10px 12px;border-radius:10px;background:var(--surface-container-low);
  border:1px solid var(--outline-variant)}
.duo-note b{color:var(--on-surface)}
/* 피치 패널 비교표 */
.cmp-t{width:100%;border-collapse:collapse;margin-top:18px;font-size:11.5px;line-height:1.45}
.cmp-t caption{text-align:left;font-size:12px;font-weight:700;padding-bottom:7px;
  color:var(--on-surface)}
.cmp-t th,.cmp-t td{border:1px solid var(--outline-variant);padding:7px 8px;text-align:left;
  vertical-align:top;word-break:keep-all}
.cmp-t th{background:var(--surface-container-low);font-weight:700;font-size:11px}
.cmp-t td:first-child{color:var(--on-surface-variant);white-space:nowrap;font-size:11px}
.cmp-t td:last-child{background:color-mix(in srgb,var(--primary) 5%,var(--surface-container-lowest))}
details.more{border:1px solid var(--outline-variant);border-radius:12px;
  background:var(--surface-container-lowest)}
details.more summary{padding:11px 14px;font-size:13px;cursor:pointer;color:var(--on-surface-variant)}
details.more[open] summary{border-bottom:1px solid var(--outline-variant)}
.trace{max-height:280px;overflow-y:auto}
.trace .row{display:grid;grid-template-columns:40px 1fr;gap:8px;padding:8px 13px;
  border-bottom:1px solid var(--outline-variant);font-size:12px;line-height:17px}
.trace .row:last-child{border-bottom:0}
.trace .row.hit{background:var(--surface-container-low)}
.trace .id{font-family:'JetBrains Mono',ui-monospace,monospace;font-size:10.5px;font-weight:700;
  color:var(--primary)}
.trace .row:not(.hit) .id{color:var(--outline)}
.trace .n2{color:var(--on-surface-variant);font-size:11px}
.evi{padding:12px 14px;display:flex;flex-direction:column;gap:10px}
.q-cite{border-left:3px solid var(--primary);padding:8px 12px;background:var(--surface-container-low);
  border-radius:0 8px 8px 0;font-size:12.5px;line-height:1.55}
.q-cite .src{display:block;margin-top:5px;font-size:10.5px;color:var(--on-surface-variant);
  font-family:'JetBrains Mono',ui-monospace,monospace}
/* Q&A */
.qa input[type=text]{width:100%;padding:11px 12px;font-size:14px;font-family:inherit;
  border:1px solid var(--outline-variant);border-radius:10px;background:var(--background);
  color:var(--on-surface);box-sizing:border-box}
.qa .preset{display:flex;gap:6px;flex-wrap:wrap;margin-top:9px}
.qa .preset button{padding:6px 11px;font-size:11.5px;border-radius:99px;font-family:inherit;
  border:1px solid var(--outline-variant);background:transparent;color:var(--on-surface-variant);
  cursor:pointer;word-break:keep-all;text-align:left}
.qa .preset button:hover{border-color:var(--primary);color:var(--primary)}
.qa .hits{margin-top:12px;display:flex;flex-direction:column;gap:9px}
.hit-c{border:1px solid var(--outline-variant);border-radius:12px;padding:11px 13px;
  background:var(--surface-container-lowest);width:100%;text-align:left;font-family:inherit;
  cursor:pointer;display:block;box-sizing:border-box}
.hit-c:hover{border-color:var(--primary)}
.hit-c .meta{font-size:10.5px;color:var(--primary);
  font-family:'JetBrains Mono',ui-monospace,monospace;margin-bottom:6px}
.hit-c .tx{font-size:12.5px;line-height:1.6;color:var(--on-surface);word-break:keep-all;
  display:-webkit-box;-webkit-line-clamp:4;-webkit-box-orient:vertical;overflow:hidden}
.hit-c .open{display:block;margin-top:7px;font-size:11px;color:var(--primary);font-weight:600}
/* 쉬운 요약 */
.easy{border:1px solid var(--primary);border-radius:12px;padding:13px 14px;
  background:color-mix(in srgb,var(--primary) 5%,var(--surface-container-lowest))}
.easy-tag{display:inline-block;font-size:10.5px;font-weight:700;letter-spacing:.03em;
  padding:3px 9px;border-radius:99px;background:var(--primary);color:#fff;margin-bottom:9px}
.easy-tx{font-size:13.5px;line-height:1.65;word-break:keep-all}
.easy .q-cite{margin-top:10px}
.src-t{font-size:11px;font-weight:700;color:var(--on-surface-variant);margin:12px 0 -2px;
  letter-spacing:.04em}
.xtra{margin-top:11px}
.xtra summary{font-size:12px;color:var(--on-surface-variant)}
.xtra-b{padding:11px 12px;display:flex;flex-direction:column;gap:9px}
/* 답을 못 찾았을 때도 원문은 읽게 해준다 — 아무것도 안 보여주는 건 도리가 아니다 */
.docrow{margin-top:13px;padding-top:12px;border-top:1px dashed var(--outline-variant)}
.docrow .src-t{margin:0 0 8px}
.dbtn{display:block;width:100%;box-sizing:border-box;text-align:left;padding:11px 12px;
  margin-bottom:7px;border:1px solid var(--outline-variant);border-radius:10px;
  background:var(--surface-container-lowest);color:var(--on-surface);font-family:inherit;
  font-size:12.5px;cursor:pointer;word-break:keep-all}
.dbtn:hover{border-color:var(--primary)}
.dbtn small{display:block;color:var(--on-surface-variant);font-size:10.5px;margin-top:3px}
.q-cite.qbtn{cursor:pointer;width:100%;text-align:left;font-family:inherit;display:block;
  box-sizing:border-box;border-top:none;border-right:none;border-bottom:none}
.q-cite.qbtn:hover{background:var(--surface-container-high)}
/* 원문 전체 모달 */
#modal{position:fixed;inset:0;z-index:20;background:rgba(15,23,42,.45);display:flex;
  align-items:center;justify-content:center;padding:18px}
#modal[hidden]{display:none}
.m-box{background:var(--background);border-radius:16px;max-width:660px;width:100%;
  max-height:84vh;display:flex;flex-direction:column;overflow:hidden;
  box-shadow:0 24px 70px rgba(0,0,0,.3)}
.m-head{display:flex;align-items:center;gap:10px;padding:13px 16px;
  border-bottom:1px solid var(--outline-variant)}
.m-head .mt{font-size:13px;font-weight:700;word-break:keep-all}
.m-head .ms{font-size:10.5px;color:var(--on-surface-variant)}
.m-head button{margin-left:auto;border:1px solid var(--outline-variant);background:transparent;
  color:var(--on-surface);border-radius:99px;width:30px;height:30px;cursor:pointer;flex:none}
.m-body{padding:16px;overflow-y:auto;font-size:12.5px;line-height:1.72;color:var(--on-surface);
  word-break:keep-all;overflow-wrap:anywhere;white-space:pre-wrap}
.m-body mark{background:color-mix(in srgb,var(--primary) 24%,transparent);
  color:var(--on-surface);padding:1px 2px;border-radius:3px;
  box-decoration-break:clone;-webkit-box-decoration-break:clone;
  box-shadow:0 0 0 1px color-mix(in srgb,var(--primary) 30%,transparent)}
.m-body .pg{display:block;margin:16px 0 9px;padding-top:9px;
  border-top:1px dashed var(--outline-variant);font-size:10.5px;
  color:var(--on-surface-variant);font-family:'JetBrains Mono',ui-monospace,monospace}
.m-note{padding:9px 16px;border-top:1px solid var(--outline-variant);font-size:10.5px;
  color:var(--on-surface-variant)}
.consult{border:1px solid var(--outline-variant);border-radius:12px;padding:14px;
  background:var(--surface-container-low);font-size:13px;line-height:1.55;word-break:keep-all}
.honesty{font-size:11.5px;line-height:1.55;color:var(--on-surface-variant);
  padding:10px 12px;border-left:3px solid var(--outline-variant);word-break:keep-all}
/* 푸터 */
.foot{font-size:11px;line-height:1.6;color:var(--on-surface-variant);padding:0 4px;word-break:keep-all}
.foot a{color:var(--primary)}
.mnote{font-size:11px;color:var(--on-surface-variant);text-align:center;padding:4px 0 0}
@media(min-width:1020px){.mnote{display:none}}
"""

_RULE_KO = {
    "REG_STD": "규제지역 · 무주택 표준",
    "REG_FIRSTHOME": "생애최초 예외 — 강화 대상 아님",
    "REG_REALDEMAND": "서민·실수요 예외",
    "REG_OWNER_0": "규제지역 · 유주택(비처분)",
    "MULTI_0": "수도권 다주택",
    "NONREG_STD_70": "비규제 기준선",
}

# 판정 근거 인용 매핑 — 규칙별로 어떤 원문 문장을 보여줄지. 인용 자체는 아래
# `_rule_quotes` 가 추출 결과(원문 대조 75/75 통과)에서 verbatim 으로 뽑는다.
# 담당자 연락처 블록 — "담당부서 … 과 장 홍길동(02-…)" 나열. 다음 페이지 마커나 참고
# 자료 제목에서 끝난다. 개별 "이름(전화)" 표기도 본문 중간에 남는다.
_CONTACT_BLOCK = re.compile(r"담당\s*부서.*?(?=-{3,}\s*p\d+|참고\s*\d|$)", re.S)
_CONTACT_NAME = re.compile(r"[가-힣]{2,4}\s*\(0\d{1,2}-\d{3,4}-\d{4}\)")
_PAGE_MARK = re.compile(r"-{3,}\s*p\d+\s*-{3,}|(?<=\s)-\s*\d{1,3}\s*-(?=\s)")
# 목차 줄 — "1-1. 질문? ······ 3" 처럼 점선 리더가 붙는다
_TOC_LINE = re.compile(r"[·․‧∙・]{3,}\s*\d*")


def customer_text(raw: str) -> str:
    """고객 화면 검색 색인용 본문 — 답변 재료가 아닌 부속을 걷어낸다.

    걷어내는 것: 담당자 연락처 블록(실명·전화), 페이지 마커, 목차의 점선 리더.
    **문장 자체는 손대지 않는다** — 남은 텍스트는 전부 원문 verbatim 이고, 모달의
    '공문 전체 보기'는 이 정제본이 아니라 원문을 보여준다.

    청크를 통째로 버리지 않는 이유: MOLIT p3 참고1(비규제 70%/유주택 60% — 고객이
    가장 많이 묻는 값)이 바로 앞 페이지 연락처 꼬리와 한 청크에 묶여 있어서, 청크 단위로
    거르면 핵심 답변 재료가 함께 사라진다(2026-08-19 실측으로 확인).
    """
    t = _CONTACT_BLOCK.sub(" ", raw)
    t = _CONTACT_NAME.sub(" ", t)
    t = _PAGE_MARK.sub(" ", t)
    t = _TOC_LINE.sub(" ", t)
    return re.sub(r"\s+", " ", t).strip()

_QUOTE_PATTERNS = {
    "REG_STD": r"비규제지역70% → 규제지역40%",
    "NONREG_STD_70": r"비규제지역70% → 규제지역40%",
    "REG_FIRSTHOME": r"생애최초 주택구입, 정책모기지 등은 완화된 LTV",
    "REG_REALDEMAND": r"서민·실수요자 주담대",
    "MULTI_0": r"다주택자는 수도권 內 주택구입시",
    "REG_OWNER_0": r"유주택 0%",
    "_GF": r"종전 규정이 그대로",
}


def _rule_quotes(extraction) -> dict:
    """추출 파이프라인의 grounded 인용에서 규칙별 근거 문장을 뽑는다 — 손으로 옮겨 적지 않는다."""
    out: dict[str, dict] = {}
    for key, pattern in _QUOTE_PATTERNS.items():
        for c in extraction.changes:
            q = re.sub(r"\s+", " ", c.citation.quote).strip()
            if re.search(pattern, q):
                out[key] = {"quote": q, "doc": c.citation.source_doc_id}
                break
        if key not in out:
            raise ValueError(f"근거 인용을 찾지 못함: {key} — 추출 결과가 바뀌었으면 패턴을 갱신하라")
    return out


def _corpus_cut(norm_corpus: dict, doc: str, anchor: str, length: int = 150,
                *, nth: int | None = None) -> dict:
    """코퍼스 원문에서 anchor 로 시작하는 구간을 그대로 잘라 온다(verbatim 보장).

    author_goldset.q 와 같은 규율 — 손으로 옮겨 적으면 반드시 어긋난다. 앵커가 여러 번
    나오면 **실패한다**: 목차와 본문에 같은 문장이 있는데 그냥 첫 것을 집으면 목차 줄
    (점선 리더·쪽번호·깨진 글리프)이 근거로 실린다(2026-08-20 폰 리뷰에서 실제로 발생).
    반복이 의도된 경우에만 nth 로 어느 것인지 명시한다.
    """
    text = norm_corpus[doc]
    needle = re.sub(r"\s+", " ", anchor).strip()
    hits = [m.start() for m in re.finditer(re.escape(needle), text)]
    if not hits:
        raise ValueError(f"[{doc}] anchor 없음: {anchor!r}")
    if len(hits) > 1 and nth is None:
        raise ValueError(
            f"[{doc}] anchor 모호 — {len(hits)}회 등장(목차·본문 중 어느 것인지 nth 로 명시): "
            f"{anchor!r}")
    i = hits[0 if nth is None else nth]
    return {"quote": text[i:i + max(length, len(anchor))].strip(), "doc": doc}


def build_customer_index(corpus: dict | None = None) -> BM25Index:
    """고객 화면 검색 색인 — 6·30 문서를 `customer_text` 로 정제해 색인한다.

    검색 알고리즘은 `search.html` 과 같은 포팅본을 쓰고(정합성은 verify_search_port 가
    대조), 색인 **재료**만 고객용으로 고른다.
    """
    src = corpus if corpus is not None else load_corpus()
    return BM25Index(chunk_sources({d: customer_text(src[d]) for d in SOURCE_FILES if d in src}))


def easy_answers(quotes: dict, constants: dict, norm_corpus: dict,
                 region_labels: list[str], all_capital: bool) -> list[dict]:
    """자주 묻는 질문의 '쉬운 요약' — **미리 작성해 사람이 검수하는 안내문**이다.

    질문을 이해해 답을 '생성'하는 LLM이 아니다(정적 배포에서 그런 척하지 않는다 —
    LLM 배선은 PoC 목표라고 화면에 적는다). 규칙 값·날짜는 전부 엔진 상수에서 오고,
    근거 인용은 verbatim 절단이라 원문과 어긋날 수 없다. 문구는 🤖 초안 — ✍️ 검수 대상.
    """
    cutoff = constants["GRANDFATHERING_CUTOFF"]
    p_base = f"{constants['LTV_BASELINE']:.0%}"
    p_std = f"{constants['LTV_REGULATED_STANDARD']:.0%}"
    p_first = f"{constants['LTV_FIRST_HOME']:.0%}"
    p_multi = f"{constants['LTV_MULTI']:.0%}"
    p_real = f"{constants['LTV_REAL_DEMAND']:.0%}"
    p_owner = f"{constants['LTV_OWNER']:.0%}"
    eff = constants["REG_EFFECTIVE"]
    fsc, molit, faq = "FSC_PRESS_20260630", "MOLIT_PRESS_20260630", "FAQ_20260630"
    return [
        {"id": "gf-timing",
         "keys": ["잔금", "중도금", "시행일 뒤", "실행일", "시행 후"],
         "easy": f"핵심은 '언제 계약했나'예요. {cutoff}까지 매매계약을 하고 계약금 낸 사실을 "
                 f"증명할 수 있으면(또는 대출 신청 접수를 마쳤으면), 잔금이나 대출 실행이 "
                 f"시행일 뒤여도 예전 기준(LTV {p_base})을 그대로 적용받아요. 해당되지 않으면 "
                 f"새 기준(LTV {p_std})이 적용됩니다. 위 ③ 경과규정 체크에 날짜를 넣으면 "
                 "내 경우를 바로 확인할 수 있어요.",
         "cites": [quotes["_GF"]]},
        {"id": "first-home",
         "keys": ["생애최초", "생애 최초", "첫 집", "첫집"],
         "easy": f"줄지 않아요. 생애최초 구입자는 이번 강화 대상이 아니어서, 규제지역이 "
                 f"되어도 완화된 비율(LTV {p_first})이 유지됩니다. 다만 정해진 기간 안에 "
                 "입주(전입)해야 하는 의무 같은 조건이 함께 붙으니 아래 원문을 확인하세요.",
         "cites": [quotes["REG_FIRSTHOME"],
                   _corpus_cut(norm_corpus, molit, "생애최초 LTV 70% + 전입의무(6개월 이내)", 90)]},
        {"id": "gf-downpay",
         "keys": ["계약금", "종전", "가계약"],
         "easy": f"네, 가능성이 높아요. {cutoff}까지 계약을 체결하고 계약금 납부 사실을 "
                 "증명하면 종전 규정이 그대로 적용됩니다. 계약서와 입금 내역 같은 증빙을 "
                 "준비해 두세요. 위 ③ 경과규정 체크에 날짜를 넣으면 바로 확인돼요.",
         "cites": [quotes["_GF"]]},
        {"id": "jeonse",
         "keys": ["전세", "전세대출"],
         "easy": "전세대출이 없어지는 건 아니에요. 다만 규제 수위가 높은 지역(투기·투기과열"
                 "지역)에서 시가 3억 원이 넘는 아파트를 사는 경우에는 전세대출 이용이 제한될 "
                 "수 있어요. 직장 이동·자녀 교육·부모 봉양 같은 불가피한 사유는 예외로 "
                 "인정됩니다. 내 경우가 예외인지는 요건이 복잡해서 상담으로 확인하는 게 안전해요.",
         "cites": [_corpus_cut(norm_corpus, faq,
                               "3억원 초과 APT를 취득한 자의 전세대출 제한의 예외사유는?", 60,
                               nth=1),   # 0번은 목차 줄
                   _corpus_cut(norm_corpus, faq, "불가피한 실수요 등*에 대해서는 적용 예외를 인정", 160)]},
        {"id": "non-regulated",
         # "수도권 규제 외 지역은 어때?" 같은 질문 (2026-08-19 폰 리뷰에서 요약 부재 확인)
         "keys": ["규제 외", "비규제", "규제가 아닌", "규제지역이 아닌", "지정 안 된",
                  "지정되지 않", "지방", "수도권 외"],
         "easy": f"이번에 새로 지정된 지역이 아니라면 대부분 그대로예요 — 무주택 기준은 "
                 f"지금처럼 LTV {p_base}가 유지됩니다. 다만 두 가지는 주의하세요. "
                 f"수도권에서 2주택 이상을 사는 경우는 규제지역이 아니어도 이번 규제"
                 f"(LTV {p_multi})가 적용되고, 유주택자의 일부 조건은 공문에 기준값이 "
                 "명시돼 있지 않아 정확한 한도는 상담 확인이 필요해요. 위 ① 지역 선택에서 "
                 "내 지역을 골라 직접 확인해 보세요.",
         "cites": [quotes["MULTI_0"], quotes["REG_STD"]]},
        {"id": "what-changed",
         # 가장 많이 묻는 질문인데 어휘 검색이 잡지 못한다 — 원문은 "바뀌다"가 아니라
         # "강화·적용"이라고 쓴다(2026-08-20 폰 리뷰: "뭐가바뀐거야?"에 아무것도 안 나옴).
         "keys": ["뭐가 바뀌", "뭐가바뀌", "무엇이 바뀌", "바뀐", "바뀌", "달라",
                  "변경", "얼마", "한도", "어떻게 되"],
         "easy": f"규제지역으로 지정되면 집을 살 때 빌릴 수 있는 비율(LTV)이 "
                 f"{p_base}에서 {p_std}로 줄어드는 것이 가장 큰 변화예요. 다만 모두 같지는 "
                 f"않아요 — 생애최초 구입자는 {p_first} 그대로, 서민·실수요자는 {p_real}, "
                 f"이미 집이 있으면 {p_owner}가 적용됩니다. 그리고 {cutoff}까지 계약하고 "
                 f"계약금을 낸 경우에는 예전 기준이 유지돼요. {eff}부터 적용되며, "
                 "내 조건에서 얼마가 되는지는 위 ② 변경 전 → 후에서 바로 볼 수 있어요.",
         "cites": [quotes["REG_STD"], quotes["_GF"]]},
        {"id": "which-regions",
         "keys": ["어디", "어느 지역", "어떤 지역", "무슨 지역", "지정된 지역", "지정된 곳",
                  "추가된 지역", "추가 지정", "새로 지정", "내 지역", "우리 동네", "포함되"],
         "easy": f"이번에 새로 지정된 곳은 {', '.join(region_labels)} "
                 f"{len(region_labels)}곳이에요"
                 + ("(모두 수도권)" if all_capital else "")
                 + f". {eff}부터 이 지역에서 강화된 기준이 적용되고, 그 밖의 지역은 이번 "
                 "지정 대상이 아니에요. 내가 사려는 집이 여기 해당하는지 위 ① 지역 선택에서 "
                 "골라 바로 확인할 수 있어요.",
         "cites": [_corpus_cut(norm_corpus, molit,
                               "최근 큰 폭으로 집값이 상승한 경기도", 130),
                   _corpus_cut(norm_corpus, fsc,
                               "금일 회의에서 참석자들은 경기도 화성시 동탄구", 120)]},
    ]


def render(ev: ValidationEvidence, fixtures: dict, search_export: dict) -> str:
    """고객용 화면. 판정·인용·검색 재료는 전부 검증된 산출물에서 온다."""
    C = fixtures["constants"]
    eff = C["REG_EFFECTIVE"]
    cutoff = C["GRANDFATHERING_CUTOFF"]
    pub = ev.this_policy.published_at.isoformat()
    before_cut = (date.fromisoformat(cutoff) - timedelta(days=2)).isoformat()

    regions = ev.extraction.target_regions
    labels = [fixtures["regions"][c]["label"] for c in regions if c in fixtures["regions"]]

    snapshots = {s["doc_id"]: s for s in load_snapshots(ev.extraction)}
    doc_labels = {
        d: {"title": s["title"], "issuer": s["issuer"], "published": s["published"]}
        for d, s in snapshots.items()
    }
    quotes = _rule_quotes(ev.extraction)

    n_cases = len(fixtures["cases"])
    n_probe = sum(len(v) for v in fixtures["region_probe"].values())
    n_aff = len(fixtures.get("affordability", {}).get("probes", ()))
    docs_630 = sorted({c.citation.source_doc_id for c in ev.extraction.changes})

    # 쉬운 요약(미리 검수된 안내) + 원문 전체(클릭 시 모달 — 발췌만 주면 일반인은 벽을 만난다)
    corpus = load_corpus()
    norm_corpus = {k: re.sub(r"\s+", " ", v).strip() for k, v in corpus.items()}
    capital = set(fixtures.get("capital_area") or ())
    easy = easy_answers(quotes, fixtures["constants"], norm_corpus,
                        labels, bool(regions) and all(c in capital for c in regions))
    # 통합 계산기 근거 — 최대한도·DSR·DTI·만기 전부 원문 verbatim (affordability.py 상수의 출처)
    quotes["_AFF_CAP"] = _corpus_cut(norm_corpus, "FAQ_20260630",
                                     "다만, 주택가격별 대출한도 규제(15억원이하6억원", 90)
    quotes["_AFF_DSR"] = _corpus_cut(norm_corpus, "FAQ_20260630",
                                     "금융권 대출은 DSR 규제(은행권 40%", 60)
    quotes["_AFF_DTI"] = _corpus_cut(norm_corpus, "FAQ_20260630",
                                     "조정대상지역(아파트 限) 50% 투기과열지구 40%", 50)
    quotes["_AFF_TERM"] = _corpus_cut(norm_corpus, "MOLIT_PRESS_20260630",
                                      "최대한도 6억원 제한", 70)
    # 상품 자격 판정의 근거 — 전부 FAQ 원문 verbatim
    quotes["_P_RELAXED"] = _corpus_cut(norm_corpus, "FAQ_20260630",
                                       "규제지역에서도 금융권 생애최초 주담대", 110)
    quotes["_P_DIDIMDOL"] = _corpus_cut(norm_corpus, "FAQ_20260630",
                                        "디딤돌 대출 (좌동) 최대한도 일반차주2.0억원", 90)
    quotes["_P_BOGEUM"] = _corpus_cut(norm_corpus, "FAQ_20260630",
                                      "보금자리론 아파트70% / 非아파트65%", 80)
    # 모달의 '공문 전체'는 **원문 그대로**(줄바꿈 보존) 보여준다. 정제본(공백까지 합친 본문)을
    # 흘리면 표가 한 줄로 뭉개져 사람이 읽을 수 없다(2026-08-20 폰 리뷰). 검색은 정제본을,
    # 화면은 원문을 본다 — 강조 위치는 JS 가 공백 정규화 좌표에서 찾아 원문 좌표로 되돌린다.
    docs_full = {d: corpus[d] for d in docs_630}

    # 고객 화면 색인 — 연락처 블록·페이지 마커·목차 리더를 걷어낸 본문으로 다시 색인한다.
    # (2026-08-19 폰 리뷰) 처음에는 "연락처가 든 청크를 통째로 제외"했는데, MOLIT p3 참고1의
    # 비규제 70%/유주택 60% — 고객이 가장 많이 묻는 값 — 이 앞 페이지 연락처 꼬리와 한 청크에
    # 묶여 있어 핵심 재료까지 사라졌다. 청크가 아니라 **텍스트**에서 골라야 했다.
    customer_export = build_customer_index(corpus).export()

    region_opts = "".join(
        f'<option value="{esc(code)}"{" selected" if code == "GURI" else ""}>'
        f'{esc(meta["label"])}</option>'
        for code, meta in sorted(fixtures["regions"].items(), key=lambda kv: kv[1]["label"])
    )

    presets_qa = [
        "뭐가 바뀐 거예요?",
        "잔금일이 시행일 뒤인데 저는 어떻게 되나요",
        "생애최초인데 한도가 줄어드나요",
        "계약금을 냈으면 종전 규정을 적용받나요",
        "전세대출도 영향이 있나요",
        "규제 외 지역인데 저도 영향 있나요",
    ]
    preset_btns = "".join(
        f'<button type="button" data-q="{esc(q)}">{esc(q)}</button>' for q in presets_qa)

    info = explainer(
        "규제가 바뀌었을 때 '내 대출 한도가 얼마에서 얼마로 달라지는지'를 조건 몇 가지로 "
        "확인하는 고객용 시뮬레이터입니다 (Tomorrow Challenge 제안 화면 · 금융앱 웹뷰 탑재형).",
        "판정은 검증 시스템(RegImpact AI)의 심사 엔진을 웹으로 옮긴 것 — 원본과 판정 "
        f"{n_cases}건·지역 조회 {n_probe}건·한도 계산 {n_aff}건을 자동 대조해 전부 일치할 "
        "때만 배포됩니다. "
        "근거 인용은 공문 원문과 글자 단위 대조를 통과한 문장만 싣습니다.",
        "조건을 바꾸면 변경 전/후 한도가 즉시 다시 계산됩니다. 아래 Q&A는 질문과 관련된 "
        "공문 원문 문단을 찾아 보여줍니다.",
    )

    pitch = f"""
<aside class="pitch">
  <div class="kicker">Tomorrow Challenge — 팀 엣지케이스</div>
  <h1>내 한도 시그널</h1>
  <p class="lede">규제가 바뀐 다음 날, 내 대출 한도가 얼마에서 얼마로 달라졌고
  나는 경과규정 대상인지 — <b>근거 조문과 함께</b> 알려주는 개인화 시뮬레이터.
  금융앱(슈퍼SOL 등) 웹뷰 탑재형 제안입니다.</p>
  <ul>
    <li><b>①</b><span><b>영향 알림</b> — 공문 발표 시 내 조건 기준 영향 여부 (아래는 시뮬레이션)</span></li>
    <li><b>②</b><span><b>전/후 비교 + 총 가능금액</b> — 변경 전·후 한도를 나란히, 어느 규칙에서
      판정됐는지까지. LTV·최대한도·DSR·DTI를 합쳐 <b>어느 규제에 막혔는지</b>도 짚어줍니다</span></li>
    <li><b>③</b><span><b>경과규정 체크</b> — 계약·계약금·접수 일자로 종전 규정 적용 여부</span></li>
    <li><b>④</b><span><b>근거 우선 Q&A</b> — 원문을 검색해 근거 문단을 보여주고, 없으면 지어내지 않고 상담 안내</span></li>
  </ul>
  <table class="cmp-t">
    <caption>일반 대출한도 계산기와 뭐가 다른가요?</caption>
    <thead><tr><th></th><th>한도 계산기 (토스 등)</th><th>내 한도 시그널</th></tr></thead>
    <tbody>
      <tr><td>답하는 질문</td><td>지금 얼마 빌릴 수 있나 — 오늘의 <b>상태</b></td>
        <td>규제가 바뀌면 나는 뭐가 달라지나 — 변경이라는 <b>사건</b></td></tr>
      <tr><td>시점</td><td>현재 규칙 하나</td>
        <td>변경 전/후 두 시점 비교 + 경과규정·생애최초 등 경계 조건 판정</td></tr>
      <tr><td>답의 근거</td><td>숫자만 (출처 없음)</td>
        <td>공문 원문 인용 — 인용이 원문에 실재하는지 기계 대조</td></tr>
      <tr><td>틀리면</td><td>"단순 참고용" 고지</td>
        <td>독립 오라클 대조·회귀 테스트·감사로그가 배포 조건 — 은행이 자기 이름으로 내보낼 수 있는 수준</td></tr>
    </tbody>
  </table>
  <div class="vbadge"><b>AI가 판정하지 않는 AI 서비스.</b> LLM은 공문에서 사실만 추출하고
  판정은 결정적 룰엔진이 합니다. 이 화면의 엔진은 원본과 판정 {n_cases}건 + 지역 조회
  {n_probe}건 + 한도 계산 {n_aff}건 자동 대조 후에만 배포되며, 서버 호출 없이 브라우저
  안에서 돌아 고객 입력이 밖으로 나가지 않습니다.</div>
  <div class="vbadge"><b>고객·현업 양면 서비스.</b> 이 엔진은 고객 화면 전용이 아닙니다 —
  같은 엔진이 현업(심사·리스크)용 산출물인 규제 변경 추출 검증·임팩트 매트릭스·포트폴리오
  영향 분석·검증보고서를 이미 구동하며 전부 공개 운영 중입니다. B2C 콘텐츠와 B2B 내부도구가
  한 번의 온보딩으로 함께 열립니다.</div>
  <div class="links">
    <a href="demo.html">시스템 시연(3분)</a>
    <a href="playground.html">판정 플레이그라운드</a>
    <a href="validation_summary.html">검증 요약</a>
    <a href="index.html">검증 산출물 전체</a>
  </div>
  <div style="margin-top:16px">{info}</div>
</aside>"""

    body = f"""
<div class="phone">
  <header class="appbar">
    <div class="logo">한</div>
    <div><div class="t">내 한도 시그널</div>
    <div class="s">규제 변경 개인화 시뮬레이터 · 데모 시나리오 {pub} 대책</div></div>
  </header>
  <div class="body">

    <div class="push">
      <div class="head"><span class="dot"></span>영향 알림 · 시뮬레이션 <span style="margin-left:auto">{esc(pub)}</span></div>
      <div class="bd"><b>규제지역 {len(labels)}곳 추가 지정 ({", ".join(esc(l) for l in labels)})</b>
      {esc(eff)}부터 강화 규제가 적용됩니다. 아래에서 내 조건으로 영향을 확인하세요.</div>
    </div>

    <div class="sec-t">① 내 조건</div>
    <form class="panel" id="cond">
      <div class="f"><label for="region">주택 소재 지역</label>
        <select id="region">{region_opts}</select></div>
      <div class="f"><label>주택 보유</label>
        <div class="seg" id="own">
          <button type="button" data-own="none" class="on">무주택</button>
          <button type="button" data-own="disposal">1주택<br>(처분예정)</button>
          <button type="button" data-own="keep">1주택<br>(계속보유)</button>
          <button type="button" data-own="multi">2주택 이상</button>
        </div></div>
      <label class="chk"><input type="checkbox" id="first">
        <span>생애최초 주택구입<small>세대 구성원 모두 주택 소유 이력 없음</small></span></label>
      <label class="chk"><input type="checkbox" id="demand">
        <span>서민·실수요자 요건<small>부부합산 소득·주택가격·무주택 요건 충족</small></span></label>
      <div class="f"><label for="price">주택 가격 (억원)</label>
        <input type="number" id="price" min="1" max="50" step="0.5" value="8"></div>

      <div class="gfbox" id="gf">
        <div class="f" style="margin-bottom:8px"><label>③ 경과규정 체크 — 규제 발표 전에 이미 진행 중이었나요?</label>
          <div class="hint">
            <button type="button" id="gf-yes">시행 전에 계약했어요</button>
            <button type="button" id="gf-no">해당 없음</button>
          </div></div>
        <div class="f"><label for="contract">주택매매계약 체결일</label>
          <input type="date" id="contract"></div>
        <label class="chk"><input type="checkbox" id="downpay">
          <span>계약금 납부 사실 증명 가능</span></label>
        <div class="f"><label for="accepted">대출 신청 접수일 (있다면)</label>
          <input type="date" id="accepted"></div>
      </div>
    </form>

    <div class="sec-t">② 변경 전 → 후, 내 한도</div>
    <div class="cmp">
      <div class="vc" id="vc-before"></div>
      <div class="vc after" id="vc-after"></div>
    </div>
    <div class="delta" id="delta"></div>

    <div class="sec-t">총 얼마까지 빌릴 수 있나 — 참고 추정</div>
    <div class="panel" id="aff">
      <div class="aff-grid">
        <div class="f"><label for="aff-income">연소득 (만원)</label>
          <input type="number" id="aff-income" min="0" step="100" placeholder="예: 6000"></div>
        <div class="f"><label for="aff-debt">기존 대출 월 상환액 (만원)</label>
          <input type="number" id="aff-debt" min="0" step="10" value="0"></div>
        <div class="f"><label for="aff-rate">예상 금리 (%)</label>
          <input type="number" id="aff-rate" min="0" max="20" step="0.1" placeholder="예: 4.0"></div>
        <div class="f"><label for="aff-years">만기 (년, 규제지역 최대 30)</label>
          <input type="number" id="aff-years" min="1" max="40" value="30"></div>
      </div>
      <div class="f"><label>대출 기관</label>
        <div class="seg" style="grid-template-columns:repeat(2,1fr)" id="aff-lender">
          <button type="button" data-lender="BANK" class="on">은행권</button>
          <button type="button" data-lender="NONBANK">2금융권</button>
        </div></div>
      <div id="aff-out"></div>
      <div class="goal-row" style="margin-top:14px">
        <div class="f"><label for="goal">이만큼 빌리고 싶어요 (억원)</label>
          <input type="number" id="goal" min="0" step="0.5" placeholder="예: 4"></div>
        <button type="button" id="goal-go">방법 찾기</button>
      </div>
      <div class="rx" id="rx"></div>
      <div class="honesty" style="margin-top:11px"><b>참고 추정이에요.</b> 원리금균등 상환 기준
      이고 <b>스트레스 금리 가산은 미반영</b>이라 실제 한도는 이보다 적을 수 있어요. 기존
      부채는 월 상환액 전액을 DSR·DTI에 반영(보수적)했고, DTI는 아파트 기준입니다. 실제
      가능 금액은 은행 심사로 확정돼요.</div>
      <details class="more" style="margin-top:10px"><summary>이 계산의 근거 조문</summary>
        <div class="evi" id="aff-evi"></div></details>
    </div>

    <div class="sec-t">내게 가능한 상품 찾기</div>
    <div class="panel">
      <div id="prod"></div>
      <div class="honesty" style="margin-top:11px"><b>추천이 아니라 자격 판정이에요.</b>
      취향을 예측하는 것이 아니라, 위에서 판정한 조건(지역·주택 수·생애최초·경과규정)으로
      <b>원문이 정한 요건에 해당하는지</b>를 되짚습니다. 소득·자산 같은 세부 신청 자격은
      이 공문에 없어서 <b>판정하지 않고 상담으로 안내</b>합니다 — 없는 근거로 "가능합니다"라고
      말하지 않습니다.</div>
      <details class="more" style="margin-top:10px"><summary>이 판정의 근거 조문</summary>
        <div class="evi" id="prod-evi"></div></details>
    </div>

    <div class="sec-t">내 한도를 움직인 일들</div>
    <div class="panel">
      <div class="tl" id="tl"></div>
      <div class="sub-cta"><b>규제만 한도를 움직이는 게 아닙니다.</b> 지역 지정·해제, 스트레스
      금리 단계, 정책 변경이 모두 내 한도를 바꿉니다. 실제 서비스에서는 내 조건을 저장해 두고
      <b>한도가 움직이는 일이 생길 때마다 알림</b>으로 알려드립니다 — 발표일에만 쓰는 도구가
      아니라, 집을 준비하는 내내 켜져 있는 신호입니다.</div>
    </div>

    <details class="more" open><summary>⚡ 같은 날 계약한 두 사람 — 왜 한도가 다른가요?</summary>
      <div class="duo-wrap">
        <div class="duo">
          <div class="pc" id="duo-a"></div>
          <div class="pc" id="duo-b"></div>
        </div>
        <div class="duo-note" id="duo-note"></div>
      </div></details>

    <details class="more"><summary>이 판정, 어떻게 나왔나요? (판정 경로)</summary>
      <div class="trace" id="trace"></div></details>
    <details class="more" open><summary>근거 조문 (공문 원문 그대로)</summary>
      <div class="evi" id="evi"></div></details>

    <div class="sec-t">④ 물어보기 — 근거가 있을 때만 답합니다</div>
    <div class="panel qa">
      <input type="text" id="q" placeholder="예) 잔금일이 시행일 뒤인데 저는 어떻게 되나요">
      <div class="preset">{preset_btns}</div>
      <div class="hits" id="hits"></div>
      <div class="docrow" id="docrow"></div>
      <div class="honesty" style="margin-top:11px">쉬운 요약은 자주 묻는 질문에 대해
      <b>미리 작성해 사람이 검수하는 안내문</b>이에요 — 질문을 이해해 답을 '생성'하는 AI가
      아닙니다. 자유 질문에 문장으로 답하는 LLM 연결(모든 문장에 인용 부착)은 PoC 기간
      배선 목표이며, 그때도 근거를 못 찾으면 지어내지 않고 전문 상담을 안내합니다.
      원문 발췌를 누르면 공문 전체를 볼 수 있어요.</div>
    </div>

    <div class="foot">
      본 화면은 데모 시나리오({pub} 대책) 기준이며 LTV 코어 판정만 다룹니다 —
      DSR·가격구간별 최대한도·중도금 등 부가 규제는 <b>미반영</b>. 실제 대출 가능 금액은
      은행 심사로 확정됩니다. 판정 엔진·인용 검증·테스트 등 검증 산출물:
      <a href="index.html">RegImpact AI</a> ·
      <a href="demo.html">시스템 시연</a> ·
      <a href="playground.html">플레이그라운드</a>
    </div>
    <div class="mnote">데스크톱에서 열면 제안 요약(팀 엣지케이스)이 함께 보입니다</div>
  </div>
</div>

<div id="modal" hidden>
  <div class="m-box">
    <div class="m-head"><div><div class="mt" id="m-title"></div>
      <div class="ms" id="m-sub"></div></div>
      <button id="m-close" aria-label="닫기">✕</button></div>
    <div class="m-body" id="m-body"></div>
    <div class="m-note">공문 원문 전체 — 줄바꿈까지 원문 그대로이며 한 글자도 빼지 않았습니다.
    표는 텍스트로 추출된 것이라 칸이 줄로 풀려 보일 수 있고, 기준은 해시로 봉인된 원본
    PDF/HWP 입니다.</div>
  </div>
</div>"""

    script_tpl = """
<script type="module">
const FX = __FX__;
const DEMO = __DEMO__;
const EASY = __EASY__;
const DOCS_FULL = __DOCS_FULL__;
const IDX_EXPORT = __IDX__;
const QUOTES = __QUOTES__;
const DOCL = __DOCL__;
const DOCS_NOW = __DOCS_NOW__;
const RULE_KO = __RULE_KO__;
__ENGINE__
__SEARCH__
__AFFORD__

const $ = (s) => document.querySelector(s);
const C = FX.constants;
let own = "none";

function app(withGf) {
  const house = own === "none" ? 0 : own === "multi" ? 2 : 1;
  return {
    region_code: $("#region").value,
    evaluation_date: withGf ? C.REG_EFFECTIVE : C.GRANDFATHERING_CUTOFF,
    house_count: house,
    disposal_condition_flag: own === "disposal",
    first_home_buyer: $("#first").checked,
    real_demand_flag: $("#demand").checked,
    policy_mortgage_flag: false,
    loan_purpose: "HOME_PURCHASE",
    application_accepted_at: withGf ? ($("#accepted").value || null) : null,
    contract_signed_at: withGf ? ($("#contract").value || null) : null,
    downpayment_paid_at: withGf && $("#downpay").checked ? ($("#contract").value || null) : null,
    land_permit_target: false,
    land_permit_applied_at: null,
  };
}

const pct = (v) => `${Math.round(v * 100)}%`;
const pct1 = (v) => `${(v * 100).toFixed(1)}%`;
function won(x) {  // 원 → "N억 M천만원". 1천만 미만은 만원 단위로 — 목표 역산의 처방이
  // "월 76만원"처럼 소액이라 억 단위로 반올림하면 "0천만원"이 된다(2026-08-20 실측).
  const eok = Math.floor(x / 1e8), chun = Math.round((x % 1e8) / 1e7);
  if (eok === 0 && chun === 0) return `${Math.round(x / 1e4).toLocaleString()}만원`;
  if (eok === 0) return `${chun}천만원`;
  return chun ? `${eok}억 ${chun}천만원` : `${eok}억원`;
}
const REVIEW_KO = {
  OWNER_BASELINE_UNKNOWN: "변경 전 기준값이 공문에 없어요 — 정확한 비교는 상담으로 안내",
  MULTI_HOME_BASELINE_UNKNOWN: "변경 전 기준값이 공문에 없어요 — 정확한 비교는 상담으로 안내",
  REGION_UNKNOWN: "이 지역 정보가 아직 등록 전이에요 — 상담으로 안내",
};

function card(el, when, d, price) {
  if (d.status === "DECIDED") {
    const amt = Math.floor(price * d.max_ltv);
    el.innerHTML = `<div class="when">${when}</div>`
      + `<div class="ltv${d.max_ltv === 0 ? " zero" : ""}">LTV ${pct(d.max_ltv)}</div>`
      + `<div class="amt">${d.max_ltv === 0 ? "대출 불가 (0원)" : "약 " + won(amt)}</div>`
      + `<div class="why">${d.grandfathering_applied
          ? '<span class="gfbadge">경과규정</span> 종전 기준 유지'
          : (RULE_KO[d.applicable_rule_id] ?? d.applicable_rule_id ?? "")}</div>`;
  } else {
    const why = (d.reason_codes || []).map((r) => REVIEW_KO[r]).filter(Boolean)[0]
      ?? "판정에 사람 확인이 필요해요";
    el.innerHTML = `<div class="when">${when}</div>`
      + `<div class="ltv review">전문 상담 필요</div><div class="why">${why}</div>`;
  }
}

// ── 원문 전체 모달 — 발췌만 주면 일반인은 벽을 만난다. 누르면 공문 전체 + 해당 문장 강조.
//    강조는 청크 통째가 아니라 **질문어가 실제로 걸린 문장만** 칠한다(2026-08-19 폰 리뷰:
//    구간 전체를 칠하면 "여기가 답"이라고 짚어주는 느낌이 아니라 덩어리가 물든 것처럼 보인다).
const TGT = [];
const tgt = (doc, marks) => (TGT.push({ doc, marks }) - 1);
const clean = (t) => t.replace(/-{2,}\\s*p\\d+\\s*-{2,}/g, " ").replace(/\\s+/g, " ").trim();
const escT = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

// 공문은 마침표가 드물고 불릿(￭ ▪ □ ㅇ - *)으로 항목이 끊긴다 — 둘 다 문장 경계로 본다.
const SENT_SPLIT = /(?<=[.?!])\\s+|(?=[￭▪□◦○●])|(?=\\sㅇ\\s)|(?=\\s-\\s)|(?=\\s\\*\\s)/;
function sentences(t) {
  const out = [];
  for (const raw of clean(t).split(SENT_SPLIT)) {
    const s = raw.trim();
    if (!s) continue;
    // 너무 짧은 조각은 앞 문장에 붙인다 — 단독으로는 근거가 되지 못한다
    if (out.length && s.length < 14) out[out.length - 1] += " " + s;
    else out.push(s);
  }
  return out;
}
// 겹친 표현의 **개수**가 아니라 **희소성**으로 점수를 매긴다(2026-08-20 폰 리뷰:
// "규제·지역·대출"처럼 어디에나 있는 말이 많이 겹친 문장이 이겨서 엉뚱한 곳이 강조됐다).
// 색인이 이미 갖고 있는 idf 를 그대로 쓴다 — 검색과 강조가 같은 기준을 보게 된다.
function sentScore(sent, qTerms) {
  const has = new Set(tokenize(sent));
  let s = 0;
  for (const t of qTerms) if (has.has(t)) s += INDEX.idf.get(t) ?? 0;
  return s;
}
const qTermsOf = (q) => [...new Set(tokenize(q))];

// 원문은 줄바꿈·들여쓰기를 그대로 두고 보여준다(2026-08-20 폰 리뷰: 한 덩어리로 흐르면
// 표가 사라지고 읽을 수 없다). 대신 강조할 문장은 **공백을 합친 좌표**에서 찾으므로,
// 정규화 문자열과 원문 사이의 위치 대응표를 만들어 되돌린다.
function normMap(raw) {
  let norm = "", map = [], sp = true;
  for (let i = 0; i < raw.length; i++) {
    if (/\s/.test(raw[i])) {
      if (!sp) { norm += " "; map.push(i); sp = true; }
    } else { norm += raw[i]; map.push(i); sp = false; }
  }
  return { norm, map };
}
// 쪽 마커는 지우지 않고 **구분선으로** 보여준다 — 몇 쪽에서 나온 문장인지가 근거의 일부다.
const PGMARK = /-{3,}\s*p(\d+)\s*-{3,}/g;
const fmtDoc = (t) => escT(t).replace(PGMARK, (_, n) => `<span class="pg">${n}쪽</span>`);
function findSpan(norm, map, m) {
  let i = norm.indexOf(m), len = m.length;
  if (i < 0) {                    // 쪽 넘김·연락처 제거로 문장이 갈린 경우 앞부분만 짚는다
    const head = m.slice(0, 40);
    if (head.length < 12) return null;
    i = norm.indexOf(head); len = head.length;
  }
  return i < 0 ? null : [map[i], map[i + len - 1] + 1];
}

function openDoc(doc, marks) {
  const d = DOCL[doc] ?? {};
  const raw = DOCS_FULL[doc] ?? "";
  const { norm, map } = normMap(raw);
  const spans = [];
  for (const m of marks ?? []) {
    const sp = findSpan(norm, map, m);
    if (sp) spans.push(sp);
  }
  spans.sort((a, b) => a[0] - b[0]);
  let html = "", cur = 0, first = true;
  for (const [s, e] of spans) {
    if (s < cur) continue;                       // 겹치면 앞의 것만
    html += fmtDoc(raw.slice(cur, s))
      + `<mark${first ? ' id="m-mark"' : ""}>` + fmtDoc(raw.slice(s, e)) + "</mark>";
    cur = e; first = false;
  }
  html += fmtDoc(raw.slice(cur));
  $("#m-title").textContent = d.title ?? doc;
  $("#m-sub").textContent = `${d.issuer ?? ""} · ${d.published ?? ""}`;
  $("#m-body").innerHTML = html;
  $("#modal").hidden = false;
  const mk = document.getElementById("m-mark");
  if (mk) mk.scrollIntoView({ block: "center" });
  else $("#m-body").scrollTop = 0;
}
document.addEventListener("click", (e) => {
  const el = e.target.closest("[data-t]");
  if (el && TGT[Number(el.dataset.t)] !== undefined) {
    const t = TGT[Number(el.dataset.t)];
    openDoc(t.doc, t.marks);
  }
});
$("#m-close").addEventListener("click", () => { $("#modal").hidden = true; });
$("#modal").addEventListener("click", (e) => { if (e.target.id === "modal") $("#modal").hidden = true; });

const qciteHtml = (q) => {
  const d = DOCL[q.doc] ?? {};
  return `<button type="button" class="q-cite qbtn" data-t="${tgt(q.doc, [clean(q.quote)])}">“${q.quote}”`
    + `<span class="src">${d.issuer ?? ""} · ${d.title ?? q.doc} · ${d.published ?? ""}`
    + ` — 원문 전체 보기 →</span></button>`;
};
function cite(box, keys, fallback) {
  box.innerHTML = keys.filter((k) => QUOTES[k]).map((k) => qciteHtml(QUOTES[k])).join("")
    || `<div class="q-cite">${fallback}</div>`;
}

function run() {
  const price = Number($("#price").value || 0) * 1e8;
  const before = evaluate(FX, app(false)), after = evaluate(FX, app(true));
  card($("#vc-before"), `~ ${C.GRANDFATHERING_CUTOFF} · 변경 전`, before.decision, price);
  card($("#vc-after"), `${C.REG_EFFECTIVE} ~ · 변경 후`, after.decision, price);

  const b = before.decision, a = after.decision, dl = $("#delta");
  if (a.status === "DECIDED" && a.grandfathering_applied) {
    dl.className = "delta good";
    dl.innerHTML = `<b>경과규정 대상이에요.</b> ${C.GRANDFATHERING_CUTOFF}까지의 계약·접수가 `
      + `인정되면 시행 후에도 <b>종전 기준(LTV ${pct(a.max_ltv)})</b>이 유지됩니다. 증빙 서류를 준비하세요.`;
  } else if (b.status === "DECIDED" && a.status === "DECIDED") {
    const diff = Math.floor(price * b.max_ltv) - Math.floor(price * a.max_ltv);
    if (diff > 0) {
      dl.className = "delta bad";
      dl.innerHTML = `<b>한도가 약 ${won(diff)} 줄어요</b> (LTV ${pct(b.max_ltv)} → ${pct(a.max_ltv)}). `
        + `계약·접수 시점에 따라 경과규정 대상일 수 있어요 — `
        + `<a class="dlink" href="#gf">위 ③ 경과규정 체크</a>에 날짜를 넣어 확인하세요.`;
    } else if (diff === 0) {
      dl.className = "delta good";
      dl.innerHTML = `<b>이번 변경으로 한도가 달라지지 않아요</b> (LTV ${pct(a.max_ltv)} 유지).`;
    } else {
      dl.className = "delta good";
      dl.innerHTML = `<b>한도가 약 ${won(-diff)} 늘어요</b> (LTV ${pct(b.max_ltv)} → ${pct(a.max_ltv)}).`;
    }
  } else {
    dl.className = "delta good";
    dl.innerHTML = `<b>자동 판정이 어려운 조건이에요.</b> 이 시스템은 모르는 것을 추정하지 않고
      전문 상담으로 안내합니다.`;
  }

  $("#trace").innerHTML = after.trace.map((t) =>
    `<div class="row ${t.hit ? "hit" : ""}"><div class="id">${t.id}</div>`
    + `<div>${t.label}<div class="n2">${t.note}</div></div></div>`).join("");

  // 어떤 원문을 근거로 보여줄까 — 경과규정이면 종전규정 문장, 강화 규칙이면 해당 규칙 문장.
  // 비규제 기준선(70%)은 이번 공문이 만든 값이 아니므로 출처를 달지 않는다(엔진과 같은 규율).
  const keys = [];
  let fallback = "판정에 사람 확인이 필요한 조건이라, 근거 조문은 상담 시 함께 안내됩니다.";
  if (a.status === "DECIDED") {
    if (a.grandfathering_applied) keys.push("_GF");
    else if (a.applicable_rule_id && a.applicable_rule_id !== "NONREG_STD_70")
      keys.push(a.applicable_rule_id);
    else fallback = "이 판정은 종전부터 있던 기준선이라, 이번 공문이 출처가 아니에요.";
  }
  cite($("#evi"), keys, fallback);

  // ── 같은 날 계약한 두 사람 — 계산기가 구조적으로 답 못 하는 질문을 엔진으로 보여준다.
  //    조건 차이는 '계약금 납부 증명' 하나뿐이고, 판정은 전부 엔진이 한다(수치 하드코딩 없음).
  const duoBase = {
    region_code: DEMO.code, evaluation_date: C.REG_EFFECTIVE, house_count: 0,
    disposal_condition_flag: false, first_home_buyer: false, real_demand_flag: false,
    policy_mortgage_flag: false, loan_purpose: "HOME_PURCHASE",
    application_accepted_at: null, contract_signed_at: DEMO.contract,
    downpayment_paid_at: null, land_permit_target: false, land_permit_applied_at: null,
  };
  const pa = evaluate(FX, { ...duoBase, downpayment_paid_at: DEMO.contract }).decision;
  const pb = evaluate(FX, duoBase).decision;
  const pcCard = (el, who, d) => {
    el.innerHTML = `<div class="who">${who}</div>`
      + `<div class="cond">${DEMO.contract} 계약 · ${DEMO.label} · 무주택</div>`
      + (d.status === "DECIDED"
        ? `<div class="ltv${d.max_ltv === 0 ? " zero" : ""}">LTV ${pct(d.max_ltv)}</div>`
          + `<div class="amt">${d.max_ltv === 0 ? "대출 불가" : "약 " + won(Math.floor(price * d.max_ltv))}</div>`
          + (d.grandfathering_applied
             ? '<div style="margin-top:5px"><span class="gfbadge">경과규정</span></div>' : "")
        : `<div class="ltv review">전문 상담 필요</div>`);
  };
  pcCard($("#duo-a"), "A — 계약금 납부 증명 있음", pa);
  pcCard($("#duo-b"), "B — 계약금 증빙 없음", pb);
  const dn = $("#duo-note");
  if (pa.status === "DECIDED" && pb.status === "DECIDED") {
    const gap = Math.abs(Math.floor(price * pa.max_ltv) - Math.floor(price * pb.max_ltv));
    dn.innerHTML = `같은 날, 같은 가격(${won(price)})의 아파트를 계약한 두 사람의 한도가 `
      + `<b>약 ${won(gap)}</b> 다릅니다 — A는 경과규정으로 종전 기준을 유지하기 때문이에요. `
      + `<b>일반 한도 계산기는 '오늘 규칙' 하나만 알기 때문에 이 두 사람에게 같은 숫자를 `
      + `보여줍니다.</b> 변경 전/후와 경계 조건을 판정하는 것이 내 한도 시그널의 차이입니다.`;
  } else {
    dn.textContent = "이 조건에서는 자동 비교가 어려워 상담으로 안내합니다.";
  }

  lastAfter = a;
  affRender();
  prodRender();
}

// ── 내게 가능한 상품 찾기 — 추천이 아니라 자격 판정.
//    엔진이 이미 판정한 사실에서 요건 충족 여부를 되짚는다. 소득·자산 요건은 공문에
//    없으므로 UNKNOWN 으로 남긴다 — 없는 근거로 "가능"이라 말하지 않는다(products.py 와 동일).
const PRODUCTS = [
  { id: "FIRST_HOME", name: "생애최초 주담대", cite: "_P_RELAXED", gate: "first" },
  { id: "REAL_DEMAND", name: "서민·실수요자 주담대", cite: "_P_RELAXED", gate: "demand" },
  { id: "DIDIMDOL", name: "디딤돌 대출 (정책모기지)", cite: "_P_DIDIMDOL", gate: null },
  { id: "BOGEUMJARI", name: "보금자리론 (정책모기지)", cite: "_P_BOGEUM", gate: null },
];
const ST_KO = { ELIGIBLE: "해당", BLOCKED: "해당 없음", UNKNOWN: "확인 필요" };
const ST_CLS = { ELIGIBLE: "ok", BLOCKED: "no", UNKNOWN: "un" };
function prodRender() {
  const a = lastAfter, box = $("#prod");
  if (!a) return;
  const first = $("#first").checked, demand = $("#demand").checked;
  const blocked = a.status === "DECIDED" && a.max_ltv === 0;
  const review = a.status !== "DECIDED";
  const region = $("#region").value;
  const regulated = regionStatus(FX, region, C.REG_EFFECTIVE) === "REGULATED";
  const rows = PRODUCTS.map((p) => {
    let st, rs;
    if (blocked) {
      st = "BLOCKED";
      rs = "이 조건에서는 신규 주택구입 주담대 자체가 제한돼(LTV 0%) 상품을 따질 단계가 아니에요.";
    } else if (review) {
      st = "UNKNOWN";
      rs = "판정에 사람 확인이 필요한 조건이라 상품 자격도 상담으로 확인해야 해요.";
    } else if (p.gate === "first") {
      st = first ? "ELIGIBLE" : "UNKNOWN";
      rs = first
        ? "생애최초로 체크하셨고, 원문이 생애최초 주담대를 완화 대상으로 명시합니다."
          + (regulated ? " 규제지역이어도 좌동입니다." : "")
        : "생애최초 여부를 체크하지 않으셨어요. 세대 구성원 모두 주택 소유 이력이 없어야 해당합니다.";
    } else if (p.gate === "demand") {
      st = demand ? "ELIGIBLE" : "UNKNOWN";
      rs = demand
        ? "서민·실수요자 요건으로 체크하셨고, 원문이 완화 대상으로 명시합니다."
        : "소득·주택가격·무주택 요건을 모두 충족해야 해당해요. 위 ① 조건에서 체크해 보세요.";
    } else {
      st = "UNKNOWN";
      rs = "원문에 한도는 나와 있지만 소득·자산 등 신청 자격 요건은 이 공문에 없어요. "
         + "해당 여부는 상담으로 확인해야 합니다."
         + (a.grandfathering_applied ? " 경과규정 대상이면 종전 기준이 함께 검토됩니다." : "");
    }
    return `<div class="pr-i ${ST_CLS[st]}"><div class="top">
      <span class="nm">${p.name}</span><span class="st">${ST_KO[st]}</span></div>
      <div class="rs">${rs}</div></div>`;
  }).join("");
  box.innerHTML = `<div class="pr">${rows}</div>`;
}
cite($("#prod-evi"), ["_P_RELAXED", "_P_DIDIMDOL", "_P_BOGEUM"], "");

// ── 총 가능금액(참고 추정) — 판정(LTV)은 엔진 결과를 받고, 나머지 한도는 포팅본이 계산한다.
//    포팅본은 Python 원본과 프로브 전건 대조 후에만 배포된다(엔진과 같은 통제).
let lastAfter = null;
let lender = "BANK";
const AFF_KO = { LTV: "담보 비율(LTV)", CAP: "가격구간 최대한도",
                 DSR: "총부채원리금(DSR)", DTI: "총부채상환(DTI·아파트)" };
function regulatedTypeAt(code, asOf) {
  const e = FX.regions[code];
  if (!e) return "NONE";
  for (const v of e.versions) {
    const a = v.effective_from === null || asOf >= v.effective_from;
    const b = v.effective_to === null || asOf <= v.effective_to;
    if (a && b) return v.regulated_type ?? "NONE";
  }
  return "NONE";
}
function affRender() {
  const box = $("#aff-out");
  const a = lastAfter;
  if (!a) return;
  if (a.status !== "DECIDED") {
    box.innerHTML = `<div class="consult">이 조건은 자동 판정이 어려워 가능금액을 추정하지
      않아요 — 지어내는 대신 전문 상담으로 안내합니다.</div>`;
    return;
  }
  const price = Number($("#price").value || 0) * 1e8;
  if (a.max_ltv === 0) {
    box.innerHTML = `<div class="aff-total"><div class="amt">대출 불가 (0원)</div>
      <div class="bind">이 조건은 LTV ${pct(a.max_ltv)} — 신규 주택구입 주담대가 막혀 있어
      다른 한도를 계산할 실익이 없어요.</div></div>`;
    return;
  }
  const income = Number($("#aff-income").value || 0) * 1e4;
  const debt = Number($("#aff-debt").value || 0) * 1e4;
  const rateRaw = $("#aff-rate").value;
  const rate = rateRaw === "" ? null : Number(rateRaw) / 100;
  const region = $("#region").value;
  const regulated = regionStatus(FX, region, C.REG_EFFECTIVE) === "REGULATED"
    && !a.grandfathering_applied;      // 경과규정이면 종전 규정 — 이번 캡의 대상이 아니다
  const res = estimateAffordability(FX, {
    price, max_ltv: a.max_ltv, rule_id: a.applicable_rule_id,
    regulated, regulated_type: regulated ? regulatedTypeAt(region, C.REG_EFFECTIVE) : "NONE",
    annual_income: income || null, monthly_debt_service: debt,
    annual_rate: rate, term_years: Number($("#aff-years").value || 0), lender,
  });
  const known = Object.values(res.limits).filter((v) => v !== null);
  const maxV = Math.max(...known, 1);
  const rows = Object.entries(res.limits).map(([k, v]) => {
    if (v === null) {
      const why = k === "CAP" ? "해당 없음 — 규제지역 조치" : "소득·금리 입력 시 계산";
      return `<div class="aff-r na"><div class="hd"><span class="nm">${AFF_KO[k]}</span>
        <span class="vv">${why}</span></div><div class="bar"></div></div>`;
    }
    const isBind = res.binding.includes(k);
    const cap = res.caps[k];
    const capTxt = cap === null || cap === undefined ? ""
      : (k === "CAP" ? `규정 한도 ${won(cap)}` : `규정 한도 ${pct(cap)}`);
    return `<div class="aff-r${isBind ? " bind" : ""}"><div class="hd">
      <span class="nm">${AFF_KO[k]}${isBind ? " ← 여기에 막혀요" : ""}</span>
      <span class="vv">${won(v)}</span></div>
      <div class="bar"><i style="width:${Math.max(3, Math.round(v / maxV * 100))}%"></i></div>
      ${capTxt ? `<div class="rt">${capTxt}</div>` : ""}</div>`;
  }).join("");
  const partial = res.limits.DSR === null
    ? ` <span style="color:var(--on-surface-variant)">· 담보 기준 — 소득·금리를 입력하면
        DSR·DTI까지 반영돼요</span>` : "";
  box.innerHTML = `<div class="aff-total"><div class="amt">약 ${won(res.total)}</div>
    <div class="bind">지금 조건에서 가장 낮은 한도는 <b>${res.binding.map((k) => AFF_KO[k]).join(" · ")}</b>${partial}</div></div>
    <div class="aff-rows">${rows}</div>`;
  if (typeof goalRender === "function") goalRender();
}
// ── 목표 역산: "그래서 얼마를 바꿔야 하나" — 조사에서 드러난 공백(계산기는 진단에서 멈춘다)
function affInput() {
  const a = lastAfter;
  const region = $("#region").value;
  const regulated = regionStatus(FX, region, C.REG_EFFECTIVE) === "REGULATED"
    && !a.grandfathering_applied;
  const rateRaw = $("#aff-rate").value;
  return {
    price: Number($("#price").value || 0) * 1e8, max_ltv: a.max_ltv,
    rule_id: a.applicable_rule_id, regulated,
    regulated_type: regulated ? regulatedTypeAt(region, C.REG_EFFECTIVE) : "NONE",
    annual_income: Number($("#aff-income").value || 0) * 1e4 || null,
    monthly_debt_service: Number($("#aff-debt").value || 0) * 1e4,
    annual_rate: rateRaw === "" ? null : Number(rateRaw) / 100,
    term_years: Number($("#aff-years").value || 0), lender,
  };
}
function goalRender() {
  const box = $("#rx");
  const raw = $("#goal").value;
  if (raw === "" || !lastAfter || lastAfter.status !== "DECIDED") { box.innerHTML = ""; return; }
  const target = Number(raw) * 1e8;
  const plan = planForTarget(FX, { ...affInput(), target });
  if (plan.reachable === null) { box.innerHTML = ""; return; }
  if (plan.reachable) {
    box.innerHTML = `<div class="rx-hd ok"><b>지금 조건으로 가능해요.</b> 목표 ${won(target)} 대비
      약 ${won(plan.headroom)} 여유가 있습니다.</div>`;
    return;
  }
  let html = `<div class="rx-hd"><b>${won(plan.shortfall)} 모자라요.</b>
    지금 한도는 ${won(plan.now.total)}입니다.</div>`;

  // ★ "규정 한도는 40%인데 당신은 58.4%" — 왜 막혔는지를 비율로 보여준다(2026-08-20 리뷰).
  const at = plan.at_target ?? {};
  const gRows = Object.entries(at).map(([k, r]) => {
    if (r.actual === null || r.cap === null) return "";
    const isAmt = r.is_amount;
    const shown = isAmt ? won(r.actual) : pct1(r.actual);
    const capTxt = isAmt ? won(r.cap) : pct(r.cap);
    // 막대: 한도를 60% 지점에 두고 내 비율을 비례로 그린다 — 초과분이 눈에 보이게
    const w = Math.max(3, Math.min(100, Math.round((r.actual / r.cap) * 60)));
    const note = r.over
      ? `규정 한도는 <b>${capTxt}</b>인데 이 금액이면 <b>${shown}</b>가 돼요 —
         ${isAmt ? `${won(r.actual - r.cap)} 초과` : `${pct1(r.gap)}p 초과`}입니다.`
      : `규정 한도 ${capTxt} 안에 들어와요 (${shown}).`;
    return `<div class="g-row${r.over ? " over" : ""}">
      <div class="g-hd"><span class="gn">${AFF_KO[k]}</span><span class="gv">${shown}</span></div>
      <div class="g-bar"><i style="width:${w}%"></i><span class="lim" style="left:60%"></span></div>
      <div class="g-note">${note}</div></div>`;
  }).join("");
  if (gRows) {
    html += `<div class="gauge"><div class="g-t">목표 ${won(target)}을 빌리면 내 비율은
      이렇게 됩니다 — 검은 선이 규정 한도예요.</div>${gRows}</div>`;
  }
  html += `<div class="rx-hd">아래 중 하나를 충족하면 목표에 닿습니다.</div>`;
  for (const a of plan.actions) {
    const nm = AFF_KO[a.limit];
    if (a.kind === "hard") {
      html += `<div class="rx-item"><div class="lb">${nm}</div>
        <div class="no">${a.detail}</div></div>`;
    } else if (a.kind === "price") {
      html += `<div class="rx-item"><div class="lb">${nm}</div>
        <div class="no">${a.detail}</div>
        <div class="ways"><div class="way"><span class="mk">·</span><span>주택가격
        <b>${won(a.need_price)}</b> 이상이면 이 한도로 목표에 닿아요.</span></div></div></div>`;
    } else {
      const ways = [];
      if (a.cut_monthly_debt) {
        ways.push(`기존 대출 월 상환액을 <b>${won(a.cut_monthly_debt)}</b> 줄이기`);
      } else if (a.impossible_by_debt) {
        ways.push("기존 부채를 전부 갚아도 이 한도만으로는 목표에 닿지 않아요");
      }
      if (a.by_term && a.by_term.enough) {
        ways.push(`만기를 <b>${a.by_term.years}년</b>으로 늘리기 `
          + `(한도 ${won(a.by_term.limit)})`);
      }
      if (a.need_income_delta > 0) {
        ways.push(`연소득 <b>${won(a.need_income)}</b> 이상 인정받기 `
          + `(지금보다 ${won(a.need_income_delta)} ↑ — 부부합산·상여 포함 여부 확인)`);
      }
      html += `<div class="rx-item"><div class="lb">${nm}</div><div class="ways">`
        + ways.map((w) => `<div class="way"><span class="mk">·</span><span>${w}</span></div>`).join("")
        + `</div></div>`;
    }
  }
  html += `<div class="honesty">각 방법은 <b>그 규제 하나를 푸는 조건</b>이에요. 여러 규제에
    동시에 막혀 있으면 모두 충족해야 목표에 닿습니다. 실제 인정 소득·부채 산정은 은행 심사
    기준을 따릅니다.</div>`;
  box.innerHTML = html;
}
$("#goal-go").addEventListener("click", goalRender);
$("#goal").addEventListener("keydown", (e) => {
  if (e.key === "Enter") { e.preventDefault(); goalRender(); }
});

// ── 한도 타임라인 — 정책 DB 실데이터. '시그널'이 발표일 전용 도구가 아님을 보여준다.
(function renderTimeline() {
  const evs = [];
  for (const [code, entry] of Object.entries(FX.regions)) {
    for (const v of entry.versions) {
      if (v.effective_from && v.source_policy_id) {
        evs.push({ date: v.effective_from, code, label: entry.label,
                   status: v.status, type: v.regulated_type });
      }
    }
  }
  const byDate = {};
  for (const e of evs) (byDate[e.date] ??= []).push(e);
  const rows = Object.entries(byDate).sort((a, b) => (a[0] < b[0] ? 1 : -1)).slice(0, 5);
  $("#tl").innerHTML = rows.map(([date, list]) => {
    const hit = date === C.REG_EFFECTIVE;
    const names = [...new Set(list.map((x) => x.label))];
    const shown = names.slice(0, 3).join(", ") + (names.length > 3 ? ` 외 ${names.length - 3}곳` : "");
    return `<div class="ev${hit ? " hit" : ""}"><div class="dt">${date}</div>
      <div class="ti">${hit ? "지금 보고 있는 변경 — " : ""}규제지역 지정 ${names.length}곳</div>
      <div class="ds">${shown} · 이 날짜를 기준으로 한도 판정이 달라집니다</div></div>`;
  }).join("");
})();

document.querySelectorAll("#aff-lender button").forEach((b) => b.addEventListener("click", () => {
  lender = b.dataset.lender;
  document.querySelectorAll("#aff-lender button").forEach((x) => x.classList.toggle("on", x === b));
  affRender();
}));
$("#aff").addEventListener("input", affRender);
cite($("#aff-evi"), ["_AFF_CAP", "_AFF_DSR", "_AFF_DTI", "_AFF_TERM"], "");

// ---- 조작 ----
document.querySelectorAll("#own button").forEach((b) => b.addEventListener("click", () => {
  own = b.dataset.own;
  document.querySelectorAll("#own button").forEach((x) => x.classList.toggle("on", x === b));
  run();
}));
$("#gf-yes").addEventListener("click", () => {
  $("#contract").value = "__BEFORE_CUT__"; $("#downpay").checked = true; run();
});
$("#gf-no").addEventListener("click", () => {
  $("#contract").value = ""; $("#accepted").value = ""; $("#downpay").checked = false; run();
});
$("#cond").addEventListener("input", run);
run();

// ---- ④ 근거 우선 Q&A — 쉬운 요약(미리 검수된 안내) + 원문 발췌 + 전체 보기 ----
//      요약은 질문 의도 매칭으로 고르는 사전 작성 안내문이지, 답을 생성하는 LLM이 아니다.
const INDEX = buildIndex(IDX_EXPORT);
// 발췌는 **질문어가 걸린 문장부터** 보여준다(2026-08-19 폰 리뷰: 420자 구간을 그대로 실으면
// 첫 줄이 앞 페이지 꼬리라 질문과 무관해 보인다). 겹치는 어휘가 하나도 없으면 근거로 제시할
// 수 없으므로 그 결과는 버린다 — 점수 임계를 지어내는 대신 "질문어가 있는가"로 자른다.
function pickSentences(text, qTerms, max) {
  const ss = sentences(text);
  const scored = ss.map((s, i) => ({ s, i, n: sentScore(s, qTerms) })).filter((x) => x.n > 0);
  if (!scored.length) return null;
  scored.sort((a, b) => b.n - a.n || a.i - b.i);
  const top = scored[0].n;
  // 같은 카드에 실을 두 번째 문장은 **가장 잘 맞은 문장의 절반 이상**일 때만 붙인다.
  // 절대 점수에 의미를 부여하지 않기 위한 상대 기준이다 — 점수 임계를 지어내지 않는다.
  const keep = scored.filter((x) => x.n >= top * 0.5).slice(0, max).sort((a, b) => a.i - b.i);
  return { marks: keep.map((x) => x.s), leading: keep[0].i > 0, score: top };
}
function matchEasy(q) {
  let best = null, bestN = 0;
  for (const e of EASY) {
    const n = e.keys.filter((k) => q.includes(k)).length;
    if (n > bestN) { best = e; bestN = n; }
  }
  return best;
}
// 강조 없이 원문만 여는 버튼 — 질문에 답하지 못해도 **원문은 그대로** 보여준다.
// marks 를 비워 openDoc 을 부르면 음영 없이 전체가 열린다(2026-08-20 폰 리뷰).
function docBtns() {
  return DOCS_NOW.map((doc) => {
    const d = DOCL[doc] ?? {};
    return `<button type="button" class="dbtn" data-t="${tgt(doc, [])}">${d.title ?? doc}`
      + `<small>${d.issuer ?? ""} · ${d.published ?? ""} · 음영 없이 전체 보기</small></button>`;
  }).join("");
}
$("#docrow").innerHTML = `<div class="src-t">공문 원문 그대로 읽기</div>` + docBtns();

function ask(q) {
  if (!q.trim()) return;
  $("#q").value = q;
  const easy = matchEasy(q);
  const hits = search(INDEX, q, 3, { expand: true, docIds: DOCS_NOW });
  const box = $("#hits");
  let html = "";
  if (easy) {
    html += `<div class="easy"><span class="easy-tag">쉬운 요약 · 미리 검수된 안내</span>`
      + `<div class="easy-tx">${easy.easy}</div>`
      + easy.cites.map(qciteHtml).join("") + `</div>`;
  }
  const qTerms = qTermsOf(q);
  const picks = [];
  for (const h of hits) {
    const picked = pickSentences(h.chunk.text, qTerms, 2);
    if (picked) picks.push({ h, picked });       // 질문어가 하나도 없는 발췌는 근거가 아니다
  }
  // 칸을 채우려고 약한 결과까지 끌어오면 "근거"라는 말이 헐거워진다. 가장 잘 맞은 발췌의
  // 40% 에 못 미치면 싣지 않는다 — 역시 상대 기준이며 절대 품질을 주장하지 않는다.
  const best = picks.reduce((mx, p) => Math.max(mx, p.picked.score), 0);
  const cards = picks.filter((p) => p.picked.score >= best * 0.4).map(({ h, picked }) => {
    const d = DOCL[h.chunk.doc_id] ?? {};
    return `<button type="button" class="hit-c" data-t="${tgt(h.chunk.doc_id, picked.marks)}">`
      + `<div class="meta">${d.issuer ?? ""} · ${d.title ?? h.chunk.doc_id}</div>`
      + `<div class="tx">${picked.leading ? "… " : ""}${picked.marks.join(" ")}</div>`
      + `<span class="open">공문 전체에서 이 문장 보기 →</span></button>`;
  });
  if (cards.length) {
    // "관련된 문장"이라고 단정하지 않는다 — 어휘가 겹치는 문장을 고른 것이지 의도를 이해한
    // 것이 아니다. 화면이 할 수 있는 주장만 한다.
    //
    // 검수된 답이 있을 때 이 문단들을 같은 비중으로 나열하면, **검수되지 않은 문단이 답처럼**
    // 보인다(2026-08-20 폰 리뷰: 엉뚱한 곳에 음영). 검수된 답의 근거는 요약 카드 안의 인용이고,
    // 어휘가 겹친 문단은 접어서 보조로 둔다. 요약이 없을 때만 이것이 유일한 단서다.
    html += easy
      ? `<details class="more xtra"><summary>공문에서 이 질문의 표현이 나온 다른 문단 `
        + `${cards.length}개 — 검수된 답은 아니에요</summary>`
        + `<div class="xtra-b">${cards.join("")}</div></details>`
      : `<div class="src-t">공문에서 질문 표현이 나온 문장</div>` + cards.join("");
  }
  const hasHits = cards.length > 0;
  if (!easy && !hasHits) {
    // 못 찾았다고 화면을 비우면 막다른 길이다 — 지어내지 않되, 읽을 것은 남겨 준다.
    html = `<div class="consult"><b>이 질문에 딱 맞는 답은 공문에서 찾지 못했어요.</b>
      지어내서 답하지 않아요 — 아래 <b>공문 원문 그대로 읽기</b>에서 전체 내용을 보실 수 있고,
      판단이 어려우면 전문 상담(대출 상담 창구·콜센터)으로 확인하세요.</div>`;
  } else if (!easy) {
    html = `<div class="consult">이 질문의 <b>쉬운 요약은 아직 준비되지 않았어요.</b>
      아래는 질문에 나온 표현이 들어 있는 공문 문장이라 <b>질문과 무관할 수 있어요</b> —
      판단이 어렵거나 찾는 내용이 아니면 전문 상담으로 확인하세요.</div>` + html;
  }
  box.innerHTML = html;
}
$("#q").addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); ask($("#q").value); } });
document.querySelectorAll(".qa .preset button").forEach((b) =>
  b.addEventListener("click", () => ask(b.dataset.q)));
</script>"""

    demo_region = "GURI" if "GURI" in regions else regions[0]
    demo = {
        "code": demo_region,
        "label": fixtures["regions"][demo_region]["label"],
        "contract": before_cut,
    }
    script = (
        script_tpl
        .replace("__FX__", json.dumps(fixtures, ensure_ascii=False, separators=(",", ":")))
        .replace("__DEMO__", json.dumps(demo, ensure_ascii=False))
        .replace("__EASY__", json.dumps(easy, ensure_ascii=False))
        .replace("__DOCS_FULL__", json.dumps(docs_full, ensure_ascii=False))
        .replace("__IDX__", json.dumps(customer_export, ensure_ascii=False, separators=(",", ":")))
        .replace("__QUOTES__", json.dumps(quotes, ensure_ascii=False))
        .replace("__DOCL__", json.dumps(doc_labels, ensure_ascii=False))
        .replace("__DOCS_NOW__", json.dumps(docs_630, ensure_ascii=False))
        .replace("__RULE_KO__", json.dumps(_RULE_KO, ensure_ascii=False))
        .replace("__BEFORE_CUT__", before_cut)
        .replace("__ENGINE__", ENGINE_JS.read_text(encoding="utf-8"))
        .replace("__AFFORD__", AFFORD_JS.read_text(encoding="utf-8"))
        .replace("__SEARCH__", SEARCH_JS.read_text(encoding="utf-8"))
    )

    return f"""<!DOCTYPE html>
<html lang="ko"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>내 한도 시그널 · 규제 변경 개인화 시뮬레이터</title>
<meta name="description" content="규제가 바뀐 다음 날, 내 대출 한도가 얼마에서 얼마로 달라졌고 나는 경과규정 대상인지 — 근거 조문과 함께.">
{FONTS}
<style>{CSS}{_SIGNAL_CSS}</style>
</head><body class="sg">
<div class="dock">
{pitch}
{body}
</div>
{script}
</body></html>"""
