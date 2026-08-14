"""Gold Set 빌더 — 100~120문항 평가셋을 생성하고 DEV/LOCKED/CHALLENGE로 freeze.

정답(expected)은 rule_engine 이 아니라 **독립 명세 오라클**(tc_generator.oracle)에서 유도한다
→ 엔진과 독립 코드 경로이므로 회귀가 tautology가 되지 않는다(브리프 §12, LOCKED §4).
결정론적(난수 없음) — 커밋된 산출물(dev/locked/challenge.json)은 이 스크립트로 재현 가능.

실행: python tools/build_gold_set.py
산출: docs/eval/gold_set/{dev,locked,challenge}.json + MANIFEST.json + README.md

split 목표(2026-08-10 결정, DECISION_LOG): DEV 40 / LOCKED 40 / CHALLENGE 35 = 115.
CHALLENGE 는 EXCEPTION·GRANDFATHERING·EFFECTIVE_DATE·CONFLICT·AMBIGUOUS 를 가중.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from regimpact.models import LoanPurpose, MortgageApplication  # noqa: E402
from regimpact.tc_generator.oracle import expected_outcome  # noqa: E402
from regimpact.proposal import RULE_ID  # noqa: E402

GOLD_DIR = ROOT / "docs" / "eval" / "gold_set"
VERSION = "v1"
FREEZE_DATE = "2026-08-14"
POLICY_VERSION = "FSC_20260630"

TARGET = ["GURI", "YONGIN_GIHEUNG", "HWASEONG_DONGTAN"]
NONREG = ["SUWON_GWONSEON", "SEOUL_JUNGGU", "BUCHEON_WONMI"]   # 미등록 → 이 시나리오에서 非규제
AFTER = ["2026-07-01", "2026-07-02", "2026-08-15", "2026-09-30", "2026-12-01"]
BEFORE = ["2026-05-01", "2026-06-15", "2026-06-29", "2026-06-30"]

# 카테고리별 근거(브리프 §11 '근거 문서·위치') — 실측 추출에서 확인한 원문 인용.
SRC = {
    "LTV40": ("FAQ_20260630", "규제지역 내 주담대 취급시 강화된 LTV(70→40%) 적용"),
    "FIRST": ("MOLIT_PRESS_20260630", "생애최초 LTV 70% + 전입의무(6개월 이내)"),
    "REAL": ("FAQ_20260630", "금융권 서민·실수요자 주담대 … 완화된 LTV가 적용됨"),
    "OWNER": ("MOLIT_PRESS_20260630", "무주택(처분조건부 1주택 포함) 40%, 유주택 0%"),
    "MULTI": ("FSC_PRESS_20260630", "다주택자는 수도권 內 주택구입시 … LTV 0% 적용"),
    "GF": ("FAQ_20260630", "6.30일까지 전산 접수 완료 또는 계약+계약금 → 종전규정 적용"),
    "EFF": ("FSC_PRESS_20260630", "강화된 대출규제가 7.1일부터 즉시 적용된다"),
    "REGION": ("MOLIT_PRESS_20260630", "3곳을 투기과열지구 및 조정대상지역으로 신규 지정"),
    "BASE": ("MOLIT_PRESS_20260630", "非규제지역(수도권 외) 무주택(처분조건부 1주택) 70%"),
    "OOS": ("FSC_PRESS_20260630", "주택구입목적 아님 → 자동판정 밖(Discovery)"),
    "POLICY": ("FAQ_20260630", "생애최초·정책모기지 등 정책대출 → Discovery"),
}


def _app(inp: dict) -> MortgageApplication:
    kw = dict(inp)
    for f in ("evaluation_date", "application_accepted_at", "contract_signed_at",
              "downpayment_paid_at", "land_permit_applied_at"):
        if isinstance(kw.get(f), str):
            kw[f] = date.fromisoformat(kw[f])
    if isinstance(kw.get("loan_purpose"), str):
        kw["loan_purpose"] = LoanPurpose(kw["loan_purpose"])
    return MortgageApplication(**kw)


# 후보 누적: (category, difficulty, input, src_key)
_pool: list[tuple[str, str, dict, str]] = []


def add(category: str, difficulty: str, src_key: str, **input_kw) -> None:
    _pool.append((category, difficulty, input_kw, src_key))


def _build_pool() -> None:
    # NORMAL — 무주택 일반 / 처분조건부 1주택 (규제지역 40%)
    for r in TARGET:
        for d in AFTER:
            add("NORMAL", "normal", "LTV40", region_code=r, evaluation_date=d, house_count=0)
        for d in ("2026-07-02", "2026-08-15"):
            add("NORMAL", "normal", "LTV40", region_code=r, evaluation_date=d,
                house_count=1, disposal_condition_flag=True)

    # EXCEPTION — 생애최초 / 서민·실수요 (규제지역)
    for r in TARGET:
        for d in ("2026-07-02", "2026-08-15", "2026-12-01"):
            add("EXCEPTION", "normal", "FIRST", region_code=r, evaluation_date=d,
                house_count=0, first_home_buyer=True)
        for d in ("2026-07-02", "2026-09-30"):
            add("EXCEPTION", "normal", "REAL", region_code=r, evaluation_date=d,
                house_count=0, real_demand_flag=True)

    # GRANDFATHERING — 규제 시점에 경과규정 충족 → 종전규정 70
    for r in TARGET:
        for acc in ("2026-06-10", "2026-06-15"):
            add("GRANDFATHERING", "normal", "GF", region_code=r, evaluation_date="2026-07-02",
                house_count=0, application_accepted_at=acc)
        add("GRANDFATHERING", "normal", "GF", region_code=r, evaluation_date="2026-08-15",
            house_count=0, contract_signed_at="2026-06-20", downpayment_paid_at="2026-06-20")
    add("GRANDFATHERING", "normal", "GF", region_code="GURI", evaluation_date="2026-07-02",
        house_count=0, land_permit_target=True, land_permit_applied_at="2026-06-25")
    add("GRANDFATHERING", "normal", "GF", region_code="YONGIN_GIHEUNG", evaluation_date="2026-07-02",
        house_count=0, land_permit_target=True, land_permit_applied_at="2026-06-28")
    # 경과규정 경계값 → CHALLENGE
    add("GRANDFATHERING", "challenge", "GF", region_code="GURI", evaluation_date="2026-07-01",
        house_count=0, application_accepted_at="2026-06-30")           # 컷오프 당일 = 인정
    add("GRANDFATHERING", "challenge", "GF", region_code="GURI", evaluation_date="2026-07-01",
        house_count=0, application_accepted_at="2026-07-01")           # 컷오프 다음날 = 미인정 → 40
    add("GRANDFATHERING", "challenge", "GF", region_code="YONGIN_GIHEUNG", evaluation_date="2026-07-02",
        house_count=0, contract_signed_at="2026-06-30")                # 계약만, 계약금 없음 → 미인정
    add("GRANDFATHERING", "challenge", "GF", region_code="HWASEONG_DONGTAN", evaluation_date="2026-07-02",
        house_count=0, contract_signed_at="2026-06-30", downpayment_paid_at="2026-07-05")  # 계약<=컷오프+계약금존재=인정
    add("GRANDFATHERING", "challenge", "GF", region_code="GURI", evaluation_date="2026-07-02",
        house_count=0, land_permit_target=True, land_permit_applied_at="2026-07-01")  # 토허 신청 늦음 → 미인정
    add("GRANDFATHERING", "challenge", "GF", region_code="GURI", evaluation_date="2026-07-02",
        house_count=0, land_permit_target=False, land_permit_applied_at="2026-06-25")  # 토허 대상 아님 → 미인정

    # EFFECTIVE_DATE — 같은 차주 시행 전(비규제 70) vs 후(규제 40)
    for r in TARGET:
        for d in ("2026-05-01", "2026-06-15"):
            add("EFFECTIVE_DATE", "normal", "BASE", region_code=r, evaluation_date=d, house_count=0)
    # 효력일 경계 6.30 vs 7.1 → CHALLENGE
    add("EFFECTIVE_DATE", "challenge", "BASE", region_code="GURI", evaluation_date="2026-06-30", house_count=0)
    add("EFFECTIVE_DATE", "challenge", "LTV40", region_code="GURI", evaluation_date="2026-07-01", house_count=0)
    add("EFFECTIVE_DATE", "challenge", "BASE", region_code="YONGIN_GIHEUNG", evaluation_date="2026-06-30", house_count=0)
    add("EFFECTIVE_DATE", "challenge", "LTV40", region_code="YONGIN_GIHEUNG", evaluation_date="2026-07-01", house_count=0)
    add("EFFECTIVE_DATE", "challenge", "BASE", region_code="HWASEONG_DONGTAN", evaluation_date="2026-06-30", house_count=0)
    add("EFFECTIVE_DATE", "challenge", "LTV40", region_code="HWASEONG_DONGTAN", evaluation_date="2026-07-01", house_count=0)
    add("EFFECTIVE_DATE", "challenge", "BASE", region_code="GURI", evaluation_date="2026-06-29", house_count=0)

    # REGION — 규제 대상 vs 미등록(非규제)
    for r in TARGET:
        for d in ("2026-07-02", "2026-09-30"):
            add("REGION", "normal", "REGION", region_code=r, evaluation_date=d, house_count=0)
    for r in NONREG:
        add("REGION", "normal", "BASE", region_code=r, evaluation_date="2026-07-02", house_count=0)
        add("REGION", "normal", "BASE", region_code=r, evaluation_date="2026-08-15", house_count=0)

    # BORROWER_TYPE — 주택수 변주 (규제지역)
    for r in TARGET:
        add("BORROWER_TYPE", "normal", "LTV40", region_code=r, evaluation_date="2026-08-15", house_count=0)
        add("BORROWER_TYPE", "normal", "OWNER", region_code=r, evaluation_date="2026-08-15", house_count=1)
        add("BORROWER_TYPE", "normal", "MULTI", region_code=r, evaluation_date="2026-08-15", house_count=2)
    add("BORROWER_TYPE", "normal", "MULTI", region_code="YONGIN_GIHEUNG", evaluation_date="2026-07-02", house_count=3)
    add("BORROWER_TYPE", "normal", "MULTI", region_code="GURI", evaluation_date="2026-09-30", house_count=4)
    add("BORROWER_TYPE", "normal", "LTV40", region_code="YONGIN_GIHEUNG", evaluation_date="2026-08-15",
        house_count=1, disposal_condition_flag=True)
    add("BORROWER_TYPE", "normal", "LTV40", region_code="HWASEONG_DONGTAN", evaluation_date="2026-09-30",
        house_count=1, disposal_condition_flag=True)

    # LOAN_PURPOSE — 주택구입목적 아님(OOS) / 정책대출(Discovery)
    for r in TARGET:
        for d in ("2026-07-02", "2026-09-30"):
            add("LOAN_PURPOSE", "normal", "OOS", region_code=r, evaluation_date=d,
                house_count=0, loan_purpose="OTHER")
    add("LOAN_PURPOSE", "normal", "OOS", region_code="GURI", evaluation_date="2026-06-15",
        house_count=0, loan_purpose="OTHER")
    for r in TARGET:
        add("LOAN_PURPOSE", "normal", "POLICY", region_code=r, evaluation_date="2026-07-02",
            house_count=0, policy_mortgage_flag=True)
        add("LOAN_PURPOSE", "normal", "POLICY", region_code=r, evaluation_date="2026-08-15",
            house_count=1, policy_mortgage_flag=True)   # 정책대출 우선(주택수 무관)
    add("LOAN_PURPOSE", "normal", "POLICY", region_code="GURI", evaluation_date="2026-07-02",
        house_count=0, policy_mortgage_flag=True, first_home_buyer=True)  # 정책대출 우선(Discovery)

    # NO_CHANGE — 非규제 무주택 항상 70 / 경과규정으로 종전 유지(변화 없음)
    for r in NONREG:
        for d in ("2026-07-02", "2026-09-30"):
            add("NO_CHANGE", "normal", "BASE", region_code=r, evaluation_date=d, house_count=0)
    for r in TARGET:
        add("NO_CHANGE", "normal", "GF", region_code=r, evaluation_date="2026-07-02",
            house_count=0, application_accepted_at="2026-06-10")
    add("NO_CHANGE", "normal", "BASE", region_code="GURI", evaluation_date="2026-06-15", house_count=0)
    for r in TARGET:
        add("NO_CHANGE", "normal", "FIRST", region_code=r, evaluation_date="2026-08-15",
            house_count=0, first_home_buyer=True)  # 생애최초 70→70 무변

    # CONFLICT — 복수 플래그 동시(우선순위 §H) → CHALLENGE
    add("CONFLICT", "challenge", "OWNER", region_code="GURI", evaluation_date="2026-07-02",
        house_count=1, first_home_buyer=True)       # 유주택+생애최초 → 유주택 0 (§H P4 우선)
    add("CONFLICT", "challenge", "MULTI", region_code="GURI", evaluation_date="2026-07-02",
        house_count=2, real_demand_flag=True)       # 다주택+실수요 → 다주택 0
    add("CONFLICT", "challenge", "MULTI", region_code="YONGIN_GIHEUNG", evaluation_date="2026-07-02",
        house_count=2, first_home_buyer=True)       # 다주택+생애최초 → 0
    add("CONFLICT", "challenge", "FIRST", region_code="GURI", evaluation_date="2026-07-02",
        house_count=1, disposal_condition_flag=True, first_home_buyer=True)  # 처분조건부+생애최초 → 70
    add("CONFLICT", "challenge", "FIRST", region_code="GURI", evaluation_date="2026-07-02",
        house_count=0, first_home_buyer=True, real_demand_flag=True)  # 생애최초+실수요 → 생애최초 70(우선)
    add("CONFLICT", "challenge", "POLICY", region_code="GURI", evaluation_date="2026-07-02",
        house_count=2, policy_mortgage_flag=True)   # 정책대출+다주택 → Discovery(P0b 우선)
    add("CONFLICT", "challenge", "OOS", region_code="GURI", evaluation_date="2026-07-02",
        house_count=2, loan_purpose="OTHER", first_home_buyer=True)  # 비주택목적+다주택 → OOS(P0 우선)
    add("CONFLICT", "challenge", "GF", region_code="GURI", evaluation_date="2026-07-02",
        house_count=0, first_home_buyer=True, application_accepted_at="2026-06-15")  # 경과규정+생애최초 → 종전 70(P1 우선)
    add("CONFLICT", "challenge", "REAL", region_code="YONGIN_GIHEUNG", evaluation_date="2026-07-02",
        house_count=1, disposal_condition_flag=True, real_demand_flag=True)  # 처분조건부+실수요 → 실수요 60
    add("CONFLICT", "challenge", "LTV40", region_code="HWASEONG_DONGTAN", evaluation_date="2026-07-02",
        house_count=1, disposal_condition_flag=True)  # 처분조건부(무주택 취급) → 40
    add("CONFLICT", "challenge", "OWNER", region_code="YONGIN_GIHEUNG", evaluation_date="2026-07-02",
        house_count=1, real_demand_flag=True)       # 유주택+실수요 → 유주택 0
    add("CONFLICT", "challenge", "MULTI", region_code="HWASEONG_DONGTAN", evaluation_date="2026-07-02",
        house_count=3, first_home_buyer=True, real_demand_flag=True)  # 다주택+복수예외 → 0

    # AMBIGUOUS — 기준 부재 → escalation (정직한 사람검토) → CHALLENGE
    for r in NONREG:
        add("AMBIGUOUS", "challenge", "BASE", region_code=r, evaluation_date="2026-07-02", house_count=1)  # 非규제 유주택 기준선 부재
    add("AMBIGUOUS", "challenge", "BASE", region_code="SUWON_GWONSEON", evaluation_date="2026-07-02", house_count=2)
    add("AMBIGUOUS", "challenge", "GF", region_code="GURI", evaluation_date="2026-07-02",
        house_count=1, application_accepted_at="2026-06-15")  # 경과규정+유주택 → 기준선 부재 escalation
    add("AMBIGUOUS", "challenge", "GF", region_code="YONGIN_GIHEUNG", evaluation_date="2026-07-02",
        house_count=2, contract_signed_at="2026-06-20", downpayment_paid_at="2026-06-20")  # 경과규정+다주택 → escalation
    add("AMBIGUOUS", "challenge", "BASE", region_code="SEOUL_JUNGGU", evaluation_date="2026-06-15", house_count=1)
    add("AMBIGUOUS", "challenge", "BASE", region_code="SUWON_GWONSEON", evaluation_date="2026-08-15", house_count=1)
    add("AMBIGUOUS", "challenge", "GF", region_code="HWASEONG_DONGTAN", evaluation_date="2026-07-02",
        house_count=1, land_permit_target=True, land_permit_applied_at="2026-06-25")  # 경과규정(토허)+유주택 → escalation
    add("AMBIGUOUS", "challenge", "BASE", region_code="SEOUL_JUNGGU", evaluation_date="2026-07-02",
        house_count=1, disposal_condition_flag=False)  # 非규제 비처분 1주택 → 기준선 부재

    # 추가 CONFLICT — 우선순위 경계 심화
    add("CONFLICT", "challenge", "GF", region_code="YONGIN_GIHEUNG", evaluation_date="2026-07-02",
        house_count=0, real_demand_flag=True, contract_signed_at="2026-06-20", downpayment_paid_at="2026-06-20")  # 경과+실수요 → 종전 70
    add("CONFLICT", "challenge", "POLICY", region_code="HWASEONG_DONGTAN", evaluation_date="2026-07-02",
        house_count=0, policy_mortgage_flag=True, real_demand_flag=True)  # 정책+실수요 → Discovery
    add("CONFLICT", "challenge", "OOS", region_code="YONGIN_GIHEUNG", evaluation_date="2026-07-02",
        house_count=0, loan_purpose="OTHER", policy_mortgage_flag=True)  # 비주택목적+정책 → OOS(P0 최우선)
    add("CONFLICT", "challenge", "MULTI", region_code="GURI", evaluation_date="2026-07-02",
        house_count=2, disposal_condition_flag=True)  # 2주택+처분조건부(다주택 우선) → 0

    # 추가 EFFECTIVE_DATE 경계 — 미등록 지역은 효력일과 무관(항상 70)
    add("EFFECTIVE_DATE", "challenge", "BASE", region_code="SUWON_GWONSEON", evaluation_date="2026-07-01", house_count=0)
    add("EFFECTIVE_DATE", "challenge", "BASE", region_code="SUWON_GWONSEON", evaluation_date="2026-06-30", house_count=0)


def _make_item(idx: int, category: str, split: str, inp: dict, src_key: str) -> dict:
    eo = expected_outcome(_app(inp))
    doc, note = SRC[src_key]
    return {
        "id": f"{split.upper()}-{category}-{idx:03d}",
        "category": category,
        "split": split,
        "input": inp,
        "expected": {
            "status": eo.status.value,
            "max_ltv": eo.max_ltv,
            "applicable_rule_id": eo.applicable_rule_id,
            "grandfathering_applied": eo.grandfathering_applied,
            "must_include_reasons": list(eo.must_include_reasons),
        },
        "expected_escalation": eo.status.value == "NEEDS_HUMAN_REVIEW",
        "policy_version": POLICY_VERSION,
        "rule_id": RULE_ID,
        "source_doc_id": doc,
        "source_note": note,
    }


def _stratified_trim(cands: list[tuple], target: int) -> list[tuple]:
    """카테고리 균형을 유지하며 target개로 라운드로빈 선택(결정론적)."""
    by_cat: dict[str, list[tuple]] = {}
    for c in cands:
        by_cat.setdefault(c[0], []).append(c)
    out, i = [], 0
    while len(out) < target and any(by_cat.values()):
        for cat in list(by_cat.keys()):
            bucket = by_cat[cat]
            if i < len(bucket):
                out.append(bucket[i])
                if len(out) >= target:
                    break
        i += 1
        if all(i >= len(b) for b in by_cat.values()):
            break
    return out[:target]


def build() -> dict:
    _build_pool()
    # 전역 dedupe(입력 서명 기준) — 순서 보존
    seen, uniq = set(), []
    for cat, diff, inp, sk in _pool:
        sig = json.dumps(inp, sort_keys=True, ensure_ascii=False)
        if sig in seen:
            continue
        seen.add(sig)
        uniq.append((cat, diff, inp, sk))

    challenge_c = [c for c in uniq if c[1] == "challenge"]
    devlocked_c = [c for c in uniq if c[1] == "normal"]

    challenge = _stratified_trim(challenge_c, 35)
    devlocked = _stratified_trim(devlocked_c, 80)

    # DEV/LOCKED: 카테고리별 교대 배정(균형·disjoint)
    dev_c, locked_c = [], []
    by_cat: dict[str, list[tuple]] = {}
    for c in devlocked:
        by_cat.setdefault(c[0], []).append(c)
    for cat, bucket in by_cat.items():
        for j, c in enumerate(bucket):
            (dev_c if j % 2 == 0 else locked_c).append(c)
    # 40/40 정확히 맞추기(결정론적 이동)
    while len(dev_c) > 40:
        locked_c.append(dev_c.pop())
    while len(locked_c) > 40:
        dev_c.append(locked_c.pop())

    splits = {"dev": dev_c, "locked": locked_c, "challenge": challenge}
    written = {}
    GOLD_DIR.mkdir(parents=True, exist_ok=True)
    manifest_splits = {}
    for name, cands in splits.items():
        items = [_make_item(i + 1, cat, name, inp, sk) for i, (cat, _d, inp, sk) in enumerate(cands)]
        payload = {
            "_meta": {
                "split": name, "version": VERSION, "freeze_date": FREEZE_DATE,
                "count": len(items),
                "note": "정답(expected)은 독립 명세 오라클(tc_generator.oracle)에서 유도. "
                        "rule_engine 은 채점 대상. 누수 방지: LOCKED/CHALLENGE는 sealed(브리프 §12).",
            },
            "items": items,
        }
        text = json.dumps(payload, ensure_ascii=False, indent=2)
        (GOLD_DIR / f"{name}.json").write_text(text, encoding="utf-8")
        h = hashlib.sha256(text.encode("utf-8")).hexdigest()
        cat_counts: dict[str, int] = {}
        for it in items:
            cat_counts[it["category"]] = cat_counts.get(it["category"], 0) + 1
        manifest_splits[name] = {"count": len(items), "sha256": h, "by_category": cat_counts}
        written[name] = len(items)

    manifest = {
        "name": "RegImpact 6·30 Gold Set",
        "version": VERSION,
        "freeze_date": FREEZE_DATE,
        "policy_version": POLICY_VERSION,
        "total": sum(written.values()),
        "expected_source": "tc_generator.oracle (독립 명세 재구현) — 엔진과 독립 코드 경로",
        "discipline": "DEV=상시 튜닝/회귀. LOCKED·CHALLENGE=sealed, 코어 완성 후 1회 실행(브리프 §12).",
        "splits": manifest_splits,
    }
    (GOLD_DIR / "MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_readme(manifest)
    return manifest


def _write_readme(manifest: dict) -> None:
    lines = [
        "# Gold Set — 6·30 규제 변경 평가셋 (freeze)", "",
        f"> version {manifest['version']} · freeze {manifest['freeze_date']} · 총 {manifest['total']}문항",
        "",
        "브리프 §11~12. 각 문항: 입력 / 골드 정답 / 근거 문서·위치 / 카테고리 / human escalation 기대 /",
        "정책 버전 / rule_id. **정답(expected)은 독립 명세 오라클(tc_generator.oracle)에서 유도** —",
        "rule_engine 과 독립 코드 경로이므로 엔진 회귀가 tautology가 되지 않는다(LOCKED §4).", "",
        "## Split (누수 방지 §12)", "",
        "| split | 규모 | 용도 | 상태 |",
        "|---|---:|---|---|",
        f"| DEV | {manifest['splits']['dev']['count']} | 개발 중 상시 회귀·튜닝 | 개방 |",
        f"| LOCKED | {manifest['splits']['locked']['count']} | 최종 성능평가 | **sealed** (Phase 3 1회) |",
        f"| CHALLENGE | {manifest['splits']['challenge']['count']} | 예외·경계·충돌·모호 적대적 평가 | **sealed** (Phase 3 1회) |",
        "",
        "`regimpact.eval.load_split('locked'/'challenge')` 는 `unlock=True` 없이는 열리지 않는다.",
        "개발 중 튜닝·상시 회귀는 `run_gold_regression('dev')` 만 사용한다.", "",
        "## 카테고리 분포", "",
        "| category | DEV | LOCKED | CHALLENGE |",
        "|---|---:|---:|---:|",
    ]
    cats = sorted({c for s in manifest["splits"].values() for c in s["by_category"]})
    for cat in cats:
        row = [cat] + [str(manifest["splits"][s]["by_category"].get(cat, 0)) for s in ("dev", "locked", "challenge")]
        lines.append("| " + " | ".join(row) + " |")
    lines += [
        "", "## 재현", "",
        "```bash", "python tools/build_gold_set.py     # 결정론적 재생성",
        "python examples/demo_gold_set.py   # DEV 회귀 출력", "```", "",
        "## 무결성", "",
        "MANIFEST.json 에 split별 sha256. LOCKED/CHALLENGE 개봉은 최종 보고 시 1회.",
    ]
    (GOLD_DIR / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    m = build()
    print(f"Gold Set freeze — 총 {m['total']}문항")
    for name, s in m["splits"].items():
        print(f"  {name:<10} {s['count']:>3}  {s['by_category']}")
