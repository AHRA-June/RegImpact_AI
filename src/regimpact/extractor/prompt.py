"""RegChange Extractor 프롬프트 (grounding·citation 강제).

핵심 원칙: 원문에 있는 것만 추출, 인용은 원문 그대로(verbatim), 추론·창작 금지.
이 원칙이 Assurance의 Citation grounding / Unsupported claim 지표로 검증된다.
"""
from __future__ import annotations

SYSTEM_PROMPT = """당신은 금융 규제 변경 분석 보조 도구다. 제공된 공식 공문 원문에서
주택담보대출 규제의 Before/After 변경사항을 구조화해 추출한다.

절대 규칙:
1. 제공된 원문에 명시된 내용만 추출한다. 원문에 없는 수치·조건을 추론하거나 지어내지 마라.
2. 각 변경 항목의 citation.quote는 반드시 원문에서 **그대로 복사한 문장(부분)**이어야 한다.
   요약·의역·재구성 금지. 원문 문자열을 verbatim으로 인용하라.
3. citation.source_doc_id는 그 인용이 나온 문서의 id를 정확히 쓴다.
4. 확신이 낮으면 confidence를 낮게(0.0~1.0) 매긴다. 불확실하면 추출하지 말고 생략하라.
5. LTV는 before/after를 명확히 구분한다(예: before "70%", after "40%").

카테고리:
- LTV: 담보인정비율 변경
- EXCEPTION: 예외(생애최초·서민실수요·정책대출 등)
- GRANDFATHERING: 경과규정(종전규정 적용 조건)
- EFFECTIVE_DATE: 시행일
- REGION: 규제지역 신규 지정
- SCOPE_LIMIT: 전세대출·신용대출·중도금·사업자대출 제한(자동판정 밖)

목표는 사람이 검토할 초안이다. 정확한 인용과 낮은 환각이 정확한 완전성보다 우선이다."""


def build_user_prompt(sources: dict[str, str]) -> str:
    """source_doc_id -> 원문 텍스트 dict로 사용자 프롬프트를 만든다."""
    parts = [
        "다음은 공식 공문 원문이다. 각 문서는 <doc id=...> 태그로 구분된다.",
        "이 원문들에서 주택담보대출 규제의 Before/After 변경사항을 추출하라.\n",
    ]
    for doc_id, text in sources.items():
        parts.append(f"<doc id={doc_id}>")
        parts.append(text.strip())
        parts.append("</doc>\n")
    parts.append(
        "policy_id는 메인 정책 식별자(예: FSC_20260630)로 설정하라. "
        "target_regions는 신규 규제지역 코드 목록. effective_from은 ISO 날짜(YYYY-MM-DD)."
    )
    return "\n".join(parts)
