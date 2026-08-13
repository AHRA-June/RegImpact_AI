"""골드 평가셋 테스트 — 스키마·결정적 채점·근거 무결성·LOCKED §4 통제.

핵심:
  - scenario 아이템의 골드 정답이 검증된 룰엔진과 일치(회귀 가드).
  - source_quote가 원문에 verbatim 존재(근거 무결성).
  - 전 항목 AI_DRAFT(사람확정 전) — LOCKED §4.
  - load_goldset 기본값은 DEV만(LOCKED/CHALLENGE 누수 방지 — 브리프 §12).
"""
from regimpact.extractor import load_sources
from regimpact.goldset import (
    CHALLENGE_WEIGHTED,
    GoldCategory,
    Split,
    Status,
    check_goldset_grounding,
    coverage,
    load_goldset,
    load_split,
    score_scenario_items,
)


def _dev_and_challenge():
    return load_goldset(splits=[Split.DEV, Split.CHALLENGE])


# ---------- 스키마 / 로드 ----------
def test_goldset_loads_and_ids_unique():
    items = _dev_and_challenge()
    assert len(items) >= 30
    ids = [it.item_id for it in items]
    assert len(ids) == len(set(ids)), "중복 item_id"
    for it in items:
        assert it.question and it.gold_answer and it.policy_version


def test_load_goldset_defaults_to_dev_only():
    """개발 중 LOCKED/CHALLENGE 미개봉 — 기본 로드는 DEV만(누수 방지)."""
    items = load_goldset()
    assert items
    assert {it.split for it in items} == {Split.DEV}


# ---------- 결정적 채점 (LOCKED §4 금지선 준수) ----------
def test_scenario_gold_matches_rule_engine_100_percent():
    """scenario 골드 정답이 검증된 룰엔진과 100% 일치(순환 아님: 골드=사람이 원문 확정)."""
    items = _dev_and_challenge()
    score = score_scenario_items(items)
    assert score.total >= 25
    assert score.accuracy == 1.0, [f"{r.item.item_id}: {r.detail}" for r in score.failures]


def test_escalation_recall_and_precision_perfect():
    score = score_scenario_items(_dev_and_challenge())
    esc = score.escalation_metrics()
    assert esc["recall"] == 1.0
    assert esc["precision"] == 1.0
    assert esc["tp"] >= 3      # escalation 기대 scenario가 실제로 존재


# ---------- 근거 무결성 ----------
def test_goldset_source_quotes_are_grounded():
    items = _dev_and_challenge()
    g = check_goldset_grounding(items, load_sources())
    assert g.total >= 5
    assert g.rate == 1.0, [u.item_id for u in g.ungrounded]


# ---------- LOCKED §4 통제 ----------
def test_all_items_are_ai_draft_until_human_confirms():
    for it in _dev_and_challenge():
        assert it.status == Status.AI_DRAFT, f"{it.item_id} 확정됨 — 사용자 검수 없이 확정 금지"


# ---------- 커버리지 / CHALLENGE 가중 ----------
def test_coverage_reports_progress_and_categories():
    items = _dev_and_challenge()
    cov = coverage(items)
    assert cov["target_total"] == 115
    # 10개 카테고리 중 대다수가 등장(실패모드 커버리지)
    assert len(cov["by_category"]) >= 8


def test_challenge_split_emphasizes_weighted_categories():
    challenge = load_split(Split.CHALLENGE)
    assert challenge
    weighted = sum(1 for it in challenge if it.category in CHALLENGE_WEIGHTED)
    # CHALLENGE는 예외·경과·시행일·충돌 가중(브리프 §11)
    assert weighted >= len(challenge) * 0.5


def test_every_scenario_item_has_expected_outcome_fields():
    for it in _dev_and_challenge():
        if it.is_scenario:
            # scenario 아이템은 최소 expected_status 또는 expected_ltv를 명시해야 채점 가능
            assert it.expected_status is not None or it.expected_ltv is not None


# ---------- 전체 골드셋(3 split) 무결성 게이트 (튜닝 아님) ----------
def _all_splits():
    return load_goldset(splits=[Split.DEV, Split.LOCKED, Split.CHALLENGE])


def test_full_goldset_reaches_target_and_is_consistent():
    """115 목표 도달 + scenario 100% 일치 + grounding 100% + 전 항목 AI_DRAFT.

    LOCKED을 로드하지만 '튜닝'이 아니라 골드셋 자체의 무결성 검사(QA 게이트)다."""
    items = _all_splits()
    ids = [it.item_id for it in items]
    assert len(ids) == len(set(ids))          # 전역 item_id 유일
    assert len(items) >= 115                   # 목표 규모 도달

    # scenario 골드가 검증된 룰엔진과 100% 일치
    score = score_scenario_items(items)
    assert score.total >= 80
    assert score.accuracy == 1.0, [f"{r.item.item_id}: {r.detail}" for r in score.failures]

    # 근거(source_quote)가 원문에 100% grounding
    g = check_goldset_grounding(items, load_sources())
    assert g.total >= 20
    assert g.rate == 1.0, [u.item_id for u in g.ungrounded]

    # LOCKED §4: 사용자 확정 전까지 전부 AI_DRAFT
    assert all(it.status == Status.AI_DRAFT for it in items)

    # 10개 카테고리 전부 등장(실패모드 완전 커버리지)
    assert {it.category for it in items} == set(GoldCategory)


def test_challenge_weighted_categories_are_majority_overall():
    """예외·경과·시행일·충돌이 전체에서 큰 비중(브리프 §11 설계철학)."""
    items = _all_splits()
    weighted = sum(1 for it in items if it.category in CHALLENGE_WEIGHTED)
    assert weighted >= len(items) * 0.5
