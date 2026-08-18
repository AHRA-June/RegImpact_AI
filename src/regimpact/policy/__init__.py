"""Policy Version DB + Temporal Policy Resolver (docs/00_BRIEF.md §7, §19).

    load_registry()                -> PolicyRegistry          (docs/policies/*.json)
    timeline(reg, as_of)           -> 날짜 축 타임라인 (지난/현재/예정/초안)
    current_policy / upcoming      -> '현재 정책' / '다음 정책'
    previous_policy(reg, p)        -> 시행일 직전까지 유효했던 정책
    resolve_region_with_policies() -> 기준선 + 정책 오버레이로 시점 규제상태 해석
    snapshot_document / draft_policy / confirm -> 업로드 → 초안 → 사람 확정
"""
from .ingest import DraftResult, confirm, draft_policy, sha256_hex, snapshot_document
from .registry import POLICY_DIR, PolicyRegistry, load_registry, registry_from
from .resolver import (
    OverlapWarning,
    RegionChange,
    TimelineEntry,
    active_at,
    current_policy,
    detect_overlaps,
    preview_region_impact,
    previous_policy,
    resolve_region_with_policies,
    timeline,
    upcoming,
)
from .version import (
    PolicyStatus,
    PolicyVersion,
    Provenance,
    RegionDelta,
    RuleNote,
    SourceDocument,
)

__all__ = [
    "PolicyVersion", "PolicyStatus", "Provenance", "SourceDocument", "RegionDelta", "RuleNote",
    "PolicyRegistry", "load_registry", "registry_from", "POLICY_DIR",
    "timeline", "TimelineEntry", "active_at", "current_policy", "upcoming", "previous_policy",
    "resolve_region_with_policies", "preview_region_impact", "RegionChange",
    "detect_overlaps", "OverlapWarning",
    "snapshot_document", "draft_policy", "confirm", "DraftResult", "sha256_hex",
]
