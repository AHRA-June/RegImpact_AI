"""마크다운 → 자체완결 HTML 문서 렌더러 (stdlib only, zero-dep).

프로젝트 리포트(report.py)와 같은 디자인 언어(Institutional Navy, Noto Sans/JetBrains Mono,
라이트/다크 대응)로 **장문 문서**(검증보고서·PRD 등)를 인쇄 친화적 HTML로 렌더한다.
외부 마크다운 라이브러리를 쓰지 않는다(런타임 의존성 0 원칙 유지).

지원 문법(문서가 실제로 쓰는 부분집합): 제목(#~####), 표, 굵게(**), 인라인 코드(`),
코드펜스(```), 인용(>), 수평선(---), 순서/비순서 목록(1./- , 2단 중첩), 문단.
"""
from __future__ import annotations

import html
import re
from typing import Optional

_BOLD = re.compile(r"\*\*([^*]+)\*\*")
_CODE = re.compile(r"`([^`]+)`")
_HEADER = re.compile(r"^(#{1,6})\s+(.*)$")
_OL_ITEM = re.compile(r"^(\s*)(\d+)\.\s+(.*)$")
_UL_ITEM = re.compile(r"^(\s*)[-*]\s+(.*)$")


def _inline(text: str) -> str:
    """인라인 마크업(코드·굵게)을 안전하게 HTML로. 먼저 escape 후 치환."""
    esc = html.escape(text, quote=False)
    # 코드 스팬 먼저(내부를 굵게 처리하지 않도록 placeholder)
    spans: list[str] = []

    def _stash(m: re.Match) -> str:
        spans.append(f"<code>{m.group(1)}</code>")
        return f"\x00{len(spans)-1}\x00"

    esc = _CODE.sub(_stash, esc)
    esc = _BOLD.sub(r"<strong>\1</strong>", esc)
    for i, s in enumerate(spans):
        esc = esc.replace(f"\x00{i}\x00", s)
    return esc


