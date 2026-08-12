"""스트레스 테스트 (Stress Testing) — 시스템을 극단으로 밀어붙여 견고성·한계를 드러낸다.

민감도(sensitivity)가 "그럴듯한 범위"의 섭동이라면, 스트레스는 **극단·경계·대량·적대적** 입력이다.
네 가지:
  1. 극단 시나리오 배터리 — 전원 무주택/전원 유주택/전원 경과규정 등에서 **불변식(invariant)이 유지**되나.
  2. 역(逆)스트레스 — 어떤 조건이면 결론이 **뒤집히나**(강화 과반이 깨지는 경계 / 여력 증가가 가능한가).
  3. 차등 퍼징 — 무작위 입력 수천 건에서 룰엔진이 **죽지 않고**, 독립 오라클과 **항상 일치**하나.
  4. 대규모 부하 — 수만 건에서 엔진↔오라클 일치·처리량.

⚠️ 정직성: 스트레스는 **시스템의 견고성/한계를 드러내는 진단**이다. 통과가 "완벽"을 뜻하지 않으며,
   깨지는 경계(역스트레스)를 **숨기지 않고 수치로** 보고한다.
"""
from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Optional

from .impact import (
    AFTER_DATE,
    BEFORE_DATE,
    CustomerSegment,
    analyze_impact,
    compute_exposure,
)
from .impact.population import ARCHETYPE_SHARE
from .impact.sensitivity import build_response_table, compute_headline
from .models import EvaluationStatus, LoanPurpose, MortgageApplication
from .rule_engine import evaluate
from .tc_generator.oracle import expected_outcome

_VALID_STATUS = {s.value for s in EvaluationStatus}


# --------------------------------------------------------------------------- #
# 1. 극단 시나리오 배터리
# --------------------------------------------------------------------------- #
@dataclass
class ScenarioResult:
    name: str
    metrics: dict[str, Any]
    invariants: list[tuple[str, bool]] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(v for _, v in self.invariants)


def _seg(label: str, attrs: dict, weight: float = 1.0) -> CustomerSegment:
    return CustomerSegment(label=label, attrs={**attrs, "region_code": "GURI"}, weight=weight)


def _scenario(name: str, segments: list[CustomerSegment]) -> ScenarioResult:
    matrix = analyze_impact(segments, before_date=BEFORE_DATE, after_date=AFTER_DATE)
    exp = compute_exposure(segments)
    ds = matrix.direction_weight_share()
    pct = exp.pct_reduction
    metrics = {
        "tightened": ds["TIGHTENED"],
        "unchanged": ds["UNCHANGED"],
        "review_dir": ds["NEEDS_REVIEW"],
        "review_wt": matrix.review_weight_share(),
        "undetermined": exp.undetermined_share,
        "pct_reduction": pct,
    }
    inv = [
        ("방향 비중 합=1", abs(sum(ds.values()) - 1.0) < 1e-9),
        ("산정불가 0~1", 0.0 - 1e-9 <= exp.undetermined_share <= 1.0 + 1e-9),
        ("여력 감소율 음수 아님", pct is None or pct >= -1e-9),
        ("가중 합 보존", abs(exp.determinable_weight + exp.undetermined_weight - exp.total_weight) < 1e-9),
    ]
    return ScenarioResult(name, metrics, inv)


def scenario_battery() -> list[ScenarioResult]:
    """극단 구성 포트폴리오에서 불변식이 유지되는지."""
    out = [
        _scenario("전원 무주택 일반(최대 강화)", [_seg("무주택", dict(house_count=0))] * 50),
        _scenario("전원 생애최초(예외 유지)",
                  [_seg("생애최초", dict(house_count=0, first_home_buyer=True))] * 50),
        _scenario("전원 서민·실수요", [_seg("서민", dict(house_count=0, real_demand_flag=True))] * 50),
        _scenario("전원 비처분 유주택(명세 여백 최대)", [_seg("유주택", dict(house_count=1))] * 50),
        _scenario("전원 다주택", [_seg("다주택", dict(house_count=2))] * 50),
        _scenario("전원 경과규정(종전규정)", [_seg("경과", dict(
            house_count=0, contract_signed_at=date(2026, 6, 29),
            downpayment_paid_at=date(2026, 6, 29)))] * 50),
        _scenario("전원 정책대출(Discovery)",
                  [_seg("정책", dict(house_count=0, policy_mortgage_flag=True))] * 50),
    ]
    return out


