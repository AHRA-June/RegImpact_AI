"""새 정책 업로드 파이프라인 (브리프 §19 라이브 파이어 1~3단계).

    1. 공식 원문 snapshot 저장  →  2. source hash 기록  →  3. Policy Version DB에 등록

이 모듈이 만드는 것은 **초안(DRAFT)** 이다. 사람이 확정(`CONFIRMED`)하기 전까지는 어떤 판정에도
쓰이지 않는다 (LOCKED §4·§9). LLM 추출을 붙이면 초안이 자동으로 채워지지만 `provenance` 는
`AI_DRAFT` 로 남고, 지역 코드로 매핑되지 않은 지역명은 **조용히 버리지 않고 따로 보고**한다 —
넘겨짚어 채우는 순간 근거 없는 규제상태가 만들어진다.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date
from typing import Optional, Sequence

from ..extractor.schema import RegChangeExtraction
from ..models import RegionStatus, RegulatedType
from ..regions import REGISTRY, canonical_code
from .version import (
    PolicyStatus,
    PolicyVersion,
    Provenance,
    RegionDelta,
    RuleNote,
    SourceDocument,
)


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def snapshot_document(
    *,
    source_document_id: str,
    title: str,
    content: bytes,
    filename: Optional[str] = None,
    source_url: Optional[str] = None,
    retrieved_at: Optional[date] = None,
) -> SourceDocument:
    """업로드된 원문을 스냅샷으로 만든다 (해시로 무결성 고정)."""
    return SourceDocument(
        source_document_id=source_document_id,
        title=title,
        source_hash=sha256_hex(content),
        retrieved_at=retrieved_at,
        source_url=source_url,
        filename=filename,
        byte_size=len(content),
    )


@dataclass
class DraftResult:
    """초안 + 사람이 채워야 하는 구멍."""
    policy: PolicyVersion
    unmapped_regions: list[str]          # 코드로 매핑하지 못한 지역명 — 사람이 채워야 함
    warnings: list[str]


def _map_region(name_or_code: str) -> Optional[str]:
    """추출된 지역 표기를 레지스트리 코드로 매핑. 확신이 없으면 None(넘겨짚지 않는다)."""
    code = canonical_code(name_or_code)
    if code in REGISTRY:
        return code
    needle = name_or_code.strip()
    hits = [c for c, r in REGISTRY.items() if needle and needle in (r.name, r.label)]
    return hits[0] if len(hits) == 1 else None


def draft_policy(
    *,
    policy_id: str,
    title: str,
    issuer: str,
    published_at: date,
    effective_from: date,
    sources: Sequence[SourceDocument],
    extraction: Optional[RegChangeExtraction] = None,
    supersedes_policy_id: Optional[str] = None,
    regulated_type: RegulatedType = RegulatedType.SPECULATIVE_OVERHEATED,
    manual_region_codes: Sequence[str] = (),
) -> DraftResult:
    """업로드 결과로 정책 버전 초안을 만든다. 항상 `DRAFT` 로 나온다.

    `manual_region_codes` 는 사람이 화면에서 직접 고른 지역이다. 추출 결과와 합쳐지며,
    같은 코드가 겹치면 한 번만 들어간다.
    """
    region_deltas: list[RegionDelta] = []
    rule_notes: list[RuleNote] = []
    unmapped: list[str] = []
    warnings: list[str] = []

    if extraction is not None:
        for raw in extraction.target_regions:
            code = _map_region(raw)
            if code is None:
                unmapped.append(raw)
                continue
            region_deltas.append(RegionDelta(
                region_code=code,
                region_name=REGISTRY[code].label,
                region_status=RegionStatus.REGULATED,
                effective_from=effective_from,
                regulated_type=regulated_type,
            ))
        for item in extraction.changes:
            rule_notes.append(RuleNote(
                field=item.category, before=item.before, after=item.after,
                citation=f"{item.citation.source_doc_id}: {item.citation.quote[:80]}",
            ))
        if extraction.effective_from and extraction.effective_from != effective_from.isoformat():
            warnings.append(
                f"추출된 시행일({extraction.effective_from})이 입력한 시행일({effective_from})과 다르다 "
                "— 원문 대조 필요")
    # 사람이 화면에서 직접 고른 지역 (추출 결과와 합침, 중복 제거)
    seen = {d.region_code for d in region_deltas}
    for raw in manual_region_codes:
        code = _map_region(raw)
        if code is None:
            unmapped.append(raw)
            continue
        if code in seen:
            continue
        seen.add(code)
        region_deltas.append(RegionDelta(
            region_code=code, region_name=REGISTRY[code].label,
            region_status=RegionStatus.REGULATED,
            effective_from=effective_from, regulated_type=regulated_type,
        ))

    if not region_deltas and not rule_notes:
        warnings.append("지역 변경도 룰 메모도 없는 빈 초안 — 확정하려면 하나는 채워야 한다")
    elif extraction is None:
        warnings.append("LLM 추출 없이 사람이 직접 입력한 초안 — 원문과 대조해 확정해야 한다")

    if unmapped:
        warnings.append(
            f"지역 코드로 매핑하지 못한 표기 {len(unmapped)}건: {', '.join(unmapped)} "
            "— 넘겨짚지 않고 비워 두었다. 사람이 채워야 한다")

    policy = PolicyVersion(
        policy_id=policy_id, title=title, issuer=issuer,
        published_at=published_at, effective_from=effective_from,
        supersedes_policy_id=supersedes_policy_id,
        status=PolicyStatus.DRAFT,
        provenance=Provenance.AI_DRAFT if extraction is not None else Provenance.HUMAN_INPUT,
        sources=list(sources), region_deltas=region_deltas, rule_notes=rule_notes,
    )
    return DraftResult(policy=policy, unmapped_regions=unmapped, warnings=warnings)


def confirm(policy: PolicyVersion, *, notes: str = "") -> PolicyVersion:
    """사람 확정 (LOCKED §4). 이 호출 이후에야 판정에 쓰인다."""
    if not policy.region_deltas and not policy.rule_notes:
        raise ValueError("빈 정책은 확정할 수 없다 — 지역 delta 또는 룰 메모가 하나는 있어야 한다")
    return PolicyVersion(
        **{**policy.__dict__,
           "status": PolicyStatus.CONFIRMED,
           "provenance": Provenance.HUMAN_CONFIRMED,
           "notes": notes or policy.notes},
    )
