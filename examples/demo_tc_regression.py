"""데모: TC Generator로 경계·예외·충돌 케이스를 생성하고 룰엔진을 회귀 검증한다.

실행:
    python examples/demo_tc_regression.py

산출:
    - 카테고리별 생성 케이스 수
    - Rule-regression Pass Rate (엔진 ⟷ 독립 명세 오라클)
    - (있으면) 실패 케이스와 불일치 필드

이 데모의 핵심 메시지: 엔진의 출력을 스스로 채점하지 않는다.
명세(05_RULE_SPEC §H)에서 독립 유도한 '오라클(challenger)'과 대조하여
룰엔진이 확정 명세와 일치함을 검증 가능한(auditable) 방식으로 보인다.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from regimpact.tc_generator import format_report, generate_all, run_regression  # noqa: E402


def main() -> None:
    cases = generate_all()

    by_cat: dict[str, int] = {}
    for c in cases:
        by_cat[c.category.value] = by_cat.get(c.category.value, 0) + 1

    print(f"생성된 회귀 케이스: {len(cases)}건")
    for cat, n in by_cat.items():
        print(f"  - {cat:<15} {n}건")
    print()

    report = run_regression(cases)
    print(format_report(report))

    # 명세 모호성이 표시된 충돌 케이스를 함께 노출(투명성).
    noted = [c for c in cases if c.spec_note]
    if noted:
        print()
        print("명세 주의사항이 부착된 케이스:")
        for c in noted:
            print(f"  • {c.case_id}: {c.spec_note}")


if __name__ == "__main__":
    main()