def _emit_table(rows: list[str]) -> str:
    def cells(line: str) -> list[str]:
        parts = line.strip().strip("|").split("|")
        return [c.strip() for c in parts]

    header = cells(rows[0])
    body = [cells(r) for r in rows[2:]]
    out = ['<div class="tbl-wrap"><table>', "<thead><tr>"]
    out += [f"<th>{_inline(c)}</th>" for c in header]
    out.append("</tr></thead><tbody>")
    for r in body:
        out.append("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in r) + "</tr>")
    out.append("</tbody></table></div>")
    return "".join(out)


def _list_indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _emit_list(lines: list[str], start: int) -> tuple[str, int]:
    """start부터 목록 블록을 파싱(2단 중첩 지원). (html, 다음 인덱스) 반환."""
    base = _list_indent(lines[start])
    ordered = bool(_OL_ITEM.match(lines[start]))
    tag = "ol" if ordered else "ul"
    out = [f"<{tag}>"]
    i = start
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            # 목록 내 빈 줄: 다음이 같은 종류·같은 들여쓰기 목록이면 이어짐, 아니면 종료
            nxt = i + 1
            if nxt < len(lines):
                nm = _OL_ITEM.match(lines[nxt]) or _UL_ITEM.match(lines[nxt])
                if (nm and _list_indent(lines[nxt]) == base
                        and bool(_OL_ITEM.match(lines[nxt])) == ordered):
                    i += 1
                    continue
            break
        m_ol = _OL_ITEM.match(line)
        m_ul = _UL_ITEM.match(line)
        if not (m_ol or m_ul):
            break
        indent = _list_indent(line)
        if indent < base:
            break
        if indent > base:
            sub, i = _emit_list(lines, i)
            out[-1] = out[-1][:-5] + sub + "</li>"   # 직전 </li> 앞에 중첩 삽입
            continue
        if bool(m_ol) != ordered:        # 같은 들여쓰기에서 종류가 바뀌면 목록 종료
            break
        content = m_ol.group(3) if m_ol else m_ul.group(2)
        out.append(f"<li>{_inline(content)}</li>")
        i += 1
    out.append(f"</{tag}>")
    return "".join(out), i


def _render_blocks(md: str) -> str:
    lines = md.split("\n")
    out: list[str] = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        # 코드펜스
        if stripped.startswith("```"):
            j = i + 1
            buf: list[str] = []
            while j < n and not lines[j].strip().startswith("```"):
                buf.append(lines[j])
                j += 1
            code = html.escape("\n".join(buf), quote=False)
            out.append(f'<pre class="code"><code>{code}</code></pre>')
            i = j + 1
            continue

        # 수평선
        if stripped == "---":
            out.append("<hr>")
            i += 1
            continue

        # 제목
        hm = _HEADER.match(line)
        if hm:
            level = len(hm.group(1))
            text = _inline(hm.group(2).strip())
            anchor = re.sub(r"[^\w가-힣]+", "-", hm.group(2).strip()).strip("-").lower()
            out.append(f'<h{level} id="{anchor}">{text}</h{level}>')
            i += 1
            continue

        # 표 (현재 줄이 |로 시작 + 다음 줄이 구분선)
        if stripped.startswith("|") and i + 1 < n and set(lines[i + 1].strip()) <= set("|-: "):
            tbl: list[str] = []
            while i < n and lines[i].strip().startswith("|"):
                tbl.append(lines[i])
                i += 1
            out.append(_emit_table(tbl))
            continue

        # 인용
        if stripped.startswith(">"):
            buf = []
            while i < n and lines[i].strip().startswith(">"):
                buf.append(lines[i].strip()[1:].lstrip())
                i += 1
            inner = " ".join(b for b in buf if b) if buf else ""
            # 인용 내부의 빈 줄 분리 문단
            paras = "</p><p>".join(
                _inline(p.strip()) for p in "\n".join(buf).split("\n\n") if p.strip()
            )
            out.append(f"<blockquote><p>{paras}</p></blockquote>")
            continue

        # 목록
        if _OL_ITEM.match(line) or _UL_ITEM.match(line):
            block, i = _emit_list(lines, i)
            out.append(block)
            continue

        # 문단 (빈 줄까지 수집)
        buf = [line]
        i += 1
        while i < n and lines[i].strip() and not _looks_block(lines[i]):
            buf.append(lines[i])
            i += 1
        out.append(f"<p>{_inline(' '.join(b.strip() for b in buf))}</p>")
    return "\n".join(out)


def _looks_block(line: str) -> bool:
    s = line.strip()
    return (
        s.startswith("#") or s.startswith(">") or s.startswith("|")
        or s.startswith("```") or s == "---"
        or bool(_OL_ITEM.match(line)) or bool(_UL_ITEM.match(line))
    )


def markdown_to_html(md: str, *, title: Optional[str] = None,
                     kicker: str = "RegImpact AI · 문서") -> str:
    """마크다운 문자열을 자체완결 HTML 문서로 렌더."""
    # 제목 추출(첫 H1) — title 미지정 시
    doc_title = title
    if doc_title is None:
        for ln in md.split("\n"):
            m = _HEADER.match(ln)
            if m and len(m.group(1)) == 1:
                doc_title = re.sub(r"<[^>]+>", "", m.group(2)).strip()
                break
        doc_title = doc_title or "문서"

    body = _render_blocks(md)
    return (
        '<!doctype html><html lang="ko"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{html.escape(doc_title)}</title>"
        f"<style>{_CSS_DOC}</style></head><body>"
        f'<div class="kicker-band">{html.escape(kicker)}</div>'
        f'<main class="doc">{body}</main>'
        "</body></html>"
    )


_CSS_DOC = """
:root{
  --surface:#fcf8ff; --card:#ffffff; --container:#f5f2ff; --container-2:#efecff;
  --ink:#1a1a2e; --ink-soft:#43474e; --outline:#c4c6cf; --line:#e2e0fc;
  --primary:#022448; --secondary:#0051d5; --accent:#7a5300; --accent-bg:#ffddb2;
  --good:#2e6b4f; --good-bg:#cde6d8; --warn:#ba1a1a;
  --sans:"Noto Sans","Malgun Gothic",system-ui,-apple-system,"Segoe UI",sans-serif;
  --mono:"JetBrains Mono",ui-monospace,"SF Mono",Menlo,monospace;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --surface:#111421; --card:#1a1f30; --container:#171b2b; --container-2:#1c2133;
  --ink:#e9e9f4; --ink-soft:#b6bac6; --outline:#3a3f52; --line:#2a3047;
  --primary:#adc8f5; --secondary:#8ab0ff; --accent:#edbf7f; --accent-bg:#33260f;
  --good:#8fd6ac; --good-bg:#123322; --warn:#ffb4ab;
}}
:root[data-theme="dark"]{
  --surface:#111421; --card:#1a1f30; --container:#171b2b; --container-2:#1c2133;
  --ink:#e9e9f4; --ink-soft:#b6bac6; --outline:#3a3f52; --line:#2a3047;
  --primary:#adc8f5; --secondary:#8ab0ff; --accent:#edbf7f; --accent-bg:#33260f;
  --good:#8fd6ac; --good-bg:#123322; --warn:#ffb4ab;
}
*{box-sizing:border-box}
body{margin:0;background:var(--surface);color:var(--ink);font-family:var(--sans);
  line-height:1.7;font-size:15.5px;-webkit-font-smoothing:antialiased}
.kicker-band{background:var(--primary);color:#fff;font-family:var(--mono);font-size:.72rem;
  letter-spacing:.12em;text-transform:uppercase;padding:10px 22px}
:root[data-theme="dark"] .kicker-band,
:root:not([data-theme="light"]) .kicker-band{color:#0b1220}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]) .kicker-band{color:#0b1220}}
main.doc{max-width:860px;margin:0 auto;padding:34px 24px 80px}
h1{font-size:clamp(1.6rem,1.2rem+1.6vw,2.15rem);font-weight:740;letter-spacing:-.02em;
  line-height:1.25;margin:8px 0 18px;padding-bottom:14px;border-bottom:3px solid var(--primary)}
h2{font-size:1.32rem;font-weight:680;letter-spacing:-.01em;margin:38px 0 12px;
  padding-top:14px;border-top:1px solid var(--line)}
h3{font-size:1.08rem;font-weight:660;margin:26px 0 8px;color:var(--primary)}
h4{font-size:.96rem;font-weight:660;margin:20px 0 6px;color:var(--ink-soft)}
p{margin:10px 0}
a{color:var(--secondary)}
strong{font-weight:680}
code{font-family:var(--mono);font-size:.86em;background:var(--container-2);
  padding:1px 6px;border-radius:5px}
pre.code{background:var(--container);border:1px solid var(--line);border-radius:11px;
  padding:14px 16px;overflow-x:auto;font-family:var(--mono);font-size:.82rem;line-height:1.55}
pre.code code{background:none;padding:0}
hr{border:none;border-top:1px solid var(--line);margin:30px 0}
blockquote{margin:16px 0;padding:12px 18px;background:var(--container);
  border-left:4px solid var(--accent);border-radius:0 10px 10px 0;color:var(--ink-soft)}
blockquote p{margin:6px 0}
ul,ol{margin:10px 0;padding-left:24px}
li{margin:5px 0}
li>ul,li>ol{margin:5px 0}
.tbl-wrap{overflow-x:auto;border:1px solid var(--line);border-radius:11px;margin:16px 0}
table{border-collapse:collapse;width:100%;min-width:440px;font-size:.86rem}
thead th{text-align:left;font-family:var(--mono);font-size:.68rem;letter-spacing:.04em;
  text-transform:uppercase;color:var(--ink-soft);font-weight:700;padding:10px 13px;
  background:var(--container);border-bottom:2px solid var(--line);white-space:nowrap}
tbody td{padding:9px 13px;border-bottom:1px solid var(--line);vertical-align:top}
tbody tr:last-child td{border-bottom:none}
tbody tr:nth-child(even){background:var(--container)}
@media print{
  .kicker-band{background:none;color:#000;border-bottom:1px solid #000}
  body{font-size:11pt} main.doc{max-width:none;padding:0}
  h2{page-break-before:auto} table{page-break-inside:avoid}
}
"""
