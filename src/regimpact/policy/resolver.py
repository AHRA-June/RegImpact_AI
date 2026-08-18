"""Temporal Policy Resolver (docs/00_BRIEF.md §7).

    "이번 정책이 시행되는 시점에, 직전까지 유효했던 정책/Rule과 무엇이 달라졌는가?"

역할(§7 그대로):
    - 신규 정책의 시행일 기준으로 **직전 유효 정책** 탐색
    - 어떤 정책을 수정·대체·추가하는지 연결 (supersedes 체인)
    - effective_from/to 기준으로 **특정 시점의 정책 버전** 반환
    - 지역의 규제상태를 **시점별로** 해석
    - 신규 정책과 기존 룰이 **중첩될 때 우선순위 검토 대상으로 표시**

지역 해석은 `regions.REGISTRY`(지금까지 확정된 사실의 누적 기준선) 위에
**아직 기준선에 반영되지 않은 정책의 delta 를 오버레이**해 계산한다. 전역 상태를 바꾸지 않는
순수 함수이므로, 업로드한 정책을 "적용해보기"만 하고 되돌리는 것이 자유롭다.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable, Optional

from ..models import RegionStatus, RegulatedType
from ..regions import REGISTRY, canonical_code, resolve_region_status
from .registry import PolicyRegistry
from .version import PolicyStatus, PolicyVersion, RegionDelta


# ---------------------------------------------------------------------------
# 시점 해석
# ---------------------------------------------------------------------------
def active_at(registry: PolicyRegistry, as_of: date) -> list[PolicyVersion]:
    """그 시점에 유효한 정책들 (CONFIRMED 만)."""
    return sorted((p for p in registry.policies if p.is_active_at(as_of)),
                  key=lambda p: p.effective_from)


def current_policy(registry: PolicyRegistry, as_of: date) -> Optional[PolicyVersion]:
    """그 시점의 '현재 정책' — 유효한 것 중 시행일이 가장 늦은 것."""
    act = active_at(registry, as_of)
    return act[-1] if act else None


def upcoming(registry: PolicyRegistry, as_of: date) -> list[PolicyVersion]:
    """'다음 정책' — 확정됐지만 아직 시행 전."""
    return sorted((p for p in registry.confirmed() if p.effective_from > as_of),
                  key=lambda p: p.effective_from)


def previous_policy(registry: PolicyRegistry, policy: PolicyVersion) -> Optional[PolicyVersion]:
    """이 정책 시행일 **직전까지 유효했던** 정책 (§7 핵심 기능).

    supersedes_policy_id 가 명시돼 있으면 그것을 우선하고, 없으면 시행일로 추론한다.
    """
    if policy.supersedes_policy_id:
        found = registry.get(policy.supersedes_policy_id)
        if found:
            return found
    earlier = [p for p in registry.confirmed()
               if p.effective_from < policy.effective_from and p.policy_id != policy.policy_id]
    return max(earlier, key=lambda p: p.effective_from) if earlier else None


@dataclass(frozen=True)
class TimelineEntry:
    policy: PolicyVersion
    state: str          # "지난 정책" | "현재 유효" | "시행 예정" | "초안(미확정)"
    predecessor_id: Optional[str]


def timeline(registry: PolicyRegistry, as_of: date) -> list[TimelineEntry]:
    """날짜 축으로 정렬한 정책 타임라인."""
    cur = current_policy(registry, as_of)
    out: list[TimelineEntry] = []
    for p in registry.sorted_by_effective():
        if p.status is PolicyStatus.DRAFT:
            state = "초안(미확정)"
        elif cur is not None and p.policy_id == cur.policy_id:
            state = "현재 유효"
        elif p.effective_from > as_of:
            state = "시행 예정"
        else:
            state = "지난 정책"
        prev = previous_policy(registry, p)
        out.append(TimelineEntry(policy=p, state=state,
                                 predecessor_id=prev.policy_id if prev else None))
    return out


# ---------------------------------------------------------------------------
# 지역 상태 — 기준선 + 정책 오버레이
# ---------------------------------------------------------------------------
def _overlay_deltas(policies: Iterable[PolicyVersion]) -> dict[str, list[RegionDelta]]:
    """CONFIRMED 정책들의 지역 delta 를 코드별로 모은다(시행일 오름차순)."""
    out: dict[str, list[RegionDelta]] = {}
    for p in policies:
        if p.status is not PolicyStatus.CONFIRMED:
            continue
        for d in p.region_deltas:
            out.setdefault(canonical_code(d.region_code), []).append(d)
    for code in out:
        out[code].sort(key=lambda d: d.effective_from)
    return out


def resolve_region_with_policies(
    region_code: str,
    as_of: date,
    policies: Iterable[PolicyVersion] = (),
) -> tuple[RegionStatus, RegulatedType]:
    """기준선(regions.REGISTRY) 위에 정책 delta 를 얹어 시점 규제상태를 해석한다.

    delta 가 없으면 기준선 결과와 동일하다 — 즉 이 함수는 `resolve_region_status` 의 확장이며
    기존 판정을 바꾸지 않는다.
    """
    code = canonical_code(region_code)
    applicable = [d for d in _overlay_deltas(policies).get(code, [])
                  if as_of >= d.effective_from
                  and (d.effective_to is None or as_of <= d.effective_to)]
    if applicable:
        latest = applicable[-1]           # 같은 시점에 겹치면 나중 시행일이 이긴다
        return latest.region_status, latest.regulated_type
    return resolve_region_status(code, as_of)


@dataclass(frozen=True)
class RegionChange:
    region_code: str
    region_name: str
    before: RegionStatus
    after: RegionStatus
    effective_from: date
    already_in_baseline: bool     # 기준선이 이미 같은 결론이면 True (중복 등록 탐지)


def preview_region_impact(policy: PolicyVersion) -> list[RegionChange]:
    """이 정책을 적용하면 지역 상태가 어떻게 바뀌는지 미리 본다.

    `already_in_baseline=True` 인 항목은 기준선(regions.REGISTRY)이 이미 같은 결론을 내고 있다는 뜻이다
    — 이미 반영된 정책을 다시 등록했거나, delta 가 불필요하다는 신호다.
    """
    out: list[RegionChange] = []
    for d in policy.region_deltas:
        code = canonical_code(d.region_code)
        before, _ = resolve_region_status(code, d.effective_from)
        baseline_after, _ = resolve_region_status(code, d.effective_from)
        out.append(RegionChange(
            region_code=code,
            region_name=d.region_name or (REGISTRY[code].label if code in REGISTRY else code),
            before=before,
            after=d.region_status,
            effective_from=d.effective_from,
            already_in_baseline=baseline_after is d.region_status,
        ))
    return out


@dataclass(frozen=True)
class OverlapWarning:
    """신규 정책과 기존 정책이 같은 지역·기간에서 겹칠 때 (§7 '우선순위 검토 대상으로 표시')."""
    region_code: str
    new_policy_id: str
    existing_policy_id: str
    effective_from: date
    detail: str


def detect_overlaps(registry: PolicyRegistry, policy: PolicyVersion) -> list[OverlapWarning]:
    """같은 지역을 건드리는 다른 확정 정책이 있으면 우선순위 검토 대상으로 표시한다 (§7).

    시간 순서와 무관하게 표시한다 — 먼저 지정된 곳을 다시 건드리는 것도, 나중 시행일이 앞당겨지는 것도
    모두 "어느 정책이 이기는가"를 사람이 판단해야 하는 상황이기 때문이다.
    """
    out: list[OverlapWarning] = []
    new_codes = {canonical_code(d.region_code): d for d in policy.region_deltas}
    for other in registry.confirmed():
        if other.policy_id == policy.policy_id:
            continue
        for d in other.region_deltas:
            code = canonical_code(d.region_code)
            if code not in new_codes:
                continue
            mine = new_codes[code]
            rel = ("기존 지정을 신규 정책이 덮어씀" if d.effective_from <= mine.effective_from
                   else "기존 정책의 시행일이 신규 정책보다 뒤 — 순서 역전")
            out.append(OverlapWarning(
                region_code=code, new_policy_id=policy.policy_id,
                existing_policy_id=other.policy_id, effective_from=mine.effective_from,
                detail=(f"{other.policy_id} 가 {d.effective_from} 부터 {d.region_status.value} 로 "
                        f"지정 · {rel} — 우선순위 검토 필요"),
            ))
    return out
