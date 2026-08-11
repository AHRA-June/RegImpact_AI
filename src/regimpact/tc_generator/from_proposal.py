"""Rule Change Proposal → 겨냥 테스트케이스 생성 + 추적성 + fidelity 검증.

파이프라인 연결: 구조화 변경안(proposal)의 각 주장(claim)을 겨냥해 회귀 케이스를
생성하고, 각 케이스가 어떤 proposal 필드를 검증하는지 추적(traceability)한다.

세 가지 산출:
  1. **Coverage**  — proposal의 모든 주장이 ≥1개 테스트로 커버되는가.
  2. **Regression**(기존 하네스) — 엔진이 명세 오라클과 일치하는가(engine ⟷ oracle).
  3. **Fidelity**  — 엔진 실제 동작이 proposal 주장과 일치하는가(engine ⟷ proposal).

이것으로 거버넌스 루프를 닫는다: "제안된 모든 변경이 테스트로 뒷받침되고,
승인 대상 deterministic 엔진이 그 제안대로 동작함을 case-level 증거로 보인다."

생성기는 '입력을 어떻게 훑을지'만 책임지고, 정답(oracle)은 여전히 명세 오라클이 준다
(관심사 분리 — generator.py 주석 참고). fidelity는 그와 별개로 proposal 주장과 대조한다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional

from ..models import EvaluationStatus, LtvDecision, MortgageApplication
from ..rule_engine import evaluate
from .generator import Category, GeneratedCase
from .oracle import expected_outcome

# proposal에서 쓰는 표준 예외 코드(builder와 정렬)
EXC_FIRST_HOME = "FIRST_HOME_BUYER"
EXC_REAL_DEMAND = "REAL_DEMAND"


@dataclass(frozen=True)
class ProposalClaim:
    """변경안이 주장하는 검증 가능한 단위. fidelity 검증의 기준."""
    claim_id: str
    field_name: str              # 이 주장이 나온 proposal 필드
    description: str
    expected_max_ltv: Optional[float] = None      # 엔진이 내야 할 LTV(있으면)
    expected_grandfathered: Optional[bool] = None  # 경과규정 적용 여부(있으면)
    is_exception: bool = False   # True면 '표준 LTV와 다르게(예외 honored)' 만 검증


@dataclass(frozen=True)
class TracedCase:
    """생성 케이스 + 그것이 검증하는 proposal 주장."""
    case: GeneratedCase
    claim_id: str


@dataclass
class ProposalTestSuite:
    rule_id: str
    claims: list[ProposalClaim] = field(default_factory=list)
    traced: list[TracedCase] = field(default_factory=list)

    def generated_cases(self) -> list[GeneratedCase]:
        """기존 회귀 하네스(run_regression)에 그대로 넘길 케이스 목록."""
        return [t.case for t in self.traced]

    def claim(self, claim_id: str) -> Optional[ProposalClaim]:
        return next((c for c in self.claims if c.claim_id == claim_id), None)

    def cases_for(self, claim_id: str) -> list[GeneratedCase]:
        return [t.case for t in self.traced if t.claim_id == claim_id]

    def coverage(self) -> dict:
        """주장별 케이스 수 + 미커버 주장. 모든 주장이 커버되면 covered=True."""
        per_claim = {c.claim_id: len(self.cases_for(c.claim_id)) for c in self.claims}
        uncovered = [cid for cid, n in per_claim.items() if n == 0]
        return {
            "total_claims": len(self.claims),
            "covered_claims": sum(1 for n in per_claim.values() if n > 0),
            "uncovered": uncovered,
            "covered": not uncovered,
            "per_claim": per_claim,
        }


# ---------------------------------------------------------------------------
# 생성
# ---------------------------------------------------------------------------
def _traced(suite_cases: list[TracedCase], case_id: str, category: Category,
            description: str, app: MortgageApplication, claim_id: str) -> None:
    """오라클이 기대값을 채우도록 케이스를 조립하고 추적 링크와 함께 적재."""
    case = GeneratedCase(
        case_id=case_id,
        category=category,
        description=description,
        app=app,
        expected=expected_outcome(app),
    )
    suite_cases.append(TracedCase(case=case, claim_id=claim_id))


def generate_cases_for_proposal(proposal) -> ProposalTestSuite:
    """변경안의 주장별로 겨냥 회귀 케이스를 생성한다.

    proposal.after.effective_from / grandfathering.cutoff_date 등 실제 제안값에서
    시점·경계를 유도하므로, 제안이 바뀌면 테스트도 따라 바뀐다(하드코딩 방지).
    """
    regions = list(proposal.after.target_regions)
    if not regions:
        raise ValueError("proposal.after.target_regions 가 비어 있음 — 케이스 생성 불가")
    if not proposal.after.effective_from:
        raise ValueError("proposal.after.effective_from 이 없음 — 시점 유도 불가")

    effective = date.fromisoformat(proposal.after.effective_from)
    before_day = effective - timedelta(days=1)     # 시행 전일 = 구규제
    eval_after = effective + timedelta(days=1)      # 시행 후(명확히 규제)
    r0 = regions[0]

    std_ltv = proposal.after.max_ltv
    base_ltv = proposal.before.max_ltv

    claims: list[ProposalClaim] = []
    traced: list[TracedCase] = []

    # 1) 지역 지정: 각 대상지역의 무주택 일반이 시행 후 규제표준 LTV로 판정
    claims.append(ProposalClaim(
        "REGION_DESIGNATION", "after.target_regions",
        "대상지역이 시행 후 규제지역으로 판정(무주택 일반 → 규제표준 LTV)",
        expected_max_ltv=std_ltv,
    ))
    for rc in regions:
        _traced(traced, f"PROP-REG-{rc}", Category.BOUNDARY,
                f"{rc} 무주택 일반 · 시행 후 → 규제표준 {std_ltv:.0%}",
                MortgageApplication(region_code=rc, evaluation_date=eval_after, house_count=0),
                "REGION_DESIGNATION")

    # 2) LTV 표준: 무주택 일반 → after.max_ltv
    claims.append(ProposalClaim(
        "LTV_STANDARD", "after.max_ltv",
        f"규제지역 무주택 일반 LTV = {std_ltv:.0%}",
        expected_max_ltv=std_ltv,
    ))
    _traced(traced, "PROP-LTV-STD", Category.EXCEPTION,
            f"{r0} 무주택 일반 → {std_ltv:.0%}",
            MortgageApplication(region_code=r0, evaluation_date=eval_after, house_count=0),
            "LTV_STANDARD")

    # 3) 시행일 경계: 시행 전일은 구규제 기준선(base_ltv)
    claims.append(ProposalClaim(
        "EFFECTIVE_BOUNDARY", "after.effective_from",
        f"시행 전일({before_day.isoformat()}) 평가 → 아직 비규제 {base_ltv:.0%}",
        expected_max_ltv=base_ltv,
    ))
    _traced(traced, "PROP-EFF-BEFORE", Category.BOUNDARY,
            f"{r0} 무주택 · 시행 전일({before_day.isoformat()}) → 비규제 {base_ltv:.0%}",
            MortgageApplication(region_code=r0, evaluation_date=before_day, house_count=0),
            "EFFECTIVE_BOUNDARY")

    # 4) 예외: 생애최초 / 서민실수요 (값은 엔진/명세에서, honored 여부만 주장)
    if EXC_FIRST_HOME in proposal.exceptions:
        claims.append(ProposalClaim(
            "EXC_FIRST_HOME", "exceptions",
            "생애최초는 표준 LTV와 다르게(예외) 판정",
            is_exception=True,
        ))
        _traced(traced, "PROP-EXC-FH", Category.EXCEPTION,
                f"{r0} 생애최초 · 시행 후 → 예외 적용",
                MortgageApplication(region_code=r0, evaluation_date=eval_after,
                                    house_count=0, first_home_buyer=True),
                "EXC_FIRST_HOME")
    if EXC_REAL_DEMAND in proposal.exceptions:
        claims.append(ProposalClaim(
            "EXC_REAL_DEMAND", "exceptions",
            "서민·실수요는 표준 LTV와 다르게(예외) 판정",
            is_exception=True,
        ))
        _traced(traced, "PROP-EXC-RD", Category.EXCEPTION,
                f"{r0} 서민·실수요 · 시행 후 → 예외 적용",
                MortgageApplication(region_code=r0, evaluation_date=eval_after,
                                    house_count=0, real_demand_flag=True),
                "EXC_REAL_DEMAND")

    # 5) 경과규정: 컷오프 당일 접수 → 종전규정 / 컷오프 다음날 접수 → 신규규정
    gf = proposal.grandfathering
    if gf is not None and gf.cutoff_date:
        cutoff = date.fromisoformat(gf.cutoff_date)
        after_cutoff = cutoff + timedelta(days=1)
        claims.append(ProposalClaim(
            "GF_ON_CUTOFF", "grandfathering.cutoff_date",
            f"컷오프 당일({cutoff.isoformat()}) 접수 → 종전규정 적용",
            expected_grandfathered=True,
        ))
        _traced(traced, "PROP-GF-ON", Category.GRANDFATHERING,
                f"{r0} G1 접수 {cutoff.isoformat()} → 종전규정",
                MortgageApplication(region_code=r0, evaluation_date=eval_after,
                                    house_count=0, application_accepted_at=cutoff),
                "GF_ON_CUTOFF")
        claims.append(ProposalClaim(
            "GF_AFTER_CUTOFF", "grandfathering.cutoff_date",
            f"컷오프 다음날({after_cutoff.isoformat()}) 접수 → 신규규정 적용",
            expected_grandfathered=False,
        ))
        _traced(traced, "PROP-GF-AFTER", Category.GRANDFATHERING,
                f"{r0} G1 접수 {after_cutoff.isoformat()} → 신규규정",
                MortgageApplication(region_code=r0, evaluation_date=eval_after,
                                    house_count=0, application_accepted_at=after_cutoff),
                "GF_AFTER_CUTOFF")

    # case_id 유일성
    seen: set[str] = set()
    for t in traced:
        if t.case.case_id in seen:
            raise ValueError(f"중복 case_id: {t.case.case_id}")
        seen.add(t.case.case_id)

    return ProposalTestSuite(rule_id=proposal.rule_id, claims=claims, traced=traced)


# ---------------------------------------------------------------------------
# Fidelity: 엔진 실제 동작이 proposal 주장과 일치하는가
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class FidelityResult:
    claim_id: str
    case_id: str
    passed: bool
    detail: str


@dataclass
class FidelityReport:
    results: list[FidelityResult] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failures(self) -> list[FidelityResult]:
        return [r for r in self.results if not r.passed]

    @property
    def all_passed(self) -> bool:
        return not self.failures

    def summary(self) -> dict:
        return {
            "total": self.total,
            "passed": self.passed,
            "failed": len(self.failures),
            "all_passed": self.all_passed,
        }


def _check_fidelity(claim: ProposalClaim, actual: LtvDecision, std_ltv: Optional[float]) -> tuple[bool, str]:
    if claim.is_exception:
        ok = actual.status == EvaluationStatus.DECIDED and actual.max_ltv != std_ltv
        return ok, f"예외 honored: status={actual.status.value} ltv={actual.max_ltv} (≠표준 {std_ltv})"
    if claim.expected_grandfathered is not None:
        ok = actual.grandfathering_applied == claim.expected_grandfathered
        return ok, f"grandfathering: expected={claim.expected_grandfathered} actual={actual.grandfathering_applied}"
    if claim.expected_max_ltv is not None:
        ok = actual.max_ltv == claim.expected_max_ltv
        return ok, f"max_ltv: expected={claim.expected_max_ltv} actual={actual.max_ltv}"
    return True, "검증 기준 없음(스킵)"


def check_proposal_fidelity(suite: ProposalTestSuite, proposal) -> FidelityReport:
    """생성된 각 케이스를 엔진에 돌려 proposal 주장과 일치하는지 검증한다."""
    std_ltv = proposal.after.max_ltv
    claims = {c.claim_id: c for c in suite.claims}
    results: list[FidelityResult] = []
    for t in suite.traced:
        claim = claims[t.claim_id]
        actual = evaluate(t.case.app)
        ok, detail = _check_fidelity(claim, actual, std_ltv)
        results.append(FidelityResult(claim_id=t.claim_id, case_id=t.case.case_id,
                                      passed=ok, detail=detail))
    return FidelityReport(results=results)


def format_suite_report(
    suite: ProposalTestSuite,
    fidelity: Optional[FidelityReport] = None,
) -> str:
    """proposal→TC 커버리지 + fidelity 요약(데모·검증보고서용)."""
    cov = suite.coverage()
    lines: list[str] = []
    lines.append("=" * 64)
    lines.append(f"Proposal → Test Cases  ({suite.rule_id})")
    lines.append("=" * 64)
    lines.append(
        f"Coverage: {cov['covered_claims']}/{cov['total_claims']} 주장 커버 "
        f"(covered={cov['covered']})"
    )
    for c in suite.claims:
        n = cov["per_claim"][c.claim_id]
        mark = "✓" if n > 0 else "✗"
        lines.append(f"  {mark} {c.claim_id:<18} ({c.field_name})  cases={n}  — {c.description}")
    if cov["uncovered"]:
        lines.append(f"  ⚠ 미커버 주장: {cov['uncovered']}")
    if fidelity is not None:
        s = fidelity.summary()
        lines.append("")
        lines.append(f"Fidelity (engine ⟷ proposal): {s['passed']}/{s['total']} pass "
                     f"(all_passed={s['all_passed']})")
        for r in fidelity.failures:
            lines.append(f"  ✗ {r.claim_id} [{r.case_id}] {r.detail}")
    lines.append("=" * 64)
    return "\n".join(lines)
