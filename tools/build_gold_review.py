"""골드 v2 도메인 검수표 생성 — 사람이 확정할 수 있는 형태로 펼친다.

검수는 사람의 일이지만(LOCKED §4), **검수 가능하게 만드는 것**은 기계가 할 수 있다:
각 주장 옆에 원문 인용을 붙이고, 확정 명세와 충돌하는 항목을 먼저 올린다.
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from regimpact.eval import Split, check_gold_against_spec, load_split  # noqa: E402
from regimpact import rule_engine as R  # noqa: E402

REASON = "검수표 생성 — 확정 명세 대조용, 정답 출력 없음 (튜닝 아님)"
gold = json.loads((REPO / "docs/eval/regchange_gold_6_30.json").read_text(encoding="utf-8"))

# 채점 특이도 — 이 entry가 실제 추출 결과에서 몇 건에 걸리는가.
# 너무 넓으면(=대부분에 걸리면) 사실상 항상 통과하는 무의미한 항목이고,
# 0건이면 채점 자체가 불가능하다. 검수자가 "이 항목이 실제로 무언가를 재는가"를 볼 수 있게 싣는다.
import re as _re  # noqa: E402
from regimpact.extractor.schema import RegChangeExtraction  # noqa: E402

_run = json.loads((REPO / "docs/eval/runs/run_perdoc_sonnet5.json").read_text(encoding="utf-8"))
_items = RegChangeExtraction.from_dict(_run["extraction"]).changes


def _n(x):
    return _re.sub(r"\s+", "", (x or "")).lower()


def specificity(entry):
    if "transition" in entry:
        t = entry["transition"]
        n = sum(
            1 for c in _items
            if (not t.get("before") or _n(t["before"]) == _n(c.before))
            and (not t.get("after") or _n(t["after"]) == _n(c.after))
        )
        return n, f"전이 대조 {t.get('before', '—')} → {t.get('after', '—')}"
    hay = [_n(f"{c.summary}{c.before or ''}{c.after or ''}") for c in _items]
    n = sum(1 for h in hay if any(_n(k) in h for k in entry["keywords"]))
    return n, "키워드"

items = []
for sp in Split:
    items += load_split(sp, **({} if sp == Split.DEV else {"unseal_reason": REASON}))
conf = check_gold_against_spec(items)
by_id = {i.id: i for i in items}

VER = gold["_version"].split()[0]
from regimpact.eval import check_confirmation  # noqa: E402

status = check_confirmation(gold)
L = [f"# 추출 골드 {VER} 도메인 검수표", "",
     f"> 생성: `python tools/build_gold_review.py` · **{status.summary()}**", ""]
if status.needs_review:
    L += ["> ⚠️ 확정 이후 채점 관련 내용이 바뀌었다. 바뀐 항목을 다시 확인해야 한다.", ""]
elif status.confirmed:
    L += ["> 이 문서는 이제 **검수 기록**이다. 골드를 손보면 지문이 어긋나 재검수가 필요함이 드러난다.", ""]

# ---------------------------------------------------------------- §1
resolved = [i for i in items if i.authored_by == "human_confirmed"]

if conf.conflicts:
    L += ["---", "", f"## 1. ⚠️ 우선 검토 — 확정 명세와 충돌 {len(conf.conflicts)}건", "",
          "아래는 **골드가 `05_RULE_SPEC`(사용자 확정)과 어긋나는** 항목이다. 둘 중 하나는 틀렸고,",
          "고치기 전까지는 이 항목들이 만드는 모든 수치가 의미를 잃는다. **가장 먼저 판단이 필요하다.**", ""]
else:
    L += ["---", "", f"## 1. ✅ 확정 명세와 충돌 없음 (검수 완료 {len(resolved)}건)", "",
          "명세 대조에서 걸린 항목이 없다. 아래는 검수로 **정정된** 항목의 기록이다.", ""]
    for it in resolved:
        L += [f"#### `{it.id}` — {it.category.value} · {it.split.value}",
              f"- **질문:** {it.question}",
              f"- **확정 답:** {it.gold_answer}",
              f"- **정정 사유:** {it.note}", ""]
for c in conf.conflicts:
    gid = c.split("]")[0].strip("[ ")
    it = by_id[gid]
    L += [f"### `{gid}` ({it.category.value} · {it.split.value})", "",
          f"- **질문:** {it.question}",
          f"- **현재 골드 답:** {it.gold_answer}",
          f"- **충돌:** {c.split('] ', 1)[1]}", "",
          "  근거 인용(원문에서 기계적으로 잘라 온 것 — verbatim은 보장됨):"]
    for cit in it.citations:
        L.append(f"  > [{cit.source_doc_id}] {' '.join(cit.quote.split())[:150]}")
    L += ["", "  **✍️ 판단:** ☐ 골드가 틀림(수정) ☐ 명세가 틀림(명세 수정) ☐ 둘 다 맞음(문맥이 다름)", ""]

# ---------------------------------------------------------------- §2
L += ["---", "", "## 2. 왜 이 충돌이 생겼나 — FAQ Q2 표 평탄화", "",
      "FAQ 원문은 HWP다. 텍스트로 추출하면 표의 **LTV 열과 DTI 열이 한 줄로 뭉개진다.**", "",
      "```", "일반 차주", "60%(아파트 限)", "조정대상지역(아파트 限) 50%", "투기과열지구 40%", "```", "",
      "평탄화된 이 텍스트만 보면 60/50/40이 전부 LTV로 읽힌다. 그러나 사용자가 **원본 이미지로 확정한**",
      f"`05_RULE_SPEC` §C에서 규제지역 LTV는 투기과열·조정 모두 **{R.LTV_REGULATED_STANDARD:.0%}** 이고,",
      f"종류별로 갈리는 40/50은 **DTI**다. 非규제(수도권) 기준선 LTV는 **{R.LTV_BASELINE:.0%}** 이다.", "",
      "**따라서 원문 텍스트만 보고 작성한 문항은 이 혼동을 반복한다.** 검수 시 원본",
      "(`docs/sources/original/faq_20260630.hwp`)의 표를 눈으로 대조하는 것이 확실하다.", "",
      "이 결함 유형은 이제 `check_gold_against_spec()`이 자동으로 잡는다(`pytest -k consistency`).", ""]

# ---------------------------------------------------------------- §3
L += ["---", "", f"## 3. 추출 골드 {VER} — 필수 변경 {len(gold['required_changes'])}건", "",
      "각 항목은 \"공문이 이것을 말하고 있다\"는 주장이다. 인용이 그 주장을 뒷받침하는지 확인한다.", ""]
for r in gold["required_changes"]:
    n, how = specificity(r)
    mark = "✅" if r.get("authored_by") == "human_confirmed" else "☐"
    L += [f"#### {mark} `{r['id']}` — {r['claim']}",
          f"- 채점: {how} · 현재 추출 {len(_items)}건 중 **{n}건**에 매칭"
          + ("  ⚠ 0건이면 채점 불가" if n == 0 else "")]
    if "transition" not in r:
        L.append(f"- 키워드: `{'`, `'.join(r['keywords'])}`")
    for cit in r["citations"]:
        L.append(f"  > [{cit['source_doc_id']}] {' '.join(cit['quote'].split())[:150]}")
    L.append("")

L += ["---", "", f"## 4. 추출 골드 {VER} — 예외 {len(gold['exceptions'])}건", ""]
for e in gold["exceptions"]:
    n, _ = specificity(e)
    mark = "✅" if e.get("authored_by") == "human_confirmed" else "☐"
    L += [f"#### {mark} `{e['name']}` — {e['claim']}",
          f"- 채점: 키워드 `{'`, `'.join(e['keywords'])}` · 현재 추출 {len(_items)}건 중 **{n}건**에 매칭"]
    for cit in e["citations"]:
        L.append(f"  > [{cit['source_doc_id']}] {' '.join(cit['quote'].split())[:150]}")
    L.append("")

# ---------------------------------------------------------------- §5
L += ["---", "", "## 5. 검수 범위와 우선순위", "",
      "| 대상 | 규모 | 상태 | 비고 |", "|---|---:|---|---|",
      f"| 추출 골드 {VER} (이 문서 §3·§4) | {len(gold['required_changes'])}+{len(gold['exceptions'])} | 🤖 초안 | "
      "Extractor 지표(Completeness/Exception Recall)의 기준 |",
      f"| QA 골드 DEV | {len(load_split(Split.DEV))} | 🤖 초안 | 튜닝에 쓰는 유일한 셋 — 다음 우선순위 |",
      "| QA 골드 LOCKED / CHALLENGE | 40 / 35 | 🤖 초안 · 🔒 봉인 | 충돌 3건만 먼저 보고 나머지는 개봉 시 |", "",
      "> 봉인된 셋의 충돌 항목을 이 문서에 옮겨 적은 것은 **정답 전체를 여는 것이 아니라** 명세와",
      "> 어긋난 3건만 드러낸 것이다. 접근은 `SEAL_ACCESS_LOG.md`에 기록돼 있다.", "",
      "**검수가 끝나면:** 해당 항목의 `authored_by`를 `human_confirmed`로 바꾸고",
      "`python tools/build_gold_review.py`로 이 표를 다시 생성한다.", ""]

out = REPO / "docs" / "eval" / "GOLD_REVIEW.md"
out.write_text("\n".join(L), encoding="utf-8")
print(f"검수표 생성: {out.relative_to(REPO)} ({len(L)}줄, 충돌 {len(conf.conflicts)}건)")

# ---------------------------------------------------------------- HTML 검수표
# 마크다운과 같은 데이터에서 생성한다 — 두 벌을 손으로 맞추면 반드시 어긋난다.
import html as _h  # noqa: E402

def esc(x):
    return _h.escape(str(x), quote=True)

def quote_block(cits):
    return "".join(
        f'<figure class="q"><figcaption>{esc(c["source_doc_id"] if isinstance(c, dict) else c.source_doc_id)}</figcaption>'
        f'<blockquote>{esc(" ".join((c["quote"] if isinstance(c, dict) else c.quote).split())[:220])}</blockquote></figure>'
        for c in cits
    )

conflict_cards = []
for c in conf.conflicts:
    gid = c.split("]")[0].strip("[ ")
    it = by_id[gid]
    detail = c.split("] ", 1)[1]
    spec_claim = detail.split(" — ", 1)[1] if " — " in detail else detail
    conflict_cards.append(f"""
    <article class="conflict">
      <header>
        <span class="id">{esc(gid)}</span>
        <span class="tag">{esc(it.category.value)}</span>
        <span class="tag seal">{esc(it.split.value)}</span>
      </header>
      <p class="ask">{esc(it.question)}</p>
      <div class="face-off">
        <div class="side gold">
          <span class="side-label">골드 초안이 말하는 것</span>
          <p>{esc(it.gold_answer)}</p>
        </div>
        <div class="versus" aria-hidden="true">vs</div>
        <div class="side spec">
          <span class="side-label">확정 명세가 말하는 것</span>
          <p>{esc(spec_claim)}</p>
        </div>
      </div>
      {quote_block(it.citations)}
      <fieldset class="verdict">
        <legend>판정</legend>
        <label><input type="radio" name="v-{esc(gid)}"> 골드가 틀림 — 골드 수정</label>
        <label><input type="radio" name="v-{esc(gid)}"> 명세가 틀림 — 명세 수정</label>
        <label><input type="radio" name="v-{esc(gid)}"> 둘 다 맞음 — 문맥이 다름</label>
      </fieldset>
    </article>""")

resolved_cards = []
for it in resolved:
    resolved_cards.append(f"""
    <article class="conflict resolved">
      <header>
        <span class="id ok">{esc(it.id)}</span>
        <span class="tag">{esc(it.category.value)}</span>
        <span class="tag seal">{esc(it.split.value)}</span>
        <span class="tag done">확정</span>
      </header>
      <p class="ask">{esc(it.question)}</p>
      <div class="side spec"><span class="side-label">확정된 답</span><p>{esc(it.gold_answer)}</p></div>
      <p class="why">{esc(it.note)}</p>
      {quote_block(it.citations)}
    </article>""")


def check_items(entries, key):
    out = []
    for e in entries:
        done = e.get("authored_by") == "human_confirmed"
        out.append(f"""
      <li class="item{' confirmed' if done else ''}">
        <label class="check"><input type="checkbox" class="cb"{' checked' if done else ''}><span></span></label>
        <div class="body">
          <div class="head"><code>{esc(e[key])}</code><span class="claim">{esc(e["claim"])}</span></div>
          <div class="kw">{"".join(f'<kbd>{esc(k)}</kbd>' for k in (e["keywords"] if "transition" not in e else [f'{e["transition"].get("before","—")} → {e["transition"].get("after","—")}']))}<span class="hits">{specificity(e)[0]}건 매칭</span></div>
          {quote_block(e["citations"])}
        </div>
      </li>""")
    return "".join(out)

total_items = len(gold["required_changes"]) + len(gold["exceptions"])
html = f"""<title>추출 골드 {VER} 검수표</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@500;700&family=Noto+Sans+KR:wght@400;500;700&family=JetBrains+Mono:wght@400;500&display=swap">
<style>
:root {{
  --ground:#fcf8ff; --panel:#ffffff; --panel-2:#f5f2ff; --line:#c4c6cf;
  --ink:#1a1a2e; --ink-2:#43474e; --navy:#022448; --action:#0051d5;
  --alarm:#ba1a1a; --alarm-bg:#ffdad6; --alarm-ink:#93000a;
  --pend:#edbf7f; --pend-bg:#fff4e2; --pend-ink:#60410c;
  --ok:#0051d5;
}}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
    --ground:#12121c; --panel:#1b1b28; --panel-2:#222232; --line:#3a3a4d;
    --ink:#eceaf6; --ink-2:#a9adbe; --navy:#adc8f5; --action:#8fb2ff;
    --alarm:#ff8a80; --alarm-bg:#3d1512; --alarm-ink:#ffb4ab;
    --pend:#edbf7f; --pend-bg:#3a2c14; --pend-ink:#f0d3a3;
    --ok:#8fb2ff;
  }}
}}
:root[data-theme="dark"] {{
  --ground:#12121c; --panel:#1b1b28; --panel-2:#222232; --line:#3a3a4d;
  --ink:#eceaf6; --ink-2:#a9adbe; --navy:#adc8f5; --action:#8fb2ff;
  --alarm:#ff8a80; --alarm-bg:#3d1512; --alarm-ink:#ffb4ab;
  --pend:#edbf7f; --pend-bg:#3a2c14; --pend-ink:#f0d3a3;
  --ok:#8fb2ff;
}}
*,*::before,*::after {{ box-sizing:border-box; }}
body {{
  background:var(--ground); color:var(--ink); margin:0;
  font-family:'Noto Sans KR',system-ui,sans-serif; line-height:1.7;
  padding:clamp(20px,4vw,56px) clamp(16px,5vw,40px);
}}
.wrap {{ max-width:920px; margin:0 auto; display:flex; flex-direction:column; gap:40px; }}
h1,h2,h3 {{ font-family:'Noto Serif KR',Georgia,serif; text-wrap:balance; margin:0; }}
h1 {{ font-size:clamp(28px,4.5vw,40px); letter-spacing:-.02em; color:var(--navy); }}
h2 {{ font-size:22px; letter-spacing:-.01em; padding-bottom:10px; border-bottom:2px solid var(--navy); }}
p {{ margin:0; }}
.lede {{ color:var(--ink-2); max-width:62ch; }}
.meta {{ display:flex; flex-wrap:wrap; gap:8px; font-family:'JetBrains Mono',monospace; font-size:12px; }}
.meta span {{ background:var(--panel-2); border:1px solid var(--line); padding:3px 9px; border-radius:3px; color:var(--ink-2); }}
section {{ display:flex; flex-direction:column; gap:18px; }}

