"""인터랙티브 플레이그라운드 — 차주 조건을 바꾸면 즉시 판정이 바뀐다.

화면에 룰엔진 **JS 포팅본**이 들어간다. 두 번째 룰 구현을 두는 것 자체가 위험이므로
`tools/verify_js_port.mjs` 가 Python 엔진 픽스처와 전 케이스를 대조하고, 대조가 실패하면
CI 가 배포를 막는다. 규칙 **값**은 JS 에 없다 — 픽스처에서 읽는다.

판정만 보여주지 않고 **어느 규칙에서 멈췄는지(trace)** 를 함께 보여준다.
"왜 이 값인가"를 못 보여주면 검증 시스템의 화면이 아니다.
"""
from __future__ import annotations

import json
from pathlib import Path

from ..report.evidence import ValidationEvidence
from .theme import CSS, FONTS, esc

ENGINE_JS = Path(__file__).resolve().parent / "static" / "engine.js"

_PG_CSS = """
body{background:var(--background);color:var(--on-surface)}
.wrap{max-width:1180px;margin:0 auto;padding:0 24px 80px}
.nav{display:flex;align-items:center;gap:12px;padding:16px 0}
.nav a{font-size:13px;color:var(--primary);font-weight:500}
.nav a:hover{text-decoration:underline}
h1{font-size:30px;font-weight:700;letter-spacing:-.02em;margin:16px 0 6px}
.lede{font-size:14px;line-height:22px;color:var(--on-surface-variant);max-width:70ch;margin:0 0 8px}
.cols{display:grid;grid-template-columns:1fr;gap:20px;margin-top:24px}
@media(min-width:940px){.cols{grid-template-columns:340px minmax(0,1fr)}}
.panel{background:var(--surface-container-lowest);border:1px solid var(--outline-variant);
  border-radius:8px;padding:18px}
.panel h2{font-size:12px;font-weight:600;letter-spacing:.05em;text-transform:uppercase;
  color:var(--on-surface-variant);margin:0 0 14px}
.f{margin-bottom:13px}
.f label{display:block;font-size:12px;color:var(--on-surface-variant);margin-bottom:4px}
.f select,.f input[type=date],.f input[type=number]{width:100%;padding:7px 9px;font-size:13px;
  font-family:inherit;border:1px solid var(--outline-variant);border-radius:5px;
  background:var(--surface-container-lowest);color:var(--on-surface)}
.chk{display:flex;align-items:flex-start;gap:8px;margin-bottom:9px;font-size:13px;cursor:pointer}
.chk input{margin-top:2px}
.chk small{display:block;color:var(--on-surface-variant);font-size:11px;line-height:15px}
.verdict{display:flex;align-items:baseline;gap:14px;flex-wrap:wrap;padding:18px 20px;
  border-radius:8px;border:1px solid var(--outline-variant);background:var(--surface-container-low)}
.verdict .ltv{font-family:'JetBrains Mono',ui-monospace,monospace;font-size:40px;font-weight:500;
  line-height:1}
.verdict .st{font-size:13px;color:var(--on-surface-variant)}
.verdict.ok .ltv{color:var(--secondary)}
.verdict.zero .ltv{color:var(--error)}
.verdict.review .ltv{font-size:22px;color:var(--on-tertiary-fixed-variant)}
.rule{font-family:'JetBrains Mono',ui-monospace,monospace;font-size:11px;
  color:var(--on-surface-variant);margin-top:10px}
.trace{margin-top:16px;border:1px solid var(--outline-variant);border-radius:8px;overflow:hidden}
.trace .row{display:grid;grid-template-columns:44px 1fr;gap:10px;padding:9px 12px;
  border-bottom:1px solid var(--outline-variant);font-size:12.5px;line-height:19px}
.trace .row:last-child{border-bottom:0}
.trace .row.hit{background:var(--surface-container-low)}
.trace .id{font-family:'JetBrains Mono',ui-monospace,monospace;font-size:11px;font-weight:600;
  color:var(--primary)}
.trace .row:not(.hit) .id{color:var(--outline)}
.trace .note{color:var(--on-surface-variant);font-size:11.5px}
.badge{display:inline-block;padding:2px 7px;border-radius:99px;font-size:10.5px;font-weight:600;
  background:var(--surface-container-highest);color:var(--on-surface-variant);margin-left:8px}
.preset{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:14px}
.preset button{padding:5px 10px;font-size:11.5px;font-family:inherit;cursor:pointer;
  border:1px solid var(--outline-variant);border-radius:99px;background:transparent;
  color:var(--on-surface-variant)}
.preset button:hover{border-color:var(--primary);color:var(--primary)}
.foot{margin-top:20px;padding:14px 16px;background:var(--surface-container-low);
  border-left:3px solid var(--primary);border-radius:0 4px 4px 0;font-size:12.5px;line-height:20px;
  color:var(--on-surface-variant)}
.foot strong{color:var(--on-surface)}
"""

