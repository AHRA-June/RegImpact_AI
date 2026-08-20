"""시연 모드 — 풀스크린 데모 무대 (시연동영상 녹화 + 라이브 시연 겸용).

목적: 심사역이 3분 안에 "무엇이 문제고, 이 시스템이 무엇을 하며, 왜 믿을 수 있는지"를
보게 한다. 7막 구성 — 발표(훅) → 원문 등록 → AI 추출 → 룰 변경안 → **라이브 판정** →
포트폴리오 영향 → 검증 성적표.

원칙은 본편 화면과 같다:
  - **수치는 전부 evidence·픽스처에서 온다.** 시연이라고 좋은 숫자를 지어내는 순간
    이 제품의 존재 이유(검증)가 무너진다. 스코어카드의 "미측정 2"도 그대로 싣는다.
  - 라이브 판정은 플레이그라운드와 **같은 JS 엔진 포팅본** — Python 원본과 전 케이스
    대조(verify_js_port)를 통과해야만 배포된다. 시연용 별도 로직을 두지 않는다.
  - 사이드바 없는 독립 무대(랜딩과 같은 층) — 녹화 화면을 메뉴가 오염하지 않는다.
    '이 페이지는?' 설명은 ℹ 오버레이 뒤에 있다(전 페이지 설명 규율은 유지).

조작: ←/→ 넘김 · Space 자동재생 · 하단 HUD(재생/전체화면) · 모바일 세로 대응.
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

from ..impact.builder import derive_rule_diff
from ..report.evidence import ValidationEvidence
from .intake import load_snapshots
from .theme import CSS, FONTS, esc, explainer

ENGINE_JS = Path(__file__).resolve().parent / "static" / "engine.js"

_DEMO_CSS = """
html,body{height:100%}
body.demo{margin:0;background:var(--background);color:var(--on-surface);overflow:hidden}
#stage{position:relative;height:100%;width:100%}
.act{position:absolute;inset:0;display:flex;flex-direction:column;justify-content:center;
  align-items:center;padding:48px 28px 96px;opacity:0;visibility:hidden;
  transition:opacity .45s ease;overflow-y:auto}
.act.on{opacity:1;visibility:visible;z-index:1}
.act-in{width:100%;max-width:1060px;margin:auto 0}
/* 등장 비트 — 막이 켜질 때 자식이 순서대로 떠오른다 */
.b{opacity:0;transform:translateY(14px);transition:opacity .5s ease,transform .5s ease}
.act.on .b{opacity:1;transform:none}
.act.on .b:nth-child(2){transition-delay:.15s}.act.on .b:nth-child(3){transition-delay:.3s}
.act.on .b:nth-child(4){transition-delay:.45s}.act.on .b:nth-child(5){transition-delay:.6s}
.act.on .b:nth-child(6){transition-delay:.75s}
.kicker{font-family:'JetBrains Mono',ui-monospace,monospace;font-size:12px;letter-spacing:.1em;
  text-transform:uppercase;color:var(--primary);font-weight:600;margin-bottom:14px}
.act h1{font-size:clamp(26px,4.6vw,52px);line-height:1.16;font-weight:700;
  letter-spacing:-.02em;margin:0 0 16px;max-width:22ch;word-break:keep-all}
.act .lede,.note,.card,.scn button{word-break:keep-all}
.act .lede{font-size:clamp(14px,1.7vw,19px);line-height:1.55;color:var(--on-surface-variant);
  max-width:62ch;margin:0}
.lede strong{color:var(--on-surface)}
.dates{display:flex;align-items:center;gap:clamp(10px,2.5vw,26px);margin:34px 0 8px;flex-wrap:wrap}
.dates .d{font-family:'JetBrains Mono',ui-monospace,monospace;
  font-size:clamp(24px,4.2vw,46px);font-weight:600}
.dates .d small{display:block;font-size:12px;font-weight:400;color:var(--on-surface-variant);
  letter-spacing:.04em;margin-top:6px}
