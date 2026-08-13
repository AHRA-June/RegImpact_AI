"""6·30 앵커 추출 — 원문에 grounding된 오프라인 RegChange 추출.

Walking Skeleton은 API 키 없이 E2E가 관통되어야 한다(04_PLAN Phase 1: "간이 또는 수동 추출").
이 모듈은 사람이 원문에서 확정한 앵커 추출(RegChangeExtraction)을 제공한다.

핵심: 각 citation.quote는 `docs/sources/raw/*.txt` 원문에 **공백 정규화 기준 verbatim**으로
존재한다(evaluate.check_citation_grounding 통과). 즉 이 앵커는 Assurance ①(Citation grounding)을
실제로 통과하는 '정답 추출'이다. 실제 LLM 추출을 pipeline.run_e2e(extraction=...)로 주입하면
동일 파이프라인으로 그 출력의 grounding·gold 점수를 측정할 수 있다.

LOCKED §4(AI초안→사람확정): 이 앵커는 사람이 원문에서 확정한 기준 산출물이다.
"""
from __future__ import annotations

from ..extractor.schema import Citation, RegChangeExtraction, RegChangeItem

# 원문 doc_id는 extractor.sources.SOURCE_FILES 키와 일치해야 한다.
_FSC = "FSC_PRESS_20260630"
_FAQ = "FAQ_20260630"


def anchor_extraction() -> RegChangeExtraction:
    """6·30 사람 확정 앵커 추출을 반환한다(원문 grounding 보장)."""
    return RegChangeExtraction(
        policy_id="FSC_20260630",
        effective_from="2026-07-01",
        target_regions=["GURI", "YONGIN_GIHEUNG", "HWASEONG_DONGTAN"],
        changes=[
            RegChangeItem(
                category="LTV",
                summary="규제지역 내 주담대 LTV 강화 (비규제 70% → 규제 40%)",
                before="비규제지역 70%",
                after="규제지역 40%",
                citation=Citation(
                    _FAQ, "규제지역 내 주담대 취급시 강화된 LTV(70→40%) 적용"
                ),
                confidence=0.99,
            ),
            RegChangeItem(
                category="EFFECTIVE_DATE",
                summary="강화된 대출규제 시행일 = 2026-07-01 (7.1일)",
                before=None,
                after="2026-07-01",
                citation=Citation(
                    _FSC, "강화된 대출규제가 7.1일부터 즉시 적용된다"
                ),
                confidence=0.99,
            ),
            RegChangeItem(
                category="REGION",
                summary="규제지역 추가 지정: 동탄구·기흥구·구리시 (투기과열지구·조정대상지역)",
                before="비규제지역(수도권)",
                after="규제지역(투기과열지구·조정대상지역)",
                citation=Citation(
                    _FSC,
                    "동탄구, 기흥구, 구리시의 규제지역(투기과열지역, 조정대상지역) 지정에",
                ),
                confidence=0.98,
            ),
            RegChangeItem(
                category="EXCEPTION",
                summary="생애최초·서민실수요·정책모기지는 완화 LTV(60~70%) 유지",
                before="70%",
                after="생애최초 70% / 서민·실수요 60% (완화 유지)",
                citation=Citation(
                    _FAQ,
                    "생애최초 주택구입, 정책모기지 등은 완화된 LTV 규제비율(60~70%) 적용",
                ),
                confidence=0.95,
            ),
            RegChangeItem(
                category="EXCEPTION",
                summary="다주택자는 수도권 주택구입시 규제지역 여부 무관 LTV 0%",
                before=None,
                after="LTV 0%",
                citation=Citation(
                    _FAQ,
                    "다주택자는 수도권 內 주택구입시 규제지역 여부와 무관하게 LTV 0% 적용",
                ),
                confidence=0.95,
            ),
            RegChangeItem(
                category="GRANDFATHERING",
                summary="경과규정: 전산접수 완료 또는 계약+계약금 증명시 종전규정 적용",
                before=None,
                after="종전규정 적용(경과규정)",
                citation=Citation(
                    _FAQ,
                    "주택매매계약을 체결하고 계약금 납부 사실 증명시 종전규정 적용 가능",
                ),
                confidence=0.9,
            ),
        ],
    )
