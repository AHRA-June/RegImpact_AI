"""AI 거버넌스 산출물 생성 — Model/System Card + AI Risk Register.

실행:  python examples/build_governance_docs.py
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from regimpact.governance import render_card, render_register   # noqa: E402
from regimpact.report import collect                            # noqa: E402

OUT_DIR = REPO / "docs" / "governance"


def main() -> int:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    ev = collect(generated_at=stamp)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for name, text in (("MODEL_SYSTEM_CARD.md", render_card(ev)),
                       ("AI_RISK_REGISTER.md", render_register(ev))):
        path = OUT_DIR / name
        path.write_text(text, encoding="utf-8")
        print(f"  {path.relative_to(REPO)}  {len(text.splitlines())}줄")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