.dates .arrow{font-size:clamp(20px,3vw,32px);color:var(--primary)}
.dates .d.hot{color:var(--error)}
.chips{display:flex;gap:8px;flex-wrap:wrap;margin-top:22px}
.chips span{padding:6px 13px;border-radius:99px;border:1px solid var(--outline-variant);
  background:var(--surface-container-lowest);font-size:13px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:12px;margin-top:26px}
.card{background:var(--surface-container-lowest);border:1px solid var(--outline-variant);
  border-radius:10px;padding:18px}
.card .t{font-size:14px;font-weight:600;line-height:1.4}
.card .i{font-size:12px;color:var(--on-surface-variant);margin-top:4px}
.card .h{font-family:'JetBrains Mono',ui-monospace,monospace;font-size:11px;
  color:var(--primary);margin-top:12px;word-break:break-all}
.card .m{font-size:12px;color:var(--on-surface-variant);margin-top:8px}
.bignum{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:1px;
  background:var(--outline-variant);border:1px solid var(--outline-variant);border-radius:10px;
  overflow:hidden;margin-top:28px}
.bignum .s{background:var(--surface-container-lowest);padding:20px}
.bignum .v{font-family:'JetBrains Mono',ui-monospace,monospace;
  font-size:clamp(22px,3vw,34px);font-weight:600;line-height:1.1}
.bignum .v.good{color:var(--secondary)}.bignum .v.bad{color:var(--error)}
.bignum .l{font-size:12px;line-height:17px;color:var(--on-surface-variant);margin-top:8px}
.flip{display:flex;align-items:baseline;gap:clamp(12px,3vw,30px);margin:30px 0 6px;flex-wrap:wrap}
.flip .v{font-family:'JetBrains Mono',ui-monospace,monospace;font-weight:600;
  font-size:clamp(44px,9vw,96px);line-height:1}
.flip .v.old{color:var(--on-surface-variant);text-decoration:line-through;
  text-decoration-thickness:5px;text-decoration-color:var(--error)}
.flip .v.new{color:var(--error)}
.flip .arrow{font-size:clamp(26px,4vw,44px);color:var(--on-surface-variant)}
.flip .cond{font-size:14px;color:var(--on-surface-variant)}
.rows{margin-top:22px;border:1px solid var(--outline-variant);border-radius:10px;overflow:hidden}
.rows .r{display:grid;grid-template-columns:minmax(110px,1.4fr) auto auto auto;gap:12px;
  align-items:center;padding:11px 16px;border-bottom:1px solid var(--outline-variant);font-size:14px}
.rows .r:last-child{border-bottom:0}
.rows .mono{font-family:'JetBrains Mono',ui-monospace,monospace;font-size:14px}
.rows .to{color:var(--on-surface-variant)}
.rows .chg{color:var(--error);font-weight:600}.rows .keep{color:var(--secondary)}
.note{margin-top:22px;padding:14px 18px;background:var(--surface-container-low);
  border-left:3px solid var(--primary);border-radius:0 6px 6px 0;font-size:13.5px;
  line-height:1.55;color:var(--on-surface-variant);max-width:72ch}
.note strong{color:var(--on-surface)}
/* 라이브 판정 */
.live{display:grid;grid-template-columns:1fr;gap:16px;margin-top:24px}
@media(min-width:860px){.live{grid-template-columns:300px minmax(0,1fr)}}
.scn{display:flex;flex-direction:column;gap:8px}
.scn button{text-align:left;padding:12px 14px;border:1px solid var(--outline-variant);
  border-radius:8px;background:var(--surface-container-lowest);color:var(--on-surface);
  font-family:inherit;font-size:13.5px;cursor:pointer}
.scn button small{display:block;color:var(--on-surface-variant);font-size:11.5px;margin-top:3px}
.scn button.sel{border-color:var(--primary);box-shadow:0 0 0 1px var(--primary) inset}
.verdict{display:flex;align-items:baseline;gap:16px;flex-wrap:wrap;padding:20px 24px;
  border-radius:10px;border:1px solid var(--outline-variant);background:var(--surface-container-lowest)}
