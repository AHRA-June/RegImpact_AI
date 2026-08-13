"""데모: 층화 합성 포트폴리오(수천 건)로 룰엔진을 대규모 차등검증한다.

실행:
    python examples/demo_portfolio_regression.py

산출:
    - 포트폴리오 커버리지(층화 셀·카테고리·결과상태·경계 분포)
    - 대규모 Rule-regression Pass Rate (엔진 ⟷ 독립 명세 오라클)
    - 카테고리별 Pass Rate

메시지(04_PLAN Phase 2 / metrics_spec): seed 30건을 넘어 수천 규모 층화 포트폴리오로
확대해도 엔진이 확정 명세와 100% 일치하는지, 그리고 실패모드 커버리지가 넓은지를
검증 가능한 방식으로 보인다. 규모가 아니라 **커버리지**가 성공 기준이다.
"""
from regimpact.tc_generator import (
    format_coverage,
    format_report,
    generate_portfolio,
    run_regression,
)


def main() -> None:
    cases = generate_portfolio(target_n=3000)
    print("=" * 60)
    print("RegImpact — 층화 합성 포트폴리오 커버리지")
    print("=" * 60)
    print(format_coverage(cases))
    print()

    report = run_regression(cases)
    print(format_report(report))


if __name__ == "__main__":
    main()
