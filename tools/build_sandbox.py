"""web/sandbox.template.html + web/fixtures.json → web/sandbox.html (자체완결 1파일).

Artifact/정적 호스팅은 외부 요청이 막혀 있으므로 픽스처를 파일 안에 인라인한다.
플레이스홀더 `/*__FIXTURES__*/ null` 자리에 JSON을 그대로 끼워 넣는다.

실행:  python tools/export_fixtures.py && python tools/build_sandbox.py
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
PLACEHOLDER = "/*__FIXTURES__*/ null"


def main() -> None:
    template = (WEB / "sandbox.template.html").read_text(encoding="utf-8")
    if PLACEHOLDER not in template:
        raise SystemExit(f"플레이스홀더를 찾을 수 없음: {PLACEHOLDER}")
    fixtures = json.loads((WEB / "fixtures.json").read_text(encoding="utf-8"))
    # </script> 가 JSON 문자열 안에 있으면 스크립트가 조기 종료되므로 방어
    blob = json.dumps(fixtures, ensure_ascii=False).replace("</", "<\\/")
    out = WEB / "sandbox.html"
    out.write_text(template.replace(PLACEHOLDER, blob), encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT)} — {len(fixtures['cases'])} cases inlined, {out.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