.verdict .ltv{font-family:'JetBrains Mono',ui-monospace,monospace;
  font-size:clamp(40px,6vw,64px);font-weight:600;line-height:1}
.verdict.ok .ltv{color:var(--secondary)}.verdict.zero .ltv{color:var(--error)}
.verdict.review .ltv{font-size:clamp(22px,3vw,30px);color:var(--on-tertiary-fixed-variant)}
.verdict .st{font-size:13px;color:var(--on-surface-variant)}
.badge{display:inline-block;padding:2px 8px;border-radius:99px;font-size:10.5px;font-weight:600;
  background:var(--surface-container-highest);color:var(--on-surface-variant);margin-left:8px}
.trace{margin-top:12px;border:1px solid var(--outline-variant);border-radius:8px;overflow:hidden;
  max-height:34vh;overflow-y:auto}
.trace .row{display:grid;grid-template-columns:44px 1fr;gap:10px;padding:8px 12px;
  border-bottom:1px solid var(--outline-variant);font-size:12.5px;line-height:18px}
.trace .row:last-child{border-bottom:0}
.trace .row.hit{background:var(--surface-container-low)}
.trace .id{font-family:'JetBrains Mono',ui-monospace,monospace;font-size:11px;font-weight:600;
  color:var(--primary)}
.trace .row:not(.hit) .id{color:var(--outline)}
.trace .note2{color:var(--on-surface-variant);font-size:11.5px}
/* 클로징 */
.cta{display:flex;gap:10px;flex-wrap:wrap;margin-top:30px}
.cta a{padding:12px 18px;border-radius:8px;font-size:14px;font-weight:600;text-decoration:none}
.cta a.pri{background:var(--primary);color:var(--on-primary,#fff)}
.cta a.sec{border:1px solid var(--outline-variant);color:var(--on-surface)}
.url{font-family:'JetBrains Mono',ui-monospace,monospace;font-size:13px;color:var(--primary);
  margin-top:22px}
/* HUD */
#hud{position:fixed;left:0;right:0;bottom:0;z-index:5;display:flex;align-items:center;
  gap:10px;padding:12px 18px;background:color-mix(in srgb,var(--background) 88%,transparent);
  backdrop-filter:blur(6px);border-top:1px solid var(--outline-variant);flex-wrap:wrap}
#hud button{font-family:inherit;font-size:12.5px;padding:7px 12px;border-radius:99px;
  border:1px solid var(--outline-variant);background:var(--surface-container-lowest);
  color:var(--on-surface);cursor:pointer}
#hud button:hover{border-color:var(--primary)}
#hud .dots{display:flex;gap:6px;align-items:center}
#hud .dots i{width:8px;height:8px;border-radius:99px;background:var(--outline-variant);
  cursor:pointer}
#hud .dots i.on{background:var(--primary);width:22px;transition:width .2s}
#hud .sp{flex:1}
#hud a.exit{font-size:12.5px;color:var(--on-surface-variant);text-decoration:none}
#hud a.exit:hover{color:var(--primary)}
#bar{position:fixed;left:0;top:0;height:3px;width:100%;z-index:6;pointer-events:none}
#bar i{display:block;height:100%;width:0;background:var(--primary)}
#info{position:fixed;top:14px;right:16px;z-index:6;width:32px;height:32px;border-radius:99px;
  border:1px solid var(--outline-variant);background:var(--surface-container-lowest);
  color:var(--on-surface-variant);font-family:'JetBrains Mono',monospace;cursor:pointer}
#infobox{position:fixed;top:56px;right:16px;z-index:6;max-width:420px;max-height:70vh;
  overflow-y:auto;box-shadow:0 12px 40px rgba(0,0,0,.18)}
#infobox[hidden]{display:none}
.actno{font-family:'JetBrains Mono',ui-monospace,monospace;font-size:11px;
  color:var(--outline);letter-spacing:.08em;margin-bottom:10px}
