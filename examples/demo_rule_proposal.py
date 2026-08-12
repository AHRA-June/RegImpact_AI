"""Rule Change Proposal 데모 — 추출 → 구조화 룰 변경안(초안) → 사람 확정 룰 대조.

저장된 6·30 추출로 오프라인(API 키 불필요) 실행. 각 변경을 룰엔진 룰 표면에 매핑하고
사람 확정 엔진 현재값과 대조. 승인상태는 항상 PENDING(자동 확정 없음, LOCKED §4).

실행: python examples/demo_rule_proposal.py
"""
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from regimpact.extractor import RegChangeExtraction  # noqa: E402
from regimpact.rule_proposal import build_proposal, format_proposal  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
SAVED = REPO / "docs" / "eval" / "extractor_run_6_30_gemini.json"


def main() -> None:
    ext = RegChangeExtraction.from_dict(json.loads(SAVED.read_text(encoding="utf-8")))
    proposal = build_proposal(ext, generated_on=date(2026, 8, 12))
    print(format_proposal(proposal))


if __name__ == "__main__":
    main()
