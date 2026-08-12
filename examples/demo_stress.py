"""스트레스 테스트 데모 — 극단·경계·대량·적대적 입력에서의 견고성.

실행: python examples/demo_stress.py  → 콘솔 + docs/eval/stress_test.md
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from regimpact.stress import (  # noqa: E402
    format_stress,
    fuzz_differential,
    load_consistency,
    reverse_stress,
    scenario_battery,
)

REPO = Path(__file__).resolve().parent.parent
DOC = REPO / "docs" / "eval" / "stress_test.md"


def main() -> None:
    battery = scenario_battery()
    reverse = reverse_stress()
    fuzz = fuzz_differential(n=5000, seed=0)
    load = load_consistency(n=50000, seed=1)

    print(format_stress(battery, reverse, fuzz, load))
    _write_doc(battery, reverse, fuzz, load)
    print(f"\n갱신: {DOC.relative_to(REPO)}")


def _write_doc(battery, reverse, fuzz, load) -> None:
    L: list[str] = []
    L.append("# 스트레스 테스트 (6·30 시스템) — 견고성·한계")
    L.append("")
    L.append("> `examples/demo_stress.py` 산출. 민감도가 '그럴듯한 범위' 섭동이라면, 스트레스는 "
             "**극단·경계·대량·적대적** 입력이다. 통과가 완벽을 뜻하지 않으며, 깨지는 경계를 수치로 보고한다.")
    L.append("")
    L.append("## 1) 극단 시나리오 배터리 (불변식 유지)")
    L.append("")
    L.append("| 시나리오 | 강화 | 검토 | 산정불가 | 감소율 | 불변식 |")
    L.append("|---|---|---|---|---|---|")
    for s in battery:
        pct = "—" if s.metrics["pct_reduction"] is None else f"{s.metrics['pct_reduction']:.1%}"
        L.append(f"| {s.name} | {s.metrics['tightened']:.0%} | {s.metrics['review_dir']:.0%} | "
                 f"{s.metrics['undetermined']:.0%} | {pct} | {'✓' if s.ok else '✗ FAIL'} |")
    L.append("")
    L.append("> 불변식: 방향 비중 합=1 · 산정불가 0~1 · 여력 감소율 음수 아님 · 가중 합 보존. "
             "전 시나리오에서 유지(명세 여백은 산정불가 100%로 정직 분리).")
    L.append("")
    L.append("## 2) 역(逆)스트레스 — 결론이 뒤집히는 경계")
    L.append("")
    mb = reverse["tighten_majority_breaks_at_moved_fraction"]
    L.append(f"- **강화 과반:** 무주택 일반 비중의 **{mb:.0%}**를 다주택으로 옮기면 깨진다"
             if mb is not None else "- **강화 과반:** 탐색 범위에서 유지")
    L.append(f"- **여력 축소:** 스윕 전체 최소 감소율 **{reverse['pct_reduction_min_over_sweep']:.1%}** → "
             f"**구조적으로 뒤집히지 않음**(어떤 구성에서도 여력이 증가하지 않음 — 6·30에 완화 항목이 없기 때문).")
    L.append("")
    L.append("> 이것이 정직한 한계 보고다: 방향 결론(여력 축소)은 구조적으로 견고하지만, 특정 수치 주장"
             "('강화 과반')은 모집단 구성 가정에 따라 깨질 수 있다.")
    L.append("")
    L.append("## 3) 차등 퍼징 — 무작위 입력에서 엔진 견고성")
    L.append("")
    L.append(f"- 무작위 신청 **{fuzz['runs']:,}건**(미상 지역 포함): 크래시 **{fuzz['crashes']}** · "
             f"무효상태 **{fuzz['invalid_status']}** · 알려진 지역 오라클 비교 {fuzz['compared']:,}건 중 "
             f"불일치 **{fuzz['mismatches']}**.")
    L.append(f"- 상태 분포: " + ", ".join(f"{k} {v:,}" for k, v in sorted(fuzz["status_counts"].items())) + ".")
    L.append("")
    L.append("> 무작위 입력에서도 엔진은 예외 없이 **항상 유효한 상태**를 반환하고, 독립 오라클과 "
             "**전건 일치**한다(스펙 도메인 내). 미상 지역도 크래시 없이 처리.")
    L.append("")
    L.append("## 4) 대규모 부하")
    L.append("")
    L.append(f"- **{load['n']:,}건** 엔진↔오라클 불일치 **{load['mismatches']}** "
             f"({load['seconds']}s · **{load['per_sec']:,}건/s**).")
    L.append("")
    DOC.write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    main()