@media(max-width:700px){
  .act{padding:28px 18px 120px;justify-content:flex-start}
  .rows .r{grid-template-columns:1fr auto auto auto;font-size:12.5px}
}
"""


def _pct(v) -> str:
    return "—" if v is None else f"{v:.0%}"


def _won_ok(v: float) -> str:
    return f"{abs(v) / 1e8:,.0f}억원"


def _act(no: int, kicker: str, inner: str, dur_ms: int) -> str:
    return (
        f'<section class="act" data-dur="{dur_ms}">'
        f'<div class="act-in"><div class="actno b">ACT {no} / 7</div>'
        f'<div class="kicker b">{esc(kicker)}</div>{inner}</div></section>'
    )


def render(ev: ValidationEvidence, fixtures: dict) -> str:
    """시연 무대. 수치는 전부 evidence·픽스처에서 온다 — 여기 리터럴 도메인 값을 적지 않는다."""
    C = fixtures["constants"]
    g, im, r = ev.grounding, ev.impact, ev.regression
    sc = ev.scorecard.summary()

    pub = ev.this_policy.published_at.isoformat()          # 발표일
    eff = C["REG_EFFECTIVE"]                               # 시행일
    cutoff = C["GRANDFATHERING_CUTOFF"]                    # 경과규정 컷오프
    after_eff = (date.fromisoformat(eff) + timedelta(days=14)).isoformat()
    before_cut = (date.fromisoformat(cutoff) - timedelta(days=2)).isoformat()

    regions = ev.extraction.target_regions
    labels = [fixtures["regions"][c]["label"] for c in regions if c in fixtures["regions"]]
    demo_region = "GURI" if "GURI" in regions else regions[0]
    demo_label = fixtures["regions"][demo_region]["label"]

    diff = derive_rule_diff()
    std = next(d for d in diff if d["rule_id"] == "REG_STD")
    others = [d for d in diff if d["rule_id"] != "REG_STD"]

    snapshots = [s for s in load_snapshots(ev.extraction) if s["doc_id"].endswith("20260630")]

    def _app(**over) -> dict:
        base = dict(
            region_code=demo_region, evaluation_date=eff, house_count=0,
            disposal_condition_flag=False, first_home_buyer=False, real_demand_flag=False,
            policy_mortgage_flag=False, loan_purpose="HOME_PURCHASE",
            application_accepted_at=None, contract_signed_at=None, downpayment_paid_at=None,
            land_permit_target=False, land_permit_applied_at=None,
        )
        base.update(over)
        return base

    scenes = [
        {"key": "before", "label": f"발표일 당일 · {pub}",
         "sub": f"{demo_label} 무주택 — 아직 시행 전", "app": _app(evaluation_date=pub)},
        {"key": "after", "label": f"시행일 · {eff}",
         "sub": f"같은 차주, 하루 뒤 — 강화 규제 적용", "app": _app(evaluation_date=eff)},
        {"key": "gf", "label": "경과규정 — 시행 전 계약 차주",
         "sub": f"{cutoff}까지 계약·계약금 → 시행 후에도 종전규정",
         "app": _app(evaluation_date=after_eff, contract_signed_at=before_cut,
                     downpayment_paid_at=before_cut)},
        {"key": "unknown", "label": "레지스트리 미등록 지역",
         "sub": "모르는 지역은 비규제로 흘리지 않는다 — 사람 검토",
         "app": _app(region_code="BUSAN_HAEUNDAE", evaluation_date=after_eff)},
    ]

    # ---- 막 1 · 훅 --------------------------------------------------------
    act1 = _act(1, "RegImpact AI — 시연", f"""
<h1 class="b">{esc(pub[:4])}년 {int(pub[5:7])}월 {int(pub[8:10])}일 저녁,<br>규제지역이 추가 지정됐다</h1>
<p class="lede b">발표 다음 날부터 강화 규제가 적용된다. 은행은 하루 안에
<strong>심사 기준·전산·창구 안내</strong>를 전부 바꿔야 하고, 하나라도 틀리면
고객 손해와 소급 정정으로 돌아온다.</p>
<div class="dates b">
  <div class="d">{esc(pub)}<small>대책 발표</small></div>
  <div class="arrow">→</div>
  <div class="d hot">{esc(eff)}<small>강화 규제 시행</small></div>
