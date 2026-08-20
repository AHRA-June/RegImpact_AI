"""내게 가능한 상품 찾기 — **자격 판정이지 추천이 아니다**.

이 파일이 지키는 것 하나: **없는 근거로 "가능합니다"라고 말하지 않는다.**
디딤돌·보금자리론의 소득·자산 요건은 6·30 공문에 없다. 원문에 없는 요건을
ELIGIBLE 로 올리는 순간 이 제품의 원칙(지어내지 않는다)이 무너진다.
"""
import re

import pytest

from regimpact.products import PRODUCTS, eligible_products, summary


def _v(**kw):
    base = dict(decision_status="DECIDED", max_ltv=0.4, grandfathered=False, regulated=True)
    base.update(kw)
    return {v.id: v for v in eligible_products(**base)}


def test_policy_mortgages_never_claim_eligibility_without_grounds():
    """★ 핵심 — 정책모기지 자격 요건(소득·자산)은 공문에 없다. 절대 ELIGIBLE 이 아니다."""
    for kw in [{}, {"first_home_buyer": True}, {"real_demand_flag": True},
               {"grandfathered": True}, {"regulated": False}]:
        v = _v(**kw)
        for pid in ("DIDIMDOL", "BOGEUMJARI"):
            assert v[pid].status != "ELIGIBLE", f"{pid}: 근거 없이 가능하다고 말했다 ({kw})"


def test_flags_the_engine_knows_become_eligible():
    """엔진이 이미 판정한 사실(생애최초·서민실수요)은 원문이 완화 대상으로 명시한다."""
    assert _v(first_home_buyer=True)["FIRST_HOME"].status == "ELIGIBLE"
    assert _v(real_demand_flag=True)["REAL_DEMAND"].status == "ELIGIBLE"
    # 체크하지 않았으면 '해당'이 아니라 '확인 필요'
    assert _v()["FIRST_HOME"].status == "UNKNOWN"
    assert _v()["REAL_DEMAND"].status == "UNKNOWN"


def test_zero_ltv_blocks_every_product():
    """대출 자체가 막혔으면 상품을 논할 단계가 아니다 — 희망을 남기지 않는다."""
    v = _v(max_ltv=0.0, house_count=2)
    assert all(x.status == "BLOCKED" for x in v.values())
    assert summary(list(v.values()))["eligible"] == []


def test_human_review_never_becomes_eligible():
    v = _v(decision_status="NEEDS_HUMAN_REVIEW", max_ltv=None)
    assert all(x.status == "UNKNOWN" for x in v.values())


def test_every_product_carries_a_source_citation_key():
    for p in PRODUCTS:
        assert p["cite"].startswith("_P_"), f"{p['id']}: 근거 인용 키가 없다"


def test_citation_anchors_exist_verbatim_in_the_source():
    """화면이 쓰는 근거 조문 3건이 원문에 그대로 있는가 — 인용을 지어내지 않는다."""
    from regimpact.extractor.sources import load_corpus
    from regimpact.ui.signal import _corpus_cut
    norm = {k: re.sub(r"\s+", " ", v).strip() for k, v in load_corpus().items()}
    for anchor in ("규제지역에서도 금융권 생애최초 주담대",
                   "디딤돌 대출 (좌동) 최대한도 일반차주2.0억원",
                   "보금자리론 아파트70% / 非아파트65%"):
        cut = _corpus_cut(norm, "FAQ_20260630", anchor, 80)
        assert cut["quote"] in norm["FAQ_20260630"]


def test_reasons_are_written_for_customers_not_engineers():
    v = _v(first_home_buyer=True)
    for x in v.values():
        assert x.reason and not re.search(r"[A-Z_]{4,}", x.reason), f"내부 코드 노출: {x.reason}"
