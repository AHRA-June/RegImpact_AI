"""6·30 Impact Matrix E2E 데모 — 브리프 §18 코어 완성의 정의를 한 번에 관통.

실행:
    python examples/demo_impact_e2e.py              # LLM 없이 (9/10 단계 실제 실행)
    python examples/demo_impact_e2e.py --llm        # ANTHROPIC_API_KEY 로 추출까지 (10/10)
    python examples/demo_impact_e2e.py --out FILE   # 검증보고서를 마크다운으로 저장
"""
import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from regimpact.impact import render_report, run_e2e  # noqa: E402

GOLD = json.loads((REPO / "docs" / "eval" / "regchange_gold_6_30.json").read_text(encoding="utf-8"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--llm", action="store_true", help="실제 LLM 으로 RegChange 추출까지 실행")
    ap.add_argument("--out", help="검증보고서 저장 경로 (.md)")
    args = ap.parse_args()

    complete = None
    if args.llm:
        try:
            from regimpact.extractor import anthropic_completion
            complete = anthropic_completion()
        except Exception as e:  # SDK 미설치 / 인증 실패
            print(f"[안내] LLM 사용 불가 ({type(e).__name__}: {e}) — 추출 없이 진행합니다.\n")

    result = run_e2e(complete=complete, gold=GOLD)

    print("=" * 78)
    print("RegImpact — 6·30 End-to-End 파이프라인")
    print("=" * 78)
    for i, s in enumerate(result.stages, 1):
        mark = {"완료": "✅", "확인 필요": "⚠️ ", "미실행": "⛔"}[s.status.value]
        print(f"{i:>2}. {mark} {s.name:<32} {s.detail}")
    print("-" * 78)
    print(f"전 단계 실행: {result.completed}")

    report = render_report(result)
    if args.out:
        Path(args.out).write_text(report + "\n", encoding="utf-8")
        print(f"\n검증보고서 저장: {args.out} ({len(report.splitlines())}줄)")
    else:
        print("\n" + report)


if __name__ == "__main__":
    main()
