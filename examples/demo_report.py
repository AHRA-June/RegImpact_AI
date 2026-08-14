"""E2E 검증 보고서 데모 — 6·30 파이프라인을 Source→…→Report로 관통해 출력.

실행: python examples/demo_report.py   (repo 루트에서)

이것이 브리프 §18 '코어 완성의 정의'다: Source Snapshot → Policy Version → RegChange →
Impact Matrix → Rule Change Proposal → Test Cases/Regression → Assurance → Human Review →
Validation Report 로 End-to-End 완결. 값은 모두 실제 산출물(gold·엔진·회귀)에서 유도된다.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from regimpact.report import build_validation_report, format_report  # noqa: E402


def main() -> None:
    report = build_validation_report()
    print(format_report(report))


if __name__ == "__main__":
    main()
