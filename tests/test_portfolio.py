"""층화 합성 포트폴리오 테스트 — 룰엔진 평가셋 100~120건 통계화.

검증: ①규모 100~120 ②case_id 유일·결정론 ③split 부여·전량 측정 ④엔진↔오라클 100% 일치
⑤카테고리·판정 커버리지 ⑥mutation으로 확장 fixture의 방어력(버그 주입 시 실패 포착).
"""
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from regimpact import rule_engine  # noqa: E402
from regimpact.tc_generator import (  # noqa: E402
    Category,
    Split,
    coverage,
    format_portfolio_stats,
    generate_grid,
    generate_portfolio,
    run_regression,
)


def test_portfolio_size_in_range():
    n = len(generate_portfolio())
    assert 100 <= n <= 120, f"포트폴리오 규모 {n} 이 100~120 밖"


def test_case_ids_unique():
    cases = generate_portfolio()
    assert len({c.case_id for c in cases}) == len(cases)


def test_generation_deterministic():
    """난수 없이 결정론 — 두 번 생성해도 (id, split, status) 동일."""
    a = generate_portfolio()
    b = generate_portfolio()
    ka = [(c.case_id, c.split, c.expected.status.value) for c in a]
    kb = [(c.case_id, c.split, c.expected.status.value) for c in b]
    assert ka == kb


def test_all_categories_present():
    cats = {c.category for c in generate_portfolio()}
    assert cats == set(Category)


def test_all_splits_present_and_assigned():
    cases = generate_portfolio()
    splits = Counter(c.split for c in cases)
    assert set(splits) == {Split.DEV.value, Split.LOCKED.value, Split.CHALLENGE.value}
    assert None not in splits           # 모든 케이스에 split 부여
    assert splits[Split.CHALLENGE.value] == 35   # 적대적 가중 목표


def test_engine_matches_oracle_100_percent():
    """확장 입력공간(106건)에서 엔진↔독립 오라클 전부 일치."""
    rep = run_regression(generate_portfolio())
    assert rep.pass_rate == 1.0
    assert rep.failures == []


def test_pass_rate_by_split_full_measurement():
    """split 전량 측정 — DEV/LOCKED/CHALLENGE 모두 산출되고 100%."""
    rep = run_regression(generate_portfolio())
    by = rep.pass_rate_by_split()
    assert set(by) == {"DEV", "LOCKED", "CHALLENGE"}
    for _sp, (p, n, rate) in by.items():
        assert p == n and rate == 1.0


def test_coverage_breadth():
    """판정 다양성 — 4개 status 전부, reason_code 다수 커버."""
    cov = coverage(generate_portfolio())
    assert cov["distinct_status"] == 4      # DECIDED/OUT_OF_SCOPE/DISCOVERY/NEEDS_HUMAN_REVIEW
    assert cov["distinct_rule_id"] >= 5
    assert cov["distinct_reason_code"] >= 10


def test_stats_report_renders():
    rep = run_regression(generate_portfolio())
    text = format_portfolio_stats(rep)
    assert "Rule Portfolio Stats" in text
    assert "By split" in text
    assert "CHALLENGE" in text
    assert "100.0%" in text


# ---------- mutation: 확장 fixture에 이빨이 있는가 ----------
def test_portfolio_catches_mutated_ltv(monkeypatch):
    """서민실수요 LTV 상수를 60%→65%로 변조하면 포트폴리오 회귀가 실패를 잡아야 한다."""
    monkeypatch.setattr(rule_engine, "LTV_REAL_DEMAND", 0.65)
    rep = run_regression(generate_portfolio())
    assert rep.pass_rate < 1.0, "변조된 엔진인데 확장 fixture가 통과 → 무력함"
    failed_cats = {r.case.category for r in rep.failures}
    assert Category.EXCEPTION in failed_cats


def test_portfolio_catches_mutated_owner_rule(monkeypatch):
    """유주택 0% 규칙을 40%로 변조하면 회귀가 실패를 잡아야 한다."""
    monkeypatch.setattr(rule_engine, "LTV_OWNER", 0.40)
    rep = run_regression(generate_portfolio())
    assert rep.pass_rate < 1.0


# ---------- 대규모 조합 격자 (수천 건) ----------
def test_grid_size_thousands():
    n = len(generate_grid())
    assert n >= 3000, f"격자 규모 {n} 이 수천 건 미만"


def test_grid_ids_unique_and_deterministic():
    a = generate_grid()
    b = generate_grid()
    assert len({c.case_id for c in a}) == len(a)
    ka = [(c.case_id, c.split, c.expected.status.value) for c in a]
    kb = [(c.case_id, c.split, c.expected.status.value) for c in b]
    assert ka == kb


def test_grid_engine_matches_oracle_100_percent():
    """수천 건 넓은 입력공간에서 엔진↔독립 오라클 전부 일치."""
    rep = run_regression(generate_grid())
    assert rep.pass_rate == 1.0
    assert rep.failures == []


def test_grid_all_splits_measured():
    rep = run_regression(generate_grid())
    by = rep.pass_rate_by_split()
    assert set(by) == {"DEV", "LOCKED", "CHALLENGE"}
    for _sp, (p, n, rate) in by.items():
        assert p == n and rate == 1.0


def test_grid_coverage_full_status():
    cov = coverage(generate_grid())
    assert cov["distinct_status"] == 4
    assert cov["distinct_reason_code"] >= 10


def test_grid_catches_mutated_grandfathering(monkeypatch):
    """경과규정을 항상 미해당으로 변조하면 격자 회귀가 실패를 잡아야 한다."""
    from regimpact import grandfathering

    monkeypatch.setattr(grandfathering, "is_grandfathered", lambda app: (False, None))
    monkeypatch.setattr(rule_engine, "is_grandfathered", lambda app: (False, None))
    rep = run_regression(generate_grid())
    assert rep.pass_rate < 1.0
    assert Category.GRANDFATHERING in {r.case.category for r in rep.failures}
