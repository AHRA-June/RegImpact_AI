"""E2E 완결 데모 — 6·30 코어 완성 파이프라인 관통 + 검증보고서 출력.

Source → 추출 → Impact Matrix → Rule Change Proposal → Test Cases → Regression
→ Assurance(4 dimension) → Validation Report. API 키 없이 오프라인으로 관통.

실행: python examples/demo_e2e.py            (검증보고서 Markdown 출력)
      python examples/demo_e2e.py --json     (구조화 요약 JSON 출력)
      python examples/demo_e2e.py --save out.md
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from regimpact.e2e import run_six_thirty_e2e  # noqa: E402
from regimpact.report import ReportMeta  # noqa: E402


def main() -> None:
    args = sys.argv[1:]
    # 재현 가능한 데모를 위해 시각/이벤트는 고정 주입(런타임에선 실제 값)
    meta = ReportMeta(generated_at="2026-08-11T00:00:00Z", event_id="demo-6-30-0001",
                      prompt_version="regchange-v1")
    result = run_six_thirty_e2e(meta=meta)

    if "--json" in args:
        print(json.dumps(result.report.to_dict(), ensure_ascii=False, indent=2))
        return

    md = result.report.render_markdown()
    if "--save" in args:
        out = Path(args[args.index("--save") + 1])
        out.write_text(md, encoding="utf-8")
        print(f"저장됨: {out}")
        return

    print(md)
    print()
    print(f"[gate] {result.assurance.gate.value}  "
          f"[decision] {result.report.decision_status}")


if __name__ == "__main__":
    main()