.conflict {{ background:var(--panel); border:1px solid var(--line); border-left:5px solid var(--alarm);
  border-radius:4px; padding:22px; display:flex; flex-direction:column; gap:16px; }}
.conflict header {{ display:flex; flex-wrap:wrap; align-items:center; gap:8px; }}
.id {{ font-family:'JetBrains Mono',monospace; font-size:13px; font-weight:500; color:var(--alarm-ink);
  background:var(--alarm-bg); padding:3px 9px; border-radius:3px; }}
.tag {{ font-size:11px; letter-spacing:.06em; text-transform:uppercase; color:var(--ink-2);
  border:1px solid var(--line); padding:2px 8px; border-radius:99px; }}
.tag.seal::before {{ content:"🔒 "; }}
.ask {{ font-family:'Noto Serif KR',serif; font-size:17px; font-weight:500; }}
.face-off {{ display:grid; grid-template-columns:1fr auto 1fr; gap:14px; align-items:stretch; }}
@media (max-width:640px) {{ .face-off {{ grid-template-columns:1fr; }} .versus {{ justify-self:start; }} }}
.side {{ padding:14px; border-radius:4px; background:var(--panel-2); border:1px solid var(--line); }}
.side.gold {{ border-color:var(--pend); background:var(--pend-bg); }}
.side.spec {{ border-color:var(--action); }}
.side-label {{ display:block; font-size:11px; letter-spacing:.06em; text-transform:uppercase;
  color:var(--ink-2); margin-bottom:6px; }}
