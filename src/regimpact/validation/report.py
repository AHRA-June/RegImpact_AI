"""Validation Report (검증보고서 stub) — 파이프라인 산출을 하나로 조립.

Walking Skeleton(docs/04_PLAN.md Phase 1)의 **[8] Validation Report 노드(stub).**

파이프라인 각 노드의 실제 산출(Extractor·Impact Matrix·Rule Proposal·Rule-Regression)을
하나의 보고서로 묶어 **6·30 1건이 원문→판정→영향→제안→검증까지 관통**됨을 보인다.
정식 15~20쪽 보고서(브리프 §18, Phase 3)의 골격이며, 여기서는 실데이터 조립 + 요약을 담당한다.

정직성: 각 노드의 present/missing 상태와 사람 검토 필요 건수를 그대로 노출한다(과대약속 금지).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ..impact.matrix import ImpactMatrix
from ..proposal.schema import ApprovalStatus, RuleChangeProposal


@dataclass
class ValidationReport:
    """파이프라인 E2E 산출 묶음 + 관통 상태."""
    scenario_title: str
    policy_id: Optional[str]
    effective_from: Optional[str]
    target_regions: list[str]

    # 노드 산출(있으면 채워짐)
    extraction: object = None            # RegChangeExtraction
    matrix: Optional[ImpactMatrix] = None
    proposal: Optional[RuleChangeProposal] = None
    regression: object = None            # RegressionReport
    assurance: Optional[dict] = None     # {지표: 값} (선택, 부분)

    def node_status(self) -> dict[str, bool]:
        """파이프라인 노드별 산출 존재 여부(관통 현황)."""
        return {
            "extraction": self.extraction is not None,
            "impact_matrix": self.matrix is not None,
            "rule_proposal": self.proposal is not None,
            "rule_regression": self.regression is not None,
            "assurance": self.assurance is not None,
        }

    @property
    def review_required_count(self) -> int:
        """사람 검토 필요 세그먼트 수(제안 기준, 없으면 매트릭스 기준)."""
        if self.proposal is not None:
            return len(self.proposal.review_required_lines)
        if self.matrix is not None:
            return len(self.matrix.review_required)
        return 0

    @property
    def is_pipeline_complete(self) -> bool:
        """핵심 노드(추출·영향·제안·회귀)가 모두 존재하면 관통으로 본다."""
        s = self.node_status()
        return all(s[k] for k in ("extraction", "impact_matrix", "rule_proposal", "rule_regression"))


def build_report(
    scenario_title: str,
    extraction=None,
    matrix: Optional[ImpactMatrix] = None,
    proposal: Optional[RuleChangeProposal] = None,
    regression=None,
    assurance: Optional[dict] = None,
) -> ValidationReport:
    """파이프라인 산출들을 검증보고서로 조립한다. 메타는 있는 소스에서 유도."""
    policy_id = (
        getattr(extraction, "policy_id", None)
        or (matrix.policy_id if matrix else None)
        or (proposal.policy_id if proposal else None)
    )
    effective_from = getattr(extraction, "effective_from", None) or (
        proposal.effective_from if proposal else None
    )
    regions = list(
        getattr(extraction, "target_regions", None)
        or (proposal.target_regions if proposal else None)
        or ([matrix.region_code] if matrix else [])
    )
    return ValidationReport(
        scenario_title=scenario_title,
        policy_id=policy_id,
        effective_from=effective_from,
        target_regions=regions,
        extraction=extraction,
        matrix=matrix,
        proposal=proposal,
        regression=regression,
        assurance=assurance,
    )


# ---------------------------------------------------------------------------
# 사람이 읽는 마크다운 렌더
# ---------------------------------------------------------------------------
def _fmt_ltv(v: Optional[float]) -> str:
    return "—" if v is None else f"{v:.0%}"


def _fmt_delta(v: Optional[float]) -> str:
    if v is None:
        return "—"
    pp = v * 100
    return f"{pp:+.0f}pp" if pp != 0 else "0pp"


def format_report_md(report: ValidationReport) -> str:
    """검증보고서를 마크다운으로 렌더(데모·CI·산출물용)."""
    L: list[str] = []
    L.append(f"# 검증보고서 (Validation Report) — {report.scenario_title}")
    L.append("")
    L.append(f"- 정책: `{report.policy_id or '-'}`")
    L.append(f"- 시행일: `{report.effective_from or '-'}`")
    L.append(f"- 대상지역: {', '.join(f'`{r}`' for r in report.target_regions) or '-'}")
    L.append("")

    # 1. 파이프라인 관통 현황
    L.append("## 1. 파이프라인 관통 현황")
    labels = {
        "extraction": "[2] RegChange Extractor",
        "impact_matrix": "[3] Impact Matrix",
        "rule_proposal": "[4] Rule Change Proposal",
        "rule_regression": "[5] TC / Rule-Regression",
        "assurance": "[6] Assurance",
    }
    for key, present in report.node_status().items():
        mark = "✅" if present else "⬜"
        L.append(f"- {mark} {labels[key]}")
    verdict = "관통(핵심 노드 완결)" if report.is_pipeline_complete else "부분 관통"
    L.append(f"\n**판정: {verdict}.**")
    L.append("")

    # 2. 규제 변경 요약(Extractor)
    if report.extraction is not None:
        changes = getattr(report.extraction, "changes", []) or []
        L.append("## 2. 규제 변경 요약 (원문 추출)")
        L.append(f"- 추출 변경 항목: {len(changes)}건")
        for c in changes:
            summ = getattr(c, "summary", "")
            cat = getattr(c, "category", "")
            L.append(f"  - `{cat}` {summ}")
        L.append("")

    # 3. 영향 매트릭스(Impact Matrix)
    if report.matrix is not None:
        m = report.matrix
        L.append("## 3. 시행 전/후 영향 매트릭스")
        L.append(f"- 지역 `{m.region_code}` · 전 `{m.before_date.isoformat()}` → 후 `{m.after_date.isoformat()}`")
        L.append("")
        L.append("| 세그먼트 | 시행 전 | 시행 후 | Δ | 방향 |")
        L.append("|---|---|---|---|---|")
        for r in m.rows:
            L.append(
                f"| {r.segment.label} | {_fmt_ltv(r.before_ltv)} | {_fmt_ltv(r.after_ltv)} "
                f"| {_fmt_delta(r.delta_ltv)} | {r.direction.value} |"
            )
        s = m.summary()
        L.append("")
        L.append(
            f"요약: 강화 {s['TIGHTENED']} · 완화 {s['LOOSENED']} · "
            f"동일 {s['UNCHANGED']} · 검토 {s['REVIEW']}"
        )
        L.append("")

    # 4. 룰 변경 제안(Proposal) + 사람 검토
    if report.proposal is not None:
        p = report.proposal
        L.append("## 4. 룰 변경 제안 (AI초안 → 사람확정)")
        L.append(f"- 제안 ID: `{p.proposal_id}`")
        L.append(f"- 승인 상태: **{p.approval.status.value}**"
                 + (f" (검토자 {p.approval.reviewer})" if p.approval.reviewer else ""))
        if p.approval.note:
            L.append(f"  - 검토 노트: {p.approval.note}")
        L.append(f"- 제안 행: {len(p.lines)}건 (사람 검토 필요 {len(p.review_required_lines)}건)")
        L.append("")
        L.append("| 세그먼트 | rule_id | 전→후 | reason_code | 검토 |")
        L.append("|---|---|---|---|---|")
        for ln in p.lines:
            tr = f"{_fmt_ltv(ln.before_ltv)}→{_fmt_ltv(ln.after_ltv)}"
            rc = ", ".join(ln.reason_codes) or "-"
            flag = "⚠" if ln.needs_review else ""
            L.append(f"| {ln.segment_label} | `{ln.rule_id or '-'}` | {tr} | `{rc}` | {flag} |")
        L.append("")

    # 5. 룰 회귀(Regression)
    if report.regression is not None:
        reg = report.regression
        pr = getattr(reg, "pass_rate", None)
        passed = getattr(reg, "passed", None)
        total = getattr(reg, "total", None)
        L.append("## 5. 룰 회귀 검증 (엔진 ⟷ 독립 오라클)")
        if pr is not None:
            L.append(f"- Rule-regression Pass Rate: {passed}/{total} = {pr:.1%}")
        by = getattr(reg, "pass_rate_by_category", None)
        if callable(by):
            for cat, (p_, n_, rate) in by().items():
                L.append(f"  - {cat}: {p_}/{n_} ({rate:.0%})")
        L.append("")

    # 6. Assurance(부분)
    if report.assurance is not None:
        L.append("## 6. Assurance (4 dimension 스코어카드, 확정 임계값)")
        for k, v in report.assurance.items():
            L.append(f"- {k}: {v}")
        L.append("")

    # 7. 한계 명시(정직성)
    L.append("## 7. 한계 (정직성)")
    L.append("- 이 보고서는 6·30 단일 앵커 기준 stub 이다(정식 15~20쪽 아님).")
    if report.review_required_count:
        L.append(f"- 사람 검토 필요 세그먼트 {report.review_required_count}건 — 자동 확정 보류(escalation).")
    if report.assurance is None:
        L.append("- Assurance 정량 지표는 부분(Citation grounding 위주). 4 dimension 정량화는 Phase 3.")
    if report.proposal is not None and report.proposal.approval.status == ApprovalStatus.PENDING_REVIEW:
        L.append("- 룰 변경 제안은 **초안**이며 사람 승인 전이다(LOCKED §4).")
    return "\n".join(L)
