"""TC Generator + Rule-Regression 테스트.

두 가지를 검증한다:
  1. 생성기·오라클·회귀 하네스의 계약(각 카테고리 존재, 100% 통과, 독립성).
  2. **mutation test** — 룰엔진에 의도적 버그를 심으면 회귀가 실패로 잡아내는지.
     (회귀 fixture가 tautology가 아니라 '이빨이 있다'는 증거. Model Risk 관점의 핵심.)
"""
from datetime import date

import pytest

from regimpact import EvaluationStatus, LoanPurpose, MortgageApplication, evaluate
from regimpact.tc_generator import (
    Category,
    expected_outcome,
    format_report,
    generate_all,
    run_regression,
)
from regimpact.tc_generator import oracle as oracle_mod
from regimpact import rule_engine


# ---------- 생성기 계약 ----------
def test_generates_cases_in_every_category():
    cases = generate_all()
    cats = {c.category for c in cases}
    assert cats == set(Category), f"누락 카테고리: {set(Category) - cats}"


def test_case_ids_are_unique():
    cases = generate_all()
    ids = [c.case_id for c in cases]
    assert len(ids) == len(set(ids))


def test_generation_is_deterministic():
    a = [(c.case_id, c.app) for c in generate_all()]
    b = [(c.case_id, c.app) for c in generate_all()]
    assert a == b


# ---------- 회귀: 엔진이 명세와 일치 (Rule-regression Pass Rate = 100%) ----------
def test_engine_matches_oracle_100_percent():
    report = run_regression()
    assert report.pass_rate == 1.0, format_report(report)
    assert report.total >= 25


def test_boundary_and_conflict_categories_pass():
    report = run_regression()
    assert report.category_pass_rate(Category.BOUNDARY) == 1.0
    assert report.category_pass_rate(Category.CONFLICT) == 1.0


def test_report_lists_no_failures_when_green():
    report = run_regression()
    assert report.failures == []


