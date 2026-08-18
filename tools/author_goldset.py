"""골드셋 작성 도구 — 문항을 정의하고 split 파일로 굽는다.

핵심 장치는 `q(doc, anchor)`다. 인용문을 손으로 옮겨 적지 않고 **원문에서 잘라 온다.**
손으로 옮기면 PDF/HWP 추출본의 개행·특수문자 때문에 반드시 어긋나고, 그 어긋남은
"인용은 그럴듯한데 원문엔 없음" — 이 프로젝트가 LLM에서 잡아내려는 바로 그 실패와 같은 모양이다.
정답지가 그 실패를 저지르면 안 된다.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from regimpact.eval.goldset import save_split  # noqa: E402
from regimpact.eval.schema import Category as C  # noqa: E402
from regimpact.eval.schema import Citation, GoldItem, Split  # noqa: E402
from regimpact.extractor.sources import load_sources  # noqa: E402

SOURCES = load_sources()
_NORM = {k: re.sub(r"\s+", " ", v).strip() for k, v in SOURCES.items()}

FSC, MOLIT, FAQ = "FSC_PRESS_20260630", "MOLIT_PRESS_20260630", "FAQ_20260630"
POLICY = "FSC_20260630"


def q(doc: str, anchor: str, length: int = 90, *, nth: int | None = None) -> Citation:
    """원문에서 anchor로 시작하는 구간을 그대로 잘라 인용으로 만든다(verbatim 보장).

    anchor가 여러 번 나오면 기본적으로 **실패한다** — 어느 문맥을 인용한 것인지 모르는 채로
    정답지에 넣으면 근거가 흐려지기 때문. 반복이 의도된 경우에만 nth로 명시한다.
    """
    text = _NORM[doc]
    anchor_n = re.sub(r"\s+", " ", anchor).strip()
    hits = [m.start() for m in re.finditer(re.escape(anchor_n), text)]
    if not hits:
        raise SystemExit(f"[anchor 없음] {doc}: {anchor_n!r}")
    if len(hits) > 1 and nth is None:
        raise SystemExit(f"[anchor 모호 — {len(hits)}회 등장] {doc}: {anchor_n!r}")
    idx = hits[0 if nth is None else nth]
    end = min(len(text), idx + max(length, len(anchor_n)))
    return Citation(source_doc_id=doc, quote=text[idx:end].strip())


def item(
    id_: str, split: Split, category: C, question: str, answer: str,
    facts: list[str], cites: list[Citation], *,
    escalate: bool = False, rule_id: str | None = None, note: str = "",
    authored_by: str = "ai_draft",
) -> GoldItem:
    return GoldItem(
        id=id_, split=split, category=category, question=question, gold_answer=answer,
        gold_facts=tuple(facts), citations=tuple(cites), expect_escalation=escalate,
        policy_version=POLICY, rule_id=rule_id, authored_by=authored_by, note=note,
    )


def bake(items: list[GoldItem], split: Split) -> None:
    from regimpact.eval.validate import validate_items

    rep = validate_items(items, SOURCES, expected_split=split)
    print(f"{split.value}: {rep.summary()}")
    for e in rep.errors:
        print("  ❌", e)
    for w in rep.warnings[:10]:
        print("  ⚠", w)
    if not rep.ok:
        raise SystemExit(1)
    path = save_split(items, split)
    print(f"  저장: {path.relative_to(REPO)}")
