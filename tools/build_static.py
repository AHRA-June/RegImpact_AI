"""정적 호스팅용 독립 문서 빌드 (Vercel · GitHub Pages · 어떤 정적 호스트든).

## 왜 별도 빌드인가
`web/sandbox.html` · `web/impact.html` 은 **Artifact 용 조각(fragment)** 이다 —
Artifact 플랫폼이 게시 시점에 `<!doctype html><head>…</head><body>` 를 씌워 주기 때문에
파일 자체에는 doctype·head 가 없다.

그 파일을 그대로 정적 호스팅하면 **모바일에서 깨진다.** `<meta name="viewport">` 가 없어
휴대폰 브라우저가 980px 데스크톱 뷰포트로 렌더한 뒤 축소해 버린다(글씨가 깨알만 해진다).
그래서 여기서 조각을 온전한 HTML 문서로 감싸 `web/dist/` 에 내보낸다.

실행:
    python tools/export_fixtures.py && python tools/build_sandbox.py
    python tools/export_impact.py   && python tools/build_impact.py
    python tools/build_static.py            # ← web/dist/ 생성
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
DIST = WEB / "dist"

SHELL = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="color-scheme" content="light dark">
<meta name="description" content="{description}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{description}">
<meta property="og:type" content="website">
<link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>{favicon}</text></svg>">
<style>
*,*::before,*::after{{box-sizing:border-box}}
html{{-webkit-text-size-adjust:100%}}
body{{margin:0}}
img,svg{{max-width:100%;height:auto}}
</style>
{head_extra}
</head>
<body>
{body}
</body>
</html>
"""


def _split(fragment: str) -> tuple[str, str, str]:
    """조각에서 <title>·<link>(폰트) 를 떼어 head 로 올린다."""
    title_m = re.search(r"<title>(.*?)</title>", fragment, re.S)
    title = title_m.group(1).strip() if title_m else "RegImpact AI"
    head_lines = re.findall(r'^\s*<link [^>]*>\s*$', fragment, re.M)
    body = fragment
    if title_m:
        body = body.replace(title_m.group(0), "", 1)
    for line in head_lines:
        body = body.replace(line, "", 1)
    head_extra = f"<title>{title}</title>\n" + "\n".join(l.strip() for l in head_lines)
    return title, head_extra, body.strip()


def wrap(fragment_path: Path, out_name: str, description: str, favicon: str) -> Path:
    title, head_extra, body = _split(fragment_path.read_text(encoding="utf-8"))
    html = SHELL.format(title=title, description=description, favicon=favicon,
                        head_extra=head_extra, body=body)
    out = DIST / out_name
    out.write_text(html, encoding="utf-8")
    return out


