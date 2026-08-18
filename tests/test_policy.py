"""Policy Version DB + Temporal Policy Resolver 테스트 (브리프 §7·§19).

여기서 지키려는 계약:
    ① 정책 버전의 지역 delta 는 **원문이 밝힌 지역 수**와 맞아야 한다(서울 25 / 경기 12 / 경기 3).
       정책 레지스트리와 지역 기준선은 같은 원문에서 나온 두 구조이므로, 서로 어긋나면 드리프트다.
    ② **DRAFT 는 어떤 판정에도 쓰이지 않는다** (LOCKED §4 — AI 초안이 사람 확정 없이 규제상태를 바꾸지 않는다).
    ③ 업로드 파이프라인은 매핑 못 한 지역을 **조용히 버리지 않는다**. 넘겨짚는 순간 근거 없는 규제상태가 생긴다.
    ④ 정책 오버레이는 기준선을 바꾸지 않는다 — delta 가 없으면 결과가 완전히 동일해야 한다.
"""
from __future__ import annotations

from datetime import date

import pytest

from regimpact.models import RegionStatus, RegulatedType
from regimpact.policy import (
    PolicyRegistry,
    PolicyStatus,
    PolicyVersion,
    Provenance,
    RegionDelta,
    confirm,
    current_policy,
    detect_overlaps,
    draft_policy,
    load_registry,
    preview_region_impact,
    previous_policy,
    resolve_region_with_policies,
    snapshot_document,
    timeline,
    upcoming,
)
from regimpact.regions import REGISTRY, regulated_codes, resolve_region_status

AFTER = date(2026, 7, 2)


@pytest.fixture(scope="module")
def registry() -> PolicyRegistry:
    return load_registry()


# ---------- ① 원문 지역 수와 대조 ----------
def test_seeded_policies_exist(registry):
    ids = {p.policy_id for p in registry.policies}
    assert ids == {"MOLIT_20161103", "MOLIT_20170803", "MOLIT_20251016", "FSC_20260630"}


def test_policy_delta_counts_match_the_official_table(registry):
    """MOLIT 참고2: 강남4구 4곳 / '25.10.16 지정분 33곳(서울21+경기12) / 6·30 신규 3곳."""
    assert len(registry.get("MOLIT_20161103").region_deltas) == 4
    assert len(registry.get("MOLIT_20170803").region_deltas) == 4
    assert len(registry.get("MOLIT_20251016").region_deltas) == 33
    assert len(registry.get("FSC_20260630").region_deltas) == 3


def test_2025_designation_splits_21_seoul_and_12_gyeonggi(registry):
    deltas = registry.get("MOLIT_20251016").region_deltas
    seoul = [d for d in deltas if REGISTRY[d.region_code].sido == "서울특별시"]
    gyeonggi = [d for d in deltas if REGISTRY[d.region_code].sido == "경기도"]
    assert len(seoul) == 21 and len(gyeonggi) == 12


def test_policy_deltas_reproduce_the_baseline_regulated_set(registry):
    """정책 delta 를 전부 합치면 기준선(regions.REGISTRY)의 규제지역 집합과 같아야 한다.

    두 구조가 같은 원문에서 나왔으므로, 한쪽만 고치면 여기서 드러난다.
    """
    from_policies = {d.region_code for p in registry.confirmed() for d in p.region_deltas}
    assert from_policies == set(regulated_codes(AFTER))


def test_six_thirty_policy_effective_date_is_july_first(registry):
    p = registry.get("FSC_20260630")
    assert p.published_at == date(2026, 6, 30)
    assert p.effective_from == date(2026, 7, 1)      # 공고 6.30, 효력 7.1
    assert all(d.effective_from == date(2026, 7, 1) for d in p.region_deltas)


def test_every_policy_carries_hashed_sources(registry):
    for p in registry.policies:
        assert p.sources, p.policy_id
        for s in p.sources:
            assert len(s.source_hash) == 64, f"{p.policy_id}/{s.source_document_id}"


