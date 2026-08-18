"""임팩트 매트릭스 (docs/00_BRIEF.md §10 — 행·열·Phase는 사용자가 확정한 스키마).

**LOCKED §7: 시간축(Phase)은 이 매트릭스의 핵심 차별점이므로 삭제하지 않는다.**
브리프 §3의 통찰 — 일은 두 물결로 온다(시행일 전 필수 / 시행 후) + 대외보고는 별도 트리거로
나중에 도착한다 — 를 그대로 담는다.

설계 원칙 두 가지:

1. **행 내용을 프로즈로 박지 않는다.** 각 행의 '변경 내용·영향 대상·산출물'은 실제 산출물
   (RegChange 추출 / 고객영향 분석 / 회귀 리포트 / 지역 레지스트리)에서 **유도**한다.
   그래야 정책이 바뀌면 매트릭스가 따라 바뀐다.
2. **근거의 출처를 행마다 밝힌다(`Provenance`).** 사람이 확정한 골드인지, LLM 추출인지,
   결정론 엔진 산출인지, 아직 안 돌린 것인지. LOCKED §10(추적 가능성) — "AI가 만들었다"와
   "사람이 확정했다"가 한 표 안에서 구분되지 않으면 이 표는 감사에 쓸 수 없다.

Discovery Scope(브리프 §5.2, §24-11)는 매트릭스에 **표시만** 하고 코어 엔진에 넣지 않는다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from ..extractor.schema import RegChangeExtraction
from ..tc_generator import RegressionReport
from .customer_impact import CustomerImpactReport


class Phase(str, Enum):
    """시간축 — LOCKED §7. 삭제 금지."""
    BEFORE_DDAY = "D-day 전"
    AFTER_EFFECTIVE = "시행 후"
    SEPARATE_TRIGGER = "별도 트리거"


class Priority(str, Enum):
    REQUIRED = "필수"
    REVIEW = "검토"
    REGRESSION = "회귀"


class Owner(str, Enum):
    POLICY = "정책"
    IT = "IT"
    COMMITTEE = "위원회"
    FIELD = "현업"


class Automation(str, Enum):
    """자동처리 가능 여부 — 브리프 공통 열."""
    AUTOMATED = "자동 산출"                  # 결정론 산출물이 그대로 쓰임
    ASSISTED = "AI 초안 → 사람 확정"          # LOCKED §9
    MANUAL = "수동"                          # Discovery / 대외 프로세스


class Provenance(str, Enum):
    ENGINE = "결정론 엔진"
    HUMAN_GOLD = "사람 확정(골드)"
    AI_EXTRACTION = "AI 추출(검증 대상)"
    SPEC = "확정 명세"
    NOT_RUN = "미실행"


class ApprovalStatus(str, Enum):
    DRAFT = "초안"
    PENDING_REVIEW = "검토 대기"
    BLOCKED = "선행작업 대기"


@dataclass(frozen=True)
class Evidence:
    """근거 1건. 원문 인용이면 quote가 채워지고, 산출물이면 ref가 채워진다."""
    provenance: Provenance
    ref: str                          # 문서 ID / 산출물 경로 / 골드 항목 id
    quote: Optional[str] = None       # 원문 verbatim (있을 때만)
    grounded: Optional[bool] = None   # Citation Assurance 통과 여부 (AI 추출일 때만)

    def render(self) -> str:
        if self.quote:
            mark = "" if self.grounded is None else (" ✓원문대조" if self.grounded else " ✕미검증")
            q = self.quote if len(self.quote) <= 60 else self.quote[:57] + "…"
            return f"{self.ref}: “{q}”{mark}"
        return self.ref


@dataclass
class MatrixRow:
    """브리프 §10의 공통 열을 그대로 따른다."""
    area: str                          # 업무영역
    change: str                        # 변경 내용
    evidence: list[Evidence]           # 근거 문서 / evidence
    target: str                        # 영향 대상
    deliverable: str                   # 산출물
    priority: Priority
    phase: Phase                       # 기한(Phase) — LOCKED
    owner: Owner                       # 담당
    approval: ApprovalStatus           # 승인 상태
    automation: Automation             # 자동처리 가능 여부
    human_review_reason: Optional[str] = None   # Human Review 필요 사유
    metrics: dict[str, str] = field(default_factory=dict)   # 행이 근거로 삼은 수치

    @property
    def provenance(self) -> Provenance:
        """행의 근거 출처. 여러 개면 가장 약한 것(미실행 > AI추출 > 골드 > 엔진/명세)을 대표로."""
        order = [Provenance.NOT_RUN, Provenance.AI_EXTRACTION, Provenance.HUMAN_GOLD,
                 Provenance.SPEC, Provenance.ENGINE]
        if not self.evidence:
            return Provenance.NOT_RUN
        return min((e.provenance for e in self.evidence), key=order.index)


@dataclass
class ImpactMatrix:
    policy_id: str
    effective_from: str
    rows: list[MatrixRow]

    def by_phase(self, phase: Phase) -> list[MatrixRow]:
        return [r for r in self.rows if r.phase is phase]

    def blocked(self) -> list[MatrixRow]:
        return [r for r in self.rows if r.approval is ApprovalStatus.BLOCKED]

    def needs_human_review(self) -> list[MatrixRow]:
        return [r for r in self.rows if r.human_review_reason]

    def automation_mix(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for r in self.rows:
            out[r.automation.value] = out.get(r.automation.value, 0) + 1
        return out


# ---------------------------------------------------------------------------
# Discovery Scope — 브리프 §5.2 / §24-11. 표시만 하고 코어 엔진에 넣지 않는다.
# ---------------------------------------------------------------------------
DISCOVERY_ITEMS: tuple[tuple[str, str], ...] = (
    ("전세대출", "규제지역 3억 초과 APT 취득·보유 차주 제한, 보증비율·한도 변경"),
    ("신용대출", "1억 초과 신용대출 보유 차주의 1년간 규제지역 주택구입 제한"),
    ("중도금·이주비", "규제지역 1주택자 재건축·재개발 중도금·이주비 취급 시 추가주택 구입 제한"),
    ("사업자대출", "매매·임대사업자 외 사업자의 규제지역 주택구입목적 주담대 제한"),
)
DISCOVERY_STATUS = "Potentially impacted — manual policy review required"


def _pct(x: float) -> str:
    return f"{x:.1%}"


def _extraction_evidence(
    extraction: Optional[RegChangeExtraction],
    categories: tuple[str, ...],
    grounding: Optional[dict[str, bool]] = None,
) -> list[Evidence]:
    """추출 결과에서 해당 카테고리의 인용을 근거로 뽑는다. 추출이 없으면 빈 목록."""
    if extraction is None:
        return []
    out: list[Evidence] = []
    for item in extraction.changes:
        if item.category not in categories:
            continue
        out.append(Evidence(
            provenance=Provenance.AI_EXTRACTION,
            ref=item.citation.source_doc_id,
            quote=item.citation.quote,
            grounded=None if grounding is None else grounding.get(item.citation.quote),
        ))
    return out


def build_impact_matrix(
    impact: CustomerImpactReport,
    regression: RegressionReport,
    *,
    policy_id: str = "FSC_20260630",
    effective_from: str = "2026-07-01",
    extraction: Optional[RegChangeExtraction] = None,
    grounding: Optional[dict[str, bool]] = None,
    gold_change_ids: tuple[str, ...] = (),
    changed_region_codes: tuple[str, ...] = (),
) -> ImpactMatrix:
    """실제 산출물에서 임팩트 매트릭스를 유도한다.

    extraction 이 None 이면 '원문 근거 인용' 행들은 **선행작업 대기**로 남는다.
    없는 근거를 있는 것처럼 채우지 않는 것이 이 프로젝트의 규칙이다(브리프 §24-9).
    """
    no_event = impact.no_event_only()
    by_group = impact.by_region_group()
    changed_groups = [k for k, v in by_group.items() if v.impacted]
    esc_reasons = impact.escalation_reasons()
    transitions = impact.rule_transitions()

    gold_ev = [Evidence(Provenance.HUMAN_GOLD, f"regchange_gold_6_30.json#{cid}")
               for cid in gold_change_ids]
    engine_ev = lambda ref: [Evidence(Provenance.ENGINE, ref)]  # noqa: E731

    rows: list[MatrixRow] = []

    # ── 1. 변경사항 식별·규정 해석 ─────────────────────────────────────────
    src_ev = _extraction_evidence(extraction, ("LTV", "REGION", "EFFECTIVE_DATE", "EXCEPTION",
                                               "GRANDFATHERING"), grounding) or gold_ev
    n_changes = len(extraction.changes) if extraction else len(gold_change_ids)
    rows.append(MatrixRow(
        area="변경사항 식별·규정 해석",
        change=f"변경 {n_changes}건 식별 (시행 {effective_from})",
        evidence=src_ev,
        target=f"정책 {policy_id}",
        deliverable="변경 요약 + 근거 인용",
        priority=Priority.REQUIRED, phase=Phase.BEFORE_DDAY, owner=Owner.POLICY,
        approval=ApprovalStatus.PENDING_REVIEW if src_ev else ApprovalStatus.BLOCKED,
        automation=Automation.ASSISTED if extraction else Automation.MANUAL,
        human_review_reason=None if src_ev else "RegChange 추출 미실행 — 원문 인용 근거 없음",
        metrics={"식별 변경 수": str(n_changes)},
    ))

    # ── 2. 고객·포트폴리오 영향 분석 ────────────────────────────────────────
    rows.append(MatrixRow(
        area="고객·포트폴리오 영향 분석",
        change=(f"영향 세그먼트 {len(changed_groups)}개 지역군 — "
                + (", ".join(changed_groups) if changed_groups else "없음")),
        evidence=engine_ev("impact/customer_impact.py — 합성 포트폴리오 Before/After 2회 판정"),
        target=f"합성 포트폴리오 {impact.total:,.0f}건 (경과규정 미해당 층 {no_event.total:,.0f}건)",
        deliverable="영향 고객군 · 예상 한도 변화 · 경과규정 대상",
        priority=Priority.REQUIRED, phase=Phase.BEFORE_DDAY, owner=Owner.POLICY,
        approval=ApprovalStatus.PENDING_REVIEW, automation=Automation.AUTOMATED,
        human_review_reason=(f"자동판정 거부 {_pct(impact.escalation_rate)} — 명세 공백 구간"
                             if impact.escalation_rate else None),
        metrics={
            "영향률(경과규정 미해당 층)": _pct(no_event.impacted_rate),
            "한도 변화 합계": f"{no_event.limit_delta_sum_eok:,.1f}억 (LTV만 반영한 참고값)",
            "escalation 비율": _pct(impact.escalation_rate),
        },
    ))

    # ── 3. 심사 Rule 변경 ──────────────────────────────────────────────────
    rows.append(MatrixRow(
        area="심사 Rule 변경",
        change=(f"rule_id 전이 {len(transitions)}종: "
                + "; ".join(f"{k} ({v:,.0f}건)" for k, v in list(transitions.items())[:3])
                or "전이 없음"),
        evidence=engine_ev("rule_engine.evaluate — Before/After rule_id 전이 집계")
                 + [Evidence(Provenance.SPEC, "docs/05_RULE_SPEC.md §C·§H")],
        target="주택구입목적 주담대 LTV 판정 룰",
        deliverable="구조화된 Rule diff 제안",
        priority=Priority.REQUIRED, phase=Phase.BEFORE_DDAY, owner=Owner.POLICY,
        approval=ApprovalStatus.PENDING_REVIEW, automation=Automation.ASSISTED,
        human_review_reason="LOCKED §4 — 룰 로직은 LLM이 생성하지 않으며 사람이 확정한다",
        metrics={f"전이 {i+1}": f"{k} · {v:,.0f}건" for i, (k, v) in enumerate(transitions.items())},
    ))

    # ── 4. 전산 요건 ───────────────────────────────────────────────────────
    rows.append(MatrixRow(
        area="전산 요건",
        change=(f"지역 규제상태 테이블 갱신 {len(changed_region_codes)}건"
                + (f" ({', '.join(changed_region_codes)})" if changed_region_codes else "")
                + f" · 판정 분기 {len(transitions)}종 수정"),
        evidence=engine_ev("regions.REGISTRY — 시점 버전 diff"),
        target="여신 심사 시스템 · 지역 마스터 · LTV 판정 로직",
        deliverable="IT 요청서 초안 — 쿼리·변수 수정 명세",
        priority=Priority.REQUIRED, phase=Phase.BEFORE_DDAY, owner=Owner.IT,
        approval=ApprovalStatus.DRAFT, automation=Automation.ASSISTED,
        human_review_reason="전산 반영 범위는 시스템 담당자 확인 필요",
        metrics={"지역 마스터 변경": f"{len(changed_region_codes)}건",
                 "판정 분기 변경": f"{len(transitions)}종"},
    ))

    # ── 5. 내규 개정 ───────────────────────────────────────────────────────
    ltv_ev = _extraction_evidence(extraction, ("LTV", "EXCEPTION"), grounding) or gold_ev
    rows.append(MatrixRow(
        area="내규 개정",
        change="여신규정 LTV 조항 및 예외(생애최초·서민실수요) 조항 개정",
        evidence=ltv_ev,
        target="여신업무방법서 · 내규",
        deliverable="공문 초안 → 위원회 승인 대기",
        priority=Priority.REQUIRED, phase=Phase.BEFORE_DDAY, owner=Owner.COMMITTEE,
        approval=ApprovalStatus.PENDING_REVIEW if ltv_ev else ApprovalStatus.BLOCKED,
        automation=Automation.ASSISTED,
        human_review_reason="위원회 승인 필요 — AI는 초안까지만 (LOCKED §9)",
    ))

    # ── 6. 경과규정 처리 ───────────────────────────────────────────────────
    gf_ev = _extraction_evidence(extraction, ("GRANDFATHERING",), grounding) or gold_ev
    rows.append(MatrixRow(
        area="경과규정 처리",
        change=(f"컷오프 2026-06-30 · 종전규정 적용 대상 {impact.grandfathered:,.0f}건 "
                f"(그중 판정이 실제로 달라지는 건 {impact.protected_by_grandfathering:,.0f}건)"),
        evidence=(gf_ev + [Evidence(Provenance.SPEC, "docs/05_RULE_SPEC.md §F (G1/G2/G3)")]
                  + engine_ev("customer_impact — 경과규정 제거 반사실 대조")),
        target="시행일 이전 접수·계약 건",
        deliverable="기존 신청건 판정 기준",
        priority=Priority.REQUIRED, phase=Phase.BEFORE_DDAY, owner=Owner.POLICY,
        approval=ApprovalStatus.PENDING_REVIEW, automation=Automation.AUTOMATED,
        human_review_reason="계약금 일부납부 증빙 인정 범위는 건별 확인 필요 (§F G2)",
        metrics={"종전규정 적용": f"{impact.grandfathered:,.0f}건",
                 "유예로 판정이 달라진 건": f"{impact.protected_by_grandfathering:,.0f}건"},
    ))

    # ── 7. 테스트 ─────────────────────────────────────────────────────────
    cat_rates = regression.pass_rate_by_category()
    rows.append(MatrixRow(
        area="테스트",
        change=(f"경계·예외·충돌 TC {regression.total}건 자동 생성 · "
                f"Pass Rate {_pct(regression.pass_rate)}"),
        evidence=engine_ev("tc_generator — 독립 명세 오라클과의 차등 검증"),
        target="LTV 판정 엔진",
        deliverable="경계·예외·충돌 TC + 회귀 리포트",
        priority=Priority.REGRESSION, phase=Phase.BEFORE_DDAY, owner=Owner.IT,
        approval=ApprovalStatus.PENDING_REVIEW, automation=Automation.AUTOMATED,
        human_review_reason=(None if not regression.failures
                             else f"회귀 불일치 {len(regression.failures)}건"),
        metrics={cat: f"{p}/{n} ({rate:.0%})" for cat, (p, n, rate) in cat_rates.items()},
    ))

    # ── 8. 현업 공지 ───────────────────────────────────────────────────────
    rows.append(MatrixRow(
        area="현업 공지",
        change=(f"{effective_from} 시행 — "
                + (", ".join(changed_groups) if changed_groups else "영향 지역군 없음")
                + " 대상 LTV 변경 및 경과규정 안내"),
        evidence=src_ev + engine_ev("impact matrix 행 1·2·6"),
        target="영업점 · 심사역",
        deliverable="공지문 초안",
        priority=Priority.REQUIRED, phase=Phase.BEFORE_DDAY, owner=Owner.FIELD,
        approval=ApprovalStatus.DRAFT, automation=Automation.ASSISTED,
        human_review_reason="대외 문구는 사람 확정 필요",
    ))

    # ── 9. 금리·한도 전략 재분석 (시행 후) ─────────────────────────────────
    rows.append(MatrixRow(
        area="금리·한도 전략 재분석",
        change=(f"영향 지역군 한도 변화 {no_event.limit_delta_sum_eok:,.1f}억 "
                "→ 취급액·마진 재추정 과제 정의"),
        evidence=engine_ev("customer_impact — 세그먼트별 한도 변화"),
        target="상품 전략 · 금리 정책",
        deliverable="재분석 과제 정의",
        priority=Priority.REVIEW, phase=Phase.AFTER_EFFECTIVE, owner=Owner.POLICY,
        approval=ApprovalStatus.DRAFT, automation=Automation.MANUAL,
        human_review_reason="전략 판단 — 자동화 대상 아님",
    ))

    # ── 10. 대외보고 집계 기준 (별도 트리거) ───────────────────────────────
    rows.append(MatrixRow(
        area="대외보고 집계 기준",
        change="감독당국 집계기준 변경 요청 도착 시 반영 — 현재 미도착",
        evidence=[Evidence(Provenance.SPEC, "docs/00_BRIEF.md §3 — 별도 트리거로 나중에 도착")],
        target="대외보고 집계 로직",
        deliverable="변경 대기 플래그",
        priority=Priority.REVIEW, phase=Phase.SEPARATE_TRIGGER, owner=Owner.POLICY,
        approval=ApprovalStatus.BLOCKED, automation=Automation.MANUAL,
        human_review_reason="외부 트리거 대기 — 이 정책 변경만으로는 확정 불가",
    ))

    # ── 11. 사후 모니터링 (시행 후) ────────────────────────────────────────
    rows.append(MatrixRow(
        area="사후 모니터링",
        change=(f"자동판정 거부 {_pct(impact.escalation_rate)} 구간 집중 점검 · "
                + (", ".join(f"{k} {v:,.0f}건" for k, v in esc_reasons.items()) or "거부 없음")),
        evidence=engine_ev("customer_impact — escalation 사유별 집계"),
        target="전산 반영 결과 · 명세 공백 구간",
        deliverable="모니터링 체크 항목",
        priority=Priority.REVIEW, phase=Phase.AFTER_EFFECTIVE, owner=Owner.IT,
        approval=ApprovalStatus.DRAFT, automation=Automation.AUTOMATED,
        human_review_reason=("명세 공백으로 사람 판정에 넘어가는 건이 있어 실무 부하가 발생한다"
                             if esc_reasons else None),
        metrics={k: f"{v:,.0f}건" for k, v in esc_reasons.items()},
    ))

    # ── Discovery Scope — 표시만 (브리프 §5.2, §24-11) ─────────────────────
    scope_ev = _extraction_evidence(extraction, ("SCOPE_LIMIT",), grounding)
    for name, desc in DISCOVERY_ITEMS:
        hits = [e for e in scope_ev if name[:2] in (e.quote or "")]
        rows.append(MatrixRow(
            area=f"[Discovery] {name}",
            change=desc,
            evidence=hits or [Evidence(Provenance.SPEC, "docs/00_BRIEF.md §5.2 Discovery Scope")],
            target=f"{name} 관련 여신",
            deliverable=DISCOVERY_STATUS,
            priority=Priority.REVIEW, phase=Phase.BEFORE_DDAY, owner=Owner.POLICY,
            approval=ApprovalStatus.PENDING_REVIEW, automation=Automation.MANUAL,
            human_review_reason="코어 룰엔진 자동판정 범위 밖 — 영향 가능성만 탐지 (의도된 설계)",
        ))

    return ImpactMatrix(policy_id=policy_id, effective_from=effective_from, rows=rows)
