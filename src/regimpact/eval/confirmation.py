"""확정 지문(confirmation digest) — "검수했다"가 시간이 지나도 참인지 확인한다.

`authored_by: human_confirmed` 는 **그 시점의 내용**에 대한 확정이다. 그런데 골드는 계속
손보게 된다(키워드 조정, 인용 교체, 항목 추가). 그 변경이 확정 표시를 그대로 달고 지나가면
"사람이 검수한 골드"라는 말이 사실이 아니게 된다 — 그리고 그 사실은 아무 데도 드러나지 않는다.

그래서 확정 시점의 내용을 해시로 박아 둔다. 이후 내용이 바뀌면 지문이 어긋나고,
검증기가 **재검수가 필요하다**고 말한다. 변경을 막지는 않는다 — 조용히 지나가지 못하게 할 뿐이다.
(LOCKED/CHALLENGE 봉인 로그와 같은 성격의 통제다.)
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

# 지문에 넣는 필드 — 채점에 영향을 주는 것만. 설명(_note 등)이 바뀐다고 재검수가 필요하진 않다.
_SCORED_FIELDS = ("id", "name", "claim", "keywords", "transition", "citations")


def _canonical(entries: list[dict]) -> str:
    slim = []
    for e in entries:
        slim.append({k: e[k] for k in _SCORED_FIELDS if k in e})
    return json.dumps(slim, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def compute_digest(gold: dict) -> str:
    """채점에 영향을 주는 내용의 지문. 확정 시점에 기록하고 이후 대조한다."""
    payload = _canonical(gold.get("required_changes", [])) + "\n" + _canonical(gold.get("exceptions", []))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


@dataclass
class ConfirmationStatus:
    confirmed: bool
    digest_matches: bool
    recorded: str | None
    actual: str
    confirmed_on: str | None

    @property
    def needs_review(self) -> bool:
        """확정 표시는 있는데 내용이 그 이후 바뀐 상태."""
        return self.confirmed and not self.digest_matches

    def summary(self) -> str:
        if not self.confirmed:
            return "🤖 미확정 (ai_draft)"
        if self.digest_matches:
            return f"✅ 확정 {self.confirmed_on} · 지문 일치 ({self.actual})"
        return (f"⚠️ 확정 {self.confirmed_on} 이후 내용 변경됨 — 재검수 필요 "
                f"(기록 {self.recorded} ≠ 현재 {self.actual})")


def check_confirmation(gold: dict) -> ConfirmationStatus:
    rec = gold.get("_confirmed") or {}
    actual = compute_digest(gold)
    return ConfirmationStatus(
        confirmed=gold.get("authored_by") == "human_confirmed",
        digest_matches=rec.get("digest") == actual,
        recorded=rec.get("digest"),
        actual=actual,
        confirmed_on=rec.get("date"),
    )