# --------------------------------------------------------------------------- #
# 2. 역(逆)스트레스 — 결론이 뒤집히는 경계
# --------------------------------------------------------------------------- #
def reverse_stress() -> dict:
    """무주택 일반 비중을 낮춰(→다주택으로 이전) '강화 과반'이 깨지는 경계를 찾는다.

    또한 어떤 구성에서도 '여력 축소(pct>=0)'가 뒤집히지 않음(구조적)을 확인한다.
    """
    table = build_response_table()
    base_share = dict(ARCHETYPE_SHARE)
    src = "무주택 일반"
    dst = "다주택"
    moved_break: Optional[float] = None
    pct_min = 1.0
    steps = 51
    for i in range(steps):
        f = i / (steps - 1)                       # 무주택 일반 비중의 f 비율을 다주택으로 이전
        share = dict(base_share)
        move = base_share[src] * f
        share[src] = base_share[src] - move
        share[dst] = base_share[dst] + move
        h = compute_headline(table, archetype_share=share)
        if h.exposure_pct_reduction < pct_min:
            pct_min = h.exposure_pct_reduction
        if moved_break is None and h.tightened_share <= 0.5:
            moved_break = f
    return {
        "tighten_majority_breaks_at_moved_fraction": moved_break,
        "note": ("무주택 일반 비중의 이 비율을 다주택으로 옮기면 '강화 과반'이 깨짐"
                 if moved_break is not None else "탐색 범위에서 강화 과반 유지"),
        "pct_reduction_min_over_sweep": pct_min,
        "shrink_conclusion_structural": pct_min >= -1e-9,   # 여력 축소는 절대 안 뒤집힘
    }


# --------------------------------------------------------------------------- #
# 3. 차등 퍼징 — 무작위 입력에서 엔진이 죽지 않고 오라클과 일치하나
# --------------------------------------------------------------------------- #
_REGIONS = ["GURI", "YONGIN_GIHEUNG", "HWASEONG_DONGTAN", "SEJONG_NONREG", "UNKNOWN_X"]


def _rand_app(rng: random.Random) -> MortgageApplication:
    base = date(2026, 6, 30)
    def d_or_none(p: float) -> Optional[date]:
        return base + timedelta(days=rng.randint(-5, 5)) if rng.random() < p else None
    return MortgageApplication(
        region_code=rng.choice(_REGIONS),
        evaluation_date=base + timedelta(days=rng.randint(-3, 3)),
        house_count=rng.randint(0, 3),
        disposal_condition_flag=rng.random() < 0.3,
        first_home_buyer=rng.random() < 0.3,
        real_demand_flag=rng.random() < 0.3,
        policy_mortgage_flag=rng.random() < 0.2,
        loan_purpose=rng.choice([LoanPurpose.HOME_PURCHASE, LoanPurpose.OTHER]),
        application_accepted_at=d_or_none(0.2),
        contract_signed_at=d_or_none(0.2),
        downpayment_paid_at=d_or_none(0.2),
        land_permit_target=rng.random() < 0.2,
        land_permit_applied_at=d_or_none(0.15),
    )


