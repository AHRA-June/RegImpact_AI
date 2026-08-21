"""추출 결과 도메인 검수표 생성 — 71건을 "다 읽으세요"로 넘기지 않는다.

검수는 사람의 일이지만(LOCKED §4), **검수 가능하게 만드는 것**은 기계가 할 수 있다.
이 도구가 하는 일은 정답을 고르는 것이 아니라 **먼저 볼 것을 짚는 것**이다.

기계가 짚을 수 있는 세 가지 — 셋 다 "주장이 틀렸다"가 아니라 "근거가 약하다"는 신호다:

  ① 인용이 원문에 여러 번 등장  어느 문장을 가리키는지 특정되지 않는다. 목차 줄과 본문에
     같은 문장이 있는데 앞의 것을 집으면 목차(점선 리더·쪽번호)가 근거로 실린다 —
     2026-08-20 폰 리뷰에서 실제로 밟은 함정이라 `_corpus_cut` 은 이제 모호하면 실패한다.
  ② 인용이 짧다              한두 어절짜리 인용은 verbatim 이어도 주장을 떠받치지 못한다.
  ③ 신뢰도가 낮다             모델 자신이 덜 확신한 항목.

인용의 verbatim 여부는 이미 기계가 대조했다(그래서 여기서 다시 묻지 않는다). 남은 질문은
하나다 — **그 인용이 그 주장을 뒷받침하는가.** 그건 사람만 판단할 수 있다.

    python tools/build_extraction_review.py --event 20251015
    python tools/build_extraction_review.py --event 20251015 --run docs/eval/runs/<파일>.json
"""
import argparse
import html
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from regimpact.extractor.sources import get_event, load_sources  # noqa: E402
from review_theme import FONTS_LINK, REVIEW_CSS  # noqa: E402

SHORT_QUOTE = 25          # 자 — 이보다 짧으면 근거로 서기 약하다
LOW_CONFIDENCE = 0.8      # 미만이면 모델이 덜 확신한 것


def esc(x) -> str:
    return html.escape(str(x if x is not None else ""))


def norm(t: str) -> str:
    return re.sub(r"\s+", " ", t or "").strip()


def doc_titles() -> dict[str, str]:
    """SOURCES.md 레지스트리에서 문서 제목을 읽는다 — 검수자가 doc_id 를 외울 필요는 없다.

    레지스트리를 못 읽으면 doc_id 를 그대로 쓴다. 제목을 손으로 옮겨 적지 않는 이유는
    저장소의 다른 곳과 같다 — 두 벌이 되면 갈라진다.
    """
    md = REPO / "docs" / "sources" / "SOURCES.md"
    if not md.exists():
        return {}
    out = {}
    for line in md.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.split("|")]
        if len(cells) > 4 and re.fullmatch(r"[A-Z0-9_]+", cells[1] or ""):
            out[cells[1]] = f"{cells[3]} · {cells[2]}" if cells[3] else cells[2]
    return out


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="추출 결과 도메인 검수표 생성")
    p.add_argument("--event", required=True, help="규제 이벤트 id (예: 20251015)")
    p.add_argument("--run", default=None,
                   help="실행 기록 JSON (생략 시 docs/eval/runs/run_cli_<event>.json)")
    p.add_argument("--out", default=None, help="출력 HTML 경로")
    return p.parse_args()


def flags_for(item: dict, sources: dict[str, str]) -> list[tuple[str, str]]:
    """이 항목을 먼저 봐야 하는 이유. 없으면 빈 목록."""
    out = []
    quote = norm(item["citation"]["quote"])
    doc = item["citation"]["source_doc_id"]
    hits = sources.get(doc, "").count(quote) if quote else 0
    if hits > 1:
        out.append(("모호", f"이 인용이 원문에 {hits}회 등장 — 어느 문장인지 특정되지 않는다"))
    if len(quote) < SHORT_QUOTE:
        out.append(("짧음", f"인용 {len(quote)}자 — 주장을 떠받치기에 짧다"))
    if item["confidence"] < LOW_CONFIDENCE:
        out.append(("저신뢰", f"신뢰도 {item['confidence']:.2f} — 모델이 덜 확신했다"))
    return out