INDEX_BODY = """<style>
:root{
  --paper:#E9ECEF; --surface:#FBFCFD; --surface-2:#F1F4F6; --line:#CBD3DA; --line-soft:#DFE5EA;
  --ink:#141A22; --ink-2:#3D4854; --muted:#69757F; --seal:#A8322B; --seal-soft:#F3E3E1;
  --ok:#1E6B58; --shadow:0 1px 2px rgba(20,26,34,.06),0 8px 24px -16px rgba(20,26,34,.35);
}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){
  --paper:#101418; --surface:#171C22; --surface-2:#1E242B; --line:#2C343D; --line-soft:#242B33;
  --ink:#E6EBEF; --ink-2:#B7C1CA; --muted:#8894A0; --seal:#E0736A; --seal-soft:#2E1E1D;
  --ok:#6BC3A8; --shadow:0 1px 2px rgba(0,0,0,.4),0 8px 24px -16px rgba(0,0,0,.8);
}}
:root[data-theme="dark"]{
  --paper:#101418; --surface:#171C22; --surface-2:#1E242B; --line:#2C343D; --line-soft:#242B33;
  --ink:#E6EBEF; --ink-2:#B7C1CA; --muted:#8894A0; --seal:#E0736A; --seal-soft:#2E1E1D;
  --ok:#6BC3A8; --shadow:0 1px 2px rgba(0,0,0,.4),0 8px 24px -16px rgba(0,0,0,.8);
}
body{margin:0; background:var(--paper); color:var(--ink); line-height:1.62;
  font-family:"IBM Plex Sans KR","Apple SD Gothic Neo","Malgun Gothic",system-ui,sans-serif;
  -webkit-font-smoothing:antialiased; font-size:15px}
.wrap{max-width:760px; margin:0 auto; padding:clamp(24px,6vw,56px) 20px 64px;
  display:flex; flex-direction:column; gap:22px}
h1{font-family:"Song Myung","Apple SD Gothic Neo",serif; font-weight:400; margin:0;
   font-size:clamp(27px,7vw,40px); letter-spacing:-.01em; text-wrap:balance}
.tag{font-size:11.5px; letter-spacing:.1em; text-transform:uppercase; color:var(--muted);
     margin:0 0 8px; font-family:"IBM Plex Mono",monospace}
.lede{margin:6px 0 0; color:var(--ink-2); font-size:15px; max-width:62ch}
.lede b{color:var(--ink); font-weight:600}
.cards{display:flex; flex-direction:column; gap:14px; margin-top:6px}
a.card{display:block; text-decoration:none; color:inherit; border:1px solid var(--line);
  background:var(--surface); box-shadow:var(--shadow); padding:20px 20px 18px;
  transition:border-color .15s ease, transform .15s ease}
a.card:hover,a.card:focus-visible{border-color:var(--seal); transform:translateY(-1px)}
a.card:focus-visible{outline:2px solid var(--seal); outline-offset:2px}
.card .k{font-family:"IBM Plex Mono",monospace; font-size:11px; letter-spacing:.09em;
  color:var(--seal); text-transform:uppercase}
.card h2{font-family:"Song Myung",serif; font-weight:400; font-size:21px; margin:6px 0 6px}
.card p{margin:0; font-size:13.5px; color:var(--muted)}
.card .go{display:inline-block; margin-top:12px; font-size:12.5px; color:var(--seal); font-weight:500}
.facts{display:flex; flex-wrap:wrap; gap:7px; margin-top:2px}
.fact{font-family:"IBM Plex Mono",monospace; font-size:11.5px; padding:4px 9px;
  border:1px solid var(--line); background:var(--surface-2); color:var(--ink-2)}
.fact b{color:var(--ok); font-weight:600}
footer{border-top:1px dashed var(--line); padding-top:16px; font-size:12.5px; color:var(--muted)}
footer code{font-family:"IBM Plex Mono",monospace; font-size:11.5px; background:var(--surface-2);
  padding:1px 5px; border:1px solid var(--line-soft)}
</style>

<div class="wrap">
  <header>
    <p class="tag">RegImpact AI</p>
    <h1>규제가 바뀌면 무엇을 고쳐야 하는가</h1>
    <p class="lede">2026-06-30 주택시장 안정대책을 공문 원문에서 출발해
    <b>룰 변경안·고객영향·테스트·검증</b>까지 관통시킨 결과다. 챗봇이 아니라
    <b>검증 가능한 의사결정 지원 시스템</b>을 목표로 한다 — 그래서 AI가 만든 것과 사람이 확정한 것을
    화면에서 구분해 표시하고, 근거가 없으면 숫자를 지어내는 대신 사람에게 넘긴다.</p>
    <div class="facts">
      <span class="fact">지역 레지스트리 <b>241</b>곳</span>
      <span class="fact">회귀 케이스 <b>60</b> · Pass <b>100%</b></span>
      <span class="fact">테스트 <b>149</b></span>
      <span class="fact">E2E <b>10/11</b> 단계</span>
    </div>
  </header>

  <!-- 링크에 .html 을 남겨 둔다: Vercel 의 cleanUrls 는 /sandbox.html → /sandbox 로
       리다이렉트해 주지만, 로컬 파일이나 GitHub Pages 처럼 cleanUrls 가 없는 곳에서는
       확장자 없는 경로가 404 다. 리다이렉트 한 번보다 이식성이 낫다. -->
  <div class="cards">
    <a class="card" href="./sandbox.html">
      <span class="k">01 · 직접 조작</span>
      <h2>LTV 판정 샌드박스</h2>
      <p>전국 241개 시·군·구 중 아무 데나 골라 조건을 바꿔 보면 적용 LTV와 판정 근거가 즉시 바뀐다.
      우선순위 사다리에서 <b>어느 단계에서 판정이 끊겼는지</b>가 보이고,
      회귀 60건은 Python 엔진 출력과 실시간 대조된다.</p>
      <span class="go">열기 →</span>
    </a>
    <a class="card" href="./impact.html">
      <span class="k">02 · 읽는 산출물</span>
      <h2>6·30 검증보고서</h2>
      <p>정책 버전 타임라인, 시간축(Phase)별 업무 임팩트 매트릭스, 세그먼트별 고객영향,
      구조화 Rule 변경안, Human Review 큐. <b>안 돌린 단계는 안 돌렸다고 표시</b>한다.</p>
      <span class="go">열기 →</span>
    </a>
  </div>

  <footer>
    두 페이지 모두 <b>자체완결 정적 파일</b>이며, 화면에 뜨는 수치는 저장소의 Python 파이프라인이
    산출해 박아 넣은 것이다(페이지는 계산하지 않는다). 정책 업로드·LLM 추출처럼 서버가 필요한 기능은
    Streamlit 콘솔 쪽에 있다 — <code>docs/ui/DEPLOY.md</code> 참고.
  </footer>
</div>
"""


def main() -> None:
    DIST.mkdir(parents=True, exist_ok=True)
    outs = [
        wrap(WEB / "sandbox.html", "sandbox.html",
             "전국 241개 시·군·구의 규제상태를 시점별로 해석해 LTV를 판정하는 검증대. "
             "회귀 60건을 Python 엔진 출력과 실시간 대조한다.", "⚖️"),
        wrap(WEB / "impact.html", "impact.html",
             "6·30 대책을 공문 스냅샷부터 정책 버전 타임라인·룰 변경안·고객영향·회귀·"
             "Human Review까지 관통시킨 E2E 검증보고서.", "📋"),
    ]
    index = DIST / "index.html"
    index.write_text(SHELL.format(
        title="RegImpact AI",
        description="규제 변경 영향분석·검증 시스템 — 6·30 주택시장 안정대책 사례",
        favicon="⚖️",
        head_extra=('<title>RegImpact AI</title>\n'
                    '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
                    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
                    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
                    'family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans+KR:wght@400;500;600'
                    '&family=Song+Myung&display=swap">'),
        body=INDEX_BODY), encoding="utf-8")
    outs.append(index)

    for o in outs:
        print(f"wrote {o.relative_to(ROOT)} — {o.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
