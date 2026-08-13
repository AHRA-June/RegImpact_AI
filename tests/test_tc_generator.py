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
    all_strata,
    expected_outcome,
    format_report,
    generate_all,
    generate_portfolio,
    portfolio_coverage,
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
def test_oracle_does_not_import_rule_engine():
    # 오라클 모듈이 엔진/지역/경과 구현을 import 하지 않아야 진짜 '챌린저'다.
    # (docstring 언급이 아니라 실제 import 문을 AST로 검사한다.)
    import ast
    import inspect

    tree = ast.parse(inspect.getsource(oracle_mod))
    forbidden = {"rule_engine", "regions", "grandfathering"}
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[-1])
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name.split(".")[-1])
    leak = forbidden & imported
    assert not leak, f"오라클이 엔진 구현을 import 함(독립성 위반): {leak}"


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


# ---------- 층화 합성 포트폴리오 (Phase 2 확대) ----------
def test_portfolio_is_deterministic():
    """같은 (target_n, seed) 는 동일 포트폴리오(case_id + 입력)를 만든다."""
    a = [(c.case_id, c.app) for c in generate_portfolio(target_n=1000, seed=42)]
    b = [(c.case_id, c.app) for c in generate_portfolio(target_n=1000, seed=42)]
    assert a == b


def test_portfolio_seed_changes_inputs():
    a = [c.app for c in generate_portfolio(target_n=1000, seed=1)]
    b = [c.app for c in generate_portfolio(target_n=1000, seed=2)]
    assert a != b


def test_portfolio_covers_all_strata_and_categories():
    cases = generate_portfolio(target_n=3000)
    cov = portfolio_coverage(cases)
    # 432 strata 전수 커버 (커버리지가 성공 기준 — metrics_spec)
    assert cov["strata_hit"] == len(all_strata()) == 432
    # 모든 리포트 카테고리 등장
    assert set(cov["by_category"]) == {c.value for c in Category}
    # 규모는 target 근처
    assert 2500 <= cov["total"] <= 3500


def test_portfolio_regression_100_percent():
    """수천 규모 층화 포트폴리오에서도 엔진이 명세 오라클과 100% 일치."""
    report = run_regression(generate_portfolio(target_n=3000))
    assert report.pass_rate == 1.0, format_report(report)
    assert report.total >= 2500
    # 판정 관련 카테고리가 실제로 존재(자명 SCOPE만이 아님)
    by = report.pass_rate_by_category()
    for cat in ("GRANDFATHERING", "CONFLICT", "BOUNDARY", "BASELINE"):
        assert cat in by and by[cat][1] > 0


def test_portfolio_mutation_power_exceeds_seed_set(monkeypatch):
    """유주택 LTV 상수 변조 시, 포트폴리오가 seed 30건보다 훨씬 많은 실패를 잡는다.

    scale-up의 가치(더 넓은 결함 검출 표면)를 정량 실증한다."""
    portfolio = generate_portfolio(target_n=3000)   # 변조 전에 케이스 고정(입력 불변)
    seed_cases = generate_all()
    monkeypatch.setattr(rule_engine, "LTV_OWNER", 0.10)  # 유주택 0% → 10% 버그 주입

    seed_fail = len(run_regression(seed_cases).failures)
    port_fail = len(run_regression(portfolio).failures)
    assert seed_fail >= 1                      # seed 도 잡긴 함
    assert port_fail > seed_fail * 10          # 포트폴리오는 훨씬 넓게 잡음


# ---------- 충돌 케이스가 명세 주석(spec_note)을 보존 ----------
def test_conflict_owner_first_home_carries_spec_note():
    case = next(c for c in generate_all() if c.case_id == "CFL-04")
    assert case.spec_note is not None
    assert "§H" in case.spec_note
    # §H 권위 기준: 유주택 short-circuit → 0%
    assert case.expected.max_ltv == 0.0
    # 엔진도 동일해야 함
    assert evaluate(case.app).max_ltv == 0.0
