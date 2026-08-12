"""Rule Change Proposal 테스트 — 추출 → 룰 변경안(초안) → 사람 확정 룰 대조.

검증 축:
  1. 매핑 — 각 카테고리가 올바른 룰엔진 필드로 매핑되고 현재값과 대조된다.
  2. disposition — 일치=CONSISTENT, 불일치=DIVERGENT, 전세/신용/정책모기지=OUT_OF_SCOPE, 불명=NEEDS_REVIEW.
  3. 초안 규율 — approval_status는 항상 PENDING(자동 확정 없음, LOCKED §4).
  4. provenance — 모든 delta가 인용(citation)을 보존.
  5. 통합 — 저장된 6·30 추출로 반영/코어밖/검토 분포 확인.
"""
import json
from pathlib import Path

from regimpact.rule_proposal import Disposition, build_proposal

REPO = Path(__file__).resolve().parents[1]
SAVED = json.loads((REPO / "docs" / "eval" / "extractor_run_6_30_gemini.json").read_text(encoding="utf-8"))


class _Cite:
    def __init__(self, doc="D", quote="근거 인용"):
        self.source_doc_id = doc
        self.quote = quote


class _Item:
    def __init__(self, category, summary, before=None, after=None, confidence=1.0):
        self.category = category
        self.summary = summary
        self.before = before
        self.after = after
        self.confidence = confidence
        self.citation = _Cite()


class _Ext:
    def __init__(self, changes, policy_id="P", effective_from="2026-07-01", target_regions=None):
        self.policy_id = policy_id
        self.effective_from = effective_from
        self.target_regions = target_regions or []
        self.changes = changes


def _one(item, **kw):
    return build_proposal(_Ext([item], **kw)).deltas[0]


# ---------- 매핑 · disposition ----------
def test_ltv_standard_consistent():
    d = _one(_Item("LTV", "규제지역 표준 LTV", "70%", "40%"))
    assert d.target_field == "LTV_REGULATED_STANDARD"
    assert d.engine_current == "40%"
    assert d.disposition == Disposition.MAPPED_CONSISTENT


def test_ltv_divergent_when_value_differs():
    d = _one(_Item("LTV", "표준 LTV", "70%", "50%"))   # 엔진은 40%
    assert d.disposition == Disposition.MAPPED_DIVERGENT
    assert "50%" in d.note


def test_multi_home_ltv_maps_to_zero():
    d = _one(_Item("LTV", "수도권 다주택자 0%", None, "0%"))
    assert d.target_field == "LTV_MULTI"
    assert d.disposition == Disposition.MAPPED_CONSISTENT


def test_first_home_exception_consistent():
    d = _one(_Item("EXCEPTION", "생애최초 완화 LTV", "70%", "60~70%"))
    assert d.target_field == "LTV_FIRST_HOME"
    assert d.disposition == Disposition.MAPPED_CONSISTENT   # 70%가 범위에 포함


def test_real_demand_exception_consistent():
    d = _one(_Item("EXCEPTION", "서민·실수요자 완화 LTV", None, "60%(아파트 限)"))
    assert d.target_field == "LTV_REAL_DEMAND"
    assert d.disposition == Disposition.MAPPED_CONSISTENT


def test_policy_mortgage_exception_out_of_scope():
    d = _one(_Item("EXCEPTION", "정책모기지(보금자리론) 완화", None, "아파트60%"))
    assert d.disposition == Disposition.OUT_OF_SCOPE
    assert d.target_field is None


def test_scope_limit_out_of_scope():
    d = _one(_Item("SCOPE_LIMIT", "전세대출 보유 차주 제한", None, "전세대출 제한"))
    assert d.disposition == Disposition.OUT_OF_SCOPE


def test_effective_date_consistent():
    d = _one(_Item("EFFECTIVE_DATE", "시행일", None, "2026-07-01"))
    assert d.target_field == "REG_EFFECTIVE"
    assert d.disposition == Disposition.MAPPED_CONSISTENT


def test_region_consistent_after_normalization():
    d = _one(_Item("REGION", "규제지역 신규 지정", "비규제지역", "투기과열지구"),
             target_regions=["화성시 동탄구", "용인시 기흥구", "구리시"])
    assert d.target_field == "REGION_VERSIONS"
    assert d.disposition == Disposition.MAPPED_CONSISTENT


def test_grandfathering_cutoff_consistent():
    d = _one(_Item("GRANDFATHERING", "6.30까지 접수/계약 종전규정", None, "종전 규정 적용"))
    assert d.target_field == "GRANDFATHERING_CUTOFF"
    assert d.disposition == Disposition.MAPPED_CONSISTENT


def test_ltv_needs_review_when_unparseable():
    d = _one(_Item("LTV", "표준 LTV", None, "해당 없음"))   # 퍼센트 없음
    assert d.disposition == Disposition.NEEDS_REVIEW


# ---------- 초안 규율 · provenance ----------
def test_approval_status_always_pending():
    from regimpact.extractor import RegChangeExtraction
    ext = RegChangeExtraction.from_dict(SAVED)
    assert build_proposal(ext).approval_status == "PENDING"


def test_every_delta_preserves_citation():
    from regimpact.extractor import RegChangeExtraction
    ext = RegChangeExtraction.from_dict(SAVED)
    for d in build_proposal(ext).deltas:
        assert d.citation_doc
        assert d.citation_quote


def test_counts_sum_to_deltas():
    from regimpact.extractor import RegChangeExtraction
    p = build_proposal(RegChangeExtraction.from_dict(SAVED))
    assert sum(p.counts().values()) == len(p.deltas)


# ---------- 통합(6·30 실제 추출) ----------
def test_six_thirty_proposal_distribution():
    from regimpact.extractor import RegChangeExtraction
    p = build_proposal(RegChangeExtraction.from_dict(SAVED))
    c = p.counts()
    # 추출이 사람 확정 엔진과 대부분 일치(반영), 나머지는 코어 밖(Discovery)
    assert c["MAPPED_CONSISTENT"] >= 6
    assert c["OUT_OF_SCOPE"] >= 3
    assert c["MAPPED_DIVERGENT"] == 0        # AI 추출이 확정 엔진과 충돌하지 않음