def card(i: int, item: dict, flags: list[tuple[str, str]], docl: dict) -> str:
    q = norm(item["citation"]["quote"])
    doc = item["citation"]["source_doc_id"]
    ba = ""
    if item.get("before") or item.get("after"):
        ba = (f'<p class="why"><code>{esc(item.get("before") or "—")}</code> → '
              f'<code>{esc(item.get("after") or "—")}</code></p>')
    flag_html = "".join(
        f'<li><strong>{esc(name)}</strong> — {esc(why)}</li>' for name, why in flags)
    flag_block = (f'<div class="note"><p>먼저 볼 이유</p><ul>{flag_html}</ul></div>'
                  if flags else "")
    corr = item.get("corroborations") or []
    corr_html = (f'<p class="why">다른 문서에서도 확인됨: '
                 f'{esc(", ".join(str(c) for c in corr))}</p>' if corr else "")
    return f"""<li class="item">
  <label class="check"><input type="checkbox" class="cb"><span></span></label>
  <div>
    <header>
      <span class="id">#{i:02d}</span>
      <span class="tag">{esc(item["category"])}</span>
      <span class="tag">신뢰도 {item["confidence"]:.2f}</span>
    </header>
    <p class="ask">{esc(item["summary"])}</p>
    {ba}
    {corr_html}
    <figure class="q">
      <blockquote>{esc(q)}</blockquote>
      <figcaption>{esc(docl.get(doc) or doc)}</figcaption>
    </figure>
    {flag_block}
    <p class="why"><strong>✍️ 판단:</strong>
      ☐ 채택(골드로)  ☐ 요약 수정 필요  ☐ 인용 교체 필요  ☐ 폐기(원문 근거 없음)</p>
  </div>
</li>"""