</div>
<div class="chips b">{"".join(f"<span>{esc(l)}</span>" for l in labels)}
  <span>신규 규제지역 {len(labels)}곳</span></div>
""", 9000)

    # ---- 막 2 · 원문 등록 -------------------------------------------------
    doc_cards = "".join(
        f'<div class="card"><div class="t">{esc(s["title"])}</div>'
        f'<div class="i">{esc(s["issuer"])} · {esc(s["published"])}</div>'
        f'<div class="h">SHA-256 {esc(s["sha256"][:16])}…</div>'
        f'<div class="m">추출 {s["changes"]}건의 출처</div></div>'
        for s in snapshots
    )
    act2 = _act(2, "1단계 — 원문 등록", f"""
<h1 class="b">모든 것은 원문에서 시작한다</h1>
<p class="lede b">공문 {len(snapshots)}건을 해시로 봉인해 등록한다. 이후의 모든 산출물은
<strong>어느 원문의 어느 문장</strong>에서 나왔는지 추적된다.</p>
<div class="cards b">{doc_cards}</div>
<div class="note b"><strong>위·변조 탐지 가능한 출발점.</strong> 산출물이 원문 레지스트리와
어긋나면 빌드 자체가 실패한다 — 배포된 화면은 항상 봉인된 원문 위에 서 있다.</div>
""", 9000)

    # ---- 막 3 · AI 추출 ---------------------------------------------------
    act3 = _act(3, "2단계 — AI 추출", f"""
<h1 class="b">AI가 변경사항을 읽는다 —<br>단, 인용 없이는 한 줄도 쓰지 못한다</h1>
<p class="lede b">LLM이 공문에서 규제 변경을 구조화해 추출한다. 모든 항목에 원문 인용이
붙고, 인용은 기계가 <strong>원문과 글자 단위로 대조</strong>한다.</p>
<div class="bignum b">
  <div class="s"><div class="v">{len(ev.extraction.changes)}건</div>
    <div class="l">추출된 변경·예외 항목</div></div>
  <div class="s"><div class="v good">{g.grounded}/{g.total}</div>
    <div class="l">인용 → 원문 대조 통과 (인용 정확성 {g.citation_correctness:.0%})</div></div>
  <div class="s"><div class="v">{len(labels)}곳</div>
    <div class="l">신규 규제지역 자동 매핑</div></div>
</div>
<div class="note b"><strong>AI는 초안까지, 확정은 사람.</strong> 원문에 없는 값은 추정하지
않고 사람 검토로 올린다 — 지어낸 답 한 줄이 심사 사고가 되는 도메인이기 때문.</div>
""", 9000)

    # ---- 막 4 · 룰 변경안 -------------------------------------------------
    other_rows = "".join(
        '<div class="r">'
        f'<div>{esc(d["condition"])}</div>'
        f'<div class="mono to">{_pct(d["before"])}</div>'
        f'<div class="mono {"chg" if d["before"] != d["after"] else "keep"}">{_pct(d["after"])}</div>'
        f'<div class="{"chg" if d["before"] != d["after"] else "keep"}">'
        f'{"변경" if d["before"] != d["after"] else "좌동"}</div></div>'
        for d in others
    )
    act4 = _act(4, "3단계 — 룰 변경안", f"""
<h1 class="b">심사 기준이 이렇게 바뀐다</h1>
<div class="flip b">
  <div class="v old">{_pct(std["before"])}</div>
  <div class="arrow">→</div>
  <div class="v new">{_pct(std["after"])}</div>
  <div class="cond">{esc(std["condition"])} LTV<br>시행 {esc(eff)}부터</div>
