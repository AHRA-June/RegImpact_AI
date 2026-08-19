"""Policy Version DB + Temporal Policy Resolver (docs/00_BRIEF.md §7·§19).

    "이번 정책이 시행되는 시점에, 직전까지 유효했던 정책과 무엇이 달라졌는가?"

정책은 문서가 아니라 **시행일 구간을 갖는 버전**이고, 서로 supersede 관계로 이어진다.
저장소는 DB 서버가 아니라 git 안의 JSON(`docs/policies/*.json`) — 정책 버전은 감사 대상이고
git 이력이 곧 "누가 언제 무엇을 확정했는가"의 기록이 된다.

업로드된 정책은 항상 DRAFT 로 태어나고, `confirm()` 을 거쳐야 판정에 쓰인다(LOCKED §4).
확정 전에도 `preview_region_impact()` 로 "적용하면 어떻게 되는지"만 미리 볼 수 있다 —
전역 상태를 바꾸지 않는 순수 함수라서 되돌릴 것이 없다.
"""
from .consistency import BaselineDrift, check_registry_matches_baseline
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
    "PolicyVersion", "PolicyStatus", "Provenance", "RegionDelta", "RuleNote", "SourceDocument",
    "PolicyRegistry", "load_registry", "registry_from", "POLICY_DIR",
    "active_at", "current_policy", "upcoming", "previous_policy", "timeline",
    "resolve_region_with_policies", "preview_region_impact", "detect_overlaps",
    "RegionChange", "OverlapWarning", "TimelineEntry",
    "draft_policy", "confirm", "snapshot_document", "sha256_hex", "DraftResult",
    "check_registry_matches_baseline", "BaselineDrift",
]
