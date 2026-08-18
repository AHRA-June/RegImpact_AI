"""문서별 개별 추출 + 병합 — 문서 간 축약 손실(D-02)의 구조적 대책.

문제: 3개 문서를 한 번에 태우면, 한 문서가 "생애최초, 정책모기지 **등**"으로 축약한 서술이
다른 문서의 완전한 열거를 가려 버린다(실측 D-02). 프롬프트로 "축약하지 마라"고 지시해도
두 모델 모두 같은 실패를 반복했다.

대책: **문서마다 따로 추출한 뒤 합친다.** 각 문서를 볼 때는 그 문서의 서술이 유일한 서술이므로
축약된 쪽에 가려질 대상이 없다. 대가는 호출 수 N배와 중복 항목이다.

중복 제거는 **보수적으로** 한다 — 정규화 후 완전히 같은 항목만 제거하고, 표현이 다른 near-duplicate는
남긴다. 이 도메인에서 가장 무서운 오류는 예외를 놓치는 것이고(브리프 §11), 중복은 사람 검토로
걸러지지만 누락은 드러나지 않기 때문이다.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .backends import CompletionFn
from .prompt import SYSTEM_PROMPT, build_user_prompt
from .schema import RegChangeExtraction, RegChangeItem


def _key(item: RegChangeItem) -> tuple:
    def n(s):
        return re.sub(r"\s+", "", (s or "")).lower()
    return (item.category, n(item.summary), n(item.before), n(item.after))


@dataclass
class MergeReport:
    """병합 과정의 추적 정보 — 어느 문서가 무엇을 기여했는지 남긴다."""
    per_document: dict[str, int] = field(default_factory=dict)
    raw_count: int = 0
    merged_count: int = 0
    duplicates_removed: int = 0
    cross_document_merged: int = 0
    effective_from_by_doc: dict[str, str] = field(default_factory=dict)
    policy_id_by_doc: dict[str, str] = field(default_factory=dict)

    @property
    def effective_from_conflict(self) -> bool:
        """문서마다 시행일이 다르면 Temporal Consistency 신호 — 조용히 하나를 고르면 안 된다."""
        vals = {v for v in self.effective_from_by_doc.values() if v}
        return len(vals) > 1

    @property
    def conflicts(self) -> list[str]:
        out = []
        if self.effective_from_conflict:
            out.append(f"effective_from 불일치: {self.effective_from_by_doc}")
        ids = {v for v in self.policy_id_by_doc.values() if v}
        if len(ids) > 1:
            out.append(f"policy_id 불일치: {self.policy_id_by_doc}")
        return out


def extract_per_document(
    sources: dict[str, str],
    *,
    complete: CompletionFn,
    cache_dir: Optional[str | Path] = None,
    merge_threshold: float = 0.5,
) -> tuple[RegChangeExtraction, MergeReport]:
    """문서를 하나씩 추출해 합친다. 문서 수만큼 LLM을 호출한다.

    cache_dir를 주면 문서별 결과를 **완료 즉시** 디스크에 남긴다. 뒤 단계에서 예외가 나거나
    호출 한도에 걸려도 이미 끝난 문서의 결과를 잃지 않는다 — 무과금 경로에서 한 번의 실행이
    10분 단위라 재시작 비용이 크다. 캐시 키에 원문 해시를 넣어 원문이 바뀌면 자동으로 무효화된다.
    """
    report = MergeReport()
    all_items: list[RegChangeItem] = []
    regions: list[str] = []
    cache = Path(cache_dir) if cache_dir else None
    if cache:
        cache.mkdir(parents=True, exist_ok=True)

    for doc_id, text in sources.items():
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
        cached = cache / f"{doc_id}.{digest}.json" if cache else None
        if cached is not None and cached.exists():
            raw = json.loads(cached.read_text(encoding="utf-8"))
        else:
            raw = complete(SYSTEM_PROMPT, build_user_prompt({doc_id: text}, single_document=True))
            if cached is not None:
                cached.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
        part = RegChangeExtraction.from_dict(raw)
        report.per_document[doc_id] = len(part.changes)
        report.effective_from_by_doc[doc_id] = part.effective_from or ""
        report.policy_id_by_doc[doc_id] = part.policy_id or ""
        all_items.extend(part.changes)
        for r in part.target_regions:
            if r not in regions:
                regions.append(r)

    # 1차: 완전 동일 항목 제거 (정규화 후 같은 것)
    seen: set[tuple] = set()
    deduped: list[RegChangeItem] = []
    for item in all_items:
        k = _key(item)
        if k in seen:
            report.duplicates_removed += 1
            continue
        seen.add(k)
        deduped.append(item)

    # 2차: 서로 다른 문서가 같은 사실을 말한 항목을 합치고 인용을 모은다
    merged, cross = merge_cross_document(deduped, threshold=merge_threshold)
    report.duplicates_removed += cross
    report.cross_document_merged = cross
    report.raw_count = len(all_items)
    report.merged_count = len(merged)

    # 시행일·policy_id: 다수결이 아니라 **가장 많이 등장한 값**을 쓰되 불일치는 report로 드러낸다.
    def _majority(values: dict[str, str]) -> str | None:
        counts: dict[str, int] = {}
        for v in values.values():
            if v:
                counts[v] = counts.get(v, 0) + 1
        return max(counts, key=counts.get) if counts else None

    return (
        RegChangeExtraction(
            policy_id=_majority(report.policy_id_by_doc) or "",
            effective_from=_majority(report.effective_from_by_doc),
            target_regions=regions,
            changes=merged,
        ),
        report,
    )


# ---------------------------------------------------------------- 문서 간 사실 병합
#
# 문서별 추출은 같은 사실을 문서 수만큼 만들어 낸다(6·30에서 LTV 70→40이 3건). 그대로 두면
# 임팩트 매트릭스가 부풀지만, **요약문 유사도로 합치는 것은 이 도메인에서 위험하다.**
# 실측(2026-08-18, `tools/tune_merge.py`)에서 유사도 0.6으로도 다음이 합쳐졌다:
#   · "생애최초 60% 유지" + "서민·실수요자 60% 유지"        → 서로 다른 차주 유형
#   · "서민 요건 9천만원/8억" + "생애최초 요건 7천만원/6억"   → 서로 다른 임계값
#   · "일반 주담대 경과규정" + "사업자 주담대 경과규정"       → 서로 다른 규제
# 개체만 다르고 문장 구조가 같은 항목들이라 텍스트 유사도로는 구분되지 않는다. 임계값 문제가 아니다.
# (골드 대비 점수는 이때도 100%였다 — 골드가 과병합을 탐지할 만큼 예민하지 않았다는 뜻이고,
#  "지표가 통과했다"만 보고 채택했다면 D-02를 병합 단계에서 되살릴 뻔했다.)
#
# 그래서 규칙을 바꿨다: **같은 문서 안의 항목은 건드리지 않는다.** 모델이 한 문서를 보며 둘로
# 나눴다면 나눈 이유가 있다고 본다. 합치는 것은 **서로 다른 문서가 같은 사실을 말한 경우뿐**이며,
# 그때는 중복이 줄 뿐 아니라 근거가 강해진다(corroborations).

_ENTITY_TOKENS = (
    "생애최초", "서민", "실수요자", "다주택", "유주택", "무주택", "처분조건부",
    "동탄", "기흥", "구리", "전세대출", "신용대출", "중도금", "이주비", "사업자",
    "집단대출", "토지거래허가", "디딤돌", "보금자리", "일반",
)


def _fingerprint(item: RegChangeItem) -> tuple:
    """항목의 **내용 지문** — 수치와 도메인 개체어. 이게 다르면 다른 사실로 본다."""
    text = f"{item.summary} {item.before or ''} {item.after or ''}"
    numbers = tuple(sorted(set(re.findall(r"\d+(?:[.,]\d+)?\s*(?:%|억|만원|년|개월|일|건|배)?", text))))
    entities = tuple(sorted({t for t in _ENTITY_TOKENS if t in text}))
    return (item.category, numbers, entities)


def merge_cross_document(
    items: list[RegChangeItem], *, threshold: float = 0.5
) -> tuple[list[RegChangeItem], int]:
    """서로 **다른 문서**가 같은 사실을 말한 항목만 합치고, 인용은 corroborations로 모은다.

    합치는 조건 셋을 모두 만족해야 한다:
      1. 출처 문서가 다르다 (같은 문서 안에서 모델이 나눈 것은 존중한다)
      2. 내용 지문(카테고리·수치·개체어)이 같다
      3. 요약문 유사도가 threshold 이상이다
    대표 요약문은 가장 긴 것을 고른다 — 축약된 서술이 완전한 열거를 덮어쓰지 않도록(D-02와 같은 이유).
    """
    groups: list[list[RegChangeItem]] = []
    for item in items:
        for g in groups:
            head = g[0]
            if (
                item.citation.source_doc_id not in {i.citation.source_doc_id for i in g}
                and _fingerprint(head) == _fingerprint(item)
                and _compatible(head, item)
                and _similarity(head.summary, item.summary) >= threshold
            ):
                g.append(item)
                break
        else:
            groups.append([item])

    merged: list[RegChangeItem] = []
    for g in groups:
        if len(g) == 1:
            merged.append(g[0])
            continue
        best = max(g, key=lambda i: len(i.summary or ""))
        merged.append(RegChangeItem(
            category=best.category,
            summary=best.summary,
            citation=best.citation,
            before=next((i.before for i in g if i.before), None),
            after=next((i.after for i in g if i.after), None),
            confidence=max(i.confidence for i in g),
            corroborations=tuple(i.citation for i in g if i is not best),
        ))
    return merged, len(items) - len(merged)


def _trigrams(s: str) -> set[str]:
    t = re.sub(r"[\s·,()（）\[\]]", "", (s or "").lower())
    return {t[i : i + 3] for i in range(max(0, len(t) - 2))} or {t}


def _similarity(a: str, b: str) -> float:
    ta, tb = _trigrams(a), _trigrams(b)
    return len(ta & tb) / len(ta | tb) if (ta | tb) else 0.0


def _compatible(a: RegChangeItem, b: RegChangeItem) -> bool:
    """before/after가 충돌하지 않는가. 한쪽이 비어 있으면 충돌로 보지 않는다."""
    def n(s):
        return re.sub(r"\s+", "", (s or "")).lower()
    for x, y in ((n(a.before), n(b.before)), (n(a.after), n(b.after))):
        if x and y and x != y:
            return False
    return True
