"""오프라인 E2E용 canonical 6·30 추출 fixture.

이 fixture는 **사람이 확정한 AI초안**(LOCKED §4, "AI초안→사람확정")의 대리물이다.
실제 파이프라인에서는 extractor.extract_regchange()의 LLM 출력이 이 자리에 온다.
값 출처: docs/regulatory_facts.md, docs/eval/regchange_gold_6_30.json (사람 확정).

API 키 없이 Rule Change Proposal 노드를 E2E로 관통시키기 위한 결정적 입력이다.
"""
from __future__ import annotations

from ..extractor.schema import Citation, RegChangeExtraction, RegChangeItem

POLICY_ID = "FSC_20260630"
EFFECTIVE_FROM = "2026-07-01"
TARGET_REGIONS = ["GURI", "YONGIN_GIHEUNG", "HWASEONG_DONGTAN"]


def six_thirty_extraction() -> RegChangeExtraction:
    """6·30 규제 변경의 정본 추출(사람 확정 대리)."""
    return RegChangeExtraction(
        policy_id=POLICY_ID,
        effective_from=EFFECTIVE_FROM,
        target_regions=list(TARGET_REGIONS),
        changes=[
            RegChangeItem(
                category="REGION",
                summary="구리·용인 기흥·화성 동탄을 투기과열지구로 추가 지정",
                before="비규제 수도권",
                after="투기과열지구(규제지역)",
                citation=Citation(
                    source_doc_id="MOLIT_PRESS_20260630",
                    quote="투기과열지구 및 조정대상지역으로 신규 지정한다",
                ),
                confidence=1.0,
            ),
            RegChangeItem(
                category="LTV",
                summary="주택구입목적 주담대 LTV 70%→40% 하향",
                before="70%",
                after="40%",
                citation=Citation(
                    source_doc_id="FSC_PRESS_20260630",
                    quote="규제지역 내 주담대 취급시 LTV 강화",
                ),
                confidence=1.0,
            ),
            RegChangeItem(
                category="EFFECTIVE_DATE",
                summary="시행일 2026-07-01",
                before=None,
                after="7.1일부터 시행",
                citation=Citation(
                    source_doc_id="FSC_PRESS_20260630",
                    quote="강화된 대출규제가 7.1일부터 즉시 적용된다",
                ),
                confidence=1.0,
            ),
            RegChangeItem(
                category="EXCEPTION",
                summary="생애최초 구입자는 완화된 LTV(70%) 유지",
                before="70%",
                after="70%",
                citation=Citation(
                    source_doc_id="FAQ_20260630",
                    quote="금융권 생애최초 주담대",
                ),
                confidence=1.0,
            ),
            RegChangeItem(
                category="EXCEPTION",
                summary="서민·실수요자는 완화된 LTV(60%) 적용",
                before="70%",
                after="60%",
                citation=Citation(
                    source_doc_id="FAQ_20260630",
                    quote="금융권 서민·실수요자 주담대",
                ),
                confidence=1.0,
            ),
            RegChangeItem(
                category="GRANDFATHERING",
                summary="2026-06-30까지 접수 또는 계약+계약금 납부 시 종전규정(70%) 적용",
                before="2026-06-30까지",
                after="종전규정 70% 유지",
                citation=Citation(
                    source_doc_id="FAQ_20260630",
                    quote="주택매매계약을 체결하고 계약금 납부 사실 증명시 종전규정 적용 가능",
                ),
                confidence=1.0,
            ),
        ],
    )
