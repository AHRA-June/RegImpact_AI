"""임팩트 매트릭스 생성 — 실제 컴포넌트 출력을 §10 행/열로 조립한다.

이 모듈은 **값을 지어내지 않는다.** 모든 행의 수치·근거는 다른 컴포넌트의 실제 출력에서 온다:
  - 변경 내용·근거 인용 → RegChange Extractor (LLM 추출 + Citation Assurance 검증 결과)
  - 고객 영향 수치     → deterministic 룰엔진의 before/after 포트폴리오 평가
  - 테스트 행          → TC Generator + Rule-Regression 실제 Pass Rate
  - 룰 diff            → 사람이 확정한 명세의 구현(rule_engine 상수) — LLM 생성 아님(LOCKED §4)

Stitch 목업의 하드코딩 값을 대체하는 것이 이 모듈의 목적이다.
"""
from __future__ import annotations

from typing import Optional

from .. import rule_engine as re_mod
from ..extractor.evaluate import GroundingReport
from ..extractor.schema import RegChangeExtraction, RegChangeItem
from ..tc_generator.regression import RegressionReport
from .customer import CustomerImpactReport, Segment
from .schema import (
    ApprovalStatus,
    Evidence,
    ImpactMatrix,
    ImpactRow,
    Owner,
    Phase,
    Priority,
)


def _won(amount: int) -> str:
    """원 단위를 사람이 읽는 억/조 단위로."""
    sign = "-" if amount < 0 else ""
    a = abs(amount)
    if a >= 1_000_000_000_000:
        return f"{sign}{a / 1_000_000_000_000:.2f}조원"
    if a >= 10_000_000_000:                      # 100억 이상은 정수 억
        return f"{sign}{a / 100_000_000:,.0f}억원"
    if a >= 100_000_000:                         # 100억 미만은 소수 첫째자리까지
        return f"{sign}{a / 100_000_000:.2f}억원"
    return f"{sign}{a:,}원"


def _evidence(
    extraction: RegChangeExtraction,
    categories: tuple[str, ...],
    grounding: Optional[GroundingReport] = None,
    limit: int = 3,
) -> list[Evidence]:
    """해당 카테고리의 추출 항목에서 근거 인용을 뽑고 grounding 검증 결과를 붙인다."""
    ungrounded = set()
    if grounding is not None:
        ungrounded = {(u.citation.source_doc_id, u.citation.quote) for u in grounding.ungrounded}

    out: list[Evidence] = []
    seen: set[tuple[str, str]] = set()
    for item in extraction.changes:
        if item.category not in categories:
            continue
        # 대표 인용 + 다른 문서의 corroboration을 함께 싣는다 — 여러 공문이 같은 변경을
        # 말했다는 사실 자체가 근거의 강도이므로 표시에서 지우지 않는다.
        for cit in (item.citation, *item.corroborations):
            key = (cit.source_doc_id, cit.quote)
            if key in seen:
                continue      # 같은 문장을 여러 항목이 인용하는 경우(지역 3곳 등) 1회만
            seen.add(key)
            out.append(Evidence(
                source_doc_id=cit.source_doc_id,
                quote=cit.quote,
                grounded=None if grounding is None else key not in ungrounded,
            ))
            if len(out) >= limit:
                return out
    return out


def derive_rule_diff() -> list[dict]:
    """확정 명세 구현(rule_engine)에서 룰 변경안을 기계적으로 유도한다.

    LOCKED §4 준수: 값은 사람이 확정한 명세에서 오고, 여기서는 그 값을 **읽어서 표로 옮길 뿐**
    새 규칙을 만들지 않는다. 룰엔진 상수가 바뀌면 이 diff도 자동으로 따라간다.
    """
    return [
        {"rule_id": "REG_STD", "condition": "규제지역·무주택·일반",
         "before": re_mod.LTV_BASELINE, "after": re_mod.LTV_REGULATED_STANDARD},
        {"rule_id": "REG_FIRSTHOME", "condition": "규제지역·생애최초",
         "before": re_mod.LTV_BASELINE, "after": re_mod.LTV_FIRST_HOME},
        {"rule_id": "REG_REALDEMAND", "condition": "규제지역·서민실수요",
         "before": re_mod.LTV_BASELINE, "after": re_mod.LTV_REAL_DEMAND},
        {"rule_id": "REG_OWNER_0", "condition": "규제지역·유주택(비처분)",
         "before": None, "after": re_mod.LTV_OWNER},
        {"rule_id": "MULTI_0", "condition": "규제지역·다주택",
         "before": None, "after": re_mod.LTV_MULTI},
        {"rule_id": "NONREG_STD_70", "condition": "경과규정 해당(종전규정)",
         "before": re_mod.LTV_BASELINE, "after": re_mod.LTV_BASELINE},
    ]