.side.gold .side-label {{ color:var(--pend-ink); }}
.side.spec .side-label {{ color:var(--action); }}
.side p {{ font-size:14px; }}
.versus {{ align-self:center; font-family:'JetBrains Mono',monospace; font-size:12px; color:var(--ink-2); }}
.verdict {{ border:1px dashed var(--line); border-radius:4px; padding:12px 14px; margin:0;
  display:flex; flex-wrap:wrap; gap:14px; }}
.verdict legend {{ font-size:11px; letter-spacing:.06em; text-transform:uppercase; color:var(--ink-2); padding:0 6px; }}
.verdict label {{ display:flex; align-items:center; gap:7px; font-size:14px; cursor:pointer; }}

.conflict.resolved {{ border-left-color:var(--ok); }}
.id.ok {{ color:var(--panel); background:var(--ok); }}
.tag.done {{ border-color:var(--ok); color:var(--ok); }}
.why {{ font-size:13.5px; color:var(--ink-2); border-left:3px solid var(--ok); padding-left:12px; }}
.q {{ margin:0; border-left:3px solid var(--line); padding-left:12px; }}
.q figcaption {{ font-family:'JetBrains Mono',monospace; font-size:11px; color:var(--action); margin-bottom:3px; }}
.q blockquote {{ margin:0; font-family:'JetBrains Mono',monospace; font-size:12.5px; line-height:1.65;
  color:var(--ink-2); word-break:keep-all; }}

