"""Policy Version DB (docs/00_BRIEF.md §19-3 "새 정책을 Policy Version DB에 등록").

저장소는 **git 안의 JSON 파일**(`docs/policies/*.json`)이다. DB 서버가 아니라 파일인 이유:
정책 버전은 감사 대상이고, git 이력이 곧 "누가 언제 무엇을 확정했는가"의 기록이 된다(LOCKED §10).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional

from .version import PolicyStatus, PolicyVersion

POLICY_DIR = Path(__file__).resolve().parents[3] / "docs" / "policies"


@dataclass
class PolicyRegistry:
    policies: list[PolicyVersion] = field(default_factory=list)

    def __post_init__(self) -> None:
        self._check_unique()

    def _check_unique(self) -> None:
        seen: set[str] = set()
        for p in self.policies:
            key = f"{p.policy_id}@{p.version}"
            if key in seen:
                raise ValueError(f"중복 정책 버전: {key}")
            seen.add(key)

    # --- 조회 ---
    def get(self, policy_id: str) -> Optional[PolicyVersion]:
        return next((p for p in self.policies if p.policy_id == policy_id), None)

    def confirmed(self) -> list[PolicyVersion]:
        return [p for p in self.policies if p.status is PolicyStatus.CONFIRMED]

    def drafts(self) -> list[PolicyVersion]:
        return [p for p in self.policies if p.status is PolicyStatus.DRAFT]

    def sorted_by_effective(self) -> list[PolicyVersion]:
        return sorted(self.policies, key=lambda p: (p.effective_from, p.policy_id))

    # --- 변경 ---
    def add(self, policy: PolicyVersion) -> "PolicyRegistry":
        return PolicyRegistry(policies=[*self.policies, policy])

    def replace(self, policy: PolicyVersion) -> "PolicyRegistry":
        others = [p for p in self.policies if p.policy_id != policy.policy_id]
        return PolicyRegistry(policies=[*others, policy])

    # --- 입출력 ---
    def save(self, directory: Optional[Path] = None) -> list[Path]:
        d = Path(directory or POLICY_DIR)
        d.mkdir(parents=True, exist_ok=True)
        written: list[Path] = []
        for p in self.policies:
            path = d / f"{p.policy_id}.json"
            path.write_text(json.dumps(p.as_dict(), ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")
            written.append(path)
        return written


def load_registry(directory: Optional[Path] = None) -> PolicyRegistry:
    """`docs/policies/*.json` 을 전부 읽어 레지스트리를 만든다."""
    d = Path(directory or POLICY_DIR)
    if not d.exists():
        return PolicyRegistry()
    policies = [
        PolicyVersion.from_dict(json.loads(f.read_text(encoding="utf-8")))
        for f in sorted(d.glob("*.json"))
    ]
    return PolicyRegistry(policies=policies)


def registry_from(policies: Iterable[PolicyVersion]) -> PolicyRegistry:
    return PolicyRegistry(policies=list(policies))
