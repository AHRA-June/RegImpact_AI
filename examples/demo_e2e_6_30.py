"""데모: 6·30 규제 변경 1건을 Source부터 Validation Report까지 E2E로 관통시킨다.

실행:
    python examples/demo_e2e_6_30.py

산출:
    - 각 단계(Source→추출→Impact Matrix→Proposal→Regression→Assurance) 요약
    - 종합 E2E 관통 판정

이 데모의 메시지(04_PLAN "코어 완성의 정의"): 6·30 1건이 볼품없어도 먼저 끝까지
관통한다. LTV 값은 전부 deterministic 룰엔진에서 오고(auditable), LLM 추출은
검증 대상(Citation grounding)으로만 흐른다. 오프라인(API 키 불필요)으로 돈다.
"""
from regimpact.impact import format_e2e_report, run_e2e


def main() -> None:
    report = run_e2e()
    print(format_e2e_report(report))


if __name__ == "__main__":
    main()
