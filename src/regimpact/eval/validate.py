"""골드셋 무결성 검사 — 정답지 자체를 먼저 검증한다.

정답지가 틀리면 그 위의 모든 지표가 틀린다. 특히 **인용이 원문에 실제로 존재하는지**는
사람 눈으로 100문항을 대조할 수 없으므로 기계가 매번 검사한다. Citation Assurance가 LLM
출력에 하는 일을 여기서는 **골드셋 자신에게** 한다.
"""
from __future__ import annotations

import re

from ..rule_engine import (
    LTV_BASELINE,  # noqa: F401 - 존재 확인용 import (모듈 로드 보증)
)
from .schema import Category, GoldItem, Split, ValidationReport

# 룰엔진이 실제로 내보내는 rule_id (rule_engine._decided / _baseline_rule 호출부)
KNOWN_RULE_IDS = frozenset({
    "REG_STD", "REG_FIRSTHOME", "REG_REALDEMAND", "REG_OWNER_0", "MULTI_0", "NONREG_STD_70",
})
KNOWN_POLICY_VERSIONS = frozenset({"FSC_20260630", "MOLIT_20260630"})


def _norm(s: str) -> str:
    """공백·개행 정규화 — 원문이 PDF/HWP 추출본이라 문장 중간에 개행이 섞여 있다."""
    return re.sub(r"\s+", " ", s).strip()


def validate_items(
    items: list[GoldItem], sources: dict[str, str], *, expected_split: Split | None = None
) -> ValidationReport:
    """문항 목록의 무결성을 검사한다. errors가 비어야 이 셋을 쓸 수 있다."""
    rep = ValidationReport(checked=len(items))
    norm_sources = {doc_id: _norm(text) for doc_id, text in sources.items()}

    seen_ids: set[str] = set()
    seen_questions: dict[str, str] = {}

    for item in items:
        tag = f"[{item.id}]"

        if item.id in seen_ids:
            rep.errors.append(f"{tag} id 중복")
        seen_ids.add(item.id)

        if expected_split is not None and item.split != expected_split:
            rep.errors.append(f"{tag} split 불일치: {item.split.value} (파일은 {expected_split.value})")
        if not item.id.startswith(item.split.value + "-"):
            rep.errors.append(f"{tag} id는 '{item.split.value}-'로 시작해야 함")

        qkey = _norm(item.question)
        if qkey in seen_questions:
            rep.errors.append(f"{tag} 질문 중복 (같은 질문: {seen_questions[qkey]})")
        else:
            seen_questions[qkey] = item.id

        if not item.question.strip():
            rep.errors.append(f"{tag} question 비어 있음")
        if not item.gold_answer.strip():
            rep.errors.append(f"{tag} gold_answer 비어 있음")
        if not item.gold_facts:
            rep.errors.append(f"{tag} gold_facts 비어 있음 — 자동 채점 앵커가 없다")

        # ★ 핵심: 인용이 원문에 verbatim으로 존재하는가
        if not item.citations:
            rep.errors.append(f"{tag} 근거 인용 없음")
        for cit in item.citations:
            src = norm_sources.get(cit.source_doc_id)
            if src is None:
                rep.errors.append(f"{tag} 알 수 없는 source_doc_id: {cit.source_doc_id}")
                continue
            quote = _norm(cit.quote)
            if not quote:
                rep.errors.append(f"{tag} 빈 인용")
            elif quote not in src:
                rep.errors.append(
                    f"{tag} 인용이 원문에 없음 ({cit.source_doc_id}): \"{quote[:60]}…\""
                )

        # gold_facts 는 정답 문장 안에서 확인 가능해야 한다(채점기가 찾을 수 없는 앵커 방지)
        hay = _norm(f"{item.gold_answer} {item.question}")
        for fact in item.gold_facts:
            if _norm(fact) not in hay:
                rep.warnings.append(f"{tag} gold_fact가 gold_answer에 없음: {fact!r}")

        if item.category == Category.AMBIGUOUS and not item.expect_escalation:
            rep.errors.append(f"{tag} AMBIGUOUS인데 expect_escalation=False — 모호하면 사람에게 올려야 한다")
        if item.rule_id is not None and item.rule_id not in KNOWN_RULE_IDS:
            rep.errors.append(f"{tag} 알 수 없는 rule_id: {item.rule_id}")
        if item.policy_version not in KNOWN_POLICY_VERSIONS:
            rep.errors.append(f"{tag} 알 수 없는 policy_version: {item.policy_version}")
        if item.authored_by not in ("ai_draft", "human_confirmed"):
            rep.errors.append(f"{tag} authored_by 값 오류: {item.authored_by}")

    return rep