</div>
<div class="rows b">{other_rows}</div>
<div class="note b"><strong>LLM은 실행 룰을 만들지 않는다.</strong> 위 값은 사람이 확정한
규칙 명세를 구현한 결정적 엔진의 상수다. {esc(cutoff)}까지 계약·접수한 차주는
<strong>경과규정</strong>으로 종전 기준을 유지한다.</div>
""", 10000)

    # ---- 막 5 · 라이브 판정 -----------------------------------------------
    scene_btns = "".join(
        f'<button type="button" data-scene="{s["key"]}">{esc(s["label"])}'
        f'<small>{esc(s["sub"])}</small></button>'
        for s in scenes
    )
    act5 = _act(5, "4단계 — 라이브 판정 (지금 이 화면에서 실행 중)", f"""
<h1 class="b">같은 차주, 하루 차이 — 판정이 갈린다</h1>
<div class="live b">
  <div class="scn">{scene_btns}</div>
  <div>
    <div class="verdict" id="verdict"></div>
    <div class="trace" id="trace"></div>
  </div>
</div>
<div class="note b"><strong>시연용 목업이 아니다.</strong> 지금 브라우저에서 도는 이 엔진은
원본(Python) 엔진과 판정 {len(fixtures["cases"])}건 + 지역×시점 조회 전건을 자동 대조해
전부 일치할 때만 배포된다. 판정 값만이 아니라 <strong>어느 규칙에서 멈췄는지</strong>까지 보여준다.</div>
""", 22000)

    # ---- 막 6 · 포트폴리오 영향 -------------------------------------------
    act6 = _act(6, "5단계 — 고객·포트폴리오 영향", f"""
<h1 class="b">우리 고객 중 누가, 얼마나 영향을 받나</h1>
<p class="lede b">보유 신청 건 {im.portfolio_size:,}건을 시행 전·후 두 시점으로 전량 재평가한다.</p>
<div class="bignum b">
  <div class="s"><div class="v bad">{len(im.reduced):,}건</div>
    <div class="l">한도 감소 (전체의 {im.affected_rate:.1%})</div></div>
  <div class="s"><div class="v bad">−{_won_ok(im.total_limit_reduction)}</div>
    <div class="l">총 한도 감소액</div></div>
  <div class="s"><div class="v good">{im.grandfathered_count:,}건</div>
    <div class="l">경과규정 보호 — 종전규정 유지</div></div>
  <div class="s"><div class="v">{im.decision_coverage:.1%}</div>
    <div class="l">자동 판정 커버리지</div></div>
</div>
<div class="note b"><strong>100%가 아닌 것이 정직함이다.</strong> 원문에 기준값이 없는
구간은 추정하지 않고 사유와 함께 사람 검토로 넘긴다 — 지어내면 커버리지는 즉시 100%가 된다.
(합성 포트폴리오 계산 결과 — 실 고객데이터 미사용)</div>
""", 10000)

    # ---- 막 7 · 검증 + 클로징 ---------------------------------------------
    act7 = _act(7, "이 시스템이 믿을 만한가 — 성적표까지 함께 낸다", f"""
<h1 class="b">숫자가 아니라 <em>증명</em>을 내는 시스템</h1>
<div class="bignum b">
  <div class="s"><div class="v good">{sc["passed"]}/{sc["total"]}</div>
    <div class="l">검증 스코어카드 통과 (미측정 {sc["not_measured"]} — 통과로 치지 않음)</div></div>
  <div class="s"><div class="v good">{g.citation_correctness:.0%}</div>
    <div class="l">인용 → 원문 실재 대조</div></div>
  <div class="s"><div class="v good">{r.passed}/{r.total}</div>
    <div class="l">룰엔진 ↔ 독립 명세 오라클 회귀</div></div>
  <div class="s"><div class="v">{len(ev.audit.events)}건</div>
    <div class="l">해시체인 감사로그 — 산출 과정 위·변조 탐지</div></div>
</div>
<div class="note b">규제 대응의 결과물에 <strong>검증보고서·모델카드·리스크 레지스터</strong>가
같은 실행에서 함께 생성된다 — 감독 대응과 내부 증빙에 그대로 쓸 수 있는 형태다.</div>
<div class="cta b">
  <a class="pri" href="index.html">전체 화면 보러 가기</a>
  <a class="sec" href="playground.html">판정 직접 만져보기</a>
  <a class="sec" href="validation_summary.html">검증 요약 1페이지</a>