def _pct(v: Optional[float]) -> str:
    return "기준없음" if v is None else f"{v:.0%}"


def build_impact_matrix(
    extraction: RegChangeExtraction,
    impact: CustomerImpactReport,
    *,
    grounding: Optional[GroundingReport] = None,
    regression: Optional[RegressionReport] = None,
) -> ImpactMatrix:
    """§10 임팩트 매트릭스를 조립한다."""
    seg = impact.segment_counts
    n = len(impact.impacts) or 1
    diff = derive_rule_diff()
    changed = [d for d in diff if d["before"] != d["after"]]

    rows: list[ImpactRow] = []

    # 1. 변경사항 식별·규정 해석
    cats = {}
    for c in extraction.changes:
        cats[c.category] = cats.get(c.category, 0) + 1
    rows.append(ImpactRow(
        area="변경사항 식별·규정 해석",
        change=(
            f"규제지역 신규 지정 {len(extraction.target_regions)}곳 "
            f"({', '.join(extraction.target_regions)}) — "
            f"LTV {_pct(re_mod.LTV_BASELINE)}→{_pct(re_mod.LTV_REGULATED_STANDARD)}, "
            f"시행 {extraction.effective_from}. 공문에서 변경 {len(extraction.changes)}건 추출"
        ),
        evidence=_evidence(extraction, ("LTV", "REGION", "EFFECTIVE_DATE"), grounding),
        affected="신규 규제지역 소재 주택구입목적 주담대 신청건 전체",
        deliverable="변경 요약 + 근거 인용 (RegChange Extraction)",
        priority=Priority.REQUIRED, phase=Phase.D_MINUS, owner=Owner.POLICY,
        approval_status=ApprovalStatus.PENDING_REVIEW,
        automatable=True,
        metrics={
            "extracted_changes": len(extraction.changes),
            "by_category": cats,
            "citation_correctness": None if grounding is None else grounding.citation_correctness,
            "unsupported_claim_rate": None if grounding is None else grounding.unsupported_claim_rate,
        },
    ))

    # 2. 고객·포트폴리오 영향 분석 ★핵심 행
    worst = impact.worst_case
    rows.append(ImpactRow(
        area="고객·포트폴리오 영향 분석",
        change=(
            f"합성 포트폴리오 {impact.portfolio_size:,}건 기준 한도 감소 "
            f"{seg[Segment.REDUCED.value]:,}건({impact.affected_rate:.1%}), "
            f"총 한도 감소 {_won(impact.total_limit_reduction)}, "
            f"건당 평균 {_won(impact.avg_limit_reduction)}"
        ),
        evidence=_evidence(extraction, ("LTV", "EXCEPTION"), grounding, limit=2),
        affected=" / ".join(f"{k} {v:,}건" for k, v in seg.items() if v),
        deliverable=(
            "영향 고객군 세그먼트 + 예상 한도 변화 + 경과규정 대상 목록 "
            f"(심사 판정 {impact.decision_coverage:.0%} / 영향 측정 {impact.impact_coverage:.0%})"
        ),
        priority=Priority.REQUIRED, phase=Phase.D_MINUS, owner=Owner.POLICY,
        approval_status=ApprovalStatus.PENDING_REVIEW,
        automatable=True,
        metrics={
            "segments": seg,
            "ltv_transitions": impact.ltv_transitions,
            "total_limit_reduction_won": impact.total_limit_reduction,
            "worst_case": None if worst is None else {
                "customer_id": worst.customer_id,
                "region": worst.region_code,
                "delta_won": worst.limit_delta,
            },
            "portfolio_seed": impact.seed,
            "decision_coverage": impact.decision_coverage,
            "impact_coverage": impact.impact_coverage,
        },
    ))

    # 3. 심사 Rule 변경
    rows.append(ImpactRow(
        area="심사 Rule 변경",
        change=(
            f"룰 {len(diff)}건 중 {len(changed)}건 변경 — "
            + ", ".join(f"{d['rule_id']} {_pct(d['before'])}→{_pct(d['after'])}" for d in changed)
        ),
        evidence=_evidence(extraction, ("LTV", "EXCEPTION"), grounding, limit=2),
        affected="여신 심사 룰셋 (주택구입목적 주담대 LTV 경로)",
        deliverable="구조화된 Rule diff 제안 (rule_id / 조건 / before / after)",
        priority=Priority.REQUIRED, phase=Phase.D_MINUS, owner=Owner.POLICY,
        approval_status=ApprovalStatus.PENDING_APPROVAL,
        automatable=True,
        metrics={"rule_diff": diff},
    ))

    # 4. 전산 요건
    rows.append(ImpactRow(
        area="전산 요건",
        change=(
            "지역 규제상태 테이블에 신규 3개 지역 버전 추가(effective_from=2026-07-01), "
            "LTV 산출 변수 교체, 경과규정 판정 플래그(접수일·계약일·계약금·토허제) 신설"
        ),
        evidence=_evidence(extraction, ("REGION", "EFFECTIVE_DATE"), grounding, limit=2),
        affected="여신 심사 시스템 · 한도 산출 배치 · 신청 접수 화면",
        deliverable="IT 요청서 초안 — 쿼리·변수 수정 명세",
        priority=Priority.REQUIRED, phase=Phase.D_MINUS, owner=Owner.IT,
        approval_status=ApprovalStatus.PENDING_REVIEW,
        automatable=True,
        metrics={
            "new_region_versions": list(extraction.target_regions),
            "new_flags": [
                "application_accepted_at", "contract_signed_at",
                "downpayment_paid_at", "land_permit_target", "land_permit_applied_at",
            ],
        },
    ))

    # 5. 내규 개정
    rows.append(ImpactRow(
        area="내규 개정",
        change="여신업무방법서 LTV 조항 및 규제지역 별표 개정 — 공문 상신 후 위원회 승인 필요",
        evidence=_evidence(extraction, ("LTV", "REGION"), grounding, limit=1),
        affected="내규 (여신업무방법서 · 규제지역 별표)",
        deliverable="개정 공문 초안 → 위원회 승인 대기",
        priority=Priority.REQUIRED, phase=Phase.D_MINUS, owner=Owner.COMMITTEE,
        approval_status=ApprovalStatus.PENDING_APPROVAL,
        automatable=False,
        human_review_reason="내규 개정은 위원회 승인이 필요한 거버넌스 절차 — AI가 대체할 수 없다(초안까지만).",
    ))

    # 6. 경과규정 처리
    rows.append(ImpactRow(
        area="경과규정 처리",
        change=(
            f"컷오프 2026-06-30(자정 포함) 기준 종전규정 적용 대상 "
            f"{impact.grandfathered_count:,}건 — G1 전산접수 / G2 계약+계약금 / G3 토허제 신청"
        ),
        evidence=_evidence(extraction, ("GRANDFATHERING",), grounding, limit=3),
        affected=f"시행 전 신청·계약 완료 건 {impact.grandfathered_count:,}건 (종전 LTV 70% 유지)",
        deliverable="기존 신청건 판정 기준 + 대상 목록",
        priority=Priority.REQUIRED, phase=Phase.D_MINUS, owner=Owner.POLICY,
        approval_status=ApprovalStatus.PENDING_REVIEW,
        automatable=True,
        metrics={
            "grandfathered": impact.grandfathered_count,
            "cutoff": "2026-06-30",
        },
    ))

    # 7. 테스트
    if regression is not None:
        rows.append(ImpactRow(
            area="테스트",
            change=(
                f"경계·예외·충돌 TC {regression.total}건 자동 생성 — "
                f"독립 명세 오라클 대조 Pass Rate {regression.pass_rate:.1%} "
                f"(실패 {len(regression.failures)}건)"
            ),
            evidence=_evidence(extraction, ("GRANDFATHERING", "EXCEPTION"), grounding, limit=1),
            affected="여신 심사 룰엔진 회귀 스위트",
            deliverable="경계·예외·충돌 TC + 회귀 리포트",
            priority=Priority.REGRESSION, phase=Phase.D_MINUS, owner=Owner.IT,
            approval_status=ApprovalStatus.PENDING_REVIEW,
            automatable=True,
            metrics={
                "total_cases": regression.total,
                "pass_rate": regression.pass_rate,
                "failures": len(regression.failures),
            },
        ))

    # 8. 현업 공지
    rows.append(ImpactRow(
        area="현업 공지",
        change=(
            f"시행일 {extraction.effective_from}부터 신규 규제지역 "
            f"{len(extraction.target_regions)}곳 LTV 변경 및 경과규정 안내"
        ),
        evidence=_evidence(extraction, ("EFFECTIVE_DATE", "REGION"), grounding, limit=1),
        affected="영업점 · 상담 채널",
        deliverable="공지문 초안",
        priority=Priority.REQUIRED, phase=Phase.D_MINUS, owner=Owner.BUSINESS,
        approval_status=ApprovalStatus.DRAFT,
        automatable=True,
    ))

    # --- 명세 공백 (실측에서 도출된 행) ---
    #
    # "심사 판정이 되는가"와 "변화량을 잴 수 있는가"를 한 줄로 합치지 않는다.
    # 규제지역 유주택자는 시행일 LTV가 0%로 확정되므로 **오늘 심사할 수 있고**,
    # 못 하는 것은 시행 전 기준값 부재로 인한 변화량 비교뿐이다(Q10).
    if impact.human_review_count:
        top = next(iter(impact.escalation_reasons.items()), ("", 0))
        rows.append(ImpactRow(
            area="규정 해석 공백 해소",
            change=(
                f"심사 판정 커버리지 {impact.decision_coverage:.1%} / "
                f"영향 측정 커버리지 {impact.impact_coverage:.1%} — "
                f"판정 불가 {impact.undecidable_count:,}건, "
                f"판정됐으나 변화량 미상 {impact.impact_unknown_count:,}건 "
                f"(최다 사유 {top[0]} {top[1]:,}건)"
            ),
            evidence=[],
            affected=(
                "①非규제(수도권) 비처분 1주택 — 시행 전 기준값 부재 "
                "②경과규정 해당 유주택 — 되돌릴 종전값 부재 ③비수도권 다주택"
            ),
            deliverable="명세 공백 목록 + 도메인 확정 요청 (Q10)",
            priority=Priority.REQUIRED, phase=Phase.D_MINUS, owner=Owner.POLICY,
            approval_status=ApprovalStatus.PENDING_REVIEW,
            automatable=False,
            human_review_reason=(
                "FAQ Q2 표 주1)이 非규제(수도권) 열을 '무주택자 기준'으로 한정해 비처분 1주택 "
                "기준값이 원문에 없다. MOLIT의 유주택 60%는 수도권 外 값이라 전용 불가. "
                "값을 추정하면 LOCKED §4 위반이므로 도메인 확정이 선행돼야 한다. "
                f"공백이 남아 있는 한 영향 측정 커버리지 상한은 {impact.impact_coverage:.0%}로 고정된다 "
                f"(심사 판정은 {impact.decision_coverage:.0%}까지 가능 — 유주택자도 코어 스코프 안이다)."
            ),
            metrics={
                "escalation_reasons": impact.escalation_reasons,
                "decision_coverage": impact.decision_coverage,
                "impact_coverage": impact.impact_coverage,
                "undecidable": impact.undecidable_count,
                "impact_unknown": impact.impact_unknown_count,
            },
        ))

    # --- Discovery Scope (브리프 §24-12: 매트릭스에만 표시, 코어 룰엔진에 넣지 않는다) ---
    for item in [c for c in extraction.changes if c.category == "SCOPE_LIMIT"]:
        rows.append(_discovery_row(item, grounding))

    # 9. 금리·한도 전략 재분석
    rows.append(ImpactRow(
        area="금리·한도 전략 재분석",
        change="규제지역 편입에 따른 취급 볼륨·마진 변화 재추정 및 가격 정책 재검토",
        evidence=[],
        affected="신규 규제지역 취급 포트폴리오",
        deliverable="재분석 과제 정의",
        priority=Priority.REVIEW, phase=Phase.POST, owner=Owner.POLICY,
        approval_status=ApprovalStatus.NOT_STARTED,
        automatable=False,
        human_review_reason="전략·가격 판단은 규칙 계산이 아니라 경영 의사결정 영역이다.",
    ))

    # 10. 대외보고 집계 기준
    rows.append(ImpactRow(
        area="대외보고 집계 기준",
        change="감독당국 집계기준 변경 요청이 별도 시점에 도착할 수 있음 — 변경 대기 플래그",
        evidence=[],
        affected="가계대출 관련 정기·수시 보고",
        deliverable="변경 대기 플래그 + 트리거 감시 항목",
        priority=Priority.REVIEW, phase=Phase.SEPARATE_TRIGGER, owner=Owner.POLICY,
        approval_status=ApprovalStatus.NOT_STARTED,
        automatable=False,
        human_review_reason="요청이 도착하기 전에는 기준이 정의되지 않는다 — 선제 자동화 불가.",
    ))

    # 11. 사후 모니터링
    rows.append(ImpactRow(
        area="사후 모니터링",
        change=(
            "전산반영 이상 여부 수시 점검 — 경과규정 오적용, 지역코드 누락, "
            "LTV 산출 불일치 3개 항목"
        ),
        evidence=[],
        affected="시행 직후 신규 취급건",
        deliverable="모니터링 체크 항목",
        priority=Priority.REVIEW, phase=Phase.POST, owner=Owner.IT,
        approval_status=ApprovalStatus.NOT_STARTED,
        automatable=True,
        metrics={"checks": ["경과규정 오적용", "지역코드 누락", "LTV 산출 불일치"]},
    ))

    return ImpactMatrix(
        policy_id=extraction.policy_id,
        effective_from=extraction.effective_from,
        target_regions=list(extraction.target_regions),
        rows=rows,
        generated_from={
            "extraction_changes": len(extraction.changes),
            "portfolio_size": impact.portfolio_size,
            "portfolio_seed": impact.seed,
            "decision_coverage": impact.decision_coverage,
            "impact_coverage": impact.impact_coverage,
            "regression_cases": None if regression is None else regression.total,
            "grounding_checked": grounding is not None,
        },
    )


