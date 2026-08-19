"""마크다운 → 자체완결 HTML (stdlib only).

검증보고서·Model Card·Risk Register 같은 **장문 문서**를 화면 5종과 같은 디자인 언어로
렌더한다. 외부 마크다운 라이브러리를 쓰지 않는다 — 이 프로젝트의 런타임 의존성 0 원칙.

지원 문법은 우리 문서가 실제로 쓰는 부분집합이다: 제목(#~######), 표, 굵게, 인라인 코드,
코드펜스, 인용, 수평선, 순서/비순서 목록(2단 중첩), 문단.

파서는 `work-in-progress-fmo0g8` 에서 가져왔고, HTML 껍데기는 `ui.theme` 토큰으로 다시 썼다.
"""
from __future__ import annotations

import html
import re
from typing import Optional

from .theme import CSS, FONTS, esc

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




# --------------------------------------------------------------------- 목차

_TOC_LEVELS = (2, 3)


def _toc(md: str) -> str:
    """H2·H3 로 문서 내 목차를 만든다. 장문 문서는 목차 없이 못 읽는다."""
    items = []
    for ln in md.split("\n"):
        m = _HEADER.match(ln)
        if not m or len(m.group(1)) not in _TOC_LEVELS:
            continue
        text = re.sub(r"[*`]", "", m.group(2).strip())
        anchor = re.sub(r"[^\w가-힣]+", "-", m.group(2).strip()).strip("-").lower()
        cls = "toc-2" if len(m.group(1)) == 2 else "toc-3"
        items.append(f'<a class="{cls}" href="#{anchor}">{esc(text)}</a>')
    return "".join(items)


_DOC_CSS = """
body{background:var(--background);color:var(--on-surface)}
.doc-shell{display:grid;grid-template-columns:minmax(0,1fr);gap:0;max-width:1180px;margin:0 auto;padding:0 24px 96px}
@media(min-width:1024px){.doc-shell{grid-template-columns:240px minmax(0,1fr);gap:40px}}
.doc-toc{display:none}
@media(min-width:1024px){.doc-toc{display:block;position:sticky;top:24px;align-self:start;max-height:calc(100vh - 48px);overflow:auto;padding:16px 0;border-right:1px solid var(--outline-variant)}}
.doc-toc a{display:block;padding:3px 12px 3px 0;font-size:12px;line-height:17px;color:var(--on-surface-variant);text-decoration:none;border-left:2px solid transparent}
.doc-toc a:hover{color:var(--primary);border-left-color:var(--primary)}
.doc-toc .toc-3{padding-left:12px;font-size:11px;opacity:.8}
.doc-body{min-width:0;padding-top:8px}
.doc-body h1{font-size:30px;line-height:38px;font-weight:700;letter-spacing:-.02em;margin:24px 0 8px}
.doc-body h2{font-size:22px;line-height:30px;font-weight:600;margin:40px 0 12px;padding-bottom:8px;border-bottom:1px solid var(--outline-variant)}
.doc-body h3{font-size:17px;line-height:24px;font-weight:600;margin:28px 0 8px}
.doc-body h4{font-size:15px;line-height:22px;font-weight:600;margin:20px 0 6px;color:var(--on-surface-variant)}
.doc-body p{margin:10px 0;line-height:25px}
.doc-body li{margin:4px 0;line-height:24px}
.doc-body ul,.doc-body ol{margin:10px 0;padding-left:22px}
.doc-body hr{border:0;border-top:1px solid var(--outline-variant);margin:32px 0}
.doc-body blockquote{margin:16px 0;padding:12px 16px;border-left:3px solid var(--primary);background:var(--surface-container-low);border-radius:0 4px 4px 0}
.doc-body blockquote p{margin:4px 0}
.doc-body code{font-family:'JetBrains Mono',ui-monospace,monospace;font-size:12.5px;background:var(--surface-container);padding:1px 5px;border-radius:3px}
.doc-body pre.code{background:var(--surface-container);border:1px solid var(--outline-variant);border-radius:6px;padding:14px 16px;overflow-x:auto;margin:14px 0}
.doc-body pre.code code{background:none;padding:0;font-size:12px;line-height:19px}
.tbl-wrap{overflow-x:auto;margin:14px 0;border:1px solid var(--outline-variant);border-radius:6px}
.doc-body table{border-collapse:collapse;width:100%;font-size:13px}
.doc-body th{text-align:left;padding:9px 12px;background:var(--surface-container);font-weight:600;white-space:nowrap;border-bottom:1px solid var(--outline-variant)}
.doc-body td{padding:9px 12px;border-bottom:1px solid var(--outline-variant);vertical-align:top}
.doc-body tr:last-child td{border-bottom:0}
.doc-nav{display:flex;align-items:center;gap:12px;max-width:1180px;margin:0 auto;padding:16px 24px}
.doc-nav a{font-size:13px;color:var(--primary);text-decoration:none;font-weight:500}
.doc-nav a:hover{text-decoration:underline}
.doc-kicker{font-family:'JetBrains Mono',ui-monospace,monospace;font-size:11px;letter-spacing:.04em;color:var(--on-surface-variant);text-transform:uppercase}
@media print{.doc-toc,.doc-nav{display:none}.doc-shell{grid-template-columns:1fr}}
"""


def markdown_to_html(md: str, *, title: Optional[str] = None,
                     kicker: str = "RegImpact AI", home: str = "index.html") -> str:
    """마크다운 문자열을 자체완결 HTML 문서로 렌더한다."""
    doc_title = title
    if doc_title is None:
        for ln in md.split("\n"):
            m = _HEADER.match(ln)
            if m and len(m.group(1)) == 1:
                doc_title = re.sub(r"[*`]", "", m.group(2)).strip()
                break
        doc_title = doc_title or "문서"

    return f"""<!DOCTYPE html>
<html lang="ko"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(doc_title)} — RegImpact AI</title>
{FONTS}
<style>{CSS}{_DOC_CSS}</style>
</head><body>
<nav class="doc-nav"><a href="{esc(home)}">← 홈</a><span class="doc-kicker">{esc(kicker)}</span></nav>
<div class="doc-shell">
  <aside class="doc-toc">{_toc(md)}</aside>
  <main class="doc-body">{_render_blocks(md)}</main>
</div>
</body></html>
"""