.note {{ background:var(--panel-2); border:1px solid var(--line); border-radius:4px; padding:18px;
  display:flex; flex-direction:column; gap:12px; }}
.note pre {{ margin:0; overflow-x:auto; background:var(--panel); border:1px solid var(--line);
  border-radius:3px; padding:12px; font-family:'JetBrains Mono',monospace; font-size:12px; color:var(--ink-2); }}

ol.items {{ list-style:none; margin:0; padding:0; display:flex; flex-direction:column; gap:2px; }}
.item {{ display:flex; gap:14px; padding:14px 12px; border-bottom:1px solid var(--line); }}
.item:has(.cb:checked) {{ background:var(--panel-2); }}
.item.confirmed {{ border-left:3px solid var(--ok); }}
.item:has(.cb:checked) .claim {{ color:var(--ink-2); text-decoration:line-through; }}
.check {{ flex-shrink:0; padding-top:3px; cursor:pointer; }}
.check input {{ position:absolute; opacity:0; width:0; height:0; }}
.check span {{ display:block; width:20px; height:20px; border:2px solid var(--line); border-radius:3px; }}
.check input:checked + span {{ background:var(--ok); border-color:var(--ok); }}
.check input:checked + span::after {{ content:"✓"; display:block; color:var(--panel); font-size:14px;
  line-height:16px; text-align:center; }}
