"""층화 합성 포트폴리오 데모 — 룰엔진 평가셋 100~120건 통계화.

실행: python examples/demo_portfolio.py   (repo 루트에서)
출력: 콘솔 통계 + docs/reports/rule_portfolio_stats.md 저장.

정답은 독립 명세 오라클이 유도(차등검증) → 100+건을 손라벨 없이 확장.
결정론 엔진이라 split(DEV/LOCKED/CHALLENGE) 전량 측정해도 누수 위험 없음(04_PLAN §0-5).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from regimpact.tc_generator import (  # noqa: E402
    format_portfolio_stats,
    generate_portfolio,
    run_regression,
)


def main() -> None:
    cases = generate_portfolio()
    report = run_regression(cases)
    stats = format_portfolio_stats(report)
    print(stats)

    out = ROOT / "docs" / "reports" / "rule_portfolio_stats.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("```\n" + stats + "\n```\n", encoding="utf-8")
    print(f"\n생성됨: {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
