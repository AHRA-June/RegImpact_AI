"""검증보고서 생성 — 파이프라인을 실행하고 실측 수치로 Markdown 을 조립한다.

실행:  python examples/build_validation_report.py [--out PATH] [--provider replay]

기본 provider 는 `replay` 라 LLM 호출 0회로 재현된다.
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from regimpact.report import collect, render        # noqa: E402

DEFAULT_OUT = REPO / "docs" / "validation" / "VALIDATION_REPORT.md"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--provider", default="replay",
                    help="replay(기본)|cli|gemini|manual|anthropic")
    ap.add_argument("--stamp", default=None,
                    help="생성 시각 (기본: 지금, UTC)")
    args = ap.parse_args()

    stamp = args.stamp or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    evidence = collect(provider=args.provider, generated_at=stamp)
    text = render(evidence)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")

    print(f"  {out.relative_to(REPO)}  {len(text.splitlines())}줄 · {len(text):,}자")
    print(f"  감사로그 head: {evidence.audit.head_hash}")
    print(f"  변경안 상태: {evidence.proposal.status.value}"
          f" · 엔진 대조 {evidence.consistency.summary()['passed']}"
          f"/{evidence.consistency.summary()['total']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