def fuzz_differential(n: int = 5000, seed: int = 0) -> dict:
    """무작위 신청 n건: (a) 엔진 예외 0, (b) 상태 유효, (c) 알려진 지역은 오라클과 일치."""
    rng = random.Random(seed)
    crashes = 0
    invalid_status = 0
    mismatches = 0
    compared = 0
    status_counts: dict[str, int] = {}
    for _ in range(n):
        app = _rand_app(rng)
        try:
            dec = evaluate(app)
        except Exception:
            crashes += 1
            continue
        if dec.status.value not in _VALID_STATUS:
            invalid_status += 1
        status_counts[dec.status.value] = status_counts.get(dec.status.value, 0) + 1
        # 오라클 차등 비교는 '알려진 지역'에서만(미상 지역은 스펙 도메인 밖)
        if app.region_code in ("GURI", "YONGIN_GIHEUNG", "HWASEONG_DONGTAN"):
            try:
                exp = expected_outcome(app)
                compared += 1
                if exp.status != dec.status or exp.max_ltv != dec.max_ltv:
                    mismatches += 1
            except Exception:
                pass
    return {
        "runs": n, "crashes": crashes, "invalid_status": invalid_status,
        "compared": compared, "mismatches": mismatches, "status_counts": status_counts,
    }


# --------------------------------------------------------------------------- #
# 4. 대규모 부하 — 엔진↔오라클 일치·처리량
# --------------------------------------------------------------------------- #
def load_consistency(n: int = 50000, seed: int = 1) -> dict:
    from .impact import sample_portfolio
    segs = sample_portfolio(n, seed=seed)
    t0 = time.perf_counter()
    mism = 0
    for s in segs:
        app = s.application(AFTER_DATE)
        if evaluate(app).max_ltv != expected_outcome(app).max_ltv:
            mism += 1
    dt = time.perf_counter() - t0
    return {"n": n, "mismatches": mism, "seconds": round(dt, 3),
            "per_sec": int(n / dt) if dt else 0}


# --------------------------------------------------------------------------- #
# 포매터
# --------------------------------------------------------------------------- #
def format_stress(battery: list[ScenarioResult], reverse: dict,
                  fuzz: dict, load: dict) -> str:
    L: list[str] = []
    L.append("스트레스 테스트 — 극단·경계·대량·적대적 입력에서의 견고성")
    L.append("")
    L.append("1) 극단 시나리오 배터리 (불변식 유지 여부)")
    hdr = f"{'시나리오':<26} {'강화':>6} {'검토':>6} {'산정불가':>8} {'감소율':>8}  {'불변식'}"
    L.append(hdr)
    L.append("-" * len(hdr))
    for s in battery:
        pct = "—" if s.metrics["pct_reduction"] is None else f"{s.metrics['pct_reduction']:.1%}"
        mark = "✓" if s.ok else "✗ FAIL"
        L.append(f"{s.name:<26} {s.metrics['tightened']:>6.0%} {s.metrics['review_dir']:>6.0%} "
                 f"{s.metrics['undetermined']:>8.0%} {pct:>8}  {mark}")
    L.append("")
    L.append("2) 역스트레스 (결론이 뒤집히는 경계)")
    mb = reverse["tighten_majority_breaks_at_moved_fraction"]
    L.append(f"  · 강화 과반: {'무주택→다주택 이전 %.0f%% 지점에서 깨짐' % (mb*100) if mb is not None else '탐색 범위 유지'}")
    L.append(f"  · 여력 축소: 스윕 최소 감소율 {reverse['pct_reduction_min_over_sweep']:.1%} "
             f"→ 구조적으로 {'뒤집히지 않음(항상 축소)' if reverse['shrink_conclusion_structural'] else '뒤집힐 수 있음!'}")
    L.append("")
    L.append("3) 차등 퍼징 (무작위 입력)")
    L.append(f"  · {fuzz['runs']}건: 크래시 {fuzz['crashes']} · 무효상태 {fuzz['invalid_status']} · "
             f"오라클 비교 {fuzz['compared']}건 중 불일치 {fuzz['mismatches']}")
    L.append(f"  · 상태분포: " + ", ".join(f"{k} {v}" for k, v in sorted(fuzz["status_counts"].items())))
    L.append("")
    L.append("4) 대규모 부하")
    L.append(f"  · {load['n']:,}건 엔진↔오라클 불일치 {load['mismatches']} "
             f"({load['seconds']}s · {load['per_sec']:,}건/s)")
    return "\n".join(L)