def main() -> None:
    args = _parse_args()
    event = get_event(args.event)
    run_path = Path(args.run) if args.run else (
        REPO / "docs" / "eval" / "runs" / f"run_cli_{event.event_id}.json")
    if not run_path.exists():
        print(f"실행 기록을 찾지 못했습니다: {run_path}")
        print("먼저 추출을 돌리세요: "
              f"python examples/run_extractor.py --event {event.event_id} --provider cli")
        return

    run = json.loads(run_path.read_text(encoding="utf-8"))
    changes = run["extraction"]["changes"]
    sources = {k: norm(v) for k, v in load_sources(event=event.event_id).items()}
    docl = {d: t for d, t in doc_titles().items() if d in sources}

    scored = [(c, flags_for(c, sources)) for c in changes]
    flagged = [(i, c, f) for i, (c, f) in enumerate(scored, 1) if f]
    clean = [(i, c, f) for i, (c, f) in enumerate(scored, 1) if not f]

    # 카테고리별로 묶되, 각 묶음 안에서는 신뢰도 낮은 것부터
    by_cat: dict[str, list] = {}
    for i, c, f in clean:
        by_cat.setdefault(c["category"], []).append((i, c, f))
    for v in by_cat.values():
        v.sort(key=lambda t: t[1]["confidence"])

    cited = run.get("assurance", {})
    cc = cited.get("citation_correctness")
    cc_txt = "—" if cc is None else f"{cc:.0%}"

    flagged_cards = "".join(card(i, c, f, docl) for i, c, f in flagged)
    cat_sections = "".join(
        f"""<section>
    <h2>{esc(cat)} — {len(v)}건</h2>
    <p class="lede">먼저 볼 이유가 걸리지 않은 항목이다. 신뢰도 낮은 것부터 정렬했다.</p>
    <ol class="items">{"".join(card(i, c, f, docl) for i, c, f in v)}</ol>
  </section>"""
        for cat, v in sorted(by_cat.items(), key=lambda kv: -len(kv[1])))

    html_out = Path(args.out) if args.out else (
        REPO / "docs" / "eval" / f"extraction_review_{event.event_id}.html")
    doc = f"""<title>{esc(event.label)} 추출 검수표</title>
{FONTS_LINK}
<style>{REVIEW_CSS}</style>

<div class="wrap">
  <header style="display:flex;flex-direction:column;gap:14px">
    <h1>{esc(event.label)} 추출 검수표</h1>
    <p class="lede">추출 <strong>{len(changes)}건</strong>. 인용이 원문에 verbatim 으로 실재하는지는
    <strong>이미 기계가 대조했다</strong>({cc_txt}) — 그래서 여기서 다시 묻지 않는다.
    남은 질문은 하나다: <strong>그 인용이 그 주장을 뒷받침하는가.</strong></p>
    <div class="meta">
      <span>{esc(event.published_at)}</span>
      <span>원문 {len(sources)}건</span>
      <span>인용 대조 {cc_txt}</span>
      <span>먼저 볼 것 {len(flagged)}건</span>
      <span>골드 없음 — 🤖 초안</span>
    </div>
  </header>

  <section>
    <h2>1. 먼저 볼 것 — {len(flagged)}건</h2>
    <p class="lede">기계가 짚을 수 있는 것은 "주장이 틀렸다"가 아니라 <strong>"근거가 약하다"</strong>
    뿐이다. 아래 셋 중 하나라도 걸린 항목을 앞으로 뺐다. 걸렸다고 틀린 것은 아니지만,
    <strong>검수 시간을 여기에 먼저 쓰는 것이 남는 장사다.</strong></p>
    <div class="note">
      <ul>
        <li><strong>모호</strong> — 인용이 원문에 여러 번 등장해 어느 문장인지 특정되지 않는다.
          목차 줄과 본문에 같은 문장이 있으면 목차(점선 리더·쪽번호)가 근거로 실린다.
          2026-08-20 폰 리뷰에서 실제로 밟은 함정이다.</li>
        <li><strong>짧음</strong> — 인용 {SHORT_QUOTE}자 미만. verbatim 이어도 주장을 떠받치지 못한다.</li>
        <li><strong>저신뢰</strong> — 모델 신뢰도 {LOW_CONFIDENCE:.2f} 미만.</li>
      </ul>
    </div>
    <ol class="items">{flagged_cards}</ol>
  </section>

  {cat_sections}

  <footer style="padding-bottom:52px">
    <p><strong>이 표의 체크는 저장되지 않습니다</strong> — 한 번의 검수 세션용 진행 표시입니다.</p>
    <p>검수를 마치면 채택한 항목으로 골드 파일을 만들고
    <code>src/regimpact/extractor/sources.py</code> 의
    <code>EVENTS["{esc(event.event_id)}"].gold</code> 에 경로를 적으세요. 그 순간부터
    완전성·예외 재현율 채점이 켜지고, <code>run_extractor.py --event {esc(event.event_id)}</code>
    가 골드 대조를 함께 출력합니다.</p>
    <p>골드가 없는 동안 이 이벤트는 <strong>인용 대조까지만</strong> 실측됩니다 —
    정답 없이 점수를 내지 않기 위해서입니다.</p>
  </footer>
</div>
<div class="progress" id="prog">확인 0 / {len(changes)}</div>

<script>
const boxes = [...document.querySelectorAll('.cb')], prog = document.getElementById('prog');
const sync = () => prog.textContent = `확인 ${{boxes.filter(b => b.checked).length}} / ${{boxes.length}}`;
boxes.forEach(b => b.addEventListener('change', sync));
sync();
</script>"""
    html_out.write_text(doc, encoding="utf-8")
    print(f"검수표: {html_out.relative_to(REPO)} ({len(doc):,} bytes)")
    print(f"  추출 {len(changes)}건 · 먼저 볼 것 {len(flagged)}건 "
          f"(모호/짧음/저신뢰) · 나머지 {len(clean)}건")


if __name__ == "__main__":
    main()
