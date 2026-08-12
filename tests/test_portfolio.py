"""층화 합성 골드셋(포트폴리오) 테스트.

검증 축:
  1. 결정성 — generate_portfolio()는 재현 가능(case_id·category·split 동일). freeze 매니페스트와 일치.
  2. 분할 규율 — 모든 케이스가 DEV/LOCKED/CHALLENGE 중 하나, 합=전체, CHALLENGE 하드 가중.
  3. 카테고리 커버리지 — 6개 실패모드 전부 존재.
  4. 차등 검증 — 전 포트폴리오가 독립 오라클과 100% 일치(큰 분모에서도).
  5. mutation 민감도 — 엔진에 버그를 심으면 큰 골드셋이 실패로 잡아낸다(분모 확대의 이빨).
"""
import json
from pathlib import Path

from regimpact import rule_engine
from regimpact.tc_generator import (
    Category,
    cases_in_split,
    category_counts,
    generate_portfolio,
    run_regression,
    split_counts,
)

REPO = Path(__file__).resolve().parents[1]
MANIFEST = REPO / "docs" / "eval" / "goldset_manifest.json"
_SPLITS = {"DEV", "LOCKED", "CHALLENGE"}
_HARD = {"EXCEPTION", "GRANDFATHERING", "BOUNDARY", "CONFLICT"}


# ---------- 결정성 ----------
def test_portfolio_is_deterministic():
    a = generate_portfolio()
    b = generate_portfolio()
    assert [c.case_id for c in a] == [c.case_id for c in b]
    assert [(c.category.value, c.split) for c in a] == [(c.category.value, c.split) for c in b]


def test_case_ids_unique():
    cases = generate_portfolio()
    ids = [c.case_id for c in cases]
    assert len(ids) == len(set(ids))


def test_freeze_manifest_matches_generator():
    """커밋된 매니페스트가 생성기 출력과 일치(골드셋 freeze 무결성, LOCKED §0-5)."""
    cases = generate_portfolio()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    gen = [{"case_id": c.case_id, "category": c.category.value, "split": c.split} for c in cases]
    assert manifest["cases"] == gen
    assert manifest["total"] == len(cases)


# ---------- 분할 규율 ----------
def test_every_case_has_valid_split():
    cases = generate_portfolio()
    assert all(c.split in _SPLITS for c in cases)
    counts = split_counts(cases)
    assert sum(counts.values()) == len(cases)


def test_challenge_weights_hard_categories():
    """CHALLENGE 내 하드 카테고리 비율 > 이지 카테고리 비율(브리프 §11 가중)."""
    cases = generate_portfolio()
    hard = [c for c in cases if c.category.value in _HARD]
    easy = [c for c in cases if c.category.value not in _HARD]
    hard_ch = sum(1 for c in hard if c.split == "CHALLENGE") / len(hard)
    easy_ch = sum(1 for c in easy if c.split == "CHALLENGE") / len(easy)
    assert hard_ch > easy_ch


def test_cases_in_split_filters():
    cases = generate_portfolio()
    dev = cases_in_split(cases, "DEV")
    assert dev and all(c.split == "DEV" for c in dev)
    assert len(dev) == split_counts(cases)["DEV"]


# ---------- 카테고리 커버리지 ----------
def test_all_categories_present():
    counts = category_counts(generate_portfolio())
    for cat in Category:
        assert counts[cat.value] > 0, f"카테고리 누락: {cat.value}"


# ---------- 차등 검증 ----------
def test_full_portfolio_matches_oracle():
    cases = generate_portfolio()
    report = run_regression(cases)
    assert report.total >= 150, "골드셋이 seed보다 충분히 커야 함(분모 확대)"
    assert report.pass_rate == 1.0, [f.case.case_id for f in report.failures][:10]
    # 분할별로도 100%
    for split, (p, n, rate) in report.pass_rate_by_split().items():
        assert rate == 1.0, f"{split} 실패"


# ---------- mutation 민감도 ----------
def test_portfolio_catches_engine_mutation(monkeypatch):
    """엔진 상수를 오염(규제 표준 40%→45%)시키면 큰 골드셋이 회귀 실패로 잡는다."""
    monkeypatch.setattr(rule_engine, "LTV_REGULATED_STANDARD", 0.45)
    report = run_regression(generate_portfolio())
    assert report.pass_rate < 1.0
    assert any("max_ltv" in " ".join(f.mismatches) for f in report.failures)