.check input:focus-visible + span {{ outline:2px solid var(--action); outline-offset:2px; }}
.body {{ display:flex; flex-direction:column; gap:7px; min-width:0; }}
.head {{ display:flex; flex-wrap:wrap; align-items:baseline; gap:10px; }}
.head code {{ font-family:'JetBrains Mono',monospace; font-size:12.5px; color:var(--navy);
  background:var(--panel-2); padding:2px 7px; border-radius:3px; }}
.claim {{ font-weight:500; }}
.kw {{ display:flex; flex-wrap:wrap; gap:5px; }}
kbd {{ font-family:'JetBrains Mono',monospace; font-size:11px; color:var(--ink-2);
  border:1px solid var(--line); border-radius:3px; padding:1px 6px; }}
.hits {{ font-family:'JetBrains Mono',monospace; font-size:11px; color:var(--action); }}

.progress {{ position:fixed; bottom:18px; left:50%; transform:translateX(-50%); z-index:10;
  background:var(--navy); color:var(--ground); font-family:'JetBrains Mono',monospace; font-size:13px;
  padding:9px 18px; border-radius:99px; box-shadow:0 4px 16px rgba(0,0,0,.28); }}
:root[data-theme="dark"] .progress, :root:not([data-theme="light"]) .progress {{ color:#12121c; }}
footer {{ color:var(--ink-2); font-size:13px; border-top:1px solid var(--line); padding-top:16px; }}
@media (prefers-reduced-motion:reduce) {{ * {{ transition:none !important; animation:none !important; }} }}
</style>

<div class="wrap">
  <header style="display:flex;flex-direction:column;gap:14px">
    <h1>추출 골드 {VER} 검수표</h1>
    <p class="lede">6·30 RegChange 추출 골드 {total_items}항목. 인용은 원문에서 기계적으로 잘라 왔으므로 verbatim은 보장되지만,
    <strong>그 인용이 그 주장을 뒷받침하는지는 사람이 판단할 몫</strong>이다.</p>
    <div class="meta">
      <span>{esc(status.summary())}</span><span>충돌 {len(conf.conflicts)}건</span>
      <span>필수 변경 {len(gold["required_changes"])}</span><span>예외 {len(gold["exceptions"])}</span>
    </div>
  </header>

  <section>
    <h2>{"1. 확정 명세와 충돌 — 먼저 판단이 필요한 " + str(len(conf.conflicts)) + "건" if conf.conflicts else "1. 검수 완료 — 정정된 " + str(len(resolved)) + "건"}</h2>
    <p class="lede">{"둘 중 하나는 틀렸다. 고치기 전까지 이 항목들이 만드는 수치는 의미를 잃는다." if conf.conflicts else "명세 대조에서 걸린 항목이 없다. 아래는 검수로 정정된 항목의 기록이다."}</p>
    {"".join(conflict_cards) if conf.conflicts else "".join(resolved_cards)}
  </section>

  <section>
    <h2>2. 왜 생겼나 — FAQ Q2 표 평탄화</h2>
    <div class="note">
      <p>FAQ 원문은 HWP다. 텍스트로 추출하면 표의 <strong>LTV 열과 DTI 열이 한 줄로 뭉개진다.</strong></p>
      <pre>일반 차주
60%(아파트 限)
조정대상지역(아파트 限) 50%
투기과열지구 40%</pre>
      <p>평탄화된 이 텍스트만 보면 60/50/40이 전부 LTV로 읽힌다. 그러나 원본 이미지로 확정한
      <code>05_RULE_SPEC</code> §C에서 규제지역 LTV는 투기과열·조정 <strong>모두 {R.LTV_REGULATED_STANDARD:.0%}</strong>이고,
      종류별로 갈리는 40/50은 <strong>DTI</strong>다. 非규제(수도권) 기준선 LTV는 <strong>{R.LTV_BASELINE:.0%}</strong>다.</p>
      <p>원문 텍스트만 보고 작성하면 이 혼동은 반드시 재발한다. 확실한 확인은 원본
      <code>docs/sources/original/faq_20260630.hwp</code>의 표를 눈으로 대조하는 것이다.
      이 결함 유형은 이제 <code>check_gold_against_spec()</code>이 자동으로 잡는다.</p>
    </div>
  </section>

  <section>
    <h2>3. 필수 변경 {len(gold["required_changes"])}건</h2>
    <p class="lede">각 항목은 "공문이 이것을 말하고 있다"는 주장이다.</p>
    <ol class="items">{check_items(gold["required_changes"], "id")}</ol>
  </section>

  <section>
    <h2>4. 예외 {len(gold["exceptions"])}건</h2>
    <ol class="items">{check_items(gold["exceptions"], "name")}</ol>
  </section>

  <footer style="padding-bottom:52px">
    검수 후 해당 항목의 <code>authored_by</code>를 <code>human_confirmed</code>로 바꾸고
    <code>python tools/build_gold_review.py</code>로 이 표를 다시 생성하세요.
    체크 상태는 <strong>저장되지 않습니다</strong> — 한 번의 검수 세션용 진행 표시입니다.
  </footer>
</div>
<div class="progress" id="prog">확인 0 / {total_items}</div>

<script>
const boxes = [...document.querySelectorAll('.cb')], prog = document.getElementById('prog');
const sync = () => prog.textContent = `확인 ${{boxes.filter(b => b.checked).length}} / ${{boxes.length}}`;
boxes.forEach(b => b.addEventListener('change', sync));
sync();
</script>"""

html_out = REPO / "docs" / "eval" / "gold_review.html"
html_out.write_text(html, encoding="utf-8")
print(f"HTML 검수표: {html_out.relative_to(REPO)} ({len(html):,} bytes)")
