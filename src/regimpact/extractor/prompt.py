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
6. **열거를 병합·축약하지 마라.** 원문이 예외·대상·조건을 여러 개 나열하면(A, B, C 등)
   대표 한 건으로 뭉뚱그리지 말고 **열거된 항목마다 별도 change 항목**으로 추출한다.
   "등"으로 생략된 자리 뒤에 실제 항목이 다른 문서에 열거돼 있으면 그 문서에서 찾아 채운다.
7. **여러 문서를 교차 확인하라.** 같은 주제를 문서마다 다르게(더 자세히) 서술하면
   가장 자세한 서술을 기준으로 추출하고, 그 문서를 citation으로 삼는다.

카테고리:
- LTV: 담보인정비율 변경
- EXCEPTION: 예외(생애최초·서민실수요·정책대출 등)
- GRANDFATHERING: 경과규정(종전규정 적용 조건)
- EFFECTIVE_DATE: 시행일
- REGION: 규제지역 신규 지정
- SCOPE_LIMIT: 전세대출·신용대출·중도금·사업자대출 제한(자동판정 밖)

목표는 사람이 검토할 초안이다. 정확한 인용과 낮은 환각이 정확한 완전성보다 우선이다."""


def build_user_prompt(sources: dict[str, str], *, single_document: bool = False) -> str:
    """source_doc_id -> 원문 텍스트 dict로 사용자 프롬프트를 만든다.

    single_document=True는 문서별 개별 추출 모드다. 이때는 "다른 문서에서 찾아 채우라"는
    지시가 불가능한 요구가 되므로, 대신 **이 문서 안의 것을 빠짐없이** 훑도록 지시를 바꾼다.
    """
    if single_document:
        parts = [
            "다음은 공식 공문 원문 1건이다.",
            "**이 문서 하나만** 보고, 이 문서에 있는 주택담보대출 규제 변경사항을",
            "**하나도 빠뜨리지 말고** 추출하라. 다른 문서에 같은 내용이 있을지 고려하지 마라",
            "— 중복은 나중에 병합 단계에서 처리한다. 여기서의 목표는 **누락 0**이다.",
            "표·각주·괄호 안 단서(최대한도, 전입의무, 만기, 적용범위 등)도 변경사항이면 항목으로 만든다.\n",
        ]
    else:
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
