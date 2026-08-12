"""내규 영향도 매핑 데모 — "규제가 바뀌면 우리 규정 어디를 고쳐야 하나".

저장된 6·30 추출을 모의 내규 대장(13건)에 매핑해 규정별 수정 필요 여부를 초안한다.
무관 규정(예금·카드)까지 함께 보여 과잉 플래그가 없음을 확인한다.

실행: python examples/demo_rule_catalog.py  → 콘솔 + docs/eval/rule_catalog_impact.md
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from regimpact.extractor import RegChangeExtraction  # noqa: E402
from regimpact.rule_catalog import (  # noqa: E402
    DEFAULT_CATALOG,
    Disposition,
    format_catalog,
    map_catalog_impact,
)

REPO = Path(__file__).resolve().parent.parent
SAVED = REPO / "docs" / "eval" / "extractor_run_6_30_gemini.json"
DOC = REPO / "docs" / "eval" / "rule_catalog_impact.md"

_KO = {Disposition.EDIT_REQUIRED: "수정필요", Disposition.NEEDS_REVIEW: "검토",
       Disposition.INDIRECT: "간접영향", Disposition.UNAFFECTED: "무관"}


def main() -> None:
    ext = RegChangeExtraction.from_dict(json.loads(SAVED.read_text(encoding="utf-8")))
    ci = map_catalog_impact(ext)
    print(format_catalog(ci))
    _write_doc(ci)
    print(f"\n갱신: {DOC.relative_to(REPO)}")


def _write_doc(ci) -> None:
    c = ci.counts()
    L: list[str] = []
    L.append("# 내규 영향도 맵 (6·30) — 규제 변경 → 우리 규정 수정 지점")
    L.append("")
    L.append("> `examples/demo_rule_catalog.py` 산출. 규제 변경을 **여신 내규 대장**에 매핑해 "
             "수정이 필요한 규정을 짚는다. `rule_proposal.py`(룰엔진 내부 파라미터 대조)와 달리 "
             "**규정 문서 대장** 관점이다.")
    L.append("")
    L.append("## 정직성 고지")
    L.append("")
    L.append("- 내규 대장은 **모의(가짜) 규정**이다(실제 회사 문서·고객 데이터 아님, LOCKED §8). "
             "실제 도입 시 이 표를 진짜 내규 레지스트리로 교체하면 매핑 로직은 불변.")
    L.append("- 규제 변경(공문)은 **실제**다. 매핑은 결정적(카테고리+키워드)이며 LLM 판단이 아니다.")
    L.append("- 모든 수정안은 **초안이며 승인 PENDING**(사람 확정, LOCKED §4). 자동 반영 없음.")
    L.append("- **무관 규정(예금·카드)도 포함** — 시스템이 무관한 규정을 과잉 플래그하지 않음을 보인다.")
    L.append("")
    L.append(f"## 6·30 결과: 수정필요 {c['EDIT_REQUIRED']} · 검토 {c['NEEDS_REVIEW']} · "
             f"간접영향 {c['INDIRECT']} · 무관 {c['UNAFFECTED']} (총 {len(ci.items)})")
    L.append("")
    L.append("| 판정 | 규정ID | 내규 | 분류 | 근거 규제변경 | 수정안(초안) |")
    L.append("|---|---|---|---|---|---|")
    for it in ci.items:
        r = it.rule
        drv = it.drivers[0]["summary"] if it.drivers else "—"
        if it.drivers and len(it.drivers) > 1:
            drv += f" 외 {len(it.drivers)-1}건"
        edit = it.suggested_edit if it.drivers else "영향 없음"
        L.append(f"| **{_KO[it.disposition]}** | {r.rid} | {r.title} | {r.category} | "
                 f"{drv} | {edit} |")
    L.append("")
    L.append("> 판정: **수정필요**=직접 대상 / **검토**=연동 가능(사람 확인) / "
             "**간접영향**=점검 권고 / **무관**=영향 없음.")
    L.append("")
    DOC.write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    main()
