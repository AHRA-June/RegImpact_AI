"""현업용 상품설명서 생성 — 파이프라인을 실행하고 실측 수치로 Markdown 을 조립한다.

실행:  python examples/build_ops_description.py [--out PATH] [--provider replay]

기본 provider 는 `replay` 라 LLM 호출 0회로 재현된다. 고객 면 설명서는 사람이 쓴 문서지만
(`docs/business/SERVICE_DESCRIPTION_TOMORROW.md`), 현업 면 설명서는 **수치가 전부 산출물
에서 나오므로** 생성한다 — 손으로 옮겨 적으면 반드시 갈라진다.
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from regimpact.business import render_ops_description   # noqa: E402
from regimpact.report import collect                    # noqa: E402

DEFAULT_OUT = REPO / "docs" / "business" / "OPS_PRODUCT_DESCRIPTION.md"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--provider", default="replay",
                    help="replay(기본)|cli|gemini|manual|anthropic")
    ap.add_argument("--stamp", default=None, help="생성 시각 (기본: 지금, UTC)")
    args = ap.parse_args()

    stamp = args.stamp or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    ev = collect(provider=args.provider, generated_at=stamp)
    text = render_ops_description(ev)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")

    print(f"  {out.relative_to(REPO)}  {len(text.splitlines())}줄 · {len(text):,}자")
    print(f"  변경 {len(ev.extraction.changes)}건 · 매트릭스 {len(ev.matrix.rows)}행 · "
          f"포트폴리오 {ev.impact.portfolio_size:,}건 · 감사로그 head {ev.audit.head_hash[:16]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
