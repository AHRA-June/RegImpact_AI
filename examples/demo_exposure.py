"""대출 여력 영향 금액 집계 데모 — 6·30 규제의 금액 환산.

Impact Matrix의 LTV %p 변화를 문서화된 담보가격 밴드와 결합해 대출 여력(한도) 변화 금액을
산출한다. 두 경로가 같은 분포로 수렴함을 보인다:
  (1) 아키타입×지역 정확 가중 프로파일 × 밴드 곱  → compute_exposure
  (2) 수천 명 몬테카를로 표본 + 담보가격 몬테카를로 부여 → compute_exposure

실행: python examples/demo_exposure.py
  → 콘솔 요약 + docs/eval/exposure_impact.md 갱신(감사/재현용).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from regimpact.impact import (  # noqa: E402
    attach_sampled_prices,
    compute_exposure,
    enumerate_weighted_profiles,
    format_exposure,
    price_model_note,
    sample_portfolio,
    weight_model_note,
)

REPO = Path(__file__).resolve().parent.parent
DOC = REPO / "docs" / "eval" / "exposure_impact.md"


def main() -> None:
    # 경로 1: 정확 가중 프로파일(아키타입×지역), 밴드는 compute_exposure가 곱한다
    exact = enumerate_weighted_profiles()
    rep_exact = compute_exposure(exact)

    print("=== 경로 1: 정확 가중 프로파일 × 담보가격 밴드 ===")
    print(format_exposure(rep_exact))

    # 경로 2: 몬테카를로 표본 + 담보가격 몬테카를로 부여
    sample = attach_sampled_prices(sample_portfolio(n=5000, seed=42), seed=7)
    rep_sample = compute_exposure(sample)
    print("\n=== 경로 2: 몬테카를로 표본 5000명(담보가격도 몬테카를로) ===")
    pct = rep_sample.pct_reduction
    print(f"판정가능 여력  전 {rep_sample.before_capacity:.1f}억 → 후 {rep_sample.after_capacity:.1f}억"
          f"  (감소율 {pct:.1%})" if pct is not None else "")
    print(f"1인당 평균 여력  전 {rep_sample.per_unit_before():.2f}억 → 후 {rep_sample.per_unit_after():.2f}억"
          f"  (Δ {rep_sample.per_unit_delta():+.2f}억)")
    print(f"산정불가 비중 {rep_sample.undetermined_share:.1%}")

    # 두 경로 1인당 평균 감소율 비교(수렴 확인)
    print("\n=== 수렴 확인(1인당 감소율) ===")
    print(f"  정확 가중  {rep_exact.pct_reduction:.2%}")
    print(f"  표본 5000  {rep_sample.pct_reduction:.2%}")

    _write_doc(rep_exact, rep_sample)
    print(f"\n갱신: {DOC.relative_to(REPO)}")


def _write_doc(rep_exact, rep_sample) -> None:
    e, s = rep_exact, rep_sample
    lines: list[str] = []
    lines.append("# 대출 여력 영향 금액 집계 (6·30) — 실측 리포트")
    lines.append("")
    lines.append("> `examples/demo_exposure.py` 산출. Impact Matrix의 LTV %p 변화를 문서화된 "
                 "담보가격 밴드와 결합해 **대출 여력(한도) 변화 금액**으로 환산한다.")
    lines.append("")
    lines.append("## 정직성 고지 (4가지)")
    lines.append("")
    lines.append("1. **여력(한도) 변화**이지 **실행액(originations)이 아니다.** 실제 실행은 수요·DSR·"
                 "차주 선택에 좌우된다 — 여기서는 규제가 허용하는 최대 담보대출 한도만 비교한다.")
    lines.append("2. **LTV 규칙만** 반영한다. 가격대별 **대출 최대한도 상한(6억/4억/2억)**은 미적용"
                 "(별도 Discovery). 상한 적용 시 고가 밴드 여력은 더 줄어 → 본 산정은 **상한(upper bound)** 성격.")
    lines.append("3. 담보가격 분포는 **문서화된 시나리오 가정**(실측 아님). 실측 확보 시 표만 교체.")
    lines.append("4. 자동판정 불가분(명세 여백, 예: 비규제 유주택 시행 전 기준선)은 **'산정 불가'로 분리**"
                 "(0으로 뭉개지 않음).")
    lines.append("")
    lines.append("## 가정 모델")
    lines.append("")
    lines.append(f"- {weight_model_note()}")
    lines.append(f"- {price_model_note()}")
    lines.append("")
    lines.append("## 결과 — 경로 1: 정확 가중 프로파일 × 밴드")
    lines.append("")
    lines.append("```")
    lines.append(format_exposure(e))
    lines.append("```")
    lines.append("")
    lines.append("## 결과 — 경로 2: 몬테카를로 표본 5000명")
    lines.append("")
    pu_reduction = s.pct_reduction
    lines.append(f"- 판정가능 여력: 전 {s.before_capacity:.1f}억 → 후 {s.after_capacity:.1f}억 "
                 f"(감소율 **{pu_reduction:.1%}**)")
    lines.append(f"- 1인당 평균 여력: 전 {s.per_unit_before():.2f}억 → 후 {s.per_unit_after():.2f}억 "
                 f"(Δ **{s.per_unit_delta():+.2f}억**)")
    lines.append(f"- 산정불가 비중: {s.undetermined_share:.1%}")
    lines.append("")
    lines.append("## 수렴 확인 (1인당 여력 감소율)")
    lines.append("")
    lines.append("| 경로 | 감소율 |")
    lines.append("|---|---|")
    lines.append(f"| 정확 가중 프로파일 | {e.pct_reduction:.2%} |")
    lines.append(f"| 몬테카를로 5000명 | {s.pct_reduction:.2%} |")
    lines.append("")
    lines.append("> 두 경로가 같은 분포를 공유하므로 1인당 감소율이 수렴한다(표본이 크면 일치에 근접).")
    lines.append("")
    DOC.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
