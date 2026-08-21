"""데모 영상 녹화 — 실제 배포 화면을 스크립트로 조작해 한 번에 찍는다.

편집·합성을 하지 않는 것이 요점이다. 잘라 붙이면 "이렇게 동작한다"가 아니라 "이렇게
보이게 만들 수 있다"가 되고, 그건 심사자가 데모를 열어 보는 순간 갈라진다.

**저장소에 둔 이유:** 화면이 바뀌면 영상도 다시 찍어야 한다. 2026-08-21 지원서 점검에서
녹화본이 이미 낡아 있었다 — 6단계에 '지켜보기'가 들어갔는데 영상은 그 전 화면이었다.
녹화 스크립트가 임시 폴더에만 있으면 다시 찍는 것 자체가 사라진다.

    python tools/build_site.py --out site
    python tools/record_demo.py --site site --out 내한도시그널_데모.webm

`--steps` 로 지나갈 주제를 출력해 대본(APPLY_TOMORROW_CHALLENGE §3)과 대조할 수 있다.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BROWSER_ROOTS = ("/opt/pw-browsers", str(Path.home() / ".cache" / "ms-playwright"))
W, H = 390, 844          # 폰 세로 — 웹뷰 탑재형이므로 데스크톱 프레임으로 찍지 않는다
UA = ("Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/120 Mobile Safari/537.36")   # 폰트 CDN 이 서브셋을 고르는 근거


def _chromium() -> str:
    for root in BROWSER_ROOTS:
        for pat in ("chromium*/chrome-linux*/chrome", "chromium*/chrome-mac*/Chromium.app"):
            hits = sorted(Path(root).glob(pat)) if Path(root).exists() else []
            if hits:
                return str(hits[0])
    print("chromium 을 찾지 못했습니다 — python -m playwright install chromium", file=sys.stderr)
    raise SystemExit(3)


# 지나갈 화면과 머무는 시간(ms). **대본의 시간표가 여기서 나온다** — 두 벌로 적으면
# 영상은 바뀌고 대본은 안 바뀐 채 제출된다(2026-08-21 점검에서 실제로 그랬다).
#   (동작, 라벨, 머무는 ms)  — 동작은 page 를 받는 함수
STEPS = [
    (None, "1단계 · 영향 알림 + 내 조건", 2500),
    (lambda pg: pg.select_option("#region", "GURI"), "지역 선택 — 구리시", 900),
    (lambda pg: pg.fill("#price", "8"), "주택가격 8억", 1800),
    (lambda pg: pg.click("#pg-next"), "2단계 · 경과규정 (해당 없음)", 2400),
    (lambda pg: pg.click("#pg-next"), "3단계 · 변경 전 → 후 (70% → 40%)", 3000),
    (lambda pg: pg.click('.delta a[href="#gf"]'), "안내 링크로 2단계 이동", 2000),
    (lambda pg: pg.click("#gf-yes"), "‘시행 전에 계약했어요’", 1800),
    (lambda pg: pg.click('#steps button[aria-controls="pg-limit"]'),
     "3단계 재판정 — 경과규정으로 70% 유지", 3200),
    (lambda pg: pg.click('#steps button[aria-controls="pg-afford"]'),
     "4단계 · 총 가능금액", 1400),
    (lambda pg: pg.fill("#aff-income", "5000"), "연소득 5,000만원", 600),
    (lambda pg: pg.fill("#aff-debt", "100"), "기존 대출 월 100만원", 600),
    (lambda pg: pg.fill("#aff-rate", "4"), "금리 4% — DSR·DTI 병목 표시", 2800),
    (lambda pg: pg.mouse.wheel(0, 260), "목표 역산 처방", 2000),
    (lambda pg: pg.click('#steps button[aria-controls="pg-product"]'),
     "5단계 · 상품 자격 판정", 2400),
    (lambda pg: pg.click('#steps button[aria-controls="pg-timeline"]'),
     "6단계 · 한도 타임라인", 2200),
    (lambda pg: pg.mouse.wheel(0, 420), "지켜보기 패널", 1600),
    (lambda pg: _click_if(pg, "#watch-acts button"), "‘이 조건으로 지켜보기’ 저장", 2600),
    (lambda pg: pg.click('#steps button[aria-controls="pg-qa"]'), "7단계 · 물어보기", 1400),
    (lambda pg: pg.click(".qa .preset button"), "쉬운 요약 + 원문 근거", 3000),
    (lambda pg: pg.mouse.wheel(0, 320), "공문 원문 발췌", 2400),
]


FONT_HOSTS = ("fonts.googleapis.com", "fonts.gstatic.com")


def _serve_webfonts(ctx) -> None:
    """웹폰트를 대신 받아 준다 — 못 받으면 **영상 앞에 12초짜리 빈 화면이 붙는다.**

    화면은 Noto Sans·JetBrains Mono 를 CDN 에서 받는데, 이 실행 환경의 브라우저는
    그 호스트에 직접 닿지 못해 요청이 timeout 까지 매달린다. 페이지가 느린 것이 아니라
    (폰트를 막고 재면 0.2초) **녹화 환경이 막힌 것**이다. 그렇다고 폰트를 꺼서 찍으면
    심사자가 여는 실제 화면과 글꼴이 달라지므로, 받아서 그대로 물려 준다.
    """
    cache: dict[str, bytes] = {}

    def handler(route, request):
        url = request.url
        if url not in cache:
            got = subprocess.run(
                ["curl", "-sS", "-L", "-A", UA, url],
                capture_output=True, timeout=30)
            if got.returncode != 0 or not got.stdout:
                route.abort()                       # 못 받으면 대체 글꼴로 간다(멈추지 않는다)
                return
            cache[url] = got.stdout
        kind = "text/css" if "googleapis" in url else "font/woff2"
        route.fulfill(status=200, body=cache[url],
                      headers={"content-type": kind, "access-control-allow-origin": "*"})

    for host in FONT_HOSTS:
        ctx.route(f"**://{host}/**", handler)


def _click_if(pg, sel) -> None:
    """없으면 넘어간다 — 저장이 막힌 환경에서도 녹화가 끝까지 돌아야 한다."""
    el = pg.query_selector(sel)
    if el:
        el.click()


def timeline() -> list[tuple[float, float, str]]:
    """(시작초, 끝초, 라벨). 대본은 이 목록에서 만든다."""
    out, t = [], 0.0
    for _, label, ms in STEPS:
        out.append((t, t + ms / 1000, label))
        t += ms / 1000
    return out


def record(site: Path, out: Path, verbose: bool = True) -> Path:
    from playwright.sync_api import sync_playwright

    page_html = (site / "signal.html").resolve()
    vid_dir = out.parent / "_vid"
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=_chromium())
        ctx = b.new_context(viewport={"width": W, "height": H}, device_scale_factor=2,
                            record_video_dir=str(vid_dir),
                            record_video_size={"width": W, "height": H})
        _serve_webfonts(ctx)
        # 영상은 컨텍스트가 열린 순간부터 녹화된다 — 시계도 거기서 시작해야
        # 시간표와 영상의 초가 맞는다(페이지 로드 시간이 앞에 붙기 때문).
        t0 = time.monotonic()
        pg = ctx.new_page()
        pg.goto(f"file://{page_html}")
        # 시간표는 **재는 것**이지 더하는 것이 아니다. 조작(클릭·입력)마다 지연이 붙어
        # 대기시간 합계와 실제 영상 길이가 15초 넘게 벌어진다 — 그 차이로 대본을 쓰면
        # 심사자가 보는 화면과 내레이션이 어긋난다.
        marks = []
        for act, label, ms in STEPS:
            start = time.monotonic() - t0
            if act is not None:
                act(pg)
            pg.wait_for_timeout(ms)
            marks.append((start, time.monotonic() - t0, label))
        src = Path(pg.video.path())
        ctx.close()
        b.close()

    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), out)
    shutil.rmtree(vid_dir, ignore_errors=True)
    sheet = out.with_suffix(".timeline.txt")
    sheet.write_text(
        "\n".join(f"{a:5.1f}–{b:5.1f}초  {label}" for a, b, label in marks) + "\n",
        encoding="utf-8")
    if verbose:
        print(f"영상: {out}  ({out.stat().st_size:,} bytes · {W}×{H} · 무음 · "
              f"약 {marks[-1][1]:.0f}초)")
        print(f"시간표: {sheet}  — 대본(APPLY_TOMORROW_CHALLENGE §3)은 이 값을 쓴다")
        for a, b, label in marks:
            print(f"  {a:5.1f}–{b:5.1f}초  {label}")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="데모 영상 녹화 (편집 없음)")
    ap.add_argument("--site", default=str(REPO / "site"), help="빌드된 사이트 폴더")
    ap.add_argument("--out", default="내한도시그널_데모.webm")
    ap.add_argument("--steps", action="store_true",
                    help="지나갈 화면과 시간표만 출력한다 (대본 대조용)")
    a = ap.parse_args()
    if a.steps:
        for start, end, label in timeline():
            print(f"  {start:5.1f}–{end:5.1f}초  {label}")
        return
    site = Path(a.site)
    if not (site / "signal.html").exists():
        print(f"{site}/signal.html 이 없습니다 — 먼저 python tools/build_site.py --out {site}")
        raise SystemExit(2)
    record(site, Path(a.out))


if __name__ == "__main__":
    main()