</div>
<div class="url b">ahra-june.github.io/RegImpact_AI</div>
""", 14000)

    info = explainer(
        "제품 흐름(발표→원문→추출→룰 변경→판정→영향→검증)을 7개 장면으로 압축한 시연 화면입니다.",
        "본편 화면들과 같은 파이프라인 실행 결과. 시연이라고 숫자를 꾸미지 않았고, "
        "라이브 판정은 원본 엔진과 전 케이스 대조를 통과한 포팅본이 브라우저에서 직접 돕니다.",
        "←/→ 또는 하단 점으로 넘기고, Space(또는 ▶)로 자동 재생합니다. 녹화할 때는 "
        "전체화면 + 자동 재생을 켜세요.",
    )

    engine = ENGINE_JS.read_text(encoding="utf-8")
    script_tpl = """
<script type="module">
const FX = __FX__;
const SCENES = __SCENES__;
__ENGINE__

const $ = (s) => document.querySelector(s);
const acts = [...document.querySelectorAll(".act")];
const dots = $("#hud .dots");
acts.forEach((_, i) => {
  const d = document.createElement("i");
  d.addEventListener("click", () => go(i));
  dots.appendChild(d);
});

// ---- 라이브 판정 (막 5) — 플레이그라운드와 같은 엔진, 같은 렌더 규칙 ----
const pct = (v) => (v === null || v === undefined) ? "—" : `${Math.round(v * 100)}%`;
const STATUS_KO = {
  DECIDED: "판정 완료", OUT_OF_SCOPE: "코어 판정 대상 아님",
  DISCOVERY: "수동 정책 검토 대상", NEEDS_HUMAN_REVIEW: "사람 검토 필요",
};
function showScene(key) {
  const s = SCENES.find((x) => x.key === key);
  document.querySelectorAll("[data-scene]").forEach((b) =>
    b.classList.toggle("sel", b.dataset.scene === key));
  const { decision, trace } = evaluate(FX, s.app);
  const v = $("#verdict");
  v.className = "verdict " + (
    decision.status !== "DECIDED" ? "review" : decision.max_ltv === 0 ? "zero" : "ok");
  v.innerHTML =
    `<div class="ltv">${decision.status === "DECIDED" ? "LTV " + pct(decision.max_ltv) : "사람 검토"}</div>`
    + `<div class="st">${STATUS_KO[decision.status] ?? decision.status}`
    + (decision.grandfathering_applied ? '<span class="badge">경과규정 적용</span>' : "")
    + `<br><span>${s.label}</span></div>`;
  $("#trace").innerHTML = trace.map((t) =>
    `<div class="row ${t.hit ? "hit" : ""}"><div class="id">${t.id}</div>`
    + `<div>${t.label}<div class="note2">${t.note}</div></div></div>`).join("");
}
document.querySelectorAll("[data-scene]").forEach((b) =>
  b.addEventListener("click", () => { stopAuto(); showScene(b.dataset.scene); }));
showScene(SCENES[0].key);

