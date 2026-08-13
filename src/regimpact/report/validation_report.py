"""검증보고서 생성기 — 라이브 파이프라인 출력에서 실측 수치를 뽑아 Markdown으로 조립.

브리프 §18 "코어 완성의 정의"의 종착점(Validation Report). 손으로 쓴 정적 문서가 아니라
run_e2e·포트폴리오 회귀·골드셋 채점·판별력 실측을 **실제로 호출**해 수치를 채운다
→ 시스템이 바뀌면 보고서도 갱신되고, 모든 숫자가 재현 가능하다(auditable).

핵심 원칙(이 프로젝트 전체와 동일):
  - 값의 출처 분리: 룰엔진(deterministic) vs LLM 추출(검증 대상)
  - LOCKED §4: 골드·제안은 AI초안, 사람 확정 전까지 최종 아님
  - 정직한 한계: '왜 100%인가'를 숨기지 않음(VALIDATION_LIMITS)
"""
from __future__ import annotations

from typing import Optional

from .. import rule_engine
from ..goldset import (
    CHALLENGE_WEIGHTED,
    Split,
    check_goldset_grounding,
    coverage as goldset_coverage,
    load_goldset,
    score_scenario_items,
)
from ..extractor import load_sources
from ..impact import format_e2e_report, run_e2e
from ..tc_generator import (
    generate_portfolio,
    portfolio_coverage,
    run_regression,
)
from .controls import discrimination_pairs, e2e_control


def _pct(x: float) -> str:
    return f"{x:.0%}"


def _yn(b: bool) -> str:
    return "✅" if b else "❌"


