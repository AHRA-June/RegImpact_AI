"""Impact Matrix 사람이 읽는 리포트 (데모·CI 로그·UI 연동 기준 출력).

tc_generator.regression.format_report 와 같은 스타일. UI(Stitch) 연동 시 하드코딩값을
이 구조의 실제 산출로 교체한다(docs/01_PROJECT_STATE.md NEXT).
"""
from __future__ import annotations

from ..models import EvaluationStatus, LtvDecision
from .matrix import ImpactDirection, ImpactMatrix

_ARROW = {
    ImpactDirection.TIGHTENED: "▼ 강화",
    ImpactDirection.LOOSENED: "▲ 완화",
    ImpactDirection.UNCHANGED: "= 동일",
    ImpactDirection.REVIEW: "⚠ 검토",
}


def _ltv_cell(dec: LtvDecision) -> str:
    """판정을 표 셀 문자열로. DECIDED면 퍼센트, 아니면 상태 라벨."""
    if dec.status == EvaluationStatus.DECIDED and dec.max_ltv is not None:
        return f"{dec.max_ltv:.0%}"
    return dec.status.value


def _delta_cell(row) -> str:
    if row.delta_ltv is None:
        return "-"
    # 퍼센트포인트 표기 (+/-). 0은 0pp.
    pp = row.delta_ltv * 100
    sign = "+" if pp > 0 else ""
    return f"{sign}{pp:.0f}pp"


def format_matrix(matrix: ImpactMatrix) -> str:
    """Impact Matrix 요약표를 텍스트로 렌더링."""
    lines: list[str] = []
    lines.append("=" * 72)
    lines.append("RegImpact — Impact Matrix (시행 전/후 세그먼트 영향)")
    lines.append("=" * 72)
    pol = f"  policy={matrix.policy_id}" if matrix.policy_id else ""
    lines.append(
        f"region={matrix.region_code}  "
        f"before={matrix.before_date.isoformat()}  "
        f"after={matrix.after_date.isoformat()}{pol}"
    )
    lines.append("")
    lines.append(f"  {'세그먼트':<18} {'before':>16} {'after':>16} {'Δ':>7}  방향")
    lines.append("  " + "-" * 68)
    for r in matrix.rows:
        lines.append(
            f"  {r.segment.label:<18} "
            f"{_ltv_cell(r.before):>16} {_ltv_cell(r.after):>16} "
            f"{_delta_cell(r):>7}  {_ARROW[r.direction]}"
        )

    # 방향 요약
    s = matrix.summary()
    lines.append("")
    lines.append(
        f"요약: 강화 {s[ImpactDirection.TIGHTENED.value]} · "
        f"완화 {s[ImpactDirection.LOOSENED.value]} · "
        f"동일 {s[ImpactDirection.UNCHANGED.value]} · "
        f"검토 {s[ImpactDirection.REVIEW.value]}"
    )

    # 검토 필요 사유 노출(정직성)
    if matrix.review_required:
        lines.append("")
        lines.append("검토 필요(사람 확정):")
        for r in matrix.review_required:
            lines.append(f"  ⚠ {r.segment.label}: {r.note or '판정 불가'}")

    lines.append("=" * 72)
    return "\n".join(lines)
