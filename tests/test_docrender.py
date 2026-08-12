"""마크다운→HTML 문서 렌더러 테스트.

핵심: 지원 문법(제목·표·굵게·코드·인용·목록·코드펜스)이 올바른 HTML로 변환되고,
마크다운 기호가 새어나오지 않으며, 검증보고서 전체가 well-formed HTML로 렌더된다.
"""
from pathlib import Path

from regimpact.docrender import markdown_to_html

REPO = Path(__file__).resolve().parents[1]


def test_headers_and_inline():
    h = markdown_to_html("# 제목\n\n본문 **굵게** 와 `code`.", title="t")
    assert "<h1" in h and ">제목<" in h
    assert "<strong>굵게</strong>" in h
    assert "<code>code</code>" in h


def test_table():
    md = "| A | B |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |"
    h = markdown_to_html(md, title="t")
    assert h.count("<table>") == 1
    assert "<th>A</th>" in h and "<td>1</td>" in h and "<td>4</td>" in h


def test_lists_and_quote_and_fence():
    md = "> 인용문\n\n- 하나\n- 둘\n\n1. 가\n2. 나\n\n```\ncode line\n```"
    h = markdown_to_html(md, title="t")
    assert "<blockquote>" in h and "인용문" in h
    assert "<ul>" in h and "<li>하나</li>" in h
    assert "<ol>" in h and "<li>가</li>" in h
    assert "<pre" in h and "code line" in h


def test_hr_and_no_markdown_leak():
    md = "para\n\n---\n\n**b** end"
    h = markdown_to_html(md, title="t")
    assert "<hr>" in h
    assert "**" not in h            # 굵게 기호가 새지 않음


def test_html_escaping():
    h = markdown_to_html("텍스트 <script> & 5 < 6", title="t")
    assert "<script>" not in h       # escape 됨
    assert "&lt;script&gt;" in h


def test_validation_report_renders_wellformed():
    md = (REPO / "docs" / "validation" / "VALIDATION_REPORT.md").read_text(encoding="utf-8")
    h = markdown_to_html(md, title="검증보고서")
    assert h.startswith("<!doctype html>")
    assert h.rstrip().endswith("</body></html>")
    assert h.count("<h1") == 1
    assert h.count("<table>") >= 15          # 표 다수
    assert "**" not in h                     # 마크다운 누출 없음
    # 실제 내용 존재(하드코딩·환각 아님)
    for token in ["178/178", "28.6%", "조건부 적합", "PENDING"]:
        assert token in h, token
