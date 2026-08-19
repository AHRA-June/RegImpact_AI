"""QA 골드 DEV 40문항 도메인 검수표 생성 — 사람이 확정할 수 있는 형태로 펼친다.

추출 골드 검수표(`build_gold_review.py`)와 같은 원칙이다: 검수는 사람의 일이지만(LOCKED §4),
**검수 가능하게 만드는 것**은 기계가 할 수 있다. 각 문항의 골드 답 옆에 원문 인용과
채점 앵커를 붙이고, 사람이 더 자세히 봐야 할 신호를 먼저 올린다:

  ① 확정 명세와 충돌하는 문항 (현재 0건이어야 정상 — 있으면 최우선)
  ② **앵커가 인용 안에 없는 문항** — 골드 답의 핵심 사실을 실린 인용만으로는 확인할 수
     없다는 뜻이다. 부정 주장("답이 없다")처럼 정당한 경우도 있지만, 그만큼 원본 대조가 필요하다.
  ③ 베이스라인(replay)이 놓친 앵커 — 이 문항이 실제로 무언가를 변별하고 있는 지점.

검수 대상은 DEV 40뿐이다. LOCKED/CHALLENGE 는 봉인을 열지 않는다(개봉 시 별도 검수).
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from regimpact.eval import Split, check_gold_against_spec, load_split  # noqa: E402
from regimpact.eval.qa import fact_matches  # noqa: E402
from regimpact.eval.schema import HIGH_RISK_CATEGORIES  # noqa: E402

items = load_split(Split.DEV)

# 채점 실측 — 저장된 replay 베이스라인(qa_dev_rescored)에서 문항별 채점 결과를 읽는다.
# 모델 답변 원문은 싣지 않는다: 검수는 "골드가 원문에 비추어 맞는가"이지 모델 평가가 아니고,
# 모델 답을 옆에 두면 검수자가 그쪽으로 앵커링된다. 숫자만 싣는다 — 이 문항이 재는 게 있는가.
_run = json.loads((REPO / "docs/eval/runs/qa_dev_rescored.json").read_text(encoding="utf-8"))
BASELINE = f"{_run['provider']}·{_run['model']}"
score_by_id = {s["item_id"]: s for s in _run["scores"]}

conf = check_gold_against_spec(items)
confirmed = [i for i in items if i.authored_by == "human_confirmed"]


def facts_not_in_citations(it) -> list[str]:
    """인용문만으로는 확인할 수 없는 채점 앵커. 검수자가 원본을 더 봐야 하는 지점."""
    hay = " ".join(c.quote for c in it.citations)
    return [f for f in it.gold_facts if not fact_matches(f, hay)]


def baseline_line(it) -> str:
    s = score_by_id.get(it.id)
    if s is None:
        return "베이스라인 기록 없음"
    parts = [f"앵커 {s['facts_hit']}/{s['facts_total']}",
             f"인용 grounding {s['citations_grounded']}/{s['citations_total']}"]
    if s["escalation_expected"] or s["escalation_given"]:
        ok = s["escalation_expected"] == s["escalation_given"]
        parts.append(f"escalation {'일치' if ok else '불일치'}")
    if s["missed_facts"]:
        parts.append("놓친 앵커: " + ", ".join(repr(f) for f in s["missed_facts"]))
    return " · ".join(parts)


# 카테고리 그룹 — 작성 순서(dev.json 순서) 유지
groups: dict = {}
for it in items:
    groups.setdefault(it.category, []).append(it)

needs_source = [(it, facts_not_in_citations(it)) for it in items]
needs_source = [(it, miss) for it, miss in needs_source if miss]
discriminating = [it for it in items if score_by_id.get(it.id, {}).get("missed_facts")]

# ---------------------------------------------------------------- 마크다운
L = [f"# QA 골드 DEV 검수표 ({len(items)}문항)", "",
     f"> 생성: `python tools/build_qa_review.py` · 확정 **{len(confirmed)}/{len(items)}** · "
     f"명세 충돌 {len(conf.conflicts)}건 · 채점 실측: {BASELINE}", "",
     "검수 질문은 문항마다 세 가지다:", "",
     "1. **골드 답이 맞는가** — 실린 인용(원문 verbatim 보장)과 원본에 비추어.",
     "2. **채점 앵커(`gold_facts`)가 답의 핵심을 재는가** — 앵커만 맞히고 요지를 틀린 답이 통과할 만큼 느슨하지 않은가.",
     "3. **escalation 기대가 맞는가** — 원문에 답이 없으면 지어내는 대신 사람에게 올리는 게 기대값이다.", "",
     "인용은 원문에서 기계적으로 잘라 온 것이라 **원문에 있음은 보장**되지만, 그 인용이 그 답을",
     "**뒷받침하는지는 사람이 판단할 몫**이다. FAQ Q2 표 구간(LTV/DTI 평탄화)은 텍스트 추출본을",
     "믿지 말고 `05_RULE_SPEC` §C(원본 이미지로 확정)와 대조한다 — `GOLD_REVIEW.md` §2 참조.", ""]

# §1 우선 확인
L += ["---", "", "## 1. 우선 확인 — 검수 주의 신호", ""]
if conf.conflicts:
    L += [f"### ⚠️ 확정 명세와 충돌 {len(conf.conflicts)}건 — 가장 먼저 판단", ""]
    for c in conf.conflicts:
        L.append(f"- {c}")
    L.append("")
else:
    L += ["**확정 명세와 충돌 0건.** (`check_gold_against_spec` — 관측된 결함 유형 2가지를 정밀 검사)", ""]

L += [f"### 인용만으로 확인 불가 — {len(needs_source)}문항", "",
      "골드 답의 채점 앵커가 실린 인용 안에 없다. 답이 틀렸다는 뜻이 아니라(부정 주장·수치 표기 차이 등),",
      "**이 문항들은 인용만 읽고 넘기면 안 되고 원본을 열어 봐야 한다**는 뜻이다.", ""]
for it, miss in needs_source:
    L.append(f"- `{it.id}` — 인용 밖 앵커: {', '.join(repr(m) for m in miss)}")
L += ["", f"### 베이스라인({BASELINE})이 놓친 앵커 — {len(discriminating)}문항", "",
      "채점이 실제로 변별하고 있는 지점이다. 검수 시 **앵커가 과하게 엄격한 것인지, 모델이 정말",
      "틀린 것인지**를 함께 본다(첫 채점 실패 12건이 전부 채점기 결함이었던 전례 — D-03 철회).", ""]
for it in discriminating:
    s = score_by_id[it.id]
    L.append(f"- `{it.id}` — {', '.join(repr(f) for f in s['missed_facts'])}")
L.append("")

# §2 문항 전체 (카테고리별)
sec = 1
for cat, its in groups.items():
    sec += 1
    risk = " · ⚠️ high-risk (브리프 §11 가중)" if cat in HIGH_RISK_CATEGORIES else ""
    L += ["---", "", f"## {sec}. {cat.value} — {len(its)}문항{risk}", ""]
    for it in its:
        mark = "✅" if it.authored_by == "human_confirmed" else "☐"
        L += [f"#### {mark} `{it.id}` — {it.question}",
              f"- **골드 답:** {it.gold_answer}",
              f"- 앵커: `{'`, `'.join(it.gold_facts)}`"
              + (" · **escalation 기대**" if it.expect_escalation else "")
              + (f" · rule_id `{it.rule_id}`" if it.rule_id else ""),
              f"- 채점 실측: {baseline_line(it)}"]
        if it.note:
            L.append(f"- 작성 노트: {it.note}")
        for cit in it.citations:
            L.append(f"  > [{cit.source_doc_id}] {' '.join(cit.quote.split())[:150]}")
        L.append("")

L += ["---", "", "## 확정 절차", "",
      "1. 문항이 맞으면 `tools/gold_dev.py` 의 해당 `item(...)`에 `authored_by=\"human_confirmed\"` 를 붙인다.",
      "   틀리면 골드를 고친다(값이 아니라 분류가 틀린 경우도 있다 — CHALLENGE-NOC-001 전례).",
      "2. `python tools/gold_dev.py` 로 재생성한다 — 검증기(인용 원문 대조 포함)가 통과해야 저장된다.",
      "3. `python tools/build_qa_review.py` 로 이 표를 다시 생성한다.", "",
      "40문항 전부 확정되면 QA 지표(Fact Coverage 95.0% 등)가 **절대값**이 된다.",
      "지금은 상대 비교(채점기·프롬프트 개선 전후)에만 쓴다.", ""]

out = REPO / "docs" / "eval" / "QA_GOLD_REVIEW.md"
out.write_text("\n".join(L), encoding="utf-8")
print(f"검수표 생성: {out.relative_to(REPO)} ({len(L)}줄, 충돌 {len(conf.conflicts)}건, "
      f"원본 대조 필요 {len(needs_source)}건)")

# ---------------------------------------------------------------- HTML 검수표
# 마크다운과 같은 데이터에서 생성한다 — 두 벌을 손으로 맞추면 반드시 어긋난다.
from review_theme import FONTS_LINK, REVIEW_CSS, esc, quote_block  # noqa: E402


def item_card(it) -> str:
    done = it.authored_by == "human_confirmed"
    miss = facts_not_in_citations(it)
    badges = []
    if it.expect_escalation:
        badges.append('<span class="tag">escalation 기대</span>')
    if it.rule_id:
        badges.append(f'<span class="tag">{esc(it.rule_id)}</span>')
    if miss:
        badges.append('<span class="tag warn">원본 대조 필요</span>')
    anchors = "".join(f"<kbd>{esc(f)}</kbd>" for f in it.gold_facts)
    note = f'<p class="why">{esc(it.note)}</p>' if it.note else ""
    return f"""
      <li class="item{' confirmed' if done else ''}">
        <label class="check"><input type="checkbox" class="cb"{' checked' if done else ''}><span></span></label>
        <div class="body">
          <div class="head"><code>{esc(it.id)}</code><span class="claim">{esc(it.question)}</span>{''.join(badges)}</div>
          <p class="gold-ans">{esc(it.gold_answer)}</p>
          <div class="kw">{anchors}<span class="hits">{esc(baseline_line(it))}</span></div>
          {note}
          {quote_block(it.citations)}
        </div>
      </li>"""


sections = []
for cat, its in groups.items():
    risk = ' <span class="tag">⚠️ high-risk</span>' if cat in HIGH_RISK_CATEGORIES else ""
    sections.append(f"""
  <section>
    <h2>{esc(cat.value)} — {len(its)}문항{risk}</h2>
    <ol class="items">{''.join(item_card(it) for it in its)}</ol>
  </section>""")

signal_rows = "".join(
    f"<li><code>{esc(it.id)}</code> — 인용 밖 앵커: {esc(', '.join(repr(m) for m in miss))}</li>"
    for it, miss in needs_source)
missed_rows = "".join(
    f"<li><code>{esc(it.id)}</code> — {esc(', '.join(repr(f) for f in score_by_id[it.id]['missed_facts']))}</li>"
    for it in discriminating)

html = f"""<title>QA 골드 DEV 검수표</title>
{FONTS_LINK}
<style>{REVIEW_CSS}
.tag.warn {{ border-color:var(--pend); color:var(--pend-ink); background:var(--pend-bg); }}
.gold-ans {{ font-size:14px; }}
.signal ul {{ margin:0; padding-left:20px; font-size:13.5px; color:var(--ink-2); }}
.signal ul code {{ font-family:'JetBrains Mono',monospace; font-size:12px; color:var(--navy); }}
</style>

