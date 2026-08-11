"""Validation Report — E2E 산출물을 사람 검토용 검증보고서(Markdown)로 조립.

브리프 §18 "코어 완성"의 최종 노드: Source→Impact→Proposal→TestCases→Regression→
Assurance→**Human Review→Validation Report** 를 한 문서로 묶는다.

거버넌스(브리프 §16~17): 승인 상태 필드 + audit trail을 포함해, 이 분석이 언제/어떤
원문/어떤 모델·룰 버전으로 만들어졌는지 재현 가능하게 남긴다. LLM은 초안만 제안하고
최종 결정은 사람이 한다(status=DRAFT/REVIEW_REQUIRED).
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Optional

from ..assurance.evaluate import AssuranceGate, AssuranceReport
from ..proposal.schema import ProposalStatus, RuleChangeProposal


@dataclass
class ReportMeta:
    """audit / 재현용 메타(브리프 §17). 비결정 값(시각·event_id)은 주입식."""
    system_version: str = "0.1.0"
    model_name: str = "deterministic-rule-engine + extractor(claude-opus-5)"
    prompt_version: Optional[str] = None
    generated_at: Optional[str] = None   # ISO datetime (런타임 주입; 없으면 미표기)
    event_id: Optional[str] = None
    reviewer: Optional[str] = None
    reviewed_at: Optional[str] = None


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass
class ValidationReport:
    policy_id: str
    proposal: RuleChangeProposal
    matrix: object                 # impact.ImpactMatrix
    coverage: dict
    regression: object             # tc_generator.RegressionReport
    fidelity: object               # tc_generator.FidelityReport
    grounding: object              # extractor.GroundingReport
    gold: object                   # extractor.GoldReport
    assurance: AssuranceReport
    meta: ReportMeta = field(default_factory=ReportMeta)
    source_hashes: dict = field(default_factory=dict)

    # ── 승인 상태: Assurance gate + proposal status 결합 ──
    @property
    def decision_status(self) -> str:
        if self.assurance.gate == AssuranceGate.REVIEW_REQUIRED:
            return ProposalStatus.NEEDS_REVIEW.value
        return self.proposal.status.value

    def to_dict(self) -> dict:
        return {
            "policy_id": self.policy_id,
            "decision_status": self.decision_status,
            "assurance": self.assurance.to_dict(),
            "impact_summary": self.matrix.summary(),
            "proposal": self.proposal.to_dict(),
            "coverage": self.coverage,
            "regression": {
                "pass_rate": self.regression.pass_rate,
                "total": self.regression.total,
                "passed": self.regression.passed,
            },
            "fidelity": self.fidelity.summary(),
            "grounding": {
                "citation_correctness": self.grounding.citation_correctness,
                "total": self.grounding.total,
                "grounded": self.grounding.grounded,
            },
            "audit": self._audit_block(),
        }

    def _audit_block(self) -> dict:
        return {
            "event_id": self.meta.event_id,
            "timestamp": self.meta.generated_at,
            "policy_id": self.policy_id,
            "source_hashes": self.source_hashes,
            "system_version": self.meta.system_version,
            "model_name": self.meta.model_name,
            "prompt_version": self.meta.prompt_version,
            "decision_status": self.decision_status,
            "reviewer": self.meta.reviewer,
            "reviewed_at": self.meta.reviewed_at,
        }

    def render_markdown(self) -> str:
        p, a = self.proposal, self.assurance
        gate = a.gate
        gate_badge = "✅ PASS" if gate == AssuranceGate.PASS else "⚠️ REVIEW REQUIRED"
        L: list[str] = []

        L.append(f"# 검증보고서 — {self.policy_id}")
        L.append("")
        L.append(f"> **Assurance Gate: {gate_badge}** · 결정상태: `{self.decision_status}`")
        L.append(">")
        L.append("> LLM은 초안만 제안하며, 최종 결정은 사람이 승인한다(브리프 §9·§16).")
        L.append("")

        # 1. RegChange 요약
        L.append("## 1. 규제 변경 요약 (RegChange)")
        L.append(f"- 대상지역: {', '.join(p.after.target_regions)}")
        L.append(f"- 시행일: {p.after.effective_from}")
        L.append(f"- 변경 항목: {self.grounding.total}건 · 인용 정합 "
                 f"{self.grounding.grounded}/{self.grounding.total} "
                 f"({self.grounding.citation_correctness:.0%})")
        L.append("")

        # 2. Impact Matrix
        s = self.matrix.summary()
        L.append("## 2. Impact Matrix (엔진 실측)")
        L.append(f"세그먼트 {s['total_segments']} (코어 {s['core_segments']}/Discovery "
                 f"{s['discovery_segments']}) · 규제강화 {s['tightened']} · 경과규정 "
                 f"{s['grandfathered']} · 고영향 {s['high_impact']} · 기준부재 {s['baseline_gap']}")
        L.append("")
        L.append("| 지역 | 차주유형 | 기존 | 변경 | 경과 | reason_code |")
        L.append("|---|---|---|---|---|---|")
        for r in self.matrix.rows:
            gf = "해당" if r.grandfathering else "-"
            L.append(f"| {r.region_label} | {r.borrower_type} | {r.before_display} | "
                     f"{r.after_display} | {gf} | {', '.join(r.reason_codes) or '-'} |")
        L.append("")

        # 3. Rule Change Proposal
        L.append("## 3. Rule Change Proposal (구조화 변경안)")
        L.append(f"- rule_id: `{p.rule_id}` · change_type: `{p.change_type.value}` · "
                 f"status: `{p.status.value}`")
        L.append(f"- LTV: {p.before.max_ltv:.0%} → {p.after.max_ltv:.0%} "
                 f"({p.before.region_status} → {p.after.region_status})")
        L.append(f"- 예외: {', '.join(p.exceptions) or '없음'}")
        if p.grandfathering:
            L.append(f"- 경과규정: 컷오프 {p.grandfathering.cutoff_date} · "
                     f"조건 {', '.join(p.grandfathering.conditions)}")
        L.append(f"- 근거 인용: {len(p.sources)}건 (필드별 원문 추적)")
        L.append("")

        # 4. Test Coverage & Regression & Fidelity
        cov = self.coverage
        fid = self.fidelity.summary()
        L.append("## 4. 테스트 커버리지 · 회귀 · 충실성")
        L.append(f"- Coverage: 제안 주장 {cov['covered_claims']}/{cov['total_claims']} 커버 "
                 f"(covered={cov['covered']})")
        L.append(f"- Regression (engine⟷oracle): {self.regression.passed}/{self.regression.total} "
                 f"= {self.regression.pass_rate:.0%}")
        L.append(f"- Fidelity (engine⟷proposal): {fid['passed']}/{fid['total']} "
                 f"(all_passed={fid['all_passed']})")
        L.append("")

        # 5. Assurance Evaluation (4 dimension)
        L.append("## 5. Assurance Evaluation (깊은 4 dimension)")
        L.append("| Dim | 항목 | 통과 | 핵심 지표 |")
        L.append("|---|---|---|---|")
        for d in a.dimensions:
            mark = "✅" if d.passed else "❌"
            metric_bits = ", ".join(f"{k}={v}" for k, v in list(d.metrics.items())[:2])
            L.append(f"| {d.dim_id} | {d.title} | {mark} | {metric_bits} |")
        L.append("")

        # 6. Human Review / Approval
        L.append("## 6. Human Review / Approval")
        L.append(f"- 결정상태: `{self.decision_status}` (승인 시 → APPROVED → rule registry 반영)")
        if a.escalations:
            L.append(f"- **검토 필수 사유 ({len(a.escalations)}):**")
            for e in a.escalations:
                L.append(f"  - {e}")
        else:
            L.append("- 검증 실패 없음 — 사람 최종 승인 대기.")
        if a.notes:
            L.append(f"- 참고(설계상 gap, {len(a.notes)}):")
            for n in a.notes:
                L.append(f"  - {n}")
        L.append("")

        # 7. Audit trail (재현용)
        L.append("## 7. Audit Trail (재현용, 브리프 §17)")
        audit = self._audit_block()
        for k, v in audit.items():
            if k == "source_hashes":
                L.append(f"- {k}:")
                for doc, h in v.items():
                    L.append(f"  - {doc}: `{h[:16]}…`")
            else:
                L.append(f"- {k}: `{v if v is not None else '(런타임 주입)'}`")
        L.append("")
        L.append("> 한계: LOCKED TEST/CHALLENGE는 미개봉(Phase 3). 이 보고서는 6·30 앵커 1건 "
                 "E2E 스모크이며, 골드셋 전량 성능평가가 아니다(브리프 §12).")
        return "\n".join(L)


def build_validation_report(
    *,
    proposal,
    matrix,
    coverage: dict,
    regression,
    fidelity,
    grounding,
    gold,
    assurance: AssuranceReport,
    policy_id: Optional[str] = None,
    sources: Optional[dict] = None,
    meta: Optional[ReportMeta] = None,
) -> ValidationReport:
    """E2E 산출물을 검증보고서로 조립한다. sources를 주면 source_hash를 계산.

    policy_id 미지정 시 proposal.sources[0].policy_id → 없으면 rule_id로 폴백.
    """
    if policy_id is None:
        policy_id = proposal.sources[0].policy_id if proposal.sources else proposal.rule_id
    source_hashes = {doc: _sha256(text) for doc, text in (sources or {}).items()}
    return ValidationReport(
        policy_id=policy_id,
        proposal=proposal,
        matrix=matrix,
        coverage=coverage,
        regression=regression,
        fidelity=fidelity,
        grounding=grounding,
        gold=gold,
        assurance=assurance,
        meta=meta or ReportMeta(),
        source_hashes=source_hashes,
    )
