"""서비스 소개서(PPTX)가 쓸 수치를 **엔진에서 계산**한다 — 덱에 손으로 적지 않기 위해.

2026-08-21 지원서 최종 점검에서 덱의 수치 두 곳이 이미 실제와 갈라져 있었다:

  · "자동 테스트 590개"      — 그 사이 늘어난 것을 덱에만 안 옮겼다.
  · 목표 역산 처방 3줄        — 엔진이 **더 이상 내지 않는 처방**이 적혀 있었다
    (부채 감축·만기 연장은 이 시나리오에서 불가로 판정되는데 덱은 가능하다고 적었고,
     "만기 40년"은 규제지역 상한 30년과 정면으로 어긋났다).

두 번째가 특히 나쁘다 — 심사자가 공개 데모에 같은 값을 넣어 보면 **덱과 다른 화면**을 본다.
제출 문서에서 이보다 빨리 신뢰를 잃는 방법은 없다. 원인은 하나다: 덱의 수치가 저장소 밖
임시 스크립트에 리터럴로 박혀 있어 아무도(테스트도) 대조하지 못했다.

    python tools/deck_facts.py            # 사람이 읽는 표로 출력
    python tools/deck_facts.py --json     # tools/build_deck.js 가 먹는 형식
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from regimpact import affordability                                   # noqa: E402
from regimpact.assurance import scorecard as SC                       # noqa: E402
from regimpact.governance import RISKS                                # noqa: E402
from regimpact.impact import (                                        # noqa: E402
    analyze_portfolio,
    build_impact_matrix,
    build_portfolio,
)
from regimpact.impact.portfolio import DEFAULT_SEED, DEFAULT_SIZE     # noqa: E402
from regimpact.grandfathering import CUTOFF                           # noqa: E402
from regimpact.models import LoanPurpose, MortgageApplication         # noqa: E402
from regimpact.regions import REG_EFFECTIVE, REGION_LABELS            # noqa: E402
from regimpact.report import collect                                  # noqa: E402
from regimpact.rule_engine import evaluate                            # noqa: E402

# 덱의 '핵심 장면'이 쓰는 시나리오. **한 곳에만 적는다** — 라벨과 값이 갈라지지 않도록
# 라벨도 여기서 만들어 내보낸다.
SCENE = {
    "region": "GURI",
    "price": 800_000_000,
    "income": 50_000_000,
    "monthly_debt": 1_000_000,
    "rate": 0.04,
    "term_years": 30,
    "lender": "BANK",
    "goal": 400_000_000,
    "contract": date(2026, 6, 28),      # 시행 전 계약 + 계약금 납부
}


def won(x: int, unit: bool = True) -> str:
    """원 → "N억 M천만원". **화면(`ui/signal.js` 의 `won`)과 같은 자리에서 반올림한다.**

    덱이 `1억 3,964만`, 화면이 `1억 4천만원` 이면 같은 값인데 다른 수처럼 보인다 —
    심사자는 덱을 읽고 데모를 열어 두 화면을 나란히 놓는 사람이다. 반올림 자리가
    다른 것만으로도 "어느 쪽이 맞나"를 묻게 되고, 그 질문은 대답할 가치가 없다.
    """
    if x <= 0:
        return "0원" if unit else "0"
    eok, rest = divmod(int(x), 100_000_000)
    chun = round(rest / 10_000_000)
    if chun == 10:                      # 반올림이 올려 붙으면 억을 올린다
        eok, chun = eok + 1, 0
    if eok == 0 and chun == 0:
        body = f"{round(x / 10_000):,}만"
    elif eok == 0:
        body = f"{chun}천만"
    else:
        body = f"{eok}억" + (f" {chun}천만" if chun else "")
    return body + ("원" if unit else "")


def _app(when, **over) -> MortgageApplication:
    base = dict(
        region_code=SCENE["region"], evaluation_date=when, house_count=0,
        disposal_condition_flag=False, first_home_buyer=False, real_demand_flag=False,
        policy_mortgage_flag=False, loan_purpose=LoanPurpose.HOME_PURCHASE,
        application_accepted_at=None, contract_signed_at=None, downpayment_paid_at=None,
        land_permit_target=False, land_permit_applied_at=None,
    )
    base.update(over)
    return MortgageApplication(**base)


def _decision(res):
    return res.decision if hasattr(res, "decision") else res


def _test_count() -> int:
    """실제 수집되는 테스트 수. 덱에 적을 값은 세어서 넣는다."""
    out = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q",
         "-p", "no:cacheprovider", str(REPO / "tests")],
        cwd=REPO, capture_output=True, text=True, check=True,
    ).stdout
    import re
    m = re.search(r"(\d+) tests? collected", out)
    if not m:
        raise RuntimeError(f"테스트 수집 결과를 읽지 못했다:\n{out[-400:]}")
    return int(m.group(1))


def _js_port_total() -> tuple[int, str]:
    """브라우저 포팅본 대조 건수 — verify_js_port 가 실제로 센 값."""
    import re
    fx = REPO / "site" / "fixtures.json"
    if not fx.exists():
        subprocess.run([sys.executable, str(REPO / "tools" / "export_fixtures.py"),
                        "--out", str(fx)], cwd=REPO, check=True, capture_output=True)
    out = subprocess.run(["node", str(REPO / "tools" / "verify_js_port.mjs"), str(fx)],
                         cwd=REPO, capture_output=True, text=True, check=True).stdout
    parts = re.findall(r"(\d+)건", out)
    detail = out.strip().splitlines()[-1]
    return sum(int(x) for x in parts), detail


def build() -> dict:
    ev = collect(generated_at="deck")
    g, r = ev.grounding, ev.regression
    # 현업 산출물 수치도 실제로 조립해서 뽑는다 — 덱에만 적어 두면 갈라진다.
    imp = analyze_portfolio(build_portfolio(size=DEFAULT_SIZE, seed=DEFAULT_SEED),
                            seed=DEFAULT_SEED)
    mx = build_impact_matrix(ev.extraction, imp, grounding=g, regression=r)
    port_total, port_detail = _js_port_total()
    card = SC.score(ev, js_port_agreement=1.0).summary()

    before = _decision(evaluate(_app(CUTOFF)))
    after = _decision(evaluate(_app(REG_EFFECTIVE)))
    gf = _decision(evaluate(_app(REG_EFFECTIVE,
                                 contract_signed_at=SCENE["contract"],
                                 downpayment_paid_at=SCENE["contract"])))
    P = SCENE["price"]
    amt = lambda d: int(P * d.max_ltv)                                  # noqa: E731

    est = affordability.estimate(
        price=P, max_ltv=after.max_ltv, rule_id=after.applicable_rule_id,
        regulated=True, regulated_type="SPECULATIVE_OVERHEATED",
        annual_income=SCENE["income"], monthly_debt_service=SCENE["monthly_debt"],
        annual_rate=SCENE["rate"], term_years=SCENE["term_years"], lender=SCENE["lender"])
    plan = affordability.plan_for_target(
        target=SCENE["goal"], price=P, max_ltv=after.max_ltv,
        rule_id=after.applicable_rule_id, regulated=True,
        regulated_type="SPECULATIVE_OVERHEATED",
        annual_income=SCENE["income"], monthly_debt_service=SCENE["monthly_debt"],
        annual_rate=SCENE["rate"], term_years=SCENE["term_years"], lender=SCENE["lender"])

    # 처방은 **엔진이 낸 것만** 적는다. 화면이 못 내는 처방을 덱이 약속하면,
    # 심사자가 데모에 같은 값을 넣는 순간 어긋난다(2026-08-21 에 실제로 그랬다).
    ways, seen = [], set()
    for a in plan["actions"]:
        if a.get("need_price"):
            w = f"주택가격 {won(a['need_price'], unit=False)} 이상이면 이 한도로 목표에 닿기"
        elif a.get("impossible_by_debt") and a.get("need_income"):
            w = (f"연소득 {won(a['need_income'], unit=False)} 이상 인정받기"
                 f" (기존 부채를 전부 갚아도 이 한도만으로는 닿지 않음)")
        elif a.get("cut_monthly_debt"):
            w = f"기존 대출 월 상환액을 {a['cut_monthly_debt'] // 10_000}만원 줄이기"
        elif a.get("by_term"):
            w = f"만기를 {a['by_term']}년으로 늘리기"
        elif a.get("need_income"):
            w = f"연소득 {won(a['need_income'], unit=False)} 이상 인정받기"
        else:
            continue
        if w not in seen:
            seen.add(w)
            ways.append(w)

    label = {"LTV": "담보 비율 (LTV)", "CAP": "가격구간 최대한도",
             "DSR": "총부채원리금 (DSR)", "DTI": "총부채상환 (DTI · 아파트)"}
    binding = set(est["binding"])

    return {
        "_note": "tools/deck_facts.py 가 엔진을 실제로 실행해 만든 값. "
                 "덱에 손으로 적지 말 것 — tools/build_deck.js 가 이 파일을 읽는다.",
        "scene": {
            "region_label": REGION_LABELS.get(SCENE["region"], SCENE["region"]),
            "price": won(P, unit=False),
            "cutoff": CUTOFF.isoformat(),
            "effective": REG_EFFECTIVE.isoformat(),
            "contract": SCENE["contract"].isoformat(),
            "inputs": (f"연소득 {SCENE['income'] // 10_000:,}만원 · "
                       f"기존 대출 월 상환 {SCENE['monthly_debt'] // 10_000}만원 · "
                       f"금리 {SCENE['rate']:.0%} · 만기 {SCENE['term_years']}년 · 은행권"),
        },
        "verdict": {
            "before_ltv": f"LTV {before.max_ltv:.0%}",
            "before_amt": f"약 {won(amt(before))}",
            "before_rule": before.applicable_rule_id,
            "after_ltv": f"LTV {after.max_ltv:.0%}",
            "after_amt": f"약 {won(amt(after))}",
            "after_rule": after.applicable_rule_id,
            "delta": won(amt(before) - amt(after)),
            "gf_ltv": f"LTV {gf.max_ltv:.0%}",
            "gf_amt": f"약 {won(amt(gf))}",
            "gf_applied": bool(gf.grandfathering_applied),
        },
        "afford": {
            "total": won(est["total"]),
            "binding": sorted(binding),
            "rows": [
                {"label": label[k] + ("  ← 여기에 막혀요" if k in binding else ""),
                 "amount": won(est["limits"][k], unit=False),
                 "ratio": round(est["limits"][k] / max(est["limits"].values()), 3),
                 "hit": k in binding}
                for k in ("LTV", "CAP", "DSR", "DTI")
            ],
            "goal": won(SCENE["goal"], unit=False),
            "short": won(SCENE["goal"] - est["total"]),
            "reachable": bool(plan["reachable"]),
            "ways": ways,
        },
        "assurance": {
            "citation": f"{g.grounded} / {g.total}",
            "oracle": f"{r.passed} / {r.total}",
            "js_port": f"{port_total}건",
            "js_port_detail": port_detail,
            "tests": f"{_test_count()}개",
            "card": (f"{card['total']}개 지표를 확정 임계와 대조해 "
                     f"{card['passed']}개 통과 · 미달 {card['failed']} · "
                     f"미측정 {card['not_measured']}"),
        },
        "reach": {
            "extraction": f"변경 {len(ev.extraction.changes)}건 · "
                          f"인용 {g.citation_correctness:.0%}",
            # `rows` 는 이미 코어+Discovery 전체다 — 다시 더하면 두 벌이 된다.
            "matrix": f"{len(mx.rows)}행 · 자동처리 {mx.automation_rate:.0%}",
            # 감소액은 음수로 들어온다. 부호를 손으로 붙이면 −−1,549억 이 된다.
            "portfolio": f"{len(imp.reduced)}건 감소 · "
                         f"{imp.total_limit_reduction / 100_000_000:,.0f}".replace("-", "−")
                         + "억 원",
            "oracle": f"{r.total}케이스 {r.pass_rate:.0%}",
            "risks": f"리스크 {len(RISKS)}건 / {len({x.category for x in RISKS})}범주",
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="소개서 덱이 쓸 수치를 엔진에서 계산")
    ap.add_argument("--json", action="store_true", help="JSON 으로 출력")
    ap.add_argument("--out", default=None, help="JSON 파일로 저장")
    a = ap.parse_args()

    f = build()
    if a.out:
        Path(a.out).write_text(json.dumps(f, ensure_ascii=False, indent=1) + "\n",
                               encoding="utf-8")
        print(f"덱 수치: {a.out}")
        return
    if a.json:
        print(json.dumps(f, ensure_ascii=False, indent=1))
        return

    v, af, asr = f["verdict"], f["afford"], f["assurance"]
    print(f"시나리오  {f['scene']['region_label']} · {f['scene']['price']} · 무주택")
    print(f"  변경 전  {v['before_ltv']} {v['before_amt']}  [{v['before_rule']}]")
    print(f"  변경 후  {v['after_ltv']} {v['after_amt']}  [{v['after_rule']}]")
    print(f"  차이     {v['delta']}")
    print(f"  경과규정 {v['gf_ltv']} {v['gf_amt']} (적용={v['gf_applied']})")
    print(f"\n총 가능금액  {af['total']}  ← {', '.join(af['binding'])} 에 막힘")
    for r in af["rows"]:
        print(f"  {r['label']:34s} {r['amount']}")
    print(f"\n목표 {af['goal']} — {af['short']} 모자람 (도달가능={af['reachable']})")
    for w in af["ways"]:
        print(f"  · {w}")
    print(f"\n인용 {asr['citation']} · 오라클 {asr['oracle']} · "
          f"JS 대조 {asr['js_port']} · 테스트 {asr['tests']}")
    print(f"  {asr['card']}")
    for k, val in f["reach"].items():
        print(f"  {k:12s} {val}")


if __name__ == "__main__":
    main()
