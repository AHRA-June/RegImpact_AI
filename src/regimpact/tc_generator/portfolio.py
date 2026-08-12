"""층화 합성 포트폴리오 (goldset 확대) — 04_PLAN Phase 2.

seed 케이스(generator.generate_all, ~30건)를 넘어 **입력 차원을 체계적으로 층화 스윕**해
수백 건의 회귀 케이스를 만든다. 목적:
  1) metrics_spec §3 지표의 **분모를 키워** "n=1 정책, 소규모 seed" 한계를 완화(신뢰구간 확보).
  2) LOCKED §0-5: 평가셋을 **DEV / LOCKED TEST / CHALLENGE 3분할**로 분리(개발 중 LOCKED/CHALLENGE 미개봉).

정답(기대값)은 여기서 만들지 않는다 — 각 케이스는 `oracle.expected_outcome`(엔진 미import, 독립
명세 재구현)이 채운다. 따라서 포트폴리오를 아무리 키워도 회귀는 tautology가 되지 않는다.

분할 규칙:
  - **결정적**(hashlib.sha256(case_id) 기반) → 재현 가능, 프로세스 무관(파이썬 hash()는 salt됨 → 사용 금지).
  - **CHALLENGE 가중**: EXCEPTION/GRANDFATHERING/BOUNDARY/CONFLICT(하드 카테고리)를 CHALLENGE에 더 배분
    (브리프 §11 철학: 적대적 평가 중심). SCOPE/BASELINE은 DEV/LOCKED 비중을 높인다.
"""
from __future__ import annotations

import hashlib
from datetime import date

from ..models import LoanPurpose, MortgageApplication
from .generator import Category, GeneratedCase
from .oracle import expected_outcome

# --- 시나리오: (region_code, evaluation_date) → 지역 규제상태·시점 경계 층 ---
_SCENARIOS: dict[str, tuple[str, date]] = {
    "REG":    ("GURI", date(2026, 7, 2)),          # 시행 후 · 규제
    "NONREG": ("GURI", date(2026, 6, 15)),         # 시행 전 · 아직 非규제
    "UNREG":  ("SEOUL_GANGNAM", date(2026, 7, 2)),  # 미등록 지역 · 非규제
    "EFFDAY": ("GURI", date(2026, 7, 1)),          # 효력일 당일 (경계)
    "PREEFF": ("GURI", date(2026, 6, 30)),         # 효력일 전일 (경계)
}

# --- 소유 상태 층 (house_count·처분조건부) ---
_OWNERSHIP: dict[str, dict] = {
    "hc0":     dict(house_count=0),
    "hc1":     dict(house_count=1),                                   # 유주택(비처분)
    "hc1disp": dict(house_count=1, disposal_condition_flag=True),      # 처분조건부 = 무주택 취급
    "hc2":     dict(house_count=2),                                    # 다주택
    "hc3":     dict(house_count=3),
}

# --- 무주택 예외 플래그 층 ---
_EXCEPTIONS: dict[str, dict] = {
    "plain": dict(),
    "fh":    dict(first_home_buyer=True),
    "rd":    dict(real_demand_flag=True),
    "fhrd":  dict(first_home_buyer=True, real_demand_flag=True),       # 충돌 유발
}

# --- 경과규정 이벤트 층 (§F) ---
_GF_CUTOFF = date(2026, 6, 30)
_GRANDFATHER: dict[str, dict] = {
    "none":  dict(),
    "g1in":  dict(application_accepted_at=_GF_CUTOFF),                 # G1 접수 <=6.30 → 종전
    "g1out": dict(application_accepted_at=date(2026, 7, 1)),           # 접수 7.1 → 신규
    "g2":    dict(contract_signed_at=date(2026, 6, 29),
                  downpayment_paid_at=date(2026, 6, 29)),              # G2 계약+계약금
    "g2ndp": dict(contract_signed_at=date(2026, 6, 29)),              # 계약만·계약금 미납 → 불인정
    "g3":    dict(land_permit_target=True,
                  land_permit_applied_at=_GF_CUTOFF,
                  contract_signed_at=date(2026, 7, 10)),              # G3 토허제
}

_HARD_CATEGORIES = frozenset({
    Category.EXCEPTION, Category.GRANDFATHERING, Category.BOUNDARY, Category.CONFLICT,
})


def _is_owner(own_kw: dict) -> bool:
    hc = own_kw.get("house_count", 0)
    if hc >= 2:
        return True
    if hc >= 1 and not own_kw.get("disposal_condition_flag", False):
        return True
    return False


def _categorize(scen: str, own_kw: dict, exc_kw: dict, gf: str,
                policy: bool, purpose: LoanPurpose) -> Category:
    """케이스의 '테스트 의도' 카테고리를 우선순위로 배정(정확히 하나)."""
    if purpose != LoanPurpose.HOME_PURCHASE or policy:
        return Category.SCOPE
    if gf != "none":
        return Category.GRANDFATHERING
    if scen in ("EFFDAY", "PREEFF"):
        return Category.BOUNDARY
    has_exc = exc_kw.get("first_home_buyer") or exc_kw.get("real_demand_flag")
    both_exc = exc_kw.get("first_home_buyer") and exc_kw.get("real_demand_flag")
    if both_exc or (_is_owner(own_kw) and has_exc):
        return Category.CONFLICT
    if scen in ("NONREG", "UNREG"):
        return Category.BASELINE
    return Category.EXCEPTION