# ---------- 타임라인 · 직전 정책 ----------
def test_current_policy_changes_with_the_date(registry):
    assert current_policy(registry, date(2016, 11, 2)) is None
    assert current_policy(registry, date(2016, 11, 3)).policy_id == "MOLIT_20161103"
    assert current_policy(registry, date(2026, 6, 30)).policy_id == "MOLIT_20251016"
    assert current_policy(registry, date(2026, 7, 1)).policy_id == "FSC_20260630"


def test_upcoming_lists_confirmed_but_not_yet_effective(registry):
    """'다음 정책' — 6.30 시점에서 보면 6·30 대책이 아직 시행 전이다."""
    nxt = upcoming(registry, date(2026, 6, 30))
    assert [p.policy_id for p in nxt] == ["FSC_20260630"]
    assert upcoming(registry, AFTER) == []


def test_previous_policy_follows_supersedes_chain(registry):
    p = registry.get("FSC_20260630")
    assert previous_policy(registry, p).policy_id == "MOLIT_20251016"


def test_previous_policy_falls_back_to_effective_date(registry):
    """supersedes 가 비어 있어도 시행일로 직전 정책을 찾아야 한다 (§7)."""
    p = registry.get("MOLIT_20161103")
    assert previous_policy(registry, p) is None      # 가장 오래된 정책


def test_timeline_labels_past_current_and_upcoming(registry):
    states = {e.policy.policy_id: e.state for e in timeline(registry, date(2026, 6, 30))}
    assert states["MOLIT_20161103"] == "지난 정책"
    assert states["MOLIT_20251016"] == "현재 유효"
    assert states["FSC_20260630"] == "시행 예정"


# ---------- ② DRAFT 는 판정에 쓰이지 않는다 ----------
def _draft_policy_for(code: str, effective: date) -> PolicyVersion:
    return PolicyVersion(
        policy_id="TEST_NEW", title="테스트 신규 지정", issuer="테스트",
        published_at=effective, effective_from=effective,
        status=PolicyStatus.DRAFT, provenance=Provenance.AI_DRAFT,
        region_deltas=[RegionDelta(
            region_code=code, region_name=REGISTRY[code].label,
            region_status=RegionStatus.REGULATED, effective_from=effective,
            regulated_type=RegulatedType.SPECULATIVE_OVERHEATED)],
    )


def test_draft_policy_does_not_change_region_status():
    """LOCKED §4 — AI 초안이 사람 확정 없이 규제상태를 바꾸지 않는다."""
    draft = _draft_policy_for("ULSAN_NAM", date(2026, 8, 1))
    status, _ = resolve_region_with_policies("ULSAN_NAM", date(2026, 8, 2), [draft])
    assert status is RegionStatus.NON_REGULATED
    assert not draft.is_active_at(date(2026, 8, 2))


def test_confirmed_policy_does_change_region_status():
    confirmed = confirm(_draft_policy_for("ULSAN_NAM", date(2026, 8, 1)), notes="테스트 확정")
    assert confirmed.status is PolicyStatus.CONFIRMED
    assert confirmed.provenance is Provenance.HUMAN_CONFIRMED

    before, _ = resolve_region_with_policies("ULSAN_NAM", date(2026, 7, 31), [confirmed])
    after, rtype = resolve_region_with_policies("ULSAN_NAM", date(2026, 8, 2), [confirmed])
    assert before is RegionStatus.NON_REGULATED
    assert after is RegionStatus.REGULATED
    assert rtype is RegulatedType.SPECULATIVE_OVERHEATED


def test_confirm_rejects_empty_policy():
    empty = PolicyVersion(policy_id="EMPTY", title="빈 정책", issuer="x",
                          published_at=date(2026, 8, 1), effective_from=date(2026, 8, 1))
    with pytest.raises(ValueError, match="빈 정책"):
        confirm(empty)


# ---------- ④ 오버레이는 기준선을 바꾸지 않는다 ----------
@pytest.mark.parametrize("code", ["SEOUL_GANGNAM", "GYEONGGI_GURI", "ULSAN_NAM", "JEJU_JEJU"])
@pytest.mark.parametrize("as_of", [date(2025, 10, 15), date(2026, 6, 30), date(2026, 7, 1)])
def test_overlay_without_policies_equals_baseline(code, as_of):
    assert resolve_region_with_policies(code, as_of, []) == resolve_region_status(code, as_of)


