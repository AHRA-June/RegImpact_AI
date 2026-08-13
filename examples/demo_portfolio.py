"""층화 포트폴리오 + 대규모 격자 데모 — 룰엔진 평가셋 통계화.

실행: python examples/demo_portfolio.py   (repo 루트에서)
출력:
    docs/reports/rule_portfolio_stats.md  — 큐레이션 106건(카테고리 균형)
    docs/reports/rule_grid_stats.md       — 조합 격자 3,200건(넓은 입력공간)

정답은 독립 명세 오라클이 유도(차등검증) → 손라벨 없이 확장.
결정론 엔진이라 split 전량 측정해도 누수 위험 없음(04_PLAN §0-5).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from regimpact.tc_generator import (  # noqa: E402
    format_portfolio_stats,
    generate_grid,
    generate_portfolio,
    run_regression,
)


def _write(name: str, stats: str) -> Path:
    out = ROOT / "docs" / "reports" / name
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("```\n" + stats + "\n```\n", encoding="utf-8")
    return out


def main() -> None:
    # 1) 큐레이션 포트폴리오 (카테고리 균형, 사람이 읽는 case_id)
    port = run_regression(generate_portfolio())
    port_stats = format_portfolio_stats(port)
    print(port_stats)
    p1 = _write("rule_portfolio_stats.md", port_stats)

    # 2) 대규모 조합 격자 (수천 건, 넓은 입력공간)
    grid = run_regression(generate_grid())
    grid_stats = format_portfolio_stats(
        grid, title="Rule Grid Stats (조합 격자, 넓은 입력공간)")
    print("\n" + grid_stats)
    p2 = _write("rule_grid_stats.md", grid_stats)

    print(f"\n생성됨: {p1.relative_to(ROOT)} (N={port.total}), "
          f"{p2.relative_to(ROOT)} (N={grid.total})")


if __name__ == "__main__":
    main()
