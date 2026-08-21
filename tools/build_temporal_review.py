"""시점 질의 골드(TEMPORAL) 도메인 검수표 — 미측정 1건을 여는 열쇠.

스코어카드의 마지막 미측정이 `Policy-version Consistency` 다. 막고 있는 것은 코드가 아니라
**골드가 아직 🤖 초안이라는 사실**이다. 초안을 정답으로 삼아 낸 비율은 비율이 아니므로,
대조가 정합이어도 수치를 보고하지 않는다.

이 표가 하는 일은 검수를 대신하는 것이 아니라 **판단할 지점을 좁히는 것**이다. 시점 질의
골드는 두 진실 위에 서 있다:

  ① 원문 인용        — 기계가 verbatim 대조를 이미 끝냈다.
  ② 정책 버전 DB의 시점 해석 — `check_temporal_gold` 가 resolver 와 대조한다.

②까지 통과했다는 것은 "골드와 DB가 서로 어긋나지 않는다"는 뜻이지, "골드가 맞다"는 뜻이
아니다. **둘이 같은 방향으로 틀렸을 수 있다.** 그 판단만 사람 몫으로 남는다.

    python tools/build_temporal_review.py
"""
import html
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from regimpact.eval.goldset import load_split  # noqa: E402
from regimpact.eval.schema import Split  # noqa: E402
from regimpact.eval.temporal import check_temporal_gold  # noqa: E402
from regimpact.policy.registry import load_registry  # noqa: E402
from regimpact.policy.resolver import current_policy  # noqa: E402
from review_theme import FONTS_LINK, REVIEW_CSS  # noqa: E402


def esc(x) -> str:
    return html.escape(str(x if x is not None else ""))


def card(it, resolver_says: str | None, conflict: str | None) -> str:
    kind = "escalation 형" if it.expect_escalation else "답변형"
    cites = "".join(
        f'<figure class="q"><blockquote>{esc(" ".join(c.quote.split())[:400])}</blockquote>'
        f'<figcaption>{esc(c.source_doc_id)}</figcaption></figure>'
        for c in it.citations)
    note = f'<p class="why">작성 메모: {esc(it.note)}</p>' if it.note else ""
    facts = ""
    if getattr(it, "gold_facts", None):
        facts = ('<p class="why">채점 사실: '
                 + ", ".join(f"<code>{esc(f)}</code>" for f in it.gold_facts) + "</p>")

    if it.as_of is None:
        cross = ('<div class="note"><p><strong>시점 대조 없음</strong> — '
                 '<code>as_of</code> 가 없어 resolver 와 대조하지 못한다. '
                 '이 문항은 원문 인용만으로 판단해야 한다.</p></div>')
    elif conflict:
        cross = (f'<div class="note"><p><strong>⚠️ resolver 와 충돌</strong></p>'
                 f'<p>{esc(conflict)}</p>'
                 f'<p>골드가 틀렸거나 정책 DB가 틀렸다. <strong>둘 중 하나는 고쳐야 한다.</strong></p></div>')
    else:
        cross = (f'<div class="note"><p><strong>resolver 와 정합</strong> — '
                 f'{esc(it.as_of)} 시점 유효 정책을 DB 도 <code>{esc(resolver_says)}</code> 로 답한다.</p>'
                 f'<p>다만 이것은 <strong>골드와 DB가 서로 어긋나지 않는다</strong>는 뜻이지 '
                 f'골드가 맞다는 뜻이 아니다 — 둘이 같은 방향으로 틀렸을 수 있다.</p></div>')

    return f"""<li class="item">
  <label class="check"><input type="checkbox" class="cb"><span></span></label>
  <div>
    <header>
      <span class="id">{esc(it.id)}</span>
      <span class="tag">{esc(it.category.value)}</span>
      <span class="tag">{esc(kind)}</span>
      {f'<span class="tag">as_of {esc(it.as_of)}</span>' if it.as_of else ''}
      {f'<span class="tag">정책 {esc(it.policy_version)}</span>' if it.policy_version else ''}
    </header>
    <p class="ask">{esc(it.question)}</p>
    <p class="why"><strong>초안 답:</strong> {esc(it.gold_answer)}</p>
    {facts}
    {note}
    {cites}
    {cross}
    <p class="why"><strong>✍️ 판단:</strong>
      ☐ 확정(answer 그대로)  ☐ 답 수정 필요  ☐ 인용 교체 필요  ☐ 문항 폐기</p>
  </div>
</li>"""


