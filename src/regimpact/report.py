"""Validation Report — 6·30 시나리오의 End-to-End 검증 보고서 (Walking Skeleton 완결선).

브리프 §18 '코어 완성의 정의': Source Snapshot → Policy Version → Before/After(RegChange) →
Impact Matrix → Rule Change Proposal → Test Cases → Deterministic Rule Regression →
Assurance → Human Review → Validation Report 로 E2E 완결.

이 모듈은 그 파이프라인을 실제로 관통시켜 **하나의 구조화 리포트 객체**로 집계한다. 값은 각
단계의 실제 산출물(gold·엔진·회귀)에서 오며, 미측정(LLM 의존)은 지어내지 않고 표기한다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from .eval import load_final_eval, load_manifest, run_gold_regression
from .extractor import SOURCE_REGISTRY, load_gold, measured_assurance
from .impact import ImpactMatrix, build_impact_matrix
from .impact.segments import REGION_LABELS
from .proposal import ApprovalStatus, Escalation, RuleChangeProposal, build_rule_change_proposal
from .tc_generator.regression import run_regression


@dataclass
class PipelineStep:
    """파이프라인 한 단계의 상태(감사추적용)."""
    order: int
    name: str
    status: str            # OK / MEASURED / PENDING / REVIEW
    detail: str


@dataclass
class AssuranceDimension:
    """검증 dimension 하나의 상태(실측/대기)."""
    key: str
    label: str
    measured: bool
    value: Optional[str]   # 실측값(있으면)
    threshold: str


@dataclass
class ValidationReport:
    """E2E 검증 보고서 — 파이프라인 전 단계의 구조화 집계."""
    title: str
    policy_event: str
    generated_note: str
    # 1. Source Snapshot
    sources: list[dict]
    # 2. Policy Version / Temporal
    effective_date: date
    grandfathering_cutoff: date
    target_regions: list[str]
    # 3. RegChange (Before/After) — gold
    regchange_gold: dict
    # 4. Impact Matrix
    impact_matrix: ImpactMatrix
    # 5. Rule Change Proposal
    proposal: RuleChangeProposal
    # 6. Test Cases / Rule Regression
    regression: dict           # {pass_rate, passed, total, by_category}
    gold_set: dict             # {version, total, dev:{...}, locked_sealed, challenge_sealed}
    # 7. Assurance
    assurance_dimensions: list[AssuranceDimension]
    # 8. Human Review
    approval_status: ApprovalStatus
    escalations: list[Escalation]
    # 파이프라인 요약(감사추적)
    steps: list[PipelineStep] = field(default_factory=list)

    @property
    def target_region_labels(self) -> list[str]:
        return [REGION_LABELS.get(c, c) for c in self.target_regions]

    @property
    def overall_status(self) -> str:
        """전체 판정: escalation/미측정이 있으면 사람 검토 필요."""
        if self.escalations or self.approval_status != ApprovalStatus.APPROVED:
            return "REVIEW_REQUIRED"
        return "OK"


def _assurance_dimensions(regression: dict) -> list[AssuranceDimension]:
    """4 DEEP dimension 상태.

    ④ Rule-regression은 항상 실측. ①②③(RegChange 계열)은 실측 추출 산출물이 있으면
    결정론적 재계산으로 실측, 없으면 '실측 대기'(지어내지 않음).
    """
    pr = regression["pass_rate"]
    m = measured_assurance()   # 기록된 추출이 없으면 None
    if m is not None:
        citation = AssuranceDimension(
            "citation", "① Citation/Source grounding", True,
            f"{m.citation_correctness:.0%} (환각 {m.unsupported_claim_rate:.0%})", "≥ 95%(초안)")
        completeness = AssuranceDimension(
            "completeness", "② Change Completeness", True,
            f"{m.change_completeness:.0%}", "≥ 95%(초안)")
        recall = AssuranceDimension(
            "recall", "③ Exception · GF Recall", True,
            f"{m.exception_recall:.0%}", "≥ 95%(초안)")
    else:
        citation = AssuranceDimension("citation", "① Citation/Source grounding", False, None, "≥ 95%(초안)")
        completeness = AssuranceDimension("completeness", "② Change Completeness", False, None, "≥ 95%(초안)")
        recall = AssuranceDimension("recall", "③ Exception · GF Recall", False, None, "≥ 95%(초안)")
    regression_dim = AssuranceDimension(
        "regression", "④ Rule-regression", True,
        f"{pr:.0%} ({regression['passed']}/{regression['total']})", "100%")
    return [citation, completeness, recall, regression_dim]


def build_validation_report(matrix: Optional[ImpactMatrix] = None) -> ValidationReport:
    """6·30 파이프라인을 E2E 관통시켜 구조화 검증 보고서를 생성한다."""
    matrix = matrix if matrix is not None else build_impact_matrix()
    gold = load_gold()
    proposal = build_rule_change_proposal(matrix)

    report_obj = run_regression()
    regression = {
        "pass_rate": report_obj.pass_rate,
        "passed": report_obj.passed,
        "total": report_obj.total,
        "by_category": report_obj.pass_rate_by_category(),
    }
    assurance = _assurance_dimensions(regression)

    # Gold Set — DEV 회귀는 상시. LOCKED/CHALLENGE는 최종 개봉(FINAL_EVAL) 있으면 결과, 없으면 sealed.
    manifest = load_manifest()
    dev = run_gold_regression("dev")
    final = load_final_eval()
    gold_set = {
        "version": manifest["version"],
        "total": manifest["total"],
        "dev": {
            "passed": dev.passed, "total": dev.total, "pass_rate": dev.pass_rate,
            "by_category": dev.pass_rate_by_category(),
        },
        "locked_sealed": manifest["splits"]["locked"]["count"],
        "challenge_sealed": manifest["splits"]["challenge"]["count"],
        "opened": final is not None,
    }
    if final is not None:
        gold_set["opened_date"] = final["_meta"]["opened_date"]
        gold_set["overall"] = final["overall"]
        for s in ("locked", "challenge"):
            fs = final["splits"][s]
            gold_set[s] = {"passed": fs["passed"], "total": fs["total"], "pass_rate": fs["pass_rate"]}

    s = matrix.summary
    steps = [
        PipelineStep(1, "Source Snapshot", "OK",
                     f"공식 원문 {len(SOURCE_REGISTRY)}건 해시 스냅샷 (공개 보도자료/FAQ)"),
        PipelineStep(2, "Policy Version / Temporal", "OK",
                     f"시행일 {proposal.effective_date.isoformat()} · 경과규정 컷오프 "
                     f"{proposal.grandfathering_cutoff.isoformat()} · 신규 규제지역 {len(proposal.target_regions)}곳"),
        PipelineStep(3, "RegChange (Before/After)", "OK",
                     f"필수 변경 {len(gold['required_changes'])}항 · 예외 {len(gold['exceptions'])}종 (gold 확정)"),
        PipelineStep(4, "Impact Matrix", "OK",
                     f"세그먼트 {s['TOTAL']} (Core {s['CORE']}) · 하향 {s['DOWNGRADE']} · "
                     f"신규제한 {s['NEW_RESTRICTION']} · Discovery {s['DISCOVERY']}"),
        PipelineStep(5, "Rule Change Proposal", "REVIEW",
                     f"{proposal.rule_id} · 파라미터 변경 {sum(1 for p in proposal.parameter_changes if p.changed)}건 · "
                     f"승인상태 {proposal.approval_status.value}"),
        PipelineStep(6, "Test Cases / Rule Regression", "MEASURED",
                     f"오라클 회귀 {regression['passed']}/{regression['total']} · "
                     + (f"Gold Set 최종 {gold_set['overall']['passed']}/{gold_set['overall']['total']} "
                        f"(DEV·LOCKED·CHALLENGE 개봉 {gold_set['opened_date']})"
                        if gold_set["opened"] else
                        f"Gold Set DEV {gold_set['dev']['passed']}/{gold_set['dev']['total']} "
                        f"(LOCKED {gold_set['locked_sealed']}·CHALLENGE {gold_set['challenge_sealed']} sealed)")),
        PipelineStep(7, "Assurance", "PENDING" if any(not d.measured for d in assurance) else "MEASURED",
                     f"4 DEEP dimension 실측 {sum(d.measured for d in assurance)}/{len(assurance)} · "
                     + ("전 dimension 실측 완료" if all(d.measured for d in assurance)
                        else "일부 LLM 실행 대기(미측정 표기)")),
        PipelineStep(8, "Human Review", "REVIEW",
                     f"escalation {len(proposal.escalations)}건 → 사람 검토 필요"),
    ]

    return ValidationReport(
        title="6·30 규제 변경 검증 보고서 (Validation Report)",
        policy_event=proposal.policy_event,
        generated_note="AI초안→사람확정. 값은 gold·엔진·회귀 실제 산출물에서 유도(LOCKED §4).",
        sources=list(SOURCE_REGISTRY),
        effective_date=proposal.effective_date,
        grandfathering_cutoff=proposal.grandfathering_cutoff,
        target_regions=proposal.target_regions,
        regchange_gold=gold,
        impact_matrix=matrix,
        proposal=proposal,
        regression=regression,
        gold_set=gold_set,
        assurance_dimensions=assurance,
        approval_status=proposal.approval_status,
        escalations=proposal.escalations,
        steps=steps,
    )


def format_report(report: ValidationReport) -> str:
    """사람이 읽는 텍스트 보고서 (markdown-ish). 리포트 stub → 실 산출."""
    L: list[str] = []
    L.append(f"# {report.title}")
    L.append(f"> {report.policy_event} · 전체 판정: {report.overall_status}")
    L.append(f"> {report.generated_note}")
    L.append("")
    L.append("## 파이프라인 (End-to-End)")
    for st in report.steps:
        L.append(f"  {st.order}. [{st.status:>8}] {st.name} — {st.detail}")
    L.append("")

    L.append("## 1. Source Snapshot")
    for src in report.sources:
        L.append(f"  - {src['org']} · {src['published']} · {src['doc_id']} (#{src['hash']})")
    L.append("")

    L.append("## 2. Policy Version / Temporal")
    L.append(f"  - 시행일: {report.effective_date.isoformat()}  경과규정 컷오프: {report.grandfathering_cutoff.isoformat()}")
    L.append(f"  - 신규 규제지역: {', '.join(report.target_region_labels)}")
    L.append("")

    L.append("## 3~4. RegChange → Impact Matrix")
    for row in report.impact_matrix.core_rows:
        before = "명세부재" if row.before_ltv is None else f"{row.before_ltv:.0%}"
        after = "-" if row.after_ltv is None else f"{row.after_ltv:.0%}"
        L.append(f"  - {row.region_label} {row.borrower_type}: {before} → {after} [{row.direction.value}]")
    if report.impact_matrix.discovery_rows:
        disc = ", ".join(r.borrower_type for r in report.impact_matrix.discovery_rows)
        L.append(f"  - Discovery(수동검토): {disc}")
    L.append("")

    L.append("## 5. Rule Change Proposal")
    p = report.proposal
    L.append(f"  - rule_id: {p.rule_id}  승인상태: {p.approval_status.value}")
    for pc in p.parameter_changes:
        mark = "" if pc.changed else " (변화 없음)"
        L.append(f"    · {pc.tier}: {pc.before_label} → {pc.after_label}  [{pc.reason_code}]{mark}")
    L.append(f"  - 근거 정책: {', '.join(p.source_policy_ids)}")
    L.append("")

    L.append("## 6. Rule Regression (독립 오라클 차등 검증)")
    reg = report.regression
    L.append(f"  - Pass Rate: {reg['pass_rate']:.0%} ({reg['passed']}/{reg['total']})")
    for cat, (passed, total, rate) in reg["by_category"].items():
        L.append(f"    · {cat}: {passed}/{total} ({rate:.0%})")
    L.append("")

    L.append("## 6b. Gold Set (평가셋 freeze · 누수 방지)")
    gs = report.gold_set
    L.append(f"  - version {gs['version']} · 총 {gs['total']}문항")
    L.append(f"  - DEV(상시): {gs['dev']['pass_rate']:.0%} ({gs['dev']['passed']}/{gs['dev']['total']})")
    if gs.get("opened"):
        L.append(f"  - LOCKED(개봉): {gs['locked']['pass_rate']:.0%} ({gs['locked']['passed']}/{gs['locked']['total']})")
        L.append(f"  - CHALLENGE(개봉): {gs['challenge']['pass_rate']:.0%} ({gs['challenge']['passed']}/{gs['challenge']['total']})")
        L.append(f"  - 전체 최종({gs['overall']['total']}): {gs['overall']['pass_rate']:.0%} "
                 f"({gs['overall']['passed']}/{gs['overall']['total']}) · 개봉일 {gs['opened_date']} (재튜닝·재보고 금지)")
    else:
        L.append(f"  - LOCKED {gs['locked_sealed']} · CHALLENGE {gs['challenge_sealed']} : sealed (Phase 3 최종 1회)")
    L.append("")

    L.append("## 7. Assurance (4 DEEP dimension)")
    for d in report.assurance_dimensions:
        val = d.value if d.measured else "미측정 (LLM 실행 대기)"
        L.append(f"  - {d.label}: {val}  [임계 {d.threshold}]")
    L.append("")

    L.append("## 8. Human Review")
    L.append(f"  - 승인상태: {report.approval_status.value}")
    for e in report.escalations:
        L.append(f"  - escalation [{e.reason_code}]: {e.description}")
    if not report.escalations:
        L.append("  - escalation 없음")
    return "\n".join(L)
