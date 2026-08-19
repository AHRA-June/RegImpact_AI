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
      f"| QA 골드 DEV | {len(load_split(Split.DEV))} | 🤖 초안 | 튜닝에 쓰는 유일한 셋 — 검수표는 `QA_GOLD_REVIEW.md` (`python tools/build_qa_review.py`) |",
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
# 스타일·이스케이프·인용 블록은 QA 검수표와 공유한다(review_theme).
from review_theme import FONTS_LINK, REVIEW_CSS, esc, quote_block  # noqa: E402

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
{FONTS_LINK}
<style>{REVIEW_CSS}</style>

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