def test_overlay_touches_only_the_named_region():
    confirmed = confirm(_draft_policy_for("ULSAN_NAM", date(2026, 8, 1)))
    for other in ("JEJU_JEJU", "SEOUL_GANGNAM", "GYEONGGI_GURI"):
        assert (resolve_region_with_policies(other, date(2026, 8, 2), [confirmed])
                == resolve_region_status(other, date(2026, 8, 2)))


# ---------- ③ 업로드 파이프라인 ----------
def test_snapshot_records_sha256_and_size():
    doc = snapshot_document(source_document_id="X", title="테스트", content=b"hello")
    assert doc.source_hash == (
        "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824")
    assert doc.byte_size == 5


def test_draft_is_always_draft_status():
    doc = snapshot_document(source_document_id="X", title="테스트", content=b"x")
    result = draft_policy(policy_id="P", title="t", issuer="i",
                          published_at=date(2026, 8, 1), effective_from=date(2026, 8, 2),
                          sources=[doc])
    assert result.policy.status is PolicyStatus.DRAFT
    assert result.warnings


def test_unmapped_region_names_are_reported_not_dropped():
    """넘겨짚어 채우면 근거 없는 규제상태가 만들어진다 — 못 매핑한 건 그대로 보고한다."""
    from regimpact.extractor.schema import RegChangeExtraction

    extraction = RegChangeExtraction(
        policy_id="P", target_regions=["GURI", "존재하지않는시", "울산광역시 남구"],
        effective_from="2026-08-02", changes=[])
    doc = snapshot_document(source_document_id="X", title="테스트", content=b"x")
    result = draft_policy(policy_id="P", title="t", issuer="i",
                          published_at=date(2026, 8, 1), effective_from=date(2026, 8, 2),
                          sources=[doc], extraction=extraction)

    codes = {d.region_code for d in result.policy.region_deltas}
    assert codes == {"GYEONGGI_GURI", "ULSAN_NAM"}     # 구 코드 별칭·지역명 모두 매핑
    assert result.unmapped_regions == ["존재하지않는시"]
    assert any("넘겨짚지 않고" in w for w in result.warnings)


def test_draft_flags_effective_date_mismatch():
    from regimpact.extractor.schema import RegChangeExtraction

    extraction = RegChangeExtraction(policy_id="P", target_regions=[],
                                     effective_from="2026-09-09", changes=[])
    doc = snapshot_document(source_document_id="X", title="테스트", content=b"x")
    result = draft_policy(policy_id="P", title="t", issuer="i",
                          published_at=date(2026, 8, 1), effective_from=date(2026, 8, 2),
                          sources=[doc], extraction=extraction)
    assert any("시행일" in w and "원문 대조 필요" in w for w in result.warnings)


# ---------- 미리보기 · 중첩 경고 ----------
def test_preview_flags_already_baselined_regions(registry):
    """이미 기준선에 반영된 정책을 다시 등록하면 알려줘야 한다."""
    changes = preview_region_impact(registry.get("FSC_20260630"))
    assert len(changes) == 3
    assert all(c.already_in_baseline for c in changes)


def test_preview_shows_transition_for_a_new_region():
    confirmed = confirm(_draft_policy_for("ULSAN_NAM", date(2026, 8, 1)))
    change = preview_region_impact(confirmed)[0]
    assert change.before is RegionStatus.NON_REGULATED
    assert change.after is RegionStatus.REGULATED
    assert change.already_in_baseline is False


def test_detect_overlaps_marks_priority_review(registry):
    """§7 — 신규 정책과 기존 룰이 중첩될 때 우선순위 검토 대상으로 표시."""
    dup = confirm(_draft_policy_for("GYEONGGI_GURI", date(2026, 9, 1)))
    warns = detect_overlaps(registry, dup)
    assert warns and warns[0].region_code == "GYEONGGI_GURI"
    assert warns[0].existing_policy_id == "FSC_20260630"


def test_no_overlap_for_untouched_region(registry):
    fresh = confirm(_draft_policy_for("JEJU_SEOGWIPO", date(2026, 9, 1)))
    assert detect_overlaps(registry, fresh) == []
