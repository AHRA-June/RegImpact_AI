"""Policy Version DB 시드 — 지금까지 확정된 지정 이력을 정책 버전으로 등록한다.

출처: `docs/sources/raw/molit_press_20260630.txt` 참고2 「투기과열지구 및 조정대상지역 현황」 표.
그 표가 각 지역의 **지정 시점**을 함께 싣고 있으므로, 지역 레지스트리(기준선)와 같은 원문에서
정책 버전 4건을 유도할 수 있다.

지역 목록은 `regions.REGISTRY`(같은 원문에서 만든 기준선)에서 읽는다. 44개 지역을 손으로 다시
옮겨 적으면 그 전사가 새 오류가 되기 때문이다 — 대신 **두 구조가 원문이 밝힌 지역 수(서울 25 /
경기 12 / 경기 3 / 강남4구 4)와 각각 일치하는지**를 `tests/test_policy.py` 가 검사한다.

실행: python tools/seed_policies.py     (한 번만 — 이후는 git 이력이 진실)
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from regimpact.models import RegionStatus, RegulatedType          # noqa: E402
from regimpact.policy import PolicyRegistry, PolicyVersion         # noqa: E402
from regimpact.policy.version import PolicyStatus, Provenance, RegionDelta, RuleNote, SourceDocument  # noqa: E402
from regimpact.regions import REGISTRY                             # noqa: E402

SRC_MOLIT = SourceDocument(
    source_document_id="MOLIT_PRESS_20260630",
    title="투기과열지구 및 조정대상지역 추가 지정 (참고2 현황표 포함)",
    source_hash="",           # 아래에서 실제 원문 해시로 채운다
    retrieved_at=date(2026, 6, 30),
    filename="molit_press_20260630.txt",
)
SRC_FSC = SourceDocument(
    source_document_id="FSC_PRESS_20260630",
    title="주택시장 안정대책 — 가계대출 규제 강화",
    source_hash="",
    retrieved_at=date(2026, 6, 30),
    filename="fsc_press_20260630.txt",
)


def _hashed(doc: SourceDocument) -> SourceDocument:
    import hashlib
    raw = (ROOT / "docs" / "sources" / "raw" / doc.filename).read_bytes()
    return SourceDocument(**{**doc.__dict__, "source_hash": hashlib.sha256(raw).hexdigest(),
                             "byte_size": len(raw)})


def _deltas(effective: date, rtype: RegulatedType) -> list[RegionDelta]:
    """기준선에서 '이 날짜에 규제로 전환된 지역'을 뽑아 delta 로 만든다."""
    out: list[RegionDelta] = []
    for code, region in sorted(REGISTRY.items()):
        for v in region.versions:
            if (v.status is RegionStatus.REGULATED
                    and v.effective_from == effective
                    and v.regulated_type is rtype):
                out.append(RegionDelta(
                    region_code=code, region_name=region.label,
                    region_status=RegionStatus.REGULATED,
                    effective_from=effective, regulated_type=rtype,
                ))
    return out


def build() -> PolicyRegistry:
    molit, fsc = _hashed(SRC_MOLIT), _hashed(SRC_FSC)

    p1 = PolicyVersion(
        policy_id="MOLIT_20161103",
        title="강남·서초·송파·용산 조정대상지역 지정",
        issuer="국토교통부", published_at=date(2016, 11, 3), effective_from=date(2016, 11, 3),
        status=PolicyStatus.CONFIRMED, provenance=Provenance.HUMAN_CONFIRMED,
        sources=[molit],
        region_deltas=_deltas(date(2016, 11, 3), RegulatedType.ADJUSTMENT),
        notes="MOLIT 참고2 현황표의 '(’16.11.3)' 표기 근거.",
    )
    p2 = PolicyVersion(
        policy_id="MOLIT_20170803",
        title="강남·서초·송파·용산 투기과열지구 지정",
        issuer="국토교통부", published_at=date(2017, 8, 3), effective_from=date(2017, 8, 3),
        supersedes_policy_id="MOLIT_20161103",
        status=PolicyStatus.CONFIRMED, provenance=Provenance.HUMAN_CONFIRMED,
        sources=[molit],
        region_deltas=_deltas(date(2017, 8, 3), RegulatedType.SPECULATIVE_OVERHEATED),
        notes="MOLIT 참고2 현황표의 '(’17.8.3)' 표기 근거. 조정대상 → 투기과열로 강화.",
    )
    p3 = PolicyVersion(
        policy_id="MOLIT_20251016",
        title="서울 21개 자치구·경기 12곳 투기과열지구 및 조정대상지역 지정",
        issuer="국토교통부", published_at=date(2025, 10, 16), effective_from=date(2025, 10, 16),
        supersedes_policy_id="MOLIT_20170803",
        status=PolicyStatus.CONFIRMED, provenance=Provenance.HUMAN_CONFIRMED,
        sources=[molit],
        region_deltas=_deltas(date(2025, 10, 16), RegulatedType.SPECULATIVE_OVERHEATED),
        notes="MOLIT 참고2 현황표의 '(‘25.10.16)' 표기 근거. 이 지정으로 서울 25개 자치구 전체가 규제지역이 됐다.",
    )
    p4 = PolicyVersion(
        policy_id="FSC_20260630",
        title="6·30 주택시장 안정대책 — 화성동탄·용인기흥·구리 규제지역 지정 및 주담대 LTV 강화",
        issuer="금융위원회·국토교통부",
        published_at=date(2026, 6, 30), effective_from=date(2026, 7, 1),
        supersedes_policy_id="MOLIT_20251016",
        status=PolicyStatus.CONFIRMED, provenance=Provenance.HUMAN_CONFIRMED,
        sources=[fsc, molit],
        region_deltas=_deltas(date(2026, 7, 1), RegulatedType.SPECULATIVE_OVERHEATED),
        rule_notes=[
            RuleNote("LTV_규제지역_무주택", "70%", "40%", "MOLIT 참고1 / FAQ Q2"),
            RuleNote("LTV_규제지역_생애최초", "70%", "70% (좌동)", "FAQ Q2"),
            RuleNote("LTV_규제지역_서민실수요", "70%", "60%", "FAQ Q2"),
            RuleNote("LTV_규제지역_유주택", "—", "0%", "MOLIT 참고1"),
            RuleNote("경과규정_컷오프", "—", "2026-06-30 (G1 접수 / G2 계약+계약금 / G3 토허제 신청)",
                     "FSC 보도자료"),
        ],
        notes="대출규제 7.1 시행, 토지거래허가구역은 7.5 효력(C03). 지역 지정 효력은 7.1.",
    )
    return PolicyRegistry(policies=[p1, p2, p3, p4])


if __name__ == "__main__":
    reg = build()
    written = reg.save()
    for p in reg.sorted_by_effective():
        print(f"{p.effective_from}  {p.policy_id:16s} {len(p.region_deltas):>2}개 지역  {p.title[:40]}")
    print(f"\nwrote {len(written)} files → docs/policies/")
