"""Policy Version DB 시드 — 지역 기준선에서 정책 JSON을 생성한다.

실행:  python tools/seed_policies.py

`regions.REGION_VERSIONS` 의 각 버전은 이미 `source_policy_id` 를 달고 있다(어느 공문이
그 상태를 만들었는지). 그것을 정책 단위로 뒤집어 모으면 Policy Version DB 가 된다.

왜 손으로 쓰지 않는가: 같은 사실을 두 번 타이핑하면 반드시 갈라진다. 생성해 두고
`policy.check_registry_matches_baseline()` 이 이후의 드리프트를 잡게 한다.

왜 8k0xmx 의 JSON 을 그대로 안 쓰는가: 그쪽은 지역 코드 체계가 다르다
(`GYEONGGI_GURI` vs 이 저장소의 `GURI`). 코드가 어긋난 채로 들이면 정합성 검사가
전부 미스로 나오고, 코드 체계를 바꾸면 기존 픽스처·골드가 전부 깨진다.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from regimpact.models import RegionStatus                      # noqa: E402
from regimpact.policy import (                                 # noqa: E402
    PolicyRegistry,
    PolicyStatus,
    PolicyVersion,
    Provenance,
    RegionDelta,
    SourceDocument,
    check_registry_matches_baseline,
)
from regimpact.regions import REGION_VERSIONS, region_label    # noqa: E402

# 정책 메타 — 공문에서 사람이 확정한 사실(regulatory_facts C16).
POLICY_META = {
    "MOLIT_20161103": dict(
        title="강남·서초·송파·용산 조정대상지역 지정",
        issuer="국토교통부", published_at=date(2016, 11, 3),
        effective_from=date(2016, 11, 3), supersedes=None,
    ),
    "MOLIT_20170803": dict(
        title="강남·서초·송파·용산 투기과열지구 지정",
        issuer="국토교통부", published_at=date(2017, 8, 3),
        effective_from=date(2017, 8, 3), supersedes="MOLIT_20161103",
    ),
    "MOLIT_20251016": dict(
        title="서울 21개 자치구·경기 12곳 투기과열지구 및 조정대상지역 지정",
        issuer="국토교통부", published_at=date(2025, 10, 16),
        effective_from=date(2025, 10, 16), supersedes="MOLIT_20170803",
    ),
    "FSC_20260630": dict(
        title="6·30 대책 — 화성동탄·용인기흥·구리 규제지역 지정 및 주담대 LTV 강화",
        issuer="금융위원회·국토교통부", published_at=date(2026, 6, 30),
        effective_from=date(2026, 7, 1), supersedes="MOLIT_20251016",
    ),
}

# 어느 정책이 어느 원문 스냅샷에 근거하는가 (docs/sources/SOURCES.md)
POLICY_SOURCES = {
    "MOLIT_20161103": ["MOLIT_PRESS_20260630"],   # 참고2 현황표가 과거 지정일을 병기
    "MOLIT_20170803": ["MOLIT_PRESS_20260630"],
    "MOLIT_20251016": ["MOLIT_PRESS_20260630"],
    "FSC_20260630": ["FSC_PRESS_20260630", "MOLIT_PRESS_20260630", "FAQ_20260630"],
}


def load_source_docs() -> dict[str, SourceDocument]:
    """SOURCES.md 의 해시 표를 읽어 원문 스냅샷 메타를 만든다."""
    text = (ROOT / "docs" / "sources" / "SOURCES.md").read_text(encoding="utf-8")
    docs: dict[str, SourceDocument] = {}
    hashes = dict(re.findall(r"^([0-9a-f]{64})\s+(\S+)$", text, re.MULTILINE))
    by_file = {v: k for k, v in hashes.items()}
    for row in re.finditer(r"^\|\s*([A-Z0-9_]+)\s*\|\s*([^|]+?)\s*\|.*?`original/([^`]+)`", text,
                           re.MULTILINE):
        doc_id, title, filename = row.group(1), row.group(2), row.group(3)
        docs[doc_id] = SourceDocument(
            source_document_id=doc_id, title=title.strip(),
            source_hash=by_file.get(filename, ""), filename=filename,
            retrieved_at=date(2026, 8, 10),
        )
    return docs


def build_registry() -> PolicyRegistry:
    source_docs = load_source_docs()
    deltas: dict[str, list[RegionDelta]] = {pid: [] for pid in POLICY_META}

    for code, versions in REGION_VERSIONS.items():
        for v in versions:
            pid = v.source_policy_id
            if pid is None:
                continue                       # 지정 전 비규제 구간 · 상시 비규제 지역
            if pid not in deltas:
                raise SystemExit(f"POLICY_META 에 없는 source_policy_id: {pid}")
            deltas[pid].append(RegionDelta(
                region_code=code, region_name=region_label(code),
                region_status=v.status, effective_from=v.effective_from,
                effective_to=v.effective_to, regulated_type=v.regulated_type,
            ))

    policies = []
    for pid, meta in POLICY_META.items():
        rows = sorted(deltas[pid], key=lambda d: d.region_code)
        policies.append(PolicyVersion(
            policy_id=pid, title=meta["title"], issuer=meta["issuer"],
            published_at=meta["published_at"], effective_from=meta["effective_from"],
            supersedes_policy_id=meta["supersedes"],
            status=PolicyStatus.CONFIRMED,
            provenance=Provenance.HUMAN_CONFIRMED,
            sources=[source_docs[s] for s in POLICY_SOURCES[pid] if s in source_docs],
            region_deltas=rows,
            notes="regions.REGION_VERSIONS 에서 생성 (tools/seed_policies.py). "
                  "근거: regulatory_facts C16 — MOLIT p5 참고2 현황표.",
        ))
    return PolicyRegistry(policies=policies)


def main() -> int:
    registry = build_registry()
    written = registry.save()
    for path in written:
        n = len(registry.get(path.stem).region_deltas)
        print(f"  {path.relative_to(ROOT)}  지역 delta {n}건")

    drift = check_registry_matches_baseline(registry)
    print(f"\n  기준선 정합성: {drift.summary()}")
    for d in drift.all[:10]:
        print(f"    ⚠ {d.region_code} · {d.policy_id} — {d.detail}")
    return 0 if drift.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