# ---------- 오라클 독립성 (회귀가 tautology가 아님을 구조적으로 보증) ----------
def _oracle_imports() -> dict[str, set[str]]:
    """오라클 모듈의 import 를 {모듈: {심볼}} 로 수집 (docstring이 아니라 AST로 검사)."""
    import ast
    import inspect

    tree = ast.parse(inspect.getsource(oracle_mod))
    out: dict[str, set[str]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            out.setdefault(node.module.split(".")[-1], set()).update(
                a.name for a in node.names)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                out.setdefault(alias.name.split(".")[-1], set())
    return out


def test_oracle_does_not_import_engine_judgment_modules():
    """판정 구현(rule_engine·grandfathering)은 통째로 금지 — 그래야 진짜 '챌린저'다."""
    leak = {"rule_engine", "grandfathering"} & set(_oracle_imports())
    assert not leak, f"오라클이 엔진 판정 구현을 import 함(독립성 위반): {leak}"


def test_oracle_shares_region_data_but_not_region_resolution():
    """지역은 심볼 단위 계약이다 — **데이터**는 공유하되 **해석 함수**는 공유하지 않는다.

    전국 241개 지역표를 오라클에 다시 옮겨 적는 것은 검증가치가 아니라 전사 오류만 늘린다.
    그래서 규제사실 데이터(REGISTRY)는 하나만 두고 공문 원문과 대조해 검증하며
    (`tests/test_regions.py`), 시점 해석 로직만 오라클이 독립 재구현한다.
    """
    symbols = _oracle_imports().get("regions", set())
    allowed = {"REGISTRY", "canonical_code"}
    assert symbols <= allowed, f"오라클이 허용되지 않은 지역 심볼을 import 함: {symbols - allowed}"
    assert "resolve_region_status" not in symbols, (
        "오라클이 엔진의 지역 해석 함수를 쓰면 지역 시점 판정이 tautology가 된다")


def test_oracle_computes_known_anchor_values():
    # 오라클 자체가 명세 앵커를 맞히는지 (엔진과 무관하게 독립 확인).
    app = MortgageApplication(region_code="GURI", evaluation_date=date(2026, 7, 2),
                              house_count=0, first_home_buyer=True)
    exp = expected_outcome(app)
    assert exp.status == EvaluationStatus.DECIDED
    assert exp.max_ltv == 0.70
    assert "EXCEPTION_FIRST_HOME" in exp.must_include_reasons


# ---------- mutation test: fixture에 이빨이 있는가 ----------
def test_regression_catches_mutated_ltv_constant(monkeypatch):
    """규제 표준 LTV 상수를 40%→50%로 변조하면 회귀가 실패를 잡아야 한다."""
    monkeypatch.setattr(rule_engine, "LTV_REGULATED_STANDARD", 0.50)
    report = run_regression()
    assert report.pass_rate < 1.0, "변조된 엔진인데 회귀가 통과 → fixture가 무력함"
    # 무주택 일반(P7) 관련 케이스가 실패로 잡혀야 함
    failed_ids = {r.case.case_id for r in report.failures}
    assert any("EXC-01" == fid or fid.startswith("BND-HC") for fid in failed_ids)


def test_regression_catches_mutated_priority(monkeypatch):
    """우선순위 버그(경과규정 무시)를 심으면 GRANDFATHERING 케이스가 실패해야 한다."""
    from regimpact import grandfathering

    # 경과규정을 항상 미해당으로 변조 → 종전규정 70%가 신규 40%로 잘못 판정됨
    monkeypatch.setattr(grandfathering, "is_grandfathered",
                        lambda app: (False, None))
    # rule_engine 은 import 시점에 심볼을 바인딩하므로 그쪽도 패치
    monkeypatch.setattr(rule_engine, "is_grandfathered",
                        lambda app: (False, None))
    report = run_regression()
    assert report.pass_rate < 1.0
    failed_cats = {r.case.category for r in report.failures}
    assert Category.GRANDFATHERING in failed_cats


# ---------- 입력 무결성 게이트 (Q8 확정 2026-08-18) ----------
def test_owner_plus_first_home_is_a_contradiction_not_a_zero_percent_decision():
    """§E-139 는 우선순위 규칙이 아니라 입력 유효성 규칙이다.

    0%를 자동으로 내주면 '정상 입력이고 답이 0%'와 '입력이 모순인데 우연히 0%'를 구분할 수 없다.
    게다가 0%는 대출 거절이고, 틀린 쪽이 first_home_buyer 플래그였다면 정답은 70%다.
    """
    case = next(c for c in generate_all() if c.case_id == "CFL-04")
    assert case.expected.status == EvaluationStatus.NEEDS_HUMAN_REVIEW
    assert case.expected.max_ltv is None
    assert "CONTRADICTION_OWNER_FIRST_HOME" in case.expected.must_include_reasons

    actual = evaluate(case.app)
    assert actual.status == EvaluationStatus.NEEDS_HUMAN_REVIEW
    assert actual.max_ltv is None
    assert "CONTRADICTION_OWNER_FIRST_HOME" in actual.reason_codes


def test_disposal_condition_plus_first_home_stays_valid():
    """§E-138 이 유효 조합으로 명시 — 게이트가 여기까지 잡아버리면 과잉이다."""
    case = next(c for c in generate_all() if c.case_id == "CFL-12")
    assert evaluate(case.app).max_ltv == 0.70


def test_contradiction_gate_outranks_grandfathering_but_not_scope():
    """게이트 위치: P0/P0b 뒤, P1 앞."""
    gf = next(c for c in generate_all() if c.case_id == "CFL-10")     # 경과규정 + 모순
    assert evaluate(gf.app).status == EvaluationStatus.NEEDS_HUMAN_REVIEW
    assert evaluate(gf.app).grandfathering_applied is False

    policy = next(c for c in generate_all() if c.case_id == "CFL-11")  # 정책대출 + 모순
    assert evaluate(policy.app).status == EvaluationStatus.DISCOVERY
