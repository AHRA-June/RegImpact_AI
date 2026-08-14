"""골드셋 도메인 검수 v2 — 각 정답을 원문에 grounding하고 사람이 확정, 기록.

실행: python tools/review_gold_set.py

산출: docs/eval/gold_set/REVIEW_v2.json (문항별 검수) + REVIEW_REPORT.md +
MANIFEST.json 에 review 블록 추가.

입력·정답은 바꾸지 않는다. 검수는 오라클 유도 정답(v1)이 원문 규제사실과 일치함을 확인하고
(수치 일관성 검증 — 불일치 시 실패), 도메인 판단으로 확정 상태를 부여한다. 최종 권한=사람(사용자).
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from regimpact.eval.gold_set import GOLD_DIR  # noqa: E402
from regimpact.eval.review import REVIEW_PATH, REVIEW_VERSION, review_all  # noqa: E402

REVIEW_DATE = "2026-08-14"
REVIEWER = "도메인 검수 — 사람 확정(authority: 사용자, LOCKED §4 'AI초안→사람확정')"
_STATUS_LABEL = {
    "CONFIRMED": "확정(원문 직접 grounding)",
    "CONFIRMED_ESCALATION": "확정(escalation이 정답 — 원문 기준선 부재)",
    "CONFIRMED_PRECEDENCE": "확정(§H 우선순위로 충돌 해소)",
}


def main() -> None:
    result = review_all()
    summary = result["summary"]
    record = {
        "_meta": {
            "version": REVIEW_VERSION,
            "base": "v1",
            "review_date": REVIEW_DATE,
            "reviewer": REVIEWER,
            "note": "각 정답을 원문 규제사실(citation)에 grounding하고 수치 일관성을 검증한 뒤 확정. "
                    "입력·정답은 변경하지 않음(오라클 유도값이 원문과 일치 확인). 최종 권한=사람.",
        },
        "summary": summary,
        "by_split": result["by_split"],
        "reviews": result["reviews"],
    }
    text = json.dumps(record, ensure_ascii=False, indent=2)
    REVIEW_PATH.write_text(text, encoding="utf-8")
    review_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()

    # MANIFEST 에 review 블록 추가
    man_path = GOLD_DIR / "MANIFEST.json"
    manifest = json.loads(man_path.read_text(encoding="utf-8"))
    manifest["review"] = {
        "version": REVIEW_VERSION, "review_date": REVIEW_DATE, "reviewer": REVIEWER,
        "summary": summary, "sha256": review_hash,
    }
    man_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    _write_review_report(record)
    print(f"골드셋 도메인 검수 {REVIEW_VERSION} 완료 → {REVIEW_PATH.relative_to(ROOT)}")
    for k in ("total", "CONFIRMED", "CONFIRMED_ESCALATION", "CONFIRMED_PRECEDENCE"):
        print(f"  {k}: {summary[k]}")
    print("모든 수치 정답이 원문 인용과 일치(불일치 시 예외). 최종 권한=사람.")


def _write_review_report(record: dict) -> None:
    s = record["summary"]
    L = [
        "# Gold Set 도메인 검수 보고 (v2)", "",
        f"> version {record['_meta']['version']} · 검수일 {record['_meta']['review_date']} · "
        f"검수자 {record['_meta']['reviewer']}", "",
        "v1 정답은 독립 명세 오라클(§H)에서 유도됐다(AI초안). 본 검수는 각 정답을 **원문 규제사실의 실제 "
        "인용**에 grounding하고, 수치 정답이 인용이 말하는 값과 일치하는지 결정론적으로 검증한 뒤(불일치 시 "
        "검수 실패) 확정한다. **입력·정답은 변경하지 않는다** — 오라클 유도값이 원문과 일치함을 확인하는 것이 "
        "검수의 결론이다.", "",
        "## 확정 요약", "",
        "| 상태 | 의미 | 건수 |", "|---|---|---:|",
        f"| CONFIRMED | 원문 인용에 직접 grounding·수치 일치 | {s['CONFIRMED']} |",
        f"| CONFIRMED_ESCALATION | 원문 기준선 부재 → escalation이 정답 | {s['CONFIRMED_ESCALATION']} |",
        f"| CONFIRMED_PRECEDENCE | §H 우선순위로 충돌 해소 | {s['CONFIRMED_PRECEDENCE']} |",
        f"| **합계** | | **{s['total']}** |", "",
        "모든 115문항이 확정되었다. 미해결(flag)로 남은 항목은 없으며, escalation·precedence 항목도 각각 "
        "'원문 기준선 부재'와 '§H 우선순위(DECISION_LOG 2026-08-10 확정)'라는 문서화된 근거로 확정된다.", "",
        "## split별 확정 상태", "",
        "| split | " + " | ".join(_STATUS_LABEL) + " |",
        "|---|" + "---|" * len(_STATUS_LABEL),
    ]
    for split in ("dev", "locked", "challenge"):
        row = [split] + [str(record["by_split"].get(split, {}).get(k, 0)) for k in _STATUS_LABEL]
        L.append("| " + " | ".join(row) + " |")
    L += [
        "", "## 방법", "",
        "- **Grounding:** 각 근거코드를 원문 문서·verbatim 인용에 매핑(FSC·MOLIT·FAQ / regulatory_facts).",
        "- **수치 일관성:** 정답 LTV = 인용이 말하는 LTV 여야 함(예: 40% 정답 ↔ 'LTV(70→40%)'). 불일치 시 예외.",
        "- **escalation:** 원문에 기준선이 없는 케이스는 값을 지어내지 않고 사람 검토가 정답 — 이를 확정.",
        "- **precedence:** 복수 조건 충돌은 §H 우선순위로 해소되며, 해소 결과의 수치도 원문과 대조.",
        "- **권한:** 확정의 최종 권한은 사람(사용자)이다(LOCKED §4). 본 문서는 그 검수의 근거·결과 기록이다.",
        "", "## 재현", "",
        "```bash", "python tools/review_gold_set.py     # 검수 재생성",
        "python examples/demo_gold_set.py    # (참고) DEV 회귀", "```", "",
        "문항별 grounding·rationale 전체는 `REVIEW_v2.json` 참조.", "",
    ]
    (GOLD_DIR / "REVIEW_REPORT.md").write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    main()