_PRESETS = [
    ("규제지역 무주택", {"region": "GURI", "date": "2026-08-01", "house": 0}),
    ("강남 무주택", {"region": "SEOUL_GANGNAM", "date": "2026-08-01", "house": 0}),
    ("시행 전(6.15) 구리", {"region": "GURI", "date": "2026-06-15", "house": 0}),
    ("수도권 다주택", {"region": "GURI", "date": "2026-08-01", "house": 2}),
    ("비수도권 유주택", {"region": "CHEONGJU", "date": "2026-08-01", "house": 1}),
    ("미등록 지역", {"region": "BUSAN_HAEUNDAE", "date": "2026-08-01", "house": 0}),
]


def render(ev: ValidationEvidence, fixtures: dict) -> str:
    engine = ENGINE_JS.read_text(encoding="utf-8")
    fx_json = json.dumps(fixtures, ensure_ascii=False, separators=(",", ":"))

    region_opts = "".join(
        f'<option value="{esc(code)}">{esc(meta["label"])} ({esc(code)})</option>'
        for code, meta in sorted(fixtures["regions"].items(),
                                 key=lambda kv: kv[1]["label"])
    ) + '<option value="BUSAN_HAEUNDAE">부산 해운대구 — 레지스트리 미등록</option>'

    presets = "".join(
        f'<button type="button" data-preset=\'{json.dumps(v)}\'>{esc(k)}</button>'
        for k, v in _PRESETS
    )

    n_cases = len(fixtures["cases"])
    n_probe = sum(len(v) for v in fixtures["region_probe"].values())

    return f"""<!DOCTYPE html>
<html lang="ko"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>플레이그라운드 — RegImpact AI</title>
{FONTS}<style>{CSS}{_PG_CSS}</style>
</head><body>
<div class="wrap">
  <nav class="nav"><a href="index.html">← 홈</a></nav>
  <h1>판정 플레이그라운드</h1>
  <p class="lede">차주 조건을 바꾸면 즉시 판정이 바뀐다. 값만이 아니라
    <strong>어느 규칙에서 멈췄는지</strong>를 함께 보여준다 — 검증 시스템의 화면이라면
    "왜 이 값인가"를 보여줘야 한다.</p>

  <div class="cols">
    <form class="panel" id="f">
      <h2>차주 조건</h2>
      <div class="preset">{presets}</div>
      <div class="f"><label for="region">지역</label>
        <select id="region">{region_opts}</select></div>
      <div class="f"><label for="date">심사 시점</label>
        <input type="date" id="date" value="2026-08-01"></div>
      <div class="f"><label for="house">보유 주택 수</label>
        <input type="number" id="house" min="0" max="5" value="0"></div>
      <label class="chk"><input type="checkbox" id="disposal">
        <span>처분조건부 1주택<small>기존 주택 처분 조건 — 무주택 기준으로 판정</small></span></label>
      <label class="chk"><input type="checkbox" id="first">
        <span>생애최초 구입자<small>세대원 전원 무주택 이력</small></span></label>
      <label class="chk"><input type="checkbox" id="demand">
        <span>서민·실수요자<small>소득·주택가격 요건 충족</small></span></label>
      <label class="chk"><input type="checkbox" id="policy">
        <span>정책대출<small>디딤돌·보금자리 — 코어 자동판정 제외</small></span></label>
      <label class="chk"><input type="checkbox" id="purpose">
        <span>주택구입목적이 아님<small>생활안정자금 등</small></span></label>
      <h2 style="margin-top:20px">경과규정</h2>
      <div class="f"><label for="accepted">전산 접수일</label>
        <input type="date" id="accepted"></div>
      <div class="f"><label for="contract">매매계약 체결일</label>
        <input type="date" id="contract"></div>
      <label class="chk"><input type="checkbox" id="downpay">
        <span>계약금 납부 증명<small>계약일과 함께 있어야 인정</small></span></label>
    </form>

    <div>
      <div class="verdict" id="verdict"><div class="ltv">—</div><div class="st"></div></div>
      <div class="rule" id="rule"></div>
      <div class="trace" id="trace"></div>
      <div class="foot">
        이 화면의 판정은 <strong>Python 엔진의 JS 포팅본</strong>이 계산한다.
        두 구현이 갈라지면 화면이 조용히 거짓말을 하므로,
        <strong>판정 {n_cases}건 · 지역×시점 프로브 {n_probe}건</strong>을 Python 엔진 실행 결과와
        대조한다. 대조가 실패하면 CI 가 배포를 막는다.
        규칙 <strong>값</strong>은 JS 에 없다 — 픽스처에서 읽는다.
      </div>
    </div>
  </div>
</div>

<script type="module">
const FX = {fx_json};
{engine}

const $ = (id) => document.getElementById(id);
const val = (id) => $(id).value || null;

function readForm() {{
  return {{
    region_code: $("region").value,
    evaluation_date: $("date").value,
    house_count: Number($("house").value || 0),
    disposal_condition_flag: $("disposal").checked,
    first_home_buyer: $("first").checked,
    real_demand_flag: $("demand").checked,
    policy_mortgage_flag: $("policy").checked,
    loan_purpose: $("purpose").checked ? "LIVING_EXPENSE" : "HOME_PURCHASE",
    application_accepted_at: val("accepted"),
    contract_signed_at: val("contract"),
    downpayment_paid_at: $("downpay").checked ? val("contract") : null,
    land_permit_target: false,
    land_permit_applied_at: null,
  }};
}}

const pct = (v) => (v === null || v === undefined) ? "—" : `${{Math.round(v * 100)}}%`;

const STATUS_KO = {{
  DECIDED: "판정 완료", OUT_OF_SCOPE: "코어 판정 대상 아님",
  DISCOVERY: "수동 정책 검토 대상", NEEDS_HUMAN_REVIEW: "사람 검토 필요",
}};

function run() {{
  const {{ decision, trace }} = evaluate(FX, readForm());
  const v = $("verdict");
  v.className = "verdict " + (
    decision.status !== "DECIDED" ? "review" : decision.max_ltv === 0 ? "zero" : "ok");
  v.innerHTML =
    `<div class="ltv">${{decision.status === "DECIDED" ? pct(decision.max_ltv) : "사람 검토"}}</div>`
    + `<div class="st">${{STATUS_KO[decision.status] ?? decision.status}}`
    + (decision.grandfathering_applied ? '<span class="badge">경과규정 적용</span>' : "")
    + `</div>`;
  $("rule").textContent =
    [decision.applicable_rule_id, ...(decision.reason_codes ?? [])].filter(Boolean).join("  ·  ");
  $("trace").innerHTML = trace.map((t) =>
    `<div class="row ${{t.hit ? "hit" : ""}}"><div class="id">${{t.id}}</div>`
    + `<div>${{t.label}}<div class="note">${{t.note}}</div></div></div>`).join("");
}}

$("f").addEventListener("input", run);
document.querySelectorAll("[data-preset]").forEach((b) => {{
  b.addEventListener("click", () => {{
    const p = JSON.parse(b.dataset.preset);
    $("region").value = p.region; $("date").value = p.date; $("house").value = p.house;
    ["disposal","first","demand","policy","purpose","downpay"].forEach((k) => $(k).checked = false);
    $("accepted").value = ""; $("contract").value = "";
    run();
  }});
}});
run();
</script>
</body></html>
"""
