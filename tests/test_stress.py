"""스트레스 테스트 하네스 테스트.

검증 축:
  1. 배터리 — 모든 극단 시나리오에서 불변식 유지, 대표 수치 확인.
  2. 역스트레스 — 여력 축소는 구조적으로 안 뒤집힘, 강화 과반 경계 존재.
  3. 차등 퍼징 — 크래시 0·무효상태 0·오라클 불일치 0(결정적 seed).
  4. 부하 — 대량에서 엔진↔오라클 일치.
"""
from regimpact.stress import (
    fuzz_differential,
    load_consistency,
    reverse_stress,
    scenario_battery,
)


def test_battery_all_invariants_hold():
    b = scenario_battery()
    for s in b:
        assert s.ok, f"{s.name}: {s.invariants}"


def test_battery_key_scenarios():
    by = {s.name.split("(")[0].strip(): s for s in scenario_battery()}
    # 전원 무주택 = 최대 강화, 감소율 (70-40)/70
    nh = by["전원 무주택 일반"]
    assert abs(nh.metrics["tightened"] - 1.0) < 1e-9
    assert abs(nh.metrics["pct_reduction"] - (30 / 70)) < 1e-6
    # 전원 유주택 = 산정불가 100%, 감소율 None
    ow = by["전원 비처분 유주택"]
    assert abs(ow.metrics["undetermined"] - 1.0) < 1e-9
    assert ow.metrics["pct_reduction"] is None


def test_reverse_stress_shrink_is_structural():
    r = reverse_stress()
    assert r["shrink_conclusion_structural"] is True
    assert r["pct_reduction_min_over_sweep"] >= -1e-9    # 여력은 절대 증가하지 않음
    mb = r["tighten_majority_breaks_at_moved_fraction"]
    assert mb is None or 0.0 < mb <= 1.0


def test_fuzz_no_crash_and_oracle_agreement():
    f = fuzz_differential(n=3000, seed=0)
    assert f["crashes"] == 0
    assert f["invalid_status"] == 0
    assert f["mismatches"] == 0
    assert f["compared"] > 0
    # 여러 상태가 실제로 나와야(경로 커버)
    assert len(f["status_counts"]) >= 3


def test_fuzz_deterministic():
    assert fuzz_differential(n=1000, seed=7) == fuzz_differential(n=1000, seed=7)


def test_load_consistency_small():
    r = load_consistency(n=3000, seed=1)
    assert r["mismatches"] == 0
    assert r["n"] == 3000
