"""골드셋 도메인 검수(v2) 요약 출력.

실행: python examples/demo_gold_review.py

각 정답을 원문 규제사실에 grounding하고 확정한 결과를 보여준다(사람 확정, LOCKED §4).
검수 재생성은 `python tools/review_gold_set.py`.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from regimpact.eval import load_review  # noqa: E402


def main() -> None:
    rec = load_review()
    if rec is None:
        print("검수 기록 없음 — python tools/review_gold_set.py 로 생성하세요.")
        return
    s = rec["summary"]
    print(f"골드셋 도메인 검수 {rec['_meta']['version']} · {rec['_meta']['review_date']}")
    print(f"  검수자: {rec['_meta']['reviewer']}")
    print("-" * 60)
    print(f"  총 {s['total']}문항 확정")
    print(f"    CONFIRMED(직접 grounding)   : {s['CONFIRMED']}")
    print(f"    CONFIRMED_ESCALATION(기준부재): {s['CONFIRMED_ESCALATION']}")
    print(f"    CONFIRMED_PRECEDENCE(§H 충돌) : {s['CONFIRMED_PRECEDENCE']}")
    print("-" * 60)
    # 각 상태 대표 1건
    seen = set()
    for cid, r in rec["reviews"].items():
        if r["status"] not in seen:
            seen.add(r["status"])
            print(f"  · [{r['status']}] {cid}")
            print(f"      근거 {r['grounding_doc']}: \"{r['grounding_quote'][:44]}...\"")
    print("\n입력·정답 불변 — 오라클 유도값이 원문과 일치함을 확인·확정. 최종 권한=사람.")


if __name__ == "__main__":
    main()