def assign_split(case_id: str, category: Category) -> str:
    """case_id·카테고리로 DEV/LOCKED/CHALLENGE를 결정적으로 배정(CHALLENGE 하드 가중)."""
    h = int(hashlib.sha256(case_id.encode("utf-8")).hexdigest(), 16) % 100
    if category in _HARD_CATEGORIES:
        # CHALLENGE 45 / LOCKED 30 / DEV 25
        if h < 45:
            return "CHALLENGE"
        if h < 75:
            return "LOCKED"
        return "DEV"
    # SCOPE·BASELINE: CHALLENGE 15 / LOCKED 40 / DEV 45
    if h < 15:
        return "CHALLENGE"
    if h < 55:
        return "LOCKED"
    return "DEV"


def _make(case_id: str, category: Category, description: str,
          app: MortgageApplication) -> GeneratedCase:
    return GeneratedCase(
        case_id=case_id,
        category=category,
        description=description,
        app=app,
        expected=expected_outcome(app),   # 정답은 오라클에서만
        split=assign_split(case_id, category),
    )


def _app(region: str, when: date, own_kw: dict, exc_kw: dict, gf_kw: dict,
         **extra) -> MortgageApplication:
    return MortgageApplication(region_code=region, evaluation_date=when,
                               **own_kw, **exc_kw, **gf_kw, **extra)


def generate_portfolio() -> list[GeneratedCase]:
    """층화 합성 포트폴리오를 결정적으로 생성한다.

    경과규정(gf)을 **전용 층에 가두어** 카테고리 균형을 유지한다(전체 예외 그리드와 교차하면
    GRANDFATHERING이 폭증하기 때문). 층 구성:
      A. 규제 코어(gf=none, scen=REG): 소유×예외 = 20  → EXCEPTION/CONFLICT
      B. 기준선(gf=none, scen∈{NONREG,UNREG}): 소유×예외 = 40 → BASELINE/CONFLICT
      C. 경계(gf=none, scen∈{EFFDAY,PREEFF}): 소유×예외 = 40 → BOUNDARY/CONFLICT
      D. 경과규정(gf≠none, exc=plain, scen∈{REG,PREEFF}): gf(5)×scen(2)×소유(5) = 50 → GRANDFATHERING
      E. 경과규정×예외 교차(소수): gf∈{g1in,g2,g3}×소유{hc0,hc1,hc2}×예외{fh,rd}, scen=REG = 18
      F. 스코프: 소유×{정책대출,비주택구입} = 10 → SCOPE
    총 178건.
    """
    cases: list[GeneratedCase] = []

    def add(cid: str, scen: str, own_kw: dict, exc_kw: dict, gf_name: str,
            gf_kw: dict) -> None:
        region, when = _SCENARIOS[scen]
        cat = _categorize(scen, own_kw, exc_kw, gf_name, False, LoanPurpose.HOME_PURCHASE)
        cases.append(_make(cid, cat, cid, _app(region, when, own_kw, exc_kw, gf_kw)))

    # A. 규제 코어
    for on, ok in _OWNERSHIP.items():
        for en, ek in _EXCEPTIONS.items():
            add(f"PF-A-REG-{on}-{en}", "REG", ok, ek, "none", {})
    # B. 기준선
    for scen in ("NONREG", "UNREG"):
        for on, ok in _OWNERSHIP.items():
            for en, ek in _EXCEPTIONS.items():
                add(f"PF-B-{scen}-{on}-{en}", scen, ok, ek, "none", {})
    # C. 경계
    for scen in ("EFFDAY", "PREEFF"):
        for on, ok in _OWNERSHIP.items():
            for en, ek in _EXCEPTIONS.items():
                add(f"PF-C-{scen}-{on}-{en}", scen, ok, ek, "none", {})
    # D. 경과규정 전용 층
    for gn in ("g1in", "g1out", "g2", "g2ndp", "g3"):
        for scen in ("REG", "PREEFF"):
            for on, ok in _OWNERSHIP.items():
                add(f"PF-D-{gn}-{scen}-{on}", scen, ok, {}, gn, _GRANDFATHER[gn])
    # E. 경과규정 × 예외 교차(소수)
    for gn in ("g1in", "g2", "g3"):
        for on in ("hc0", "hc1", "hc2"):
            for en in ("fh", "rd"):
                add(f"PF-E-{gn}-{on}-{en}", "REG", _OWNERSHIP[on],
                    _EXCEPTIONS[en], gn, _GRANDFATHER[gn])
    # F. 스코프
    region, when = _SCENARIOS["REG"]
    for on, ok in _OWNERSHIP.items():
        cases.append(_make(f"PF-F-policy-{on}", Category.SCOPE, f"정책대출/{on}",
                           _app(region, when, ok, {}, {}, policy_mortgage_flag=True)))
        cases.append(_make(f"PF-F-other-{on}", Category.SCOPE, f"비주택구입/{on}",
                           _app(region, when, ok, {}, {}, loan_purpose=LoanPurpose.OTHER)))

    seen: set[str] = set()
    for c in cases:
        if c.case_id in seen:
            raise ValueError(f"중복 case_id: {c.case_id}")
        seen.add(c.case_id)
    return cases


def split_counts(cases: list[GeneratedCase]) -> dict[str, int]:
    out = {"DEV": 0, "LOCKED": 0, "CHALLENGE": 0}
    for c in cases:
        if c.split in out:
            out[c.split] += 1
    return out


def category_counts(cases: list[GeneratedCase]) -> dict[str, int]:
    out: dict[str, int] = {cat.value: 0 for cat in Category}
    for c in cases:
        out[c.category.value] += 1
    return out


def cases_in_split(cases: list[GeneratedCase], split: str) -> list[GeneratedCase]:
    """개발 중에는 DEV만 열람하는 규율(LOCKED §0-5)을 코드로 표현."""
    return [c for c in cases if c.split == split]