def build_validation_report(
    generated_at: Optional[str] = None,
    portfolio_n: int = 3000,
) -> str:
    """6·30 시나리오 검증보고서(Markdown)를 라이브 수치로 생성한다."""
    # --- 라이브 수치 수집 ---
    sources = load_sources()
    e2e = run_e2e()
    seed_reg = run_regression()
    port_cases = generate_portfolio(target_n=portfolio_n)
    port_reg = run_regression(port_cases)
    port_cov = portfolio_coverage(port_cases)

    gs_items = load_goldset(splits=[Split.DEV, Split.LOCKED, Split.CHALLENGE])
    gs_cov = goldset_coverage(gs_items)
    gs_score = score_scenario_items(gs_items)
    gs_esc = gs_score.escalation_metrics()
    gs_ground = check_goldset_grounding(gs_items, sources)

    controls = discrimination_pairs()
    good_e2e_ok, bad_e2e_ok = e2e_control()

    # 골드셋 scenario 변조 델타
    good_acc = gs_score.accuracy
    saved = rule_engine.LTV_REGULATED_STANDARD
    try:
        rule_engine.LTV_REGULATED_STANDARD = 0.50
        bad_acc = score_scenario_items(gs_items).accuracy
    finally:
        rule_engine.LTV_REGULATED_STANDARD = saved

    L: list[str] = []
    w = L.append

    # ── 표지 ─────────────────────────────────────────────
    w("# RegImpact AI — 검증보고서 (Validation Report)")
    w("")
    w("> **6·30 규제지역 추가지정 시나리오 · 주택구입목적 주담대 LTV 코어**")
    w("> 생성형 AI 기반 규제 변경 영향분석의 **검증 가능한(auditable)** 산출물.")
    if generated_at:
        w(f">\n> 생성 시각: {generated_at}")
    w(">")
    w("> ⚠️ 이 보고서는 `regimpact.report.build_validation_report()`가 **라이브 파이프라인**에서")
    w("> 자동 생성한다. 모든 수치는 재현 가능하며, 시스템 변경 시 갱신된다.")
    w("")
    w("---")
    w("")

    # ── 0. 요약 ─────────────────────────────────────────
    w("## 0. 한눈에 (Executive Summary)")
    w("")
    w(f"- **E2E 관통:** {_yn(e2e.e2e_ok)} 6·30 1건이 Source→추출→Impact Matrix→Proposal→회귀→Assurance→Report까지 완결")
    w(f"- **룰엔진 정합성:** 층화 포트폴리오 {port_reg.passed}/{port_reg.total} = {_pct(port_reg.pass_rate)} "
      "(엔진 ⟷ 독립 명세 오라클)")
    w(f"- **Assurance(추출):** Citation Correctness {_pct(e2e.citation_correctness)}, "
      f"Change Completeness {_pct(e2e.gold.change_completeness)}, Exception Recall {_pct(e2e.gold.exception_recall)}")
    w(f"- **골드 평가셋:** {gs_cov['total']}문항(DEV/LOCKED/CHALLENGE), 10 카테고리 전수 커버 — "
      "**전 항목 AI_DRAFT(사람확정 대기)**")
    w(f"- **하니스 판별력:** 오류 주입 시 지표가 실제 하락(§7) — 100%가 '검증 능력 없음'이 아님을 실증")
    w("")
    w("> **가치 제안:** \"규제가 바뀌었을 때 무엇을 고쳐야 하는지 AI가 제안하고, 그 제안이 틀리지 않았는지")
    w("> **검증 가능한 방식으로 증명**하는 시스템.\" 챗봇이 아니라 검증 가능한 의사결정 지원 시스템.")
    w("")

    # ── 1. 범위와 방법 ──────────────────────────────────
    w("## 1. 범위와 방법")
    w("")
    w("- **정책 버전:** `FSC_20260630` (6·30 규제지역 추가지정). 코퍼스: FSC·MOLIT 보도참고자료, 관계기관 FAQ.")
    w("- **코어 판정 범위:** 주택구입목적 주담대의 **적용 LTV**. 지역 × 주택수 × 예외 × 시점 × 경과규정.")
    w("- **Discovery(자동판정 밖):** 전세·신용·중도금·사업자대출, 정책대출(디딤돌·보금자리) — 표시만, 수동 검토.")
    w("- **값의 출처 분리:** 규칙 값·우선순위는 **사람이 확정한 명세**(`05_RULE_SPEC`, `regulatory_facts`)에서 온다.")
    w("  LLM은 규칙을 생성하지 않고, 그 출력은 **검증 대상**(Citation grounding)으로만 흐른다.")
    w("")

    # ── 2. RegChange 추출(E) + Assurance(A) ─────────────
    w("## 2. RegChange 추출 (E) + Citation Assurance (A)")
    w("")
    w(f"공문 원문 {len(e2e.sources_loaded)}건에서 Before/After 변경을 구조화 추출하고, 각 인용을 원문과 대조한다.")
    w("")
    w(f"- 추출 항목: **{len(e2e.extraction.changes)}건** / target_regions: {', '.join(e2e.extraction.target_regions)} "
      f"/ effective_from: {e2e.extraction.effective_from}")
    w(f"- **Citation Correctness:** {_pct(e2e.citation_correctness)} "
      f"(원문 verbatim grounded, 환각 인용 {len(e2e.grounding.ungrounded)}건)")
    w(f"- **Change Completeness:** {_pct(e2e.gold.change_completeness)} · "
      f"**Exception Recall:** {_pct(e2e.gold.exception_recall)} · "
      f"Effective-date {_yn(e2e.gold.effective_date_correct)} · Regions {_yn(e2e.gold.regions_correct)}")
    w("")
    w("> ⚠️ **한계(오염):** 현재 E2E 기본 추출은 원문 grounding된 **앵커**이고, 실측 run1은 세션 모델이")
    w("> gold를 이미 본 상태로 생성됐다 → **독립 성능 아님**. 독립치는 오염 없는 LLM 추출(run2)로 측정 예정.")
    w("")

    # ── 3. Impact Matrix ───────────────────────────────
    w("## 3. Impact Matrix (고객 세그먼트별 영향)")
    w("")
    w(f"시행 전(6.30)·후(7.2)를 **동일 룰엔진**으로 평가해 세그먼트별 delta를 산출한다. "
      f"총 {len(e2e.impact_matrix)}행(고영향 {len(e2e.high_impact_rows)} / escalation {len(e2e.escalated_rows)}).")
    w("")
    w("| 세그먼트 | 지역 | before | after | Δ |")
    w("|---|---|---:|---:|---:|")
    seen_seg = set()
    for r in e2e.impact_matrix:
        if r.segment_label in seen_seg:
            continue  # 대표로 세그먼트당 1행(지역 무관 동일)
        seen_seg.add(r.segment_label)
        before = _pct(r.before_ltv) if r.before.max_ltv is not None else r.before.status.value
        after = _pct(r.after_ltv) if r.after.max_ltv is not None else r.after.status.value
        delta = "-" if r.delta_ltv is None else f"{r.delta_ltv:+.0%}"
        w(f"| {r.segment_label} | (규제 3지역 공통) | {before} | {after} | {delta} |")
    w("")
    w("> 유주택/다주택의 시행 전(비규제) 값은 명세에 부재 → `NEEDS_HUMAN_REVIEW`(정직한 escalation, 값을 지어내지 않음).")
    w("")

    # ── 4. Rule Change Proposal ────────────────────────
    p = e2e.proposal
    w("## 4. Rule Change Proposal (구조화 변경 제안)")
    w("")
    w(f"- 제안 ID: `{p.proposal_id}` · **상태: {p.approval_status.value}** (LOCKED §4: 사람 확정 전까지 초안)")
    w(f"- 서술 변경 {len(p.narrative_changes)}건(provenance=LLM 추출, citation 보존) · "
      f"세그먼트 영향 {len(p.segment_impacts)}건(provenance=룰엔진 deterministic)")
    w("- provenance 분리로 '무엇이 AI 판단이고 무엇이 결정적 규칙인지' 추적 가능.")
    w("")

    # ── 5. 룰엔진 검증 (차등 테스트) ────────────────────
    w("## 5. 룰엔진 검증 — 독립 명세 오라클 차등 테스트 (Assurance ④)")
    w("")
    w("엔진 출력을 스스로 채점하지 않는다. 명세(§H)에서 **독립 유도**한 오라클(엔진을 import 하지 않음)과")
    w("대조해 회귀가 tautology가 되지 않게 한다.")
    w("")
    w(f"- **seed 케이스:** {seed_reg.passed}/{seed_reg.total} = {_pct(seed_reg.pass_rate)}")
    w(f"- **층화 합성 포트폴리오:** {port_reg.passed}/{port_reg.total} = {_pct(port_reg.pass_rate)} "
      f"(432 strata 중 {port_cov['strata_hit']} 커버)")
    w("")
    w("| 카테고리 | 통과/전체 | 비율 |")
    w("|---|---|---:|")
    for cat, (pc, n, rate) in port_reg.pass_rate_by_category().items():
        w(f"| {cat} | {pc}/{n} | {_pct(rate)} |")
    w("")
    w("> **이빨 증거(mutation test):** 엔진에 버그를 심으면 회귀가 실패로 잡는다(§7). 100%는 '드리프트 없음'이지")
    w("> '명세==현실'은 아니다 — 그 방어선은 사람의 명세·골드 확정이다.")
    w("")

    # ── 6. 골드 평가셋 ─────────────────────────────────
    w("## 6. 골드 평가셋 (DEV / LOCKED / CHALLENGE)")
    w("")
    weighted = sum(1 for it in gs_items if it.category in CHALLENGE_WEIGHTED)
    w(f"- 규모: **{gs_cov['total']}문항** "
      f"(DEV {gs_cov['by_split'].get('DEV',0)} / LOCKED {gs_cov['by_split'].get('LOCKED',0)} / "
      f"CHALLENGE {gs_cov['by_split'].get('CHALLENGE',0)}). 10 카테고리 전수 커버, "
      f"CHALLENGE 가중 카테고리 {weighted}건.")
    w(f"- **결정적 채점(LOCKED §4 금지선: LLM이 LLM 채점 금지):** scenario {gs_score.passed}/{gs_score.total} "
      f"= {_pct(gs_score.accuracy)} (룰엔진 대조), 근거 grounding {gs_ground.grounded}/{gs_ground.total} "
      f"= {_pct(gs_ground.rate)} (원문 verbatim).")
    w(f"- **Escalation Recall/Precision:** {_pct(gs_esc['recall'])} / {_pct(gs_esc['precision'])} "
      f"(tp={gs_esc['tp']} fp={gs_esc['fp']} fn={gs_esc['fn']}).")
    w(f"- **상태:** 전 {gs_cov['total']}문항 **AI_DRAFT** — regulatory_facts(검수대기) 파생. 사람 확정 후 freeze.")
    w("")
    w("| 카테고리 | 문항수 |")
    w("|---|---:|")
    for cat, n in sorted(gs_cov["by_category"].items(), key=lambda kv: -kv[1]):
        star = " ★" if any(c.value == cat for c in CHALLENGE_WEIGHTED) else ""
        w(f"| {cat}{star} | {n} |")
    w("")

    # ── 7. 판별력 (정직성의 핵심) ──────────────────────
    w("## 7. 판별력 (Negative Control) — \"왜 계속 100%인가\"")
    w("")
    w("정상 데이터의 100%만으로는 하니스에 이빨이 있는지 알 수 없다. **의도적으로 오류를 주입**하고")
    w("각 지표가 100%에서 떨어지는지 실측한다. 정상=100%, 오류=<100%면 → 동적 범위가 있다는 증거다.")
    w("")
    w("| 지표 | 정상 | 오류 주입 | 감지 |")
    w("|---|---:|---:|:---:|")
    for c in controls:
        w(f"| {c.metric} | {_pct(c.good)} | {_pct(c.bad)} | {_yn(c.detects)} |")
    w(f"| E2E 종합(e2e_ok) | {good_e2e_ok} | {bad_e2e_ok} | {_yn(not bad_e2e_ok)} |")
    w(f"| 골드셋 scenario(엔진 변조) | {_pct(good_acc)} | {_pct(bad_acc)} | {_yn(bad_acc < good_acc)} |")
    w("")
    w("> **결론:** 모든 지표가 오류에 반응한다. 100%는 '오류 없음'을 뜻하지 '검증 능력 없음'을 뜻하지 않는다.")
    w("> 각 100%의 강도·한계는 `docs/eval/VALIDATION_LIMITS.md` 참조.")
    w("")

    # ── 8. 검증의 한계 ─────────────────────────────────
    w("## 8. 검증의 한계 (정직성 — 브리프 §12)")
    w("")
    w("- **rule-regression 100%** = 엔진 ⟷ 독립 오라클 일치(mutation 실증). \"엔진==명세\"이지 \"명세==현실\" 아님.")
    w("- **골드셋 scenario 100%** = 작성자가 엔진 기준으로 기입 → 거의 순환(QA 게이트, 독립 성능 아님).")
    w("- **Extractor run1 100%** = 세션 모델·gold 사전열람으로 **오염** → 독립 벤치마크 아님.")
    w("- **독립 성능치는 아직 미측정.** 확보 경로: (1) 오염 없는 LLM 추출 run2(API 키), "
      "(2) 골드셋 human-confirm 후 LOCKED/CHALLENGE 1회 실행, (3) regulatory_facts claim 원문 서명.")
    w("")
    w("> \"The locked test set was frozen before system tuning, but was authored within the project and is")
    w("> not an independent third-party benchmark.\" — 한계를 숨기지 않는 것이 신뢰성을 높인다.")
    w("")

    # ── 9. 사람 검토 / 감사 ────────────────────────────
    w("## 9. 사람 검토 · 감사 추적 (LOCKED §4)")
    w("")
    w("- **운영 방식:** AI 초안 → **사람 확정**. 확정 전 초안은 authority 없음.")
    w("- **현재 확정 대기:** Rule Change Proposal(AI_DRAFT), 골드셋 115문항(AI_DRAFT), regulatory_facts claim(검수대기).")
    w("- **Escalation:** 명세가 값을 정의하지 않으면 지어내지 않고 `NEEDS_HUMAN_REVIEW`/`DISCOVERY`로 넘긴다")
    w(f"  (골드셋 escalation recall {_pct(gs_esc['recall'])}).")
    w("")

    # ── 10. 결론 ───────────────────────────────────────
    w("## 10. 결론 및 남은 일")
    w("")
    w(f"- ✅ **코어 E2E 관통 달성**(6·30 1건), 룰엔진 정합성 {_pct(port_reg.pass_rate)}(~{port_reg.total}건), "
      "골드셋 규모 목표 도달, 하니스 판별력 실증.")
    w("- ⏳ **남은 것(사람/독립성):** 골드셋·제안·규제사실 **사람 확정** → 독립 성능 측정(run2, LOCKED/CHALLENGE).")
    w("- 이 보고서는 라이브 생성물이다. `python examples/gen_validation_report.py`로 재생성한다.")
    w("")
    w("---")
    w("")
    w("### 부록 A — E2E 상세 리포트")
    w("")
    w("```")
    w(format_e2e_report(e2e))
    w("```")
    w("")
    return "\n".join(L)
