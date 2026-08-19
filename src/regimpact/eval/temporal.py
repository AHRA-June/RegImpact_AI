"""시점 질의 골드 ⟷ Temporal Policy Resolver 정합 검사.

시점 질의 골드는 두 진실 위에 서 있다 — 원문 인용(validate_items가 대조)과
**정책 버전 DB의 시점 해석**(이 파일이 대조). as_of가 있는 문항의 policy_version은
"그 시점에 유효한 최신 정책"이라는 주장이므로, resolver의 답과 어긋나면 골드가 틀렸거나
정책 DB가 틀렸거나 둘 중 하나다 — 어느 쪽이든 조용히 지나가면 안 된다.

escalation 문항은 반대 방향을 검사한다: "DB가 그 시점을 답할 수 없다"가 escalation의
근거이므로, **DB가 답할 수 있게 되는 순간**(예: 2020 6·17 해제 원문 확보 후 confirm())
이 검사가 그 문항을 갱신하라고 요구한다. 한계를 골드에 새겼으면, 한계가 풀릴 때
골드도 함께 풀려야 한다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from ..policy.registry import PolicyRegistry, load_registry
from ..policy.resolver import current_policy
from .schema import GoldItem


@dataclass
class TemporalReport:
    conflicts: list[str] = field(default_factory=list)
    checked: int = 0            # as_of가 있어 실제로 대조한 문항 수
    answerable: int = 0         # resolver가 답해야 하는 문항(escalation 아님)
    escalations: int = 0        # DB가 답할 수 없어야 하는 문항

    @property
    def ok(self) -> bool:
        return not self.conflicts

    def summary(self) -> str:
        return (f"시점 대조 {self.checked}문항(답변형 {self.answerable} · "
                f"escalation형 {self.escalations}) — "
                f"{'✅ resolver와 정합' if self.ok else f'❌ 충돌 {len(self.conflicts)}건'}")


def check_temporal_gold(
    items: list[GoldItem], registry: PolicyRegistry | None = None
) -> TemporalReport:
    """as_of가 있는 문항을 Temporal Policy Resolver와 대조한다."""
    reg = registry if registry is not None else load_registry()
    rep = TemporalReport()

    for item in items:
        if item.as_of is None:
            continue
        rep.checked += 1
        as_of = date.fromisoformat(item.as_of)
        cur = current_policy(reg, as_of)     # 그 시점 유효 정책 중 최신 (CONFIRMED만)
        cur_id = cur.policy_id if cur else None

        if item.expect_escalation:
            rep.escalations += 1
            # escalation의 근거는 "DB가 이 시점의 그 정책을 확정 상태로 답할 수 없다"이다.
            # DB가 답할 수 있게 되면(정책 confirm 등) 이 문항은 답변형으로 갱신돼야 한다.
            if cur_id == item.policy_version:
                rep.conflicts.append(
                    f"[{item.id}] escalation 문항인데 resolver가 {item.as_of} 시점을 "
                    f"{cur_id}로 답할 수 있다 — 정책이 확정된 것이라면 이 문항을 "
                    "답변형으로 갱신하라(해제 원문 확보 시나리오)"
                )
        else:
            rep.answerable += 1
            if cur_id != item.policy_version:
                rep.conflicts.append(
                    f"[{item.id}] {item.as_of} 시점 유효 정책: 골드={item.policy_version} "
                    f"/ resolver={cur_id} — 골드나 정책 DB 중 하나가 틀렸다"
                )

    return rep


def policy_version_consistency(
    items: list[GoldItem], registry: PolicyRegistry | None = None
) -> tuple[int, int]:
    """Policy-version Consistency 실측 (metrics_spec §1).

    분모 = as_of가 있는 답변형 문항 수, 분자 = resolver가 골드와 일치한 수.
    ⚠️ 골드가 ai_draft인 동안 이 수치는 **상대 비교용**이다 — 사람 확정 후에야 절대값이
    된다(QA 지표와 같은 규율). 임계는 검수·측정 가동 후 별도 확정한다(2026-08-19 결정).
    """
    rep = check_temporal_gold(items, registry)
    return rep.answerable - sum(
        1 for c in rep.conflicts if "escalation" not in c
    ), rep.answerable
