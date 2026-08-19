"""Policy Version DB ↔ 지역 기준선 정합성 (드리프트 탐지).

같은 사실이 두 곳에 산다 — `regions.REGION_VERSIONS`(엔진이 쓰는 기준선)와
`docs/policies/*.json`(감사 대상 정책 버전 기록). 둘을 하나로 합치지 않은 이유는 역할이
다르기 때문이다. 기준선은 **확정된 사실의 누적 결과**이고, 정책 DB는 **그 사실이 어느
공문에서 언제 왔는지**의 기록이자 아직 확정되지 않은 정책을 담아 두는 자리다.

문제는 둘이 조용히 갈라질 수 있다는 것이다. 한쪽만 고치면 엔진 판정과 감사 기록이
어긋나고, 그 상태로도 테스트는 전부 통과한다. 그래서 갈라지는 순간을 잡는다.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..models import RegionStatus
from ..regions import REGION_VERSIONS, canonical_code, resolve_region_status
from .registry import PolicyRegistry
from .version import PolicyStatus


@dataclass(frozen=True)
class BaselineDrift:
    region_code: str
    policy_id: str
    detail: str


@dataclass
class DriftReport:
    missing_in_baseline: list[BaselineDrift] = field(default_factory=list)
    missing_in_registry: list[BaselineDrift] = field(default_factory=list)
    status_mismatch: list[BaselineDrift] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not (self.missing_in_baseline or self.missing_in_registry
                    or self.status_mismatch)

    @property
    def all(self) -> list[BaselineDrift]:
        return [*self.missing_in_baseline, *self.missing_in_registry, *self.status_mismatch]

    def summary(self) -> dict:
        return {
            "ok": self.ok,
            "missing_in_baseline": len(self.missing_in_baseline),
            "missing_in_registry": len(self.missing_in_registry),
            "status_mismatch": len(self.status_mismatch),
        }


def check_registry_matches_baseline(registry: PolicyRegistry) -> DriftReport:
    """확정 정책의 지역 delta 와 엔진 기준선이 같은 결론을 내는지 양방향으로 본다.

    DRAFT 정책은 대상이 아니다 — 아직 기준선에 없는 것이 정상이고, 그게 초안의 뜻이다.
    """
    report = DriftReport()

    # ① 정책 → 기준선: 확정 정책이 말하는 상태를 기준선도 말하는가
    claimed: set[tuple[str, str]] = set()
    for policy in registry.confirmed():
        for d in policy.region_deltas:
            code = canonical_code(d.region_code)
            claimed.add((code, policy.policy_id))
            status, rtype = resolve_region_status(code, d.effective_from)
            if status is RegionStatus.UNKNOWN:
                report.missing_in_baseline.append(BaselineDrift(
                    code, policy.policy_id,
                    f"{policy.policy_id} 가 {d.effective_from} 부터 "
                    f"{d.region_status.value} 라고 하는데 기준선에 지역이 없다",
                ))
            elif status is not d.region_status:
                report.status_mismatch.append(BaselineDrift(
                    code, policy.policy_id,
                    f"{d.effective_from} 기준 정책={d.region_status.value} / "
                    f"기준선={status.value}",
                ))
            elif rtype is not d.regulated_type:
                # 규제 '유형'도 봐야 한다 — 투기과열지구와 조정대상지역은 DTI 가 다르다
                # (40% vs 50%). status 만 비교하면 이 차이가 조용히 갈라진다.
                report.status_mismatch.append(BaselineDrift(
                    code, policy.policy_id,
                    f"{d.effective_from} 규제유형 정책={d.regulated_type.value} / "
                    f"기준선={rtype.value}",
                ))

    # ② 기준선 → 정책: 기준선이 출처로 지목한 정책이 실제로 등록돼 있는가
    for code, versions in REGION_VERSIONS.items():
        for v in versions:
            pid = v.source_policy_id
            if not pid or (code, pid) in claimed:
                continue
            policy = registry.get(pid)
            if policy is None:
                report.missing_in_registry.append(BaselineDrift(
                    code, pid, f"기준선이 출처로 {pid} 를 지목하는데 정책 DB에 없다"))
            elif policy.status is not PolicyStatus.CONFIRMED:
                report.missing_in_registry.append(BaselineDrift(
                    code, pid,
                    f"기준선이 쓰는 {pid} 가 정책 DB에서 {policy.status.value} 상태다"))
            else:
                report.missing_in_registry.append(BaselineDrift(
                    code, pid, f"{pid} 에 {code} 의 region_delta 가 없다"))

    return report