def _discovery_row(item: RegChangeItem, grounding: Optional[GroundingReport]) -> ImpactRow:
    """Discovery Scope 항목 행 — 영향은 표시하되 코어 자동판정에는 넣지 않는다."""
    ungrounded = set()
    if grounding is not None:
        ungrounded = {(u.citation.source_doc_id, u.citation.quote) for u in grounding.ungrounded}
    key = (item.citation.source_doc_id, item.citation.quote)
    return ImpactRow(
        area="[Discovery] 적용범위 제한",
        change=item.summary,
        evidence=[Evidence(
            source_doc_id=item.citation.source_doc_id,
            quote=item.citation.quote,
            grounded=None if grounding is None else key not in ungrounded,
        )],
        affected="전세대출·신용대출·중도금/이주비·사업자대출 등 코어 밖 상품",
        deliverable="영향 가능성 표시 + 별도 검토 과제",
        priority=Priority.REVIEW, phase=Phase.D_MINUS, owner=Owner.POLICY,
        approval_status=ApprovalStatus.NOT_STARTED,
        automatable=False,
        human_review_reason=(
            "Discovery Scope — 브리프 §24-12에 따라 코어 룰엔진에 억지로 포함하지 않는다. "
            "탐지는 하되 자동판정은 하지 않는다."
        ),
    )
