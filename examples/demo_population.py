"""가중 합성 모집단 데모 — 비중 실측화 + 수천 건 확장 (오프라인).

(1) 정확 가중 프로파일(아키타입×지역)로 가중 포트폴리오 임팩트 통계를 낸다.
(2) 같은 비중 모델에서 5,000명 몬테카를로 표본을 뽑아 (1)에 수렴함을 보인다.
(3) 5,000명 표본을 룰엔진 ⟷ 독립 오라클로 회귀 검증(수천 건 분모).

⚠️ 비중은 실제 은행 데이터가 아니라 문서화된 시나리오 가정. 실행: python examples/demo_population.py
"""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from regimpact import evaluate  # noqa: E402
from regimpact.impact import (  # noqa: E402
    analyze_impact,
    enumerate_weighted_profiles,
    sample_portfolio,
    weight_model_note,
)
from regimpact.tc_generator.oracle import expected_outcome  # noqa: E402

AFTER = date(2026, 7, 2)


def _summary(matrix, label: str) -> None:
    ds = matrix.direction_weight_share()
    wmd = matrix.weighted_mean_delta()
    print(f"[{label}]  n={len(matrix.rows)}")
    print(f"   강화 {ds['TIGHTENED']:.1%} · 유지 {ds['UNCHANGED']:.1%} · "
          f"검토(수치불가) {ds['NEEDS_REVIEW']:.1%}")
    print(f"   가중평균 Δ {wmd * 100:+.1f}pp · 사람검토 필요 {matrix.review_weight_share():.1%}")


def main() -> None:
    print(weight_model_note(), "\n")

    # (1) 정확 가중 프로파일
    _summary(analyze_impact(enumerate_weighted_profiles()), "정확 가중 프로파일 (아키타입×지역)")

    # (2) 몬테카를로 5,000명 — (1)에 수렴
    sample = sample_portfolio(n=5000, seed=42)
    _summary(analyze_impact(sample), "몬테카를로 표본 5,000명")

    # (3) 표본 회귀 (engine ⟷ oracle) — 수천 건 분모
    ok = 0
    for seg in sample:
        app = seg.application(AFTER)
        exp = expected_outcome(app)
        act = evaluate(app)
        if act.status == exp.status and act.max_ltv == exp.max_ltv:
            ok += 1
    print(f"\n표본 회귀(engine ⟷ 독립 오라클): {ok}/{len(sample)} 일치 = {ok / len(sample):.2%}")
    print("주: 비중은 문서화된 가정(실측 아님). 실측 데이터 확보 시 population.py 비중표만 교체.")


if __name__ == "__main__":
    main()
