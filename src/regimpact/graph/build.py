"""영향 지식그래프 빌더 — LLM이 아니라 **검증된 산출물**에서 조립한다.

"GraphRAG" 류의 시스템은 보통 LLM이 문서에서 엔티티·관계를 추출해 그래프를 만든다.
그 그래프는 추출 환각을 그대로 물려받는다. 이 프로젝트는 반대로 간다 —
이미 각자 검증을 거친 산출물(정책 버전 DB · 지역 레지스트리 · 룰엔진 상수 diff ·
고객 영향 실측 · 룰 회귀 결과)이 곧 엔티티·관계다. **모든 엣지는 provenance
(어느 산출물에서 왔는가)를 갖고, 그것이 없는 엣지는 생성 시점에 거부된다.**

노드 열(column)이 곧 파이프라인 서사다:
    원문 문서 → 정책 버전 → 규제지역 → 룰 → 고객 세그먼트
                                      └→ 룰 회귀(검증) 카테고리
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Optional

from ..extractor.schema import RegChangeExtraction
from ..impact.builder import derive_rule_diff
from ..impact.customer import CustomerImpactReport
from ..policy import PolicyRegistry, load_registry
from ..regions import region_label
from ..tc_generator.regression import RegressionReport

# 열 순서 — 화면 레이아웃과 서사가 여기서 결정된다
COLUMNS = ("doc", "policy", "region", "rule", "segment", "tc")

# 자동판정 밖(사람·수동 경로)을 표현하는 의사 노드.
# rule_id=None 인 실측 건들을 조용히 떨어뜨리지 않기 위해 존재한다.
HUMAN_NODE_ID = "HUMAN_PATH"


@dataclass(frozen=True)
class Node:
    id: str
    type: str            # COLUMNS 중 하나
    label: str
    sub: str = ""        # 보조 라벨 (시행일·값·건수 등)
    value: int = 0       # 크기 가중치 (고객 수·지역 수 등)

    def to_dict(self) -> dict:
        return {"id": self.id, "type": self.type, "label": self.label,
                "sub": self.sub, "value": self.value}


@dataclass(frozen=True)
class Edge:
    source: str
    target: str
    kind: str            # evidences | supersedes | designates | activates | decides | verifies
    provenance: str      # 어느 산출물에서 왔는가 — 비어 있으면 생성 거부
    label: str = ""
    weight: int = 1

    def __post_init__(self):
        if not self.provenance.strip():
            raise ValueError(f"provenance 없는 엣지는 만들 수 없다: {self.source}→{self.target}")

    def to_dict(self) -> dict:
        return {"source": self.source, "target": self.target, "kind": self.kind,
                "label": self.label, "weight": self.weight, "provenance": self.provenance}


@dataclass
class Graph:
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)

    def node_ids(self) -> set[str]:
        return {n.id for n in self.nodes}

    def validate(self) -> None:
        ids = self.node_ids()
        if len(ids) != len(self.nodes):
            raise ValueError("노드 id 중복")
        for e in self.edges:
            if e.source not in ids or e.target not in ids:
                raise ValueError(f"끊어진 엣지: {e.source}→{e.target}")

    def to_dict(self) -> dict:
        return {"columns": list(COLUMNS),
                "nodes": [n.to_dict() for n in self.nodes],
                "edges": [e.to_dict() for e in self.edges]}


def build_graph(
    extraction: RegChangeExtraction,
    impact: CustomerImpactReport,
    regression: RegressionReport,
    *,
    registry: Optional[PolicyRegistry] = None,
) -> Graph:
    g = Graph()
    registry = registry or load_registry()
    policies = registry.sorted_by_effective()
    current = policies[-1]

    # ---------------- ① 원문 문서 — 추출 인용의 출처 (실측: 문서별 추출 건수)
    per_doc = Counter(c.citation.source_doc_id for c in extraction.changes)
    for doc_id in sorted(per_doc):
        g.nodes.append(Node(id=doc_id, type="doc", label=doc_id.rsplit("_", 1)[0],
                            sub=f"추출 {per_doc[doc_id]}건", value=per_doc[doc_id]))
        g.edges.append(Edge(source=doc_id, target=current.policy_id, kind="evidences",
                            label=f"변경 {per_doc[doc_id]}건 추출",
                            weight=per_doc[doc_id],
                            provenance="RegChange 추출 (인용 원문 대조 통과)"))

    # ---------------- ② 정책 버전 — supersedes 타임라인
    for p in policies:
        g.nodes.append(Node(id=p.policy_id, type="policy", label=p.title,
                            sub=f"시행 {p.effective_from.isoformat()} · {p.status.value}",
                            value=len(p.region_deltas)))
        if p.supersedes_policy_id:
            g.edges.append(Edge(source=p.supersedes_policy_id, target=p.policy_id,
                                kind="supersedes", label="직전 정책",
                                provenance="정책 버전 DB (supersedes)"))

    # ---------------- ③ 규제지역 — 이번 정책의 신규 지정은 개별, 과거는 집계
    # 집계 수는 **확정 정책만** 센다 — DRAFT 지정(해제 원문 대기)을 섞으면
    # "지정 N곳"이 확립된 사실처럼 읽힌다. DRAFT 는 엣지에 (초안)으로만 나타난다.
    prior_total = sum(
        len(p.region_deltas) for p in policies[:-1] if p.status.value == "CONFIRMED")
    prior_id = "REGIONS_PRIOR"
    g.nodes.append(Node(id=prior_id, type="region", label="기존 규제지역",
                        sub=f"{policies[0].effective_from.year}~"
                            f"{policies[-2].effective_from.year} 확정 지정 {prior_total}곳",
                        value=prior_total))
    for p in policies[:-1]:
        if not p.region_deltas:
            continue   # 지역 이관 전 DRAFT — 없는 지정을 그리지 않는다
        draft = p.status.value != "CONFIRMED"
        g.edges.append(Edge(source=p.policy_id, target=prior_id, kind="designates",
                            label=f"{len(p.region_deltas)}곳 지정" + (" (초안)" if draft else ""),
                            weight=len(p.region_deltas),
                            provenance="정책 버전 DB (region_deltas"
                                       + (" — DRAFT, 해제 원문 대기)" if draft else ")")))
    for d in current.region_deltas:
        g.nodes.append(Node(id=d.region_code, type="region",
                            label=region_label(d.region_code),
                            sub="신규 지정", value=1))
        g.edges.append(Edge(source=current.policy_id, target=d.region_code,
                            kind="designates", label="신규 지정",
                            provenance="정책 버전 DB (region_deltas)"))

    # ---------------- ④ 룰 — 엔진 상수 diff (값의 출처는 확정 명세의 구현)
    diff = derive_rule_diff()
    for d in diff:
        moved = d["before"] != d["after"]
        fmt = lambda v: "기준없음" if v is None else f"{v:.0%}"  # noqa: E731
        g.nodes.append(Node(id=d["rule_id"], type="rule", label=d["condition"],
                            sub=f"{fmt(d['before'])} → {fmt(d['after'])}"
                                + (" (변경)" if moved else " (좌동)"),
                            value=2 if moved else 1))
        g.edges.append(Edge(source=current.policy_id, target=d["rule_id"],
                            kind="activates", label="변경" if moved else "좌동",
                            provenance="룰엔진 상수 diff (확정 명세 05_RULE_SPEC 구현)"))
    g.nodes.append(Node(id=HUMAN_NODE_ID, type="rule", label="자동판정 밖",
                        sub="사람 검토·수동 경로", value=1))
    g.edges.append(Edge(source=current.policy_id, target=HUMAN_NODE_ID,
                        kind="activates", label="escalation",
                        provenance="룰엔진 (판정 불가 시 사유와 함께 사람에게)"))

    # ---------------- ⑤ 고객 세그먼트 — (rule → segment) 실측 건수
    seg_totals = Counter(i.segment.value for i in impact.impacts)
    rule_seg = Counter(
        (i.after.applicable_rule_id or HUMAN_NODE_ID, i.segment.value)
        for i in impact.impacts
    )
    seg_ids = {}
    for seg_name, n in seg_totals.items():
        sid = "SEG_" + str(len(seg_ids))
        seg_ids[seg_name] = sid
        g.nodes.append(Node(id=sid, type="segment", label=seg_name,
                            sub=f"{n:,}건", value=n))
    for (rid, seg_name), n in sorted(rule_seg.items()):
        g.edges.append(Edge(source=rid, target=seg_ids[seg_name], kind="decides",
                            label=f"{n:,}건", weight=n,
                            provenance=f"고객 영향 실측 (합성 {len(impact.impacts):,}건, "
                                       f"seed={impact.seed})"))

    # ---------------- ⑥ 룰 회귀 — 어떤 룰이 어느 카테고리에서 검증되는가 (실행 결과)
    by_cat = regression.pass_rate_by_category()
    tc_rule = Counter(
        (res.case.category.value, res.actual.applicable_rule_id or HUMAN_NODE_ID)
        for res in regression.results
    )
    for cat, (passed, total, _rate) in by_cat.items():
        cid = f"TC_{cat}"
        g.nodes.append(Node(id=cid, type="tc", label=cat,
                            sub=f"오라클 대조 {passed}/{total}", value=total))
    for (cat, rid), n in sorted(tc_rule.items()):
        g.edges.append(Edge(source=rid, target=f"TC_{cat}", kind="verifies",
                            label=f"{n}케이스", weight=n,
                            provenance="룰 회귀 실행 결과 (독립 명세 오라클 대조)"))

    g.validate()
    return g
