"""web/impact.template.html + web/impact.json → web/impact.html (자체완결 1파일).

실행:  python tools/export_impact.py && python tools/build_impact.py
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
PLACEHOLDER = "/*__IMPACT__*/ null"


def main() -> None:
    template = (WEB / "impact.template.html").read_text(encoding="utf-8")
    if PLACEHOLDER not in template:
        raise SystemExit(f"플레이스홀더를 찾을 수 없음: {PLACEHOLDER}")
    data = json.loads((WEB / "impact.json").read_text(encoding="utf-8"))
    blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    out = WEB / "impact.html"
    out.write_text(template.replace(PLACEHOLDER, blob), encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT)} — {out.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