<div class="wrap">
  <header style="display:flex;flex-direction:column;gap:14px">
    <h1>QA 골드 DEV 검수표</h1>
    <p class="lede">DEV {len(items)}문항 — 튜닝에 쓰는 유일한 셋. 문항마다 세 가지를 본다:
    <strong>골드 답이 맞는가</strong> · <strong>채점 앵커가 핵심을 재는가</strong> ·
    <strong>escalation 기대가 맞는가</strong>. 인용은 원문 verbatim이 보장되지만
    그 인용이 답을 뒷받침하는지는 사람이 판단할 몫이다.</p>
    <div class="meta">
      <span>확정 {len(confirmed)}/{len(items)}</span><span>명세 충돌 {len(conf.conflicts)}건</span>
      <span>원본 대조 필요 {len(needs_source)}건</span><span>채점 실측 {esc(BASELINE)}</span>
    </div>
  </header>

  <section class="signal">
    <h2>우선 확인 — 검수 주의 신호</h2>
    <div class="note">
      <p><strong>확정 명세와 충돌 {len(conf.conflicts)}건.</strong>{' 가장 먼저 판단이 필요하다.' if conf.conflicts else ' (check_gold_against_spec 통과)'}</p>
      {('<ul>' + ''.join(f'<li>{esc(c)}</li>' for c in conf.conflicts) + '</ul>') if conf.conflicts else ''}
      <p><strong>인용만으로 확인 불가 — {len(needs_source)}문항.</strong> 답이 틀렸다는 뜻이 아니라
      실린 인용만 읽고 넘기면 안 되고 <strong>원본을 열어 봐야 한다</strong>는 뜻이다.</p>
      <ul>{signal_rows}</ul>
      <p><strong>베이스라인({esc(BASELINE)})이 놓친 앵커 — {len(discriminating)}문항.</strong>
      앵커가 과하게 엄격한 것인지, 모델이 정말 틀린 것인지를 함께 본다.</p>
      <ul>{missed_rows}</ul>
      <p>FAQ Q2 표 구간(LTV/DTI 평탄화)은 텍스트 추출본을 믿지 말고
      <code>05_RULE_SPEC</code> §C와 대조한다.</p>
    </div>
  </section>
  {''.join(sections)}

  <footer style="padding-bottom:52px">
    검수 후 <code>tools/gold_dev.py</code>의 해당 항목에 <code>authored_by="human_confirmed"</code>를 붙이고
    <code>python tools/gold_dev.py</code> → <code>python tools/build_qa_review.py</code>로 재생성하세요.
    체크 상태는 <strong>저장되지 않습니다</strong> — 한 번의 검수 세션용 진행 표시입니다.
  </footer>
</div>
<div class="progress" id="prog">확인 0 / {len(items)}</div>

<script>
const boxes = [...document.querySelectorAll('.cb')], prog = document.getElementById('prog');
const sync = () => prog.textContent = `확인 ${{boxes.filter(b => b.checked).length}} / ${{boxes.length}}`;
boxes.forEach(b => b.addEventListener('change', sync));
sync();
</script>"""

html_out = REPO / "docs" / "eval" / "qa_gold_review.html"
html_out.write_text(html, encoding="utf-8")
print(f"HTML 검수표: {html_out.relative_to(REPO)} ({len(html):,} bytes)")
