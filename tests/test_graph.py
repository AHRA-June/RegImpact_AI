"""지식그래프 — LLM 이 아니라 검증된 산출물에서 조립됐는지 고정한다.

UI grounding 테스트와 같은 정신: 그래프의 노드 값(룰 LTV·지역·건수)이 실제
엔진·레지스트리·실측과 어긋나면 그래프가 조용히 거짓말을 하는 것이다.
"""
import json

import pytest

from regimpact import rule_engine
from regimpact.extractor.schema import RegChangeExtraction
from regimpact.graph import Edge, build_graph
from regimpact.graph.build import HUMAN_NODE_ID
from regimpact.impact import analyze_portfolio, build_portfolio
from regimpact.policy import load_registry
from regimpact.tc_generator import run_regression

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RUN = REPO / "docs" / "eval" / "runs" / "run_cli_sonnet5_v2.json"


@pytest.fixture(scope="module")
def graph():
    payload = json.loads(RUN.read_text(encoding="utf-8"))
    extraction = RegChangeExtraction.from_dict(payload["extraction"])
    impact = analyze_portfolio(build_portfolio(size=400, seed=7), seed=7)
    regression = run_regression()
    return build_graph(extraction, impact, regression), extraction, impact, regression


def test_every_edge_has_provenance_and_endpoints(graph):
    g, *_ = graph
    ids = g.node_ids()
    for e in g.edges:
        assert e.provenance.strip(), f"{e.source}→{e.target} provenance 없음"
        assert e.source in ids and e.target in ids


def test_provenance_is_constructor_enforced():
    """빈 provenance 는 생성 자체가 거부된다 — 문서 약속이 아니라 코드 강제."""
    with pytest.raises(ValueError):
        Edge(source="a", target="b", kind="decides", provenance="  ")


def test_rule_nodes_match_engine_constants(graph):
    """룰 노드의 before→after 값은 엔진 상수에서 온다 — 다른 값이 있으면 환각."""
    g, *_ = graph
    allowed = {f"{v:.0%}" for v in (
        rule_engine.LTV_BASELINE, rule_engine.LTV_REGULATED_STANDARD,
        rule_engine.LTV_FIRST_HOME, rule_engine.LTV_REAL_DEMAND,
        rule_engine.LTV_OWNER, rule_engine.LTV_MULTI)} | {"기준없음"}
    import re
    for n in g.nodes:
        if n.type != "rule" or n.id == HUMAN_NODE_ID:
            continue
        for token in re.findall(r"\d+%|기준없음", n.sub):
            assert token in allowed, f"{n.id}: 엔진에 없는 값 {token}"


def test_segment_edge_weights_sum_to_portfolio(graph):
    """룰→세그먼트 엣지 가중치 합 = 포트폴리오 전체 건수 (한 건도 잃지 않는다)."""
    g, _, impact, _ = graph
    total = sum(e.weight for e in g.edges if e.kind == "decides")
    assert total == len(impact.impacts)


def test_human_path_is_not_silently_dropped(graph):
    """rule_id 없는 건(사람·수동 경로)이 그래프에서 사라지면 자동화율이 과장된다."""
    g, *_ = graph
    assert any(e.source == HUMAN_NODE_ID and e.kind == "decides" for e in g.edges)


def test_regions_come_from_policy_registry(graph):
    g, *_ = graph
    registry_codes = set()
    for p in load_registry().sorted_by_effective():
        registry_codes |= {d.region_code for d in p.region_deltas}
    for n in g.nodes:
        if n.type == "region" and n.id != "REGIONS_PRIOR":
            assert n.id in registry_codes, f"정책 DB에 없는 지역 {n.id}"


def test_no_hallucinated_region_names(graph):
    """Stitch 사고(2026-08-10)의 환각 지역명이 그래프에 없다."""
    g, *_ = graph
    blob = json.dumps(g.to_dict(), ensure_ascii=False)
    for bad in ("세종", "부산", "해운대", "SEJONG", "BUSAN"):
        assert bad not in blob


def test_tc_edges_come_from_actual_runs(graph):
    """룰→회귀 엣지 가중치 합 = 실제 실행된 케이스 수."""
    g, _, _, regression = graph
    total = sum(e.weight for e in g.edges if e.kind == "verifies")
    assert total == regression.total
