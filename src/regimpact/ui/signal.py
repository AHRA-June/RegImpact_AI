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

from ..report.evidence import ValidationEvidence
from .intake import load_snapshots
from .theme import CSS, FONTS, esc, explainer

ENGINE_JS = Path(__file__).resolve().parent / "static" / "engine.js"
SEARCH_JS = Path(__file__).resolve().parent / "static" / "search.js"

_SIGNAL_CSS = """
body.sg{margin:0;background:var(--surface-container-low);color:var(--on-surface)}
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
.gfbox{border-top:1px dashed var(--outline-variant);margin-top:13px;padding-top:13px}
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
  background:var(--surface-container-lowest)}
.hit-c .meta{font-size:10.5px;color:var(--primary);
  font-family:'JetBrains Mono',ui-monospace,monospace;margin-bottom:6px}
.hit-c .tx{font-size:12.5px;line-height:1.6;color:var(--on-surface);word-break:keep-all}
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
    docs_630 = sorted({c.citation.source_doc_id for c in ev.extraction.changes})

    region_opts = "".join(
        f'<option value="{esc(code)}"{" selected" if code == "GURI" else ""}>'
        f'{esc(meta["label"])}</option>'
        for code, meta in sorted(fixtures["regions"].items(), key=lambda kv: kv[1]["label"])
    )

    presets_qa = [
        "잔금일이 시행일 뒤인데 저는 어떻게 되나요",
        "생애최초인데 한도가 줄어드나요",
        "계약금을 냈으면 종전 규정을 적용받나요",
        "전세대출도 영향이 있나요",
    ]
    preset_btns = "".join(
        f'<button type="button" data-q="{esc(q)}">{esc(q)}</button>' for q in presets_qa)

    info = explainer(
        "규제가 바뀌었을 때 '내 대출 한도가 얼마에서 얼마로 달라지는지'를 조건 몇 가지로 "
        "확인하는 고객용 시뮬레이터입니다 (Tomorrow Challenge 제안 화면 · 금융앱 웹뷰 탑재형).",
        "판정은 검증 시스템(RegImpact AI)의 심사 엔진을 웹으로 옮긴 것 — 원본과 판정 "
        f"{n_cases}건·지역 조회 {n_probe}건을 자동 대조해 전부 일치할 때만 배포됩니다. "
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
    <li><b>②</b><span><b>전/후 비교</b> — 변경 전·후 한도를 나란히, 어느 규칙에서 판정됐는지까지</span></li>
    <li><b>③</b><span><b>경과규정 체크</b> — 계약·계약금·접수 일자로 종전 규정 적용 여부</span></li>
    <li><b>④</b><span><b>근거 우선 Q&A</b> — 원문을 검색해 근거 문단을 보여주고, 없으면 지어내지 않고 상담 안내</span></li>
  </ul>
  <div class="vbadge"><b>AI가 판정하지 않는 AI 서비스.</b> LLM은 공문에서 사실만 추출하고
  판정은 결정적 룰엔진이 합니다. 이 화면의 엔진은 원본과 판정 {n_cases}건 + 지역 조회
  {n_probe}건 자동 대조 후에만 배포되며, 서버 호출 없이 브라우저 안에서 돌아
  고객 입력이 밖으로 나가지 않습니다.</div>
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

      <div class="gfbox">
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

    <details class="more"><summary>이 판정, 어떻게 나왔나요? (판정 경로)</summary>
      <div class="trace" id="trace"></div></details>
    <details class="more" open><summary>근거 조문 (공문 원문 그대로)</summary>
      <div class="evi" id="evi"></div></details>

    <div class="sec-t">④ 물어보기 — 근거가 있을 때만 답합니다</div>
    <div class="panel qa">
      <input type="text" id="q" placeholder="예) 잔금일이 시행일 뒤인데 저는 어떻게 되나요">
      <div class="preset">{preset_btns}</div>
      <div class="hits" id="hits"></div>
      <div class="honesty" style="margin-top:11px">지금은 질문과 관련된 <b>공문 원문 문단</b>을
      찾아 그대로 보여줍니다(검색 품질은 정답셋 기준 실측). 문장으로 답을 만들어 주는
      LLM 연결은 PoC 기간 배선 목표이며, 그때도 근거 없는 답은 만들지 않습니다.</div>
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
</div>"""

    script_tpl = """
<script type="module">
const FX = __FX__;
const IDX_EXPORT = __IDX__;
const QUOTES = __QUOTES__;
const DOCL = __DOCL__;
const DOCS_NOW = __DOCS_NOW__;
const RULE_KO = __RULE_KO__;
__ENGINE__
__SEARCH__

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
function won(x) {  // 원 → "N억 M천만원"
  const eok = Math.floor(x / 1e8), chun = Math.round((x % 1e8) / 1e7);
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

function cite(box, keys, fallback) {
  box.innerHTML = keys.filter((k) => QUOTES[k]).map((k) => {
    const q = QUOTES[k], d = DOCL[q.doc] ?? {};
    return `<div class="q-cite">“${q.quote}”`
      + `<span class="src">${d.issuer ?? ""} · ${d.title ?? q.doc} · ${d.published ?? ""}</span></div>`;
  }).join("") || `<div class="q-cite">${fallback}</div>`;
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
        + `계약·접수 시점에 따라 경과규정 대상일 수 있으니 아래 ③을 확인하세요.`;
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
}

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

// ---- ④ 근거 우선 Q&A — BM25 포팅본 (원본과 전 프로브 대조 후 배포) ----
const INDEX = buildIndex(IDX_EXPORT);
const clean = (t) => t.replace(/-{2,}\\s*p\\d+\\s*-{2,}/g, " ").replace(/\\s+/g, " ").trim();
function ask(q) {
  if (!q.trim()) return;
  $("#q").value = q;
  const hits = search(INDEX, q, 3, { expand: true, docIds: DOCS_NOW });
  const box = $("#hits");
  if (!hits.length) {
    box.innerHTML = `<div class="consult"><b>이 질문의 근거를 공문에서 찾지 못했어요.</b>
      지어내서 답하지 않아요 — 전문 상담(대출 상담 창구·콜센터)을 안내해 드릴게요.</div>`;
    return;
  }
  box.innerHTML = hits.map((h) => {
    const d = DOCL[h.chunk.doc_id] ?? {};
    return `<div class="hit-c"><div class="meta">${d.issuer ?? ""} · ${d.title ?? h.chunk.doc_id}</div>`
      + `<div class="tx">${clean(h.chunk.text)}</div></div>`;
  }).join("");
}
$("#q").addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); ask($("#q").value); } });
document.querySelectorAll(".qa .preset button").forEach((b) =>
  b.addEventListener("click", () => ask(b.dataset.q)));
</script>"""

    script = (
        script_tpl
        .replace("__FX__", json.dumps(fixtures, ensure_ascii=False, separators=(",", ":")))
        .replace("__IDX__", json.dumps(search_export, ensure_ascii=False, separators=(",", ":")))
        .replace("__QUOTES__", json.dumps(quotes, ensure_ascii=False))
        .replace("__DOCL__", json.dumps(doc_labels, ensure_ascii=False))
        .replace("__DOCS_NOW__", json.dumps(docs_630, ensure_ascii=False))
        .replace("__RULE_KO__", json.dumps(_RULE_KO, ensure_ascii=False))
        .replace("__BEFORE_CUT__", before_cut)
        .replace("__ENGINE__", ENGINE_JS.read_text(encoding="utf-8"))
        .replace("__SEARCH__", SEARCH_JS.read_text(encoding="utf-8"))
    )

    return f"""<!DOCTYPE html>
<html lang="ko"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
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