// ---- 무대 진행 ----
let cur = 0, auto = false, timer = null, sceneTimer = null;
const LIVE_ACT = 4;   // 0-based — 막 5
function go(i) {
  cur = Math.max(0, Math.min(acts.length - 1, i));
  acts.forEach((a, k) => a.classList.toggle("on", k === cur));
  [...dots.children].forEach((d, k) => d.classList.toggle("on", k === cur));
  if (auto) armAuto();
}
function armAuto() {
  clearTimeout(timer); clearInterval(sceneTimer);
  const dur = Number(acts[cur].dataset.dur || 8000);
  const bar = $("#bar i");
  bar.style.transition = "none"; bar.style.width = "0";
  requestAnimationFrame(() => requestAnimationFrame(() => {
    bar.style.transition = `width ${dur}ms linear`; bar.style.width = "100%";
  }));
  if (cur === LIVE_ACT) {           // 자동 재생 중엔 장면을 차례로 넘겨준다
    let si = 0; showScene(SCENES[0].key);
    sceneTimer = setInterval(() => {
      si = (si + 1) % SCENES.length;
      const s = SCENES[si];
      document.querySelectorAll("[data-scene]").forEach((b) =>
        b.classList.toggle("sel", b.dataset.scene === s.key));
      showSceneKeepAuto(s.key);
    }, Math.floor(dur / (SCENES.length + 0.5)));
  }
  timer = setTimeout(() => {
    if (cur < acts.length - 1) go(cur + 1); else stopAuto();
  }, dur);
}
function showSceneKeepAuto(key) {   // 자동 순환용 — stopAuto 없이
  const s = SCENES.find((x) => x.key === key);
  const { decision, trace } = evaluate(FX, s.app);
  const v = $("#verdict");
  v.className = "verdict " + (
    decision.status !== "DECIDED" ? "review" : decision.max_ltv === 0 ? "zero" : "ok");
  v.innerHTML =
    `<div class="ltv">${decision.status === "DECIDED" ? "LTV " + pct(decision.max_ltv) : "사람 검토"}</div>`
    + `<div class="st">${STATUS_KO[decision.status] ?? decision.status}`
    + (decision.grandfathering_applied ? '<span class="badge">경과규정 적용</span>' : "")
    + `<br><span>${s.label}</span></div>`;
  $("#trace").innerHTML = trace.map((t) =>
    `<div class="row ${t.hit ? "hit" : ""}"><div class="id">${t.id}</div>`
    + `<div>${t.label}<div class="note2">${t.note}</div></div></div>`).join("");
}
function startAuto() {
  auto = true; $("#play").textContent = "⏸ 일시정지"; armAuto();
}
function stopAuto() {
  auto = false; clearTimeout(timer); clearInterval(sceneTimer);
  const bar = $("#bar i");
  bar.style.transition = "none"; bar.style.width = "0";
  $("#play").textContent = "▶ 자동 재생";
}
$("#play").addEventListener("click", () => auto ? stopAuto() : startAuto());
$("#prev").addEventListener("click", () => { stopAuto(); go(cur - 1); });
$("#next").addEventListener("click", () => { stopAuto(); go(cur + 1); });
$("#fs").addEventListener("click", () =>
  document.fullscreenElement ? document.exitFullscreen()
                             : document.documentElement.requestFullscreen());
document.addEventListener("keydown", (e) => {
  if (e.key === "ArrowRight") { stopAuto(); go(cur + 1); }
  else if (e.key === "ArrowLeft") { stopAuto(); go(cur - 1); }
  else if (e.key === " ") { e.preventDefault(); auto ? stopAuto() : startAuto(); }
});
$("#info").addEventListener("click", () => {
  const b = $("#infobox"); b.hidden = !b.hidden;
});
go(0);
</script>"""
    script = (
        script_tpl
        .replace("__FX__", json.dumps(fixtures, ensure_ascii=False, separators=(",", ":")))
        .replace("__SCENES__", json.dumps(scenes, ensure_ascii=False, separators=(",", ":")))
        .replace("__ENGINE__", engine)
    )

    return f"""<!DOCTYPE html>
<html lang="ko"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>시연 모드 · RegImpact AI</title>
<meta name="description" content="규제 발표부터 심사 반영·검증까지 — RegImpact AI 3분 시연.">
{FONTS}
<style>{CSS}{_DEMO_CSS}</style>
</head><body class="demo">
<div id="bar"><i></i></div>
<button id="info" title="이 페이지는?">i</button>
<div id="infobox" hidden>{info}</div>
<div id="stage">
{act1}{act2}{act3}{act4}{act5}{act6}{act7}
</div>
<div id="hud">
  <button id="prev" title="이전 (←)">‹</button>
  <div class="dots"></div>
  <button id="next" title="다음 (→)">›</button>
  <button id="play">▶ 자동 재생</button>
  <button id="fs">⛶ 전체화면</button>
  <div class="sp"></div>
  <a class="exit" href="index.html">시연 종료 — 사이트로 ↗</a>
</div>
{script}
</body></html>"""
