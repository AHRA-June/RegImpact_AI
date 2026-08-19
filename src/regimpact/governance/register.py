"""AI Risk Register 렌더러 — 판단은 risk.py, 정량은 evidence 에서."""
from __future__ import annotations

from typing import Optional

from ..report.evidence import ValidationEvidence
from .risk import RISKS, Band, ControlState, Risk, by_category, heatmap, summary


def _bar(r: Risk) -> str:
    return (f"{r.inherent_likelihood}×{r.inherent_impact}={r.inherent} "
            f"({r.inherent_band.value}) → "
            f"{r.residual_likelihood}×{r.residual_impact}={r.residual} "
            f"({r.residual_band.value})")


def _controls(r: Risk) -> str:
    mark = {ControlState.OPERATING: "✅", ControlState.PARTIAL: "🟡",
            ControlState.PLANNED: "⬜"}
    lines = []
    for c in r.controls:
        ev = " · ".join(f"`{e}`" for e in c.evidence) or "—"
        lines.append(f"  - {mark[c.state]} **[{c.kind}]** {c.description}<br/>근거: {ev}")
    return "\n".join(lines)


def render(ev: Optional[ValidationEvidence] = None) -> str:
    s = summary()
    hm = heatmap(residual=True)

    rows = []
    for cat, risks in by_category().items():
        rows.append(f"\n### {cat}\n")
        for r in sorted(risks, key=lambda x: -x.residual):
            realized = (f"\n- **실제 발생:** {r.realized_as} — `docs/validation/VALIDATION_REPORT.md` §12"
                        if r.realized_as else "")
            accepted = (f"\n- **잔여위험 수용 근거:** {r.accepted_reason}"
                        if r.accepted_reason else "")
            rows.append(
                f"""#### {r.risk_id} — {r.title}

{r.description}

- **평가:** {_bar(r)} (감소 {r.reduction})
- **통제:**
{_controls(r)}{accepted}{realized}
""")

    grid_rows = []
    for likelihood in range(5, 0, -1):
        cells = []
        for impact in range(1, 6):
            ids = hm.get((likelihood, impact), [])
            cells.append(", ".join(ids) if ids else "")
        grid_rows.append(f"| **L{likelihood}** | " + " | ".join(cells) + " |")
    grid = "\n".join(grid_rows)

    inherent = s["inherent_bands"]
    residual = s["residual_bands"]
    planned = "\n".join(f"- {rid}: {desc}" for rid, desc in s["planned_controls"]) or "- 없음"
    realized_ids = ", ".join(s["realized"])

    live = ""
    if ev is not None:
        live = f"""
## 3. 현재 실측 (검증보고서 연동)

| 통제 | 실측 |
|---|---|
| 인용 verbatim 대조 | Citation Correctness {ev.grounding.citation_correctness:.0%} ({ev.grounding.grounded}/{ev.grounding.total}) |
| 차등 검증 | Rule Regression {ev.regression.pass_rate:.0%} ({ev.regression.passed}/{ev.regression.total}) |
| 판별력 | {len([d for d in ev.discrimination.results if d.detected])}/{len(ev.discrimination.results)} 지표가 오류에 반응 |
| 정책 DB ↔ 기준선 | 드리프트 {"없음" if ev.drift.ok else "발생"} |
| 사람 검토 유도 | 변경안 {ev.proposal.status.value} · 엔진 대조 {ev.consistency.summary()['passed']}/{ev.consistency.summary()['total']} |
| 감사로그 | {len(ev.audit)}건 · 체인 {"OK" if ev.audit.verify().ok else "BROKEN"} |

감사로그 head (외부 앵커): `{ev.audit.head_hash}`
"""

    return f"""# AI Risk Register — RegImpact AI

> 생성: `python examples/build_governance_docs.py` · 정량 수치는 파이프라인 실측에서 온다.
>
> 리스크의 발생가능성·영향은 **측정값이 아니라 판단**이므로 `src/regimpact/governance/risk.py`
> 에 사람이 적는다. 대신 통제는 말로 끝나지 않게 **실재하는 코드·테스트를 가리키도록 강제**한다
> — `tests/test_governance.py` 가 참조 경로의 존재를 확인한다.

## 1. 평가 방법론

**Rating = Likelihood(1~5) × Impact(1~5)**
Low 1–4 · Medium 5–9 · High 10–15 · Critical 16–25

Impact 기준은 도메인 특수하다 — 잘못된 규제 사실·LTV 오판이 여신 의사결정과 고객 피해로
전파되는 정도로 잰다.

통제 유형: **[검증]** 결정론적 검사 · **[설계]** 아키텍처 통제 · **[프로세스]** 운영 규율
상태: ✅ 운영 · 🟡 부분 · ⬜ 계획

**잔여위험은 0으로 만들지 않는다.** 통제 후에도 남는 것을 정직하게 적고, 수용한다면 근거를 남긴다.

## 2. 요약

- 등록 리스크 **{s['total']}건** / {s['categories']}범주
- 고유위험: Critical {inherent['Critical']} · High {inherent['High']} · Medium {inherent['Medium']} · Low {inherent['Low']}
- 잔여위험: Critical {residual['Critical']} · High {residual['High']} · Medium {residual['Medium']} · Low {residual['Low']}
- **실제 발생 이력이 있는 리스크: {realized_ids}** — 가상의 목록이 아니라는 뜻이다
- 미구현 통제:
{planned}

### 잔여위험 히트맵

| | I1 | I2 | I3 | I4 | I5 |
|---|---|---|---|---|---|
{grid}

잔여 High 는 **R-RUL-02(명세 자체의 원문 오독)** 하나다. 차등검증으로 잡을 수 없는 범주라
의도적으로 높게 유지한다 — 실제로 R-01 이 이 경로로 발생했고, 어떤 지표로도 잡히지 않았다.
{live}
## 4. 리스크 상세
{"".join(rows)}
## 5. 이 레지스터의 한계

- 발생가능성·영향은 **1인 작성자의 판단**이며 외부 검증을 받지 않았다
- 통제의 **존재**는 테스트로 강제하지만, 통제의 **충분성**은 판단 영역이다
- 운영 이력이 없어 발생 빈도는 사후 데이터가 아니라 사전 추정이다
"""
