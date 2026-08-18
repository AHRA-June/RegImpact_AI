"""골드셋 무결성 리포트 — 정답지 자체를 검증한다 (LLM 호출 0회).

    python examples/validate_goldset.py

봉인된 셋(LOCKED/CHALLENGE)도 **정답을 화면에 내보내지 않고** 무결성만 검사한다.
검증에 필요한 것은 "인용이 원문에 있는가"이지 "정답이 무엇인가"가 아니기 때문이다.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from regimpact.eval import (  # noqa: E402
    Split,
    coverage_report,
    load_split,
    split_stats,
    validate_items,
)
from regimpact.eval.goldset import SEALED  # noqa: E402
from regimpact.extractor.sources import load_sources  # noqa: E402

REASON = "무결성 검사 전용 실행 — 정답을 출력하지 않고 인용·필드만 대조 (튜닝 아님)"


def main() -> None:
    sources = load_sources()
    print(f"원문 {len(sources)}건 로드: {', '.join(sources)}\n")

    total, all_ok = 0, True
    for split in Split:
        stats = split_stats(split)          # 봉인을 열지 않고 구성 확인
        kw = {} if split not in SEALED else {"unseal_reason": REASON}
        items = load_split(split, **kw)
        rep = validate_items(items, sources, expected_split=split)
        cov = coverage_report(items)
        total += stats["count"]
        all_ok = all_ok and rep.ok

        seal = "🔓" if split not in SEALED else "🔒"
        print(f"{seal} {split.value:10s} {rep.summary()}  "
              f"high-risk {stats['high_risk_ratio']:.0%}  상태 {stats['authored_by']}")
        print(f"     카테고리: {stats['categories']}")
        for e in rep.errors[:5]:
            print("     ❌", e)
        for w in (rep.warnings + cov.warnings)[:5]:
            print("     ⚠", w)
        print()

    print(f"총 {total}문항 — {'✅ 전체 무결성 통과' if all_ok else '❌ 오류 있음'}")
    print("\n주의: LOCKED/CHALLENGE 접근은 docs/eval/gold/SEAL_ACCESS_LOG.md에 기록됩니다.")


if __name__ == "__main__":
    main()
