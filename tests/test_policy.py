"""Policy Version DB + Temporal Policy Resolver (브리프 §7).

정책은 문서가 아니라 시행일 구간을 갖는 버전이다. 여기 테스트는 (a) 시점 해석이
실제로 시간축을 쓰는지, (b) 확정 전 정책이 판정에 새어 들어가지 않는지,
(c) 기준선과 정책 DB가 갈라지면 잡히는지를 고정한다.
"""
from datetime import date

import pytest

from regimpact.models import RegionStatus, RegulatedType
from regimpact.policy import (
    PolicyRegistry,
    PolicyStatus,
    PolicyVersion,
    Provenance,
    RegionDelta,
    SourceDocument,
    check_registry_matches_baseline,
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
from regimpact.regions import resolve_region_status

NOW = date(2026, 8, 19)


@pytest.fixture(scope="module")
def registry():
    return load_registry()


def _delta(code, status=RegionStatus.REGULATED, when=date(2027, 2, 1)):
    return RegionDelta(
        region_code=code, region_name=code, region_status=status,
        effective_from=when, regulated_type=RegulatedType.SPECULATIVE_OVERHEATED,
    )


def _policy(pid="TEST_2027", *, status=PolicyStatus.DRAFT, deltas=None,
            effective_from=date(2027, 2, 1), supersedes=None):
    return PolicyVersion(
        policy_id=pid, title="테스트 정책", issuer="테스트",
        published_at=date(2027, 1, 15), effective_from=effective_from,
        supersedes_policy_id=supersedes, status=status,
        region_deltas=deltas if deltas is not None else [_delta("ANSAN_SANGNOK")],
    )


# ---------- 시드된 레지스트리 ----------
def test_seeded_registry_has_the_four_designation_policies(registry):
    assert {p.policy_id for p in registry.policies} == {
        "MOLIT_20161103", "MOLIT_20170803", "MOLIT_20251016", "FSC_20260630",
    }
    assert len(registry.confirmed()) == 4


def test_registry_agrees_with_engine_baseline(registry):
    """같은 사실이 두 곳에 산다 — 갈라지면 여기서 잡힌다."""
    drift = check_registry_matches_baseline(registry)
    assert drift.ok, [d.detail for d in drift.all]


def test_supersedes_chain_is_complete(registry):
    chain, cur = [], registry.get("FSC_20260630")
    while cur is not None:
        chain.append(cur.policy_id)
        cur = previous_policy(registry, cur)
    assert chain == ["FSC_20260630", "MOLIT_20251016", "MOLIT_20170803", "MOLIT_20161103"]


# ---------- 시점 해석 ----------
@pytest.mark.parametrize("as_of,expected", [
    (date(2017, 1, 1), "MOLIT_20161103"),
    (date(2020, 1, 1), "MOLIT_20170803"),
    (date(2026, 6, 30), "MOLIT_20251016"),   # 6·30 시행 전날
    (date(2026, 7, 1), "FSC_20260630"),      # 시행일
])
def test_current_policy_moves_with_time(registry, as_of, expected):
    assert current_policy(registry, as_of).policy_id == expected


def test_no_policy_before_the_first_one(registry):
    assert current_policy(registry, date(2000, 1, 1)) is None


def test_timeline_marks_states(registry):
    states = {e.policy.policy_id: e.state for e in timeline(registry, NOW)}
    assert states["FSC_20260630"] == "현재 유효"
    assert states["MOLIT_20161103"] == "지난 정책"


def test_is_pending_at_needs_a_time_reference():
    """이전 판은 status만 보고 '시행 예정'이라 했다 — 시행 중인 정책까지 전부 예정이 됐다."""
    p = _policy(status=PolicyStatus.CONFIRMED, effective_from=date(2027, 2, 1))
    assert p.is_pending_at(date(2027, 1, 1)) is True
    assert p.is_pending_at(date(2027, 2, 1)) is False
    assert p.is_pending_at(date(2027, 3, 1)) is False


def test_upcoming_lists_confirmed_but_not_yet_effective(registry):
    future = confirm(_policy(status=PolicyStatus.DRAFT))
    assert [p.policy_id for p in upcoming(registry.add(future), NOW)] == ["TEST_2027"]


# ---------- 확정 전에는 판정에 안 쓰인다 (LOCKED §4) ----------
def test_draft_policy_does_not_change_region_status():
    draft = _policy(status=PolicyStatus.DRAFT)
    status, _ = resolve_region_with_policies("ANSAN_SANGNOK", date(2027, 3, 1), [draft])
    assert status is RegionStatus.UNKNOWN, "확정 전 정책이 규제상태를 만들면 안 된다"


def test_confirmed_policy_overlays_new_region():
    approved = confirm(_policy(status=PolicyStatus.DRAFT))
    status, rtype = resolve_region_with_policies("ANSAN_SANGNOK", date(2027, 3, 1), [approved])
    assert status is RegionStatus.REGULATED
    assert rtype is RegulatedType.SPECULATIVE_OVERHEATED


def test_overlay_does_not_mutate_the_baseline():
    approved = confirm(_policy(status=PolicyStatus.DRAFT))
    resolve_region_with_policies("ANSAN_SANGNOK", date(2027, 3, 1), [approved])
    assert resolve_region_status("ANSAN_SANGNOK", date(2027, 3, 1))[0] is RegionStatus.UNKNOWN


def test_overlay_before_effective_date_falls_back_to_baseline():
    approved = confirm(_policy(status=PolicyStatus.DRAFT))
    status, _ = resolve_region_with_policies("ANSAN_SANGNOK", date(2027, 1, 1), [approved])
    assert status is RegionStatus.UNKNOWN


def test_confirm_refuses_empty_policy():
    with pytest.raises(ValueError):
        confirm(_policy(deltas=[]))


def test_confirm_marks_provenance_only_after_confirming():
    draft = _policy()
    assert draft.provenance is Provenance.AI_DRAFT
    assert confirm(draft).provenance is Provenance.HUMAN_CONFIRMED
    assert confirm(draft).status is PolicyStatus.CONFIRMED


# ---------- 미리보기 ----------
def test_preview_shows_the_transition_not_the_end_state(registry):
    """before 는 시행 **전날** 상태여야 한다.

    이전 판은 before/after 를 같은 시점으로 조회해서(복붙 실수) 미리보기가
    'REGULATED → REGULATED' 로 보이고 변화가 사라졌다.
    """
    changes = preview_region_impact(registry.get("FSC_20260630"))
    guri = next(c for c in changes if c.region_code == "GURI")
    assert guri.before is RegionStatus.NON_REGULATED
    assert guri.after is RegionStatus.REGULATED


def test_preview_flags_regions_already_in_baseline(registry):
    """이미 반영된 정책을 다시 등록하면 알려준다."""
    changes = preview_region_impact(registry.get("FSC_20260630"))
    assert all(c.already_in_baseline for c in changes), \
        "시드된 정책은 기준선에서 나왔으므로 전부 이미 반영 상태다"


def test_preview_of_new_region_is_not_already_in_baseline():
    changes = preview_region_impact(_policy())
    assert not changes[0].already_in_baseline


# ---------- 중복·우선순위 ----------
def test_overlap_detected_when_new_policy_touches_designated_region(registry):
    overlapping = _policy(deltas=[_delta("GURI")])
    warns = detect_overlaps(registry, overlapping)
    assert any(w.region_code == "GURI" and w.existing_policy_id == "FSC_20260630"
               for w in warns)


def test_no_overlap_for_untouched_region(registry):
    assert detect_overlaps(registry, _policy()) == []


# ---------- 업로드 초안 ----------
def test_draft_is_never_confirmed_on_creation():
    src = snapshot_document(source_document_id="D1", title="t", content=b"x")
    result = draft_policy(policy_id="P1", title="t", issuer="i",
                          published_at=date(2027, 1, 1), effective_from=date(2027, 2, 1),
                          sources=[src], manual_region_codes=["구리시"])
    assert result.policy.status is PolicyStatus.DRAFT


def test_unmappable_region_name_is_reported_not_guessed():
    src = snapshot_document(source_document_id="D1", title="t", content=b"x")
    result = draft_policy(policy_id="P1", title="t", issuer="i",
                          published_at=date(2027, 1, 1), effective_from=date(2027, 2, 1),
                          sources=[src], manual_region_codes=["구리시", "존재하지않는시"])
    assert result.unmapped_regions == ["존재하지않는시"]
    assert [d.region_code for d in result.policy.region_deltas] == ["GURI"]
    assert any("넘겨짚지 않고" in w for w in result.warnings)


def test_snapshot_records_source_hash():
    doc = snapshot_document(source_document_id="D1", title="t", content=b"hello")
    assert len(doc.source_hash) == 64
    assert doc.byte_size == 5


# ---------- 드리프트 탐지가 실제로 작동하는가 ----------
def test_drift_detected_when_registry_claims_something_baseline_denies(registry):
    bogus = PolicyVersion(
        policy_id="MOLIT_20161103", title="변조", issuer="x",
        published_at=date(2016, 11, 3), effective_from=date(2016, 11, 3),
        status=PolicyStatus.CONFIRMED,
        region_deltas=[_delta("SEOUL_GANGNAM", RegionStatus.NON_REGULATED,
                              date(2026, 8, 1))],
    )
    drift = check_registry_matches_baseline(registry.replace(bogus))
    assert not drift.ok
    assert any(d.region_code == "SEOUL_GANGNAM" for d in drift.status_mismatch)


def test_drift_detected_when_policy_is_missing_from_registry(registry):
    without = PolicyRegistry([p for p in registry.policies
                              if p.policy_id != "FSC_20260630"])
    drift = check_registry_matches_baseline(without)
    assert not drift.ok
    assert any(d.policy_id == "FSC_20260630" for d in drift.missing_in_registry)


def test_drift_detected_when_policy_is_only_a_draft(registry):
    demoted = PolicyVersion(**{**registry.get("FSC_20260630").__dict__,
                               "status": PolicyStatus.DRAFT})
    drift = check_registry_matches_baseline(registry.replace(demoted))
    assert not drift.ok


# ---------- 저장/로드 ----------
def test_json_roundtrip_preserves_everything(registry, tmp_path):
    registry.save(tmp_path)
    reloaded = load_registry(tmp_path)
    assert {p.policy_id for p in reloaded.policies} == {p.policy_id for p in registry.policies}
    assert reloaded.get("MOLIT_20251016").region_deltas == \
        registry.get("MOLIT_20251016").region_deltas


def test_duplicate_policy_version_is_rejected():
    with pytest.raises(ValueError, match="중복"):
        PolicyRegistry([_policy("SAME"), _policy("SAME")])


def test_drift_detects_regulated_type_change_not_just_status(registry):
    """투기과열지구 ↔ 조정대상지역은 status 가 같아도 DTI 가 다르다(40% vs 50%).

    status 만 비교하던 판에서는 이 변이가 통과했다 — 변이 테스트로 잡힌 구멍이다.
    """
    from regimpact.models import RegulatedType
    p = registry.get("FSC_20260630")
    swapped = PolicyVersion(**{
        **p.__dict__,
        "region_deltas": [
            RegionDelta(
                region_code=d.region_code, region_name=d.region_name,
                region_status=d.region_status, effective_from=d.effective_from,
                effective_to=d.effective_to, regulated_type=RegulatedType.ADJUSTMENT,
            ) for d in p.region_deltas
        ],
    })
    drift = check_registry_matches_baseline(registry.replace(swapped))
    assert not drift.ok
    assert all("규제유형" in d.detail for d in drift.status_mismatch)
