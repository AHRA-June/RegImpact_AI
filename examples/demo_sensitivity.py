"""비중/가격 민감도·견고성 분석 데모 — 헤드라인 결론이 가정에 얼마나 견고한가.

임팩트/여력의 헤드라인(여력 축소·강화 과반·감소율 28.6%)은 문서화된 가정(아키타입 비중·지역 mix·
담보가격 분포/수준) 위에 서 있다. 이 데모는 그 가정을 흔들어(규칙은 고정):
  1. OAT 토네이도 — 어떤 가정이 헤드라인을 가장 크게 좌우하는가.
  2. 몬테카를로 밴드 — P5/P50/P95 밴드 + 결론 견고성(성립 표본 비율).
  3. 가격 불변성 — 감소율(%)은 담보가격 수준에 불변, 절대 금액(억)만 비례 이동.

실행: python examples/demo_sensitivity.py
  → 콘솔 요약 + docs/eval/sensitivity_impact.md 갱신(감사/재현용).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from regimpact.impact.sensitivity import (  # noqa: E402
    build_response_table,
    format_bands,
    format_tornado,
    oat_tornado,
    sensitivity_bands,
)

REPO = Path(__file__).resolve().parent.parent
DOC = REPO / "docs" / "eval" / "sensitivity_impact.md"
N = 3000
SEED = 42


def main() -> None:
    table = build_response_table()
    base, bars = oat_tornado(table)
    sb = sensitivity_bands(table, n=N, seed=SEED)

    t_pct = format_tornado(base, bars, "exposure_pct_reduction")
    t_eok = format_tornado(base, bars, "per_unit_delta_eok")
    t_rev = format_tornado(base, bars, "review_share")
    bands = format_bands(sb)

    print("=== OAT 토네이도: 여력 감소율(%) ===")
    print(t_pct)
    print("\n=== OAT 토네이도: 1인당 Δ여력(억) ===")
    print(t_eok)
    print("\n=== 몬테카를로 민감도 밴드 ===")
    print(bands)

    # 가격 불변성 하이라이트
    price_bar = next(b for b in bars if b.assumption.startswith("담보가격 수준"))
    print("\n=== 가격 불변성 하이라이트 ===")
    print(f"  담보가격 수준 ±30% → 여력 감소율 스윙 "
          f"{price_bar.swing('exposure_pct_reduction'):.1%} (사실상 0),")
    print(f"                     1인당 Δ여력 스윙 "
          f"{price_bar.swing('per_unit_delta_eok'):+.2f}억 (비례 이동).")

    _write_doc(sb, t_pct, t_eok, t_rev, price_bar)
    print(f"\n갱신: {DOC.relative_to(REPO)}")


def _write_doc(sb, t_pct, t_eok, t_rev, price_bar) -> None:
    L: list[str] = []
    L.append("# 비중/가격 민감도·견고성 분석 (6·30) — 실측 리포트")
    L.append("")
    L.append("> `examples/demo_sensitivity.py` 산출. 임팩트/여력의 헤드라인 결론이 **문서화된 가정**"
             "(아키타입 비중·지역 mix·담보가격 분포/수준)에 얼마나 **견고한가**를 측정한다.")
    L.append("")
    L.append("## 정직성 고지")
    L.append("")
    L.append("- 이것은 **문서화된 가정 입력에 대한 민감도**이지 **실세계 불확실성의 정량화가 아니다**"
             "(실측 데이터 없음).")
    L.append("- **룰엔진·LTV 로직·시행일·경과규정은 절대 흔들지 않는다** — 사람이 확정한 사실이지 가정이 아니다."
             " 민감도는 오직 예시적 모집단·가격 구성에만 가한다(\"확정 규칙 고정, 가정 입력만 스트레스\").")
    L.append("- 섭동 범위(아키타입 ±50%, 담보가격 ±30%, Dirichlet 집중도 40, 가격 수준 로그정규 σ0.20)도"
             " **문서화된 가정**이다.")
    L.append("")
    L.append("## 1) 무엇이 헤드라인을 좌우하나 (OAT 토네이도)")
    L.append("")
    L.append("### 출력지표 = 여력 감소율(%)")
    L.append("```")
    L.append(t_pct)
    L.append("```")
    L.append("### 출력지표 = 1인당 Δ여력(억)")
    L.append("```")
    L.append(t_eok)
    L.append("```")
    L.append("### 출력지표 = 사람검토 비중(%)")
    L.append("```")
    L.append(t_rev)
    L.append("```")
    L.append("")
    L.append("**핵심 관찰**")
    L.append("")
    L.append("- **여력 감소율(%)**은 오직 **아키타입 비중**(특히 무주택 일반)이 좌우한다. "
             "**담보가격 수준·지역 mix는 영향 0** — 아래 '가격 불변성' 참조.")
    L.append("- **1인당 Δ여력(억)**은 반대로 **담보가격 수준**이 최대 driver다(절대 금액이 가격에 비례). "
             "같은 출력이라도 비율(%)이냐 수준(억)이냐에 따라 driver가 뒤바뀐다.")
    L.append("- **사람검토/산정불가 비중**은 유주택·다주택·정책대출 비중이 좌우한다(여력 금액엔 안 들어가는 셀).")
    L.append("")
    L.append("## 2) 헤드라인 밴드 + 결론 견고성 (몬테카를로)")
    L.append("")
    L.append("```")
    L.append(format_bands(sb))
    L.append("```")
    L.append("")
    L.append("**해석**")
    L.append("")
    r = sb.robustness
    L.append(f"- **방향 결론은 견고하다:** 여력 축소({r['여력 축소(감소율>0)']:.0%})·"
             f"1인당 여력 감소({r['1인당 여력 감소(Δ<0)']:.0%})가 **전 표본에서 성립**.")
    L.append(f"- **크기는 밴드로 말한다:** 여력 감소율 base {sb.base.exposure_pct_reduction:.1%}, "
             f"P5–P95 **[{sb.bands['exposure_pct_reduction'][0]:.1%}, "
             f"{sb.bands['exposure_pct_reduction'][2]:.1%}]** — 점추정 과잉확신 대신 밴드.")
    L.append(f"- **가정-취약한 결론도 정직하게 표기:** '강화 과반(>50%)'은 "
             f"{r['강화 과반(강화>50%)']:.0%} 표본에서만 성립 → "
             "무주택 비중 가정에 따라 흔들리는 결론(방향과 달리 견고하지 않음).")
    L.append("")
    L.append("## 3) 가격 불변성 (Model Risk 인사이트)")
    L.append("")
    L.append(f"- 담보가격을 세그먼트와 **독립·균일**하게 적용하므로, **여력 감소율(%)은 담보가격 수준에 불변**이다: "
             f"±30%를 흔들어도 감소율 스윙 **{price_bar.swing('exposure_pct_reduction'):.1%}**(사실상 0).")
    L.append(f"- 반면 **절대 금액(억)은 가격에 비례**한다: 같은 ±30%에서 1인당 Δ여력 스윙 "
             f"**{price_bar.swing('per_unit_delta_eok'):+.2f}억**.")
    L.append("- **함의:** 감소율은 **모집단 구성**의 진술이고, 억 금액은 **가격 가정**까지 얹은 진술이다. "
             "보고 시 둘을 구분해야 한다(감소율은 상대적으로 견고, 억 금액은 가격 가정에 종속).")
    L.append("")
    DOC.write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    main()