def main() -> None:
    items = load_split(Split.TEMPORAL)
    rep = check_temporal_gold(items)
    reg = load_registry()

    conflict_for = {}
    for c in rep.conflicts:
        gid = c.split("]")[0].strip("[ ")
        conflict_for[gid] = c

    from datetime import date as _date
    resolver_for = {}
    for it in items:
        if it.as_of:
            cur = current_policy(reg, _date.fromisoformat(it.as_of))
            resolver_for[it.id] = cur.policy_id if cur else "답할 수 없음"

    drafts = [i for i in items if i.authored_by != "human_confirmed"]
    with_conflict = [i for i in items if i.id in conflict_for]
    rest = [i for i in items if i.id not in conflict_for]

    cards_conflict = "".join(
        card(i, resolver_for.get(i.id), conflict_for.get(i.id)) for i in with_conflict)
    cards_rest = "".join(card(i, resolver_for.get(i.id), None) for i in rest)

    doc = f"""<title>시점 질의 골드 검수표</title>
{FONTS_LINK}
<style>{REVIEW_CSS}</style>

<div class="wrap">
  <header style="display:flex;flex-direction:column;gap:14px">
    <h1>시점 질의 골드 검수표</h1>
    <p class="lede">스코어카드의 마지막 미측정 <code>Policy-version Consistency</code> 를 막고 있는 것은
    코드가 아니라 <strong>이 골드 {len(items)}문항이 아직 🤖 초안이라는 사실</strong>이다.
    초안을 정답으로 삼아 낸 비율은 비율이 아니므로, 대조가 정합이어도 수치를 보고하지 않는다.</p>
    <div class="meta">
      <span>{esc(rep.summary())}</span>
      <span>🤖 초안 {len(drafts)} / {len(items)}</span>
      <span>충돌 {len(rep.conflicts)}건</span>
    </div>
  </header>

  <section>
    <h2>이 표를 읽는 법</h2>
    <div class="note">
      <p>시점 질의 골드는 <strong>두 진실</strong> 위에 서 있다.</p>
      <ul>
        <li><strong>원문 인용</strong> — 기계가 verbatim 대조를 이미 끝냈다. 다시 묻지 않는다.</li>
        <li><strong>정책 버전 DB의 시점 해석</strong> — <code>check_temporal_gold</code> 가
          resolver 와 대조했다. 결과를 각 문항에 실었다.</li>
      </ul>
      <p>대조 통과는 <strong>"골드와 DB가 서로 어긋나지 않는다"</strong>는 뜻이지
      <strong>"골드가 맞다"</strong>는 뜻이 아니다. 둘이 같은 방향으로 틀렸을 수 있고,
      그 판단만 사람 몫으로 남는다.</p>
      <p><strong>escalation 형</strong> 문항은 방향이 반대다 — "DB 가 이 시점을 답할 수 없다"가
      정답의 근거다. 나중에 DB 가 답할 수 있게 되면(해제 원문 확보 등) 이 검사가
      "답변형으로 갱신하라"고 지목한다. 한계를 골드에 새겼으면 한계가 풀릴 때 골드도 풀려야 한다.</p>
    </div>
  </section>

  {"" if not with_conflict else f'''<section>
    <h2>1. ⚠️ resolver 와 충돌 — {len(with_conflict)}건</h2>
    <p class="lede">골드가 틀렸거나 정책 DB 가 틀렸다. 고치기 전까지 이 문항이 만드는 수치는 의미를 잃는다.</p>
    <ol class="items">{cards_conflict}</ol>
  </section>'''}

  <section>
    <h2>{"2. 나머지" if with_conflict else "1. 전체"} — {len(rest)}문항</h2>
    <p class="lede">기계 대조는 통과했다. 남은 질문은 <strong>"이 답이 도메인 사실로 맞는가"</strong> 하나다.</p>
    <ol class="items">{cards_rest}</ol>
  </section>

  <footer style="padding-bottom:52px">
    <p><strong>이 표의 체크는 저장되지 않습니다</strong> — 한 번의 검수 세션용 진행 표시입니다.</p>
    <p>검수를 마치면 <code>docs/eval/gold/temporal.json</code> 의 각 문항
    <code>authored_by</code> 를 <code>human_confirmed</code> 로 바꾸세요.
    <strong>그 순간 측정이 스스로 켜집니다</strong> — 스코어카드는 골드의 검수 상태를 코드가 읽어
    판단하므로, 파일을 하나도 더 고칠 필요가 없습니다
    (<code>tests/test_assurance.py</code> 가 이 자동 전환을 검사합니다).</p>
    <p>남는 것은 <strong>임계값</strong> 하나입니다. 2026-08-19 결정에 따라 "측정할 수 없는 지표에
    임계를 먼저 적지 않는다"이므로, 측정이 켜진 뒤 관측값을 보고
    <code>src/regimpact/assurance/thresholds.py</code> 에 근거와 함께 적으면 됩니다.</p>
  </footer>
</div>
<div class="progress" id="prog">확인 0 / {len(items)}</div>

<script>
const boxes = [...document.querySelectorAll('.cb')], prog = document.getElementById('prog');
const sync = () => prog.textContent = `확인 ${{boxes.filter(b => b.checked).length}} / ${{boxes.length}}`;
boxes.forEach(b => b.addEventListener('change', sync));
sync();
</script>"""

    out = REPO / "docs" / "eval" / "temporal_gold_review.html"
    out.write_text(doc, encoding="utf-8")
    print(f"검수표: {out.relative_to(REPO)} ({len(doc):,} bytes)")
    print(f"  {rep.summary()}")
    print(f"  🤖 초안 {len(drafts)}/{len(items)} · 충돌 {len(rep.conflicts)}건")


if __name__ == "__main__":
    main()
