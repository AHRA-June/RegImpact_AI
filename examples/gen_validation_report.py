"""검증보고서를 라이브 파이프라인 수치로 생성해 docs/validation_report_6_30.md에 쓴다.

실행:
    python examples/gen_validation_report.py

모든 수치(E2E·포트폴리오 회귀·골드셋·판별력)는 실제 호출에서 나오므로 재현 가능하다.
시스템이 바뀌면 이 스크립트를 다시 돌려 보고서를 갱신한다.
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from regimpact.report import build_validation_report  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "docs" / "validation_report_6_30.md"


def main() -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    report = build_validation_report(generated_at=stamp)
    OUT.write_text(report, encoding="utf-8")
    print(f"검증보고서 생성: {OUT}  ({len(report.splitlines())}줄)")


if __name__ == "__main__":
    main()
