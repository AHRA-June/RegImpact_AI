"""서비스 설명서 화면 — 공모전 심사용 문서를 공개 웹 페이지로 낸다.

원본은 `docs/business/service_description.html` 하나뿐이다. 이 모듈은 그것을 **복사하지
않고 감싸기만** 한다 — 문서를 두 벌 두면 반드시 갈라지기 때문이다. 저장소의 문서를 고치면
다음 배포에서 이 페이지가 따라 바뀐다.

감싸는 것은 세 가지다.
  ① 문서 조각(<title>·<link>·<style> + 본문)을 온전한 HTML 문서로 만든다.
  ② 사이트 규약인 '이 페이지는?' 밴드를 문서 자신의 토큰으로 그려 넣는다.
  ③ 나가는 길(홈 링크)을 붙인다 — 사이드바가 없는 독립 화면이므로 본문에 있어야 한다.
"""
from __future__ import annotations

from pathlib import Path

from regimpact.ui.theme import NOINDEX

DOC = Path(__file__).resolve().parents[3] / "docs" / "business" / "service_description.html"

# 문서 자신의 색·서체 토큰만 쓴다. 사이트 셸의 CSS 를 끌어오면 문서 디자인이 깨진다.
_EXTRA_CSS = """
  .pg-explain{margin:28px 0 0; padding:18px 20px; background:var(--surface);
    border:1px solid var(--line); border-radius:6px}
  .pg-explain .hd{font-family:var(--mono); font-size:11.5px; letter-spacing:.12em;
    text-transform:uppercase; color:var(--accent); font-weight:600; margin-bottom:12px}
  .pg-explain .pe-row{display:grid; grid-template-columns:180px minmax(0,1fr); gap:12px;
    padding:7px 0; font-size:13.5px; line-height:1.6}
  .pg-explain .pe-q{color:var(--muted); font-weight:600; font-size:12.5px}
  @media (max-width:640px){.pg-explain .pe-row{grid-template-columns:minmax(0,1fr); gap:2px}}
  .homelink{margin-top:40px; display:inline-block; font-family:var(--mono); font-size:12.5px;
    color:var(--accent); text-decoration:none}
  .homelink:hover{text-decoration:underline}
"""

_EXPLAIN = """
  <div class="pg-explain">
    <div class="hd">이 페이지는?</div>
    <div class="pe-row"><div class="pe-q">무엇을 보는 화면인가요?</div>
      <div>신한퓨처스랩 Tomorrow Challenge 에 낸 <strong>서비스 설명서</strong>입니다 —
      이 서비스가 무엇이고, 무엇이 이미 되고, 무엇이 아직 안 되는지를 적었습니다.</div></div>
    <div class="pe-row"><div class="pe-q">무엇으로 만들었나요?</div>
      <div>문서 안의 성능·검증 수치는 이 저장소의 파이프라인을 실제로 실행한 결과이고,
      외부에서 가져온 주장은 전부 <a href="#src">출처</a>에 링크를 남겼습니다.
      손으로 적은 숫자는 없습니다.</div></div>
    <div class="pe-row"><div class="pe-q">어떻게 보나요?</div>
      <div>위에서 아래로 읽으시면 됩니다. 실제 동작을 보시려면
      <a href="signal.html">고객 화면</a>이나 <a href="demo.html">3분 시연</a>으로 가세요.</div></div>
  </div>
"""

_HOME = '\n  <a class="homelink" href="index.html">← 전체 산출물 홈으로</a>\n'

# 문서 원본은 배포 주소를 절대 URL 로 적는다(제출·인쇄용이므로 그래야 한다). 그러나
# 사이트 안에서는 같은 사이트를 밖으로 한 바퀴 돌아 가리키게 되므로 상대 링크로 바꾼다 —
# 링크 검사 테스트도 이 변환을 전제로 깨진 링크를 잡는다.
SITE_ROOT = "https://ahra-june.github.io/RegImpact_AI/"


def _localize(html: str) -> str:
    return (html
            .replace(f'href="{SITE_ROOT}"', 'href="index.html"')
            .replace(f'href="{SITE_ROOT}', 'href="'))


def render() -> str:
    """저장소의 설명서 HTML 을 사이트 페이지로 감싼다."""
    raw = DOC.read_text(encoding="utf-8")
    # 탭 제목은 고객 화면(signal.html)과 겹치면 안 된다 — 나란히 열어 두고 비교하는 화면이다.
    raw = raw.replace("<title>내 한도 시그널</title>",
                      "<title>내 한도 시그널 — 서비스 설명서</title>", 1)
    head, sep, body = raw.partition("</style>")
    if not sep:                       # 스타일 블록이 사라졌다면 조용히 넘어가지 않는다
        raise ValueError(f"{DOC.name}: </style> 를 찾지 못했다 — 문서 구조가 바뀌었다")

    # '이 페이지는?' 밴드는 머리말 바로 뒤, 본문 첫 절 앞에 둔다.
    anchor = "  </header>"
    if anchor not in body:
        raise ValueError(f"{DOC.name}: </header> 를 찾지 못했다 — 문서 구조가 바뀌었다")
    body = body.replace(anchor, anchor + "\n" + _EXPLAIN, 1)

    # 나가는 길은 맨 끝 각주 앞에.
    if "  <footer>" not in body:
        raise ValueError(f"{DOC.name}: <footer> 를 찾지 못했다 — 문서 구조가 바뀌었다")
    body = body.replace("  <footer>", _HOME + "\n  <footer>", 1)

    return _localize(
        "<!doctype html>\n<html lang=\"ko\">\n<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        + NOINDEX + "\n"
        + head + _EXTRA_CSS + "</style>\n</head>\n<body>\n"
        + body.strip() + "\n</body>\n</html>\n"
    )
