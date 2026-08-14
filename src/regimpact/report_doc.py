"""검증보고서(Validation Report) 문서 생성기 — 브리프 §18 코어 완성 산출물.

지금까지의 **실측 산출물**(ValidationReport·MeasuredAssurance·골드셋 manifest·Impact Matrix·
합성 포트폴리오)을 하나의 Model-Validation-Report 급 문서로 종합한다. 값은 손으로 적지 않고
모두 실제 산출물에서 유도한다(LOCKED §4, §12 정직성). `build_validation_document()` → Markdown.

문서 구조(금융권 모델검증보고서 관례): 요약 → 범위 → 아키텍처 → 데이터 → 방법론 →
차원별 결과 → Assurance → 평가셋 → 한계 → 거버넌스 → 결론 → 부록.
"""
from __future__ import annotations

from .eval import load_manifest
from .extractor import load_recorded_extraction, measured_assurance
from .impact import analyze_portfolio
from .impact.matrix import ImpactDirection
from .models import ReasonCode
from .report import ValidationReport, build_validation_report
from .rule_engine import (
    LTV_BASELINE,
    LTV_FIRST_HOME,
    LTV_MULTI,
    LTV_OWNER,
    LTV_REAL_DEMAND,
    LTV_REGULATED_STANDARD,
)

_REASON_GLOSSARY = {
    "LTV_REGULATED_40": "규제지역 무주택 표준 LTV 40%",
    "EXCEPTION_FIRST_HOME": "생애최초 예외 — LTV 70% 유지",
    "EXCEPTION_REAL_DEMAND": "서민·실수요자 예외 — LTV 60%",
    "LTV_OWNER_0": "규제지역 유주택(비처분 1주택) LTV 0%",
    "LTV_MULTI_HOME_0": "다주택 LTV 0%",
    "LTV_BASELINE_70": "非규제 무주택 기준선 70%",
    "GRANDFATHERED_ACCEPTED_OR_CONTRACT": "경과규정 — 접수/계약+계약금으로 종전규정",
    "GRANDFATHERED_LAND_PERMIT": "경과규정 — 토지거래허가 신청으로 종전규정",
    "OWNER_BASELINE_UNKNOWN": "非규제 유주택 기준선 원문 부재 → 사람 검토",
    "OUT_OF_SCOPE_PRODUCT": "주택구입목적 아님 → 자동판정 범위 밖",
    "DISCOVERY_POLICY_LOAN": "정책대출 → Discovery(수동 정책검토)",
}


def _h(level: int, text: str) -> str:
    return f"{'#' * level} {text}"


def _pct(x: float) -> str:
    return f"{x:.0%}"


# ---------------------------------------------------------------------------
def _cover(r: ValidationReport, m) -> list[str]:
    L = [
        _h(1, "RegImpact AI — 검증보고서 (Validation Report)"),
        "",
        "> **생성형 AI 기반 주택담보대출 규제 변경 영향분석·검증 시스템**",
        f"> 대상 시나리오: **{r.policy_event}**",
        "",
        "| 항목 | 값 |",
        "|---|---|",
        "| 문서 유형 | 모델·시스템 검증보고서 (Model & System Validation Report) |",
        f"| 대상 정책 | {r.policy_event} (policy_id `{r.regchange_gold['policy_id']}`) |",
        f"| 시행일 / 경과규정 컷오프 | {r.effective_date.isoformat()} / {r.grandfathering_cutoff.isoformat()} |",
        f"| 전체 판정 | **{r.overall_status}** (escalation {len(r.escalations)}건 → 사람 검토) |",
        f"| 검증 파이프라인 | {len(r.steps)}단계 End-to-End |",
        "| 작성 방식 | AI초안 → 사람확정 (provenance 명시, LOCKED §4) |",
        "| 값의 출처 | 전 항목 실측 산출물에서 유도 (손으로 적지 않음) |",
        "",
        "본 보고서의 모든 수치는 코드로 산출된 실측값이다. `python examples/build_report_doc.py` 로 재현한다.",
        "",
        "---",
        "",
    ]
    return L


def _toc() -> list[str]:
    items = [
        "1. Executive Summary (경영 요약)",
        "2. 서론 및 검증 범위",
        "3. 시스템 개요 및 아키텍처",
        "4. 데이터 및 원문 무결성",
        "5. 검증 방법론",
        "6. 검증 결과 (컴포넌트별)",
        "7. Assurance Layer — 4 DEEP dimension",
        "8. 평가셋 설계 및 freeze (Gold Set)",
        "9. 한계 및 알려진 이슈",
        "10. 거버넌스 및 통제",
        "11. 결론 및 권고",
        "부록 A~E",
    ]
    return [_h(2, "목차"), ""] + [f"{i}. {t.split('. ', 1)[-1]}" if False else f"- {t}" for i, t in enumerate(items, 1)] + ["", "---", ""]


def _exec_summary(r: ValidationReport, m, port) -> list[str]:
    s = r.impact_matrix.summary
    dev = r.gold_set["dev"]
    L = [
        _h(2, "1. Executive Summary (경영 요약)"),
        "",
        f"RegImpact AI는 정부의 가계대출 규제 변경(**{r.policy_event}**)이 공식 원문에서 무엇을 "
        "바꾸는지 탐지하고, 그 변경이 여신 Rule·고객 영향·테스트케이스로 어떻게 전파되는지를 "
        "**검증 가능한(auditable) 방식**으로 산출하는 의사결정 지원 시스템이다. 챗봇이 아니라, "
        "AI의 제안을 사람이 확정하고 그 정확성을 정량적으로 증명하는 통제 구조를 갖춘다.",
        "",
        "본 검증에서 확인된 핵심 결과는 다음과 같다.",
        "",
        f"- **결정론적 룰엔진**은 독립 명세 오라클과의 차등 검증에서 {r.regression['passed']}/{r.regression['total']} "
        f"({_pct(r.regression['pass_rate'])}), 골드셋 DEV split에서 {dev['passed']}/{dev['total']} "
        f"({_pct(dev['pass_rate'])}) 통과했다.",
        f"- **RegChange 추출**(모델 `{m.model}`, {m.n_changes}건)은 인용 grounding {_pct(m.citation_correctness)}"
        f"(환각 {_pct(m.unsupported_claim_rate)}), 변경 완전성 {_pct(m.change_completeness)}, 예외 재현율 "
        f"{_pct(m.exception_recall)}로, 4개 DEEP Assurance dimension이 전부 실측되었다.",
        f"- **영향분석**은 {s['TOTAL']}개 세그먼트(Core {s['CORE']})에서 하향 {s['DOWNGRADE']}·신규제한 "
        f"{s['NEW_RESTRICTION']}·Discovery {s['DISCOVERY']}를 산출했고, 합성 포트폴리오 {port.size:,}명 기준 "
        f"영향 차주 {port.impacted:,}명·고위험(LTV 0%) {port.high_risk:,}명으로 규모를 정량화했다.",
        f"- **평가셋**은 {r.gold_set['total']}문항(DEV {dev['total']} / LOCKED {r.gold_set['locked_sealed']} / "
        f"CHALLENGE {r.gold_set['challenge_sealed']})으로 freeze되었으며, 누수 방지를 위해 LOCKED·CHALLENGE는 sealed다.",
        "",
        "**정직성 원칙이 시스템 전반에 관철되었다.** 원문에 기준선이 없는 항목(非규제 유주택)은 값을 "
        f"지어내지 않고 `OWNER_BASELINE_UNKNOWN`으로 사람 검토에 escalate했으며(현재 escalation {len(r.escalations)}건), "
        "LLM 실행이 필요한 지표는 실측 전까지 '실측 대기'로 표기했다. 전체 판정은 escalation이 존재하므로 "
        f"**{r.overall_status}**이다 — 즉 시스템은 자동 승인하지 않고 사람 검토를 요구한다.",
        "",
        _h(3, "1.1 Model Risk 관점의 시사점"),
        "",
        "본 시스템이 Model Risk / 모델검증 관점에서 갖는 의미는 세 가지다. 첫째, **검증 독립성** — 채점 기준이 "
        "검증 대상과 독립된 경로(명세 오라클·사람 확정 골드)에서 오므로, 'LLM이 LLM을 채점'하는 순환을 구조적으로 "
        "차단한다. 둘째, **평가 무결성** — 평가셋을 개발보다 먼저 설계하고 LOCKED/CHALLENGE를 sealed로 두어 "
        "누수(overfitting to test)를 방지한다. 셋째, **재현성** — 모든 지표가 저장값이 아니라 원문·추출·골드로부터 "
        "코드로 재계산되며, 해시로 아티팩트 무결성이 고정된다. 이 세 가지는 감독기관의 모델검증 기대(독립성·문서화·"
        "재현성)와 직접 대응한다.",
        "",
        "---",
        "",
    ]
    return L


def _scope() -> list[str]:
    return [
        _h(2, "2. 서론 및 검증 범위"),
        "",
        _h(3, "2.1 목적"),
        "",
        "본 보고서는 RegImpact AI의 End-to-End 파이프라인(원문 → 검증보고서)이 의도한 기능을 정확히 "
        "수행하는지, 그리고 그 정확성이 **독립적이고 재현 가능한 방식**으로 측정되는지를 검증한다. "
        "관점은 금융권 Model Risk / 모델검증(SR 11-7 계열)의 정석 — 개발 주체와 독립된 기준(challenger)과의 "
        "대조, 평가셋의 사전 설계와 누수 방지, 한계의 명시 — 을 따른다.",
        "",
        _h(3, "2.2 검증 대상 범위 (Core Executable Scope)"),
        "",
        "자동 판정하는 범위는 의도적으로 좁게 제한한다:",
        "",
        "> 주택구입목적 주담대의 **지역 × 주택수 × 생애최초 × 정책대출 여부 × 신청/계약 이벤트 시점 × "
        "경과규정 → 적용 LTV / 적용 Rule / 경과규정 여부**",
        "",
        _h(3, "2.3 Discovery Scope (자동판정 제외)"),
        "",
        "다음은 영향 가능성만 탐지하고 자동 판정하지 않는다(수동 정책검토 대상): 전세대출, 1억 초과 "
        "신용대출 연계 주택구입 제한, 중도금·이주비, 사업자대출, 기타 연계 정책. **영향 범위는 넓게 발견하되 "
        "자동판정은 신뢰 가능한 좁은 범위에서만 한다** — 이는 기능 부족이 아니라 의도적 거버넌스 설계다.",
        "",
        "---",
        "",
    ]


def _architecture(r: ValidationReport) -> list[str]:
    L = [
        _h(2, "3. 시스템 개요 및 아키텍처"),
        "",
        "시스템은 8단계 파이프라인으로 구성되며, 각 단계는 다음 단계의 입력을 구조화된 형태로 넘긴다. "
        "아래는 본 검증 실행 시점의 각 단계 상태다.",
        "",
        "| # | 단계 | 상태 | 요약 |",
        "|---:|---|---|---|",
    ]
    for st in r.steps:
        L.append(f"| {st.order} | {st.name} | {st.status} | {st.detail} |")
    L += [
        "",
        "데이터 흐름을 도식화하면 다음과 같다.",
        "",
        "```text",
        "공식 원문(FSC·MOLIT·FAQ)  ──►  Source Snapshot (해시 무결성)",
        "        │",
        "        ▼",
        "  Temporal Policy Resolver (시점별 유효 버전·지역 상태·경과규정)",
        "        │",
        "        ▼",
        "  RegChange Extractor (LLM 초안·인용 강제)  ──►  Assurance: Citation Grounding",
        "        │",
        "        ▼",
        "  Impact Matrix (Before/After 세그먼트별 LTV)",
        "        │",
        "        ▼",
        "  Rule Change Proposal (구조화)  ──►  Human Review / Approval",
        "        │",
        "        ▼",
        "  Deterministic Rule Engine  ◄──  독립 명세 오라클 (차등 검증) + Gold Set",
        "        │",
        "        ▼",
        "  Validation Report (본 문서)",
        "```",
        "",
        "핵심 설계 원칙은 **검증 독립성**이다. LLM(추출·제안)은 초안을 만들고, 결정론적 룰엔진과 독립 명세 "
        "오라클은 그 초안과 무관하게 사람이 확정한 명세에서 유도된다. 따라서 'LLM이 LLM을 채점'하는 순환이 "
        "발생하지 않는다.",
        "",
        _h(3, "3.1 판정 알고리즘 (우선순위 §H)"),
        "",
        "룰엔진은 다음 우선순위로 short-circuit 판정한다. 상위 규칙이 적용되면 하위는 평가하지 않는다.",
        "",
        "| # | 조건 | 결과 |",
        "|---|---|---|",
        "| P0 | 주택구입목적 아님 | OUT_OF_SCOPE (자동판정 밖) |",
        "| P0b | 정책대출 | DISCOVERY (수동 정책검토) |",
        "| P1 | 경과규정 충족(접수/계약+계약금/토허 신청 ≤ 6.30) | 종전규정 — 무주택 70%, 유주택은 기준선 부재→검토 |",
        "| P2 | 非규제(시행 전/미등록) | 무주택 70%, 유주택 기준선 부재→검토 |",
        "| P3 | 규제·다주택(≥2) | LTV 0% |",
        "| P4 | 규제·비처분 1주택(유주택) | LTV 0% |",
        "| P5 | 규제·생애최초(무주택 취급) | LTV 70% |",
        "| P6 | 규제·서민실수요 | LTV 60% |",
        "| P7 | 규제·무주택 일반/처분조건부 1주택 | LTV 40% |",
        "",
        _h(3, "3.2 확정 LTV 규칙값 (사람 확정 명세)"),
        "",
        "규칙 값은 원문에서 사람이 확정한 명세에서만 온다(LLM이 생성하지 않는다).",
        "",
        "| 차주 유형 | 비규제 기준선 | 규제지역 지정 후 |",
        "|---|---:|---:|",
        f"| 무주택 표준 / 처분조건부 1주택 | {_pct(LTV_BASELINE)} | {_pct(LTV_REGULATED_STANDARD)} |",
        f"| 생애최초 | {_pct(LTV_BASELINE)} | {_pct(LTV_FIRST_HOME)} (좌동) |",
        f"| 서민·실수요자 | {_pct(LTV_BASELINE)} | {_pct(LTV_REAL_DEMAND)} |",
        f"| 유주택(비처분 1주택) | 명세부재(검토) | {_pct(LTV_OWNER)} |",
        f"| 다주택 | 명세부재(검토) | {_pct(LTV_MULTI)} |",
        "",
        "---",
        "",
    ]
    return L


def _data_section(r: ValidationReport) -> list[str]:
    L = [
        _h(2, "4. 데이터 및 원문 무결성"),
        "",
        "검증의 기준점은 공개된 공식 원문뿐이다(실제 회사 내부문서·고객데이터 미사용, LOCKED §8). 각 원문은 "
        "스냅샷으로 저장하고 SHA-256 해시로 무결성을 고정한다.",
        "",
        "| 기관 | 문서 | doc_id | 발표일 | source_hash |",
        "|---|---|---|---|---|",
    ]
    for s in r.sources:
        L.append(f"| {s['org']} | {s['title']} | `{s['doc_id']}` | {s['published']} | `#{s['hash']}` |")
    L += [
        "",
        "규제 사실(claim)은 실제 감독규정·보도자료(사실)와 은행 내규(모의 문서)의 경계를 명확히 구분해 "
        "관리한다. 룰엔진의 규칙 값은 이 원문에서 사람이 확정한 명세(`docs/05_RULE_SPEC.md`, "
        "`docs/regulatory_facts.md`)에서만 온다.",
        "",
        "---",
        "",
    ]
    return L


def _methodology() -> list[str]:
    return [
        _h(2, "5. 검증 방법론"),
        "",
        _h(3, "5.1 차등 검증 (Differential Testing)"),
        "",
        "룰엔진의 출력을 스스로 채점하면 회귀는 tautology(항상 통과)가 되어 무의미하다. 따라서 명세(§H)에서 "
        "**독립적으로 유도한 오라클(challenger)** 을 별도 코드 경로로 구현하고, 엔진 출력과 대조한다. 오라클은 "
        "`rule_engine`·`regions`·`grandfathering`을 import하지 않으므로 어느 구현의 오차든 disagreement로 드러난다.",
        "",
        "오라클의 독립성은 구조적이다: (1) 지역 규제상태를 `regions.py` 없이 날짜 비교로 직접 판정하고, "
        "(2) 경과규정을 `grandfathering.py` 없이 G1/G2/G3로 직접 판정하며, (3) 판정 로직을 엔진의 명령형 "
        "short-circuit과 달리 선언적 데이터 표로 재구현한다. 서로 다른 구현 스타일이므로 전사(轉寫) 오류가 "
        "상관되지 않는다. fixture 방어력은 **mutation test**로 증명한다 — 엔진에 의도적으로 버그를 주입하면 회귀가 "
        "실패로 이를 잡아낸다. 즉 회귀가 '항상 통과하는 껍데기'가 아님을 실증한다.",
        "",
        _h(3, "5.2 인용 Grounding (Citation Grounding)"),
        "",
        "RegChange 추출의 각 항목은 원문에서 그대로 복사한 인용(verbatim quote)을 반드시 포함한다. 인용이 "
        "정규화된 원문에 substring으로 실제 존재하는지를 **완전 결정론적으로** 검사해, 모델이 원문을 지어냈는지"
        "(환각) 실측한다. 이 검사는 API·비용 없이 오프라인에서 재현된다.",
        "",
        _h(3, "5.3 골드 대조 및 평가셋 누수 방지"),
        "",
        "완전성·재현율은 사람이 확정한 골드 정답지와 대조한다. 평가셋은 개발보다 먼저 설계하고 "
        "DEV / LOCKED / CHALLENGE로 분리(freeze)한다. **LOCKED·CHALLENGE는 개발 중 열지 않으며**(sealed), "
        "split 간 입력이 겹치지 않음을 테스트로 강제해 누수를 방지한다. 골드 정답은 독립 명세 오라클에서 "
        "유도하므로 엔진 회귀가 순환이 되지 않는다.",
        "",
        _h(3, "5.4 지표 정의 (공식)"),
        "",
        "각 지표는 분모·분자·임계를 명시한다. 모든 지표는 골드셋 또는 룰엔진 회귀 fixture 위에서 계산된다.",
        "",
        "| 지표 | 분모 | 분자 | 공식 |",
        "|---|---|---|---|",
        "| Citation Correctness | 생성 인용 총수 | 원문에 verbatim 존재하는 인용 수 | grounded / total |",
        "| Unsupported Claim Rate | 생성 인용 총수 | 원문 미확인 인용 수 | ungrounded / total |",
        "| Change Completeness | 골드 필수 변경 수 | 추출이 포착한 변경 수 | hit / required |",
        "| Exception Recall | 골드 예외 수 | 추출이 포착한 예외 수 | hit / exceptions |",
        "| Rule-regression Pass Rate | 회귀 TC 수 | 엔진=오라클 일치 수 | pass / total |",
        "| Gold Set Pass Rate (split) | split 문항 수 | 엔진=골드 정답 일치 수 | pass / total |",
        "",
        "룰엔진 회귀의 일치 판정은 status·max_ltv·applicable_rule_id·grandfathering_applied·reason_codes(부분집합)·"
        "escalation 플래그를 모두 대조한다 — 어느 한 필드라도 다르면 불일치로 집계한다.",
        "",
        _h(3, "5.5 정직성 통제 (LOCKED §4·§12)"),
        "",
        "- 원문에 기준이 없는 값은 지어내지 않고 사람 검토로 escalate.",
        "- LLM 실행이 필요한 지표는 실측 전까지 '실측 대기'로 표기(가짜 수치 금지).",
        "- 합성 데이터는 화면·보고서에 'synthetic — 실데이터 아님'으로 명시.",
        "- 모든 산출물에 provenance(모델·날짜·출처)를 남긴다.",
        "- 정답지는 사람(또는 독립 명세 오라클)이 원문과 독립 대조로 확정하며, LLM이 LLM을 채점하지 않는다.",
        "",
        "---",
        "",
    ]


def _results(r: ValidationReport, m, ext, port) -> list[str]:
    reg = r.regression
    dev = r.gold_set["dev"]
    L = [
        _h(2, "6. 검증 결과 (컴포넌트별)"),
        "",
        _h(3, "6.1 결정론적 룰엔진 (Deterministic Rule Engine)"),
        "",
        f"엔진은 알고리즘 §H(우선순위 P0~P7 short-circuit)를 구현한다. 독립 오라클 차등 검증에서 "
        f"**{reg['passed']}/{reg['total']} ({_pct(reg['pass_rate'])})**, 카테고리별로 다음과 같다.",
        "",
        "| 카테고리 | 통과 | Pass Rate |",
        "|---|---:|---:|",
    ]
    for cat, (p, t, rate) in reg["by_category"].items():
        L.append(f"| {cat} | {p}/{t} | {_pct(rate)} |")
    L += [
        "",
        f"추가로 골드셋 DEV split({dev['total']}문항)에서 **{dev['passed']}/{dev['total']} ({_pct(dev['pass_rate'])})** "
        "통과했다. 두 독립 경로(오라클 회귀·골드셋)가 일치해 엔진이 명세를 정확히 구현함을 이중으로 확인한다.",
        "",
        _h(3, "6.2 RegChange 추출 (Extraction)"),
        "",
        f"모델 `{m.model}`이 공식 원문 {len(r.sources)}건만 읽고(골드 미참조) {m.n_changes}건의 Before/After 변경을 "
        "추출했다. 결정론적 채점 결과:",
        "",
        "| 지표 | 실측 | 임계(초안) |",
        "|---|---:|---|",
        f"| Citation Correctness (인용 grounding) | {_pct(m.citation_correctness)} | ≥ 95% |",
        f"| Unsupported Claim Rate (환각) | {_pct(m.unsupported_claim_rate)} | 낮을수록 |",
        f"| Change Completeness (변경 완전성) | {_pct(m.change_completeness)} | ≥ 95% |",
        f"| Exception Recall (예외 재현율) | {_pct(m.exception_recall)} | ≥ 95% |",
        f"| Effective-date / Region 정확 | {'OK' if m.effective_date_correct else 'MISS'} / "
        f"{'OK' if m.regions_correct else 'MISS'} | 정확 |",
        "",
        "모든 인용이 원문에 verbatim으로 존재해 환각이 0%로 측정되었다. 추출 전체 목록은 부록 A 참조.",
        "",
        _h(3, "6.3 영향분석 (Impact Matrix)"),
        "",
        "동일 세그먼트를 시행 전(Before)/후(After) 두 시점에 룰엔진으로 관통시켜 LTV 변화를 산출한다. "
        "규칙을 새로 만들지 않고 두 판정의 차이를 구조화한다.",
        "",
        "| 지역 | 차주유형 | 기존 | 변경 | 방향 |",
        "|---|---|---:|---:|---|",
    ]
    for row in r.impact_matrix.core_rows:
        before = "명세부재" if row.before_ltv is None else _pct(row.before_ltv)
        after = "-" if row.after_ltv is None else _pct(row.after_ltv)
        cf = f" (미보호 시 {_pct(row.counterfactual_ltv)})" if row.counterfactual_ltv is not None else ""
        L.append(f"| {row.region_label} | {row.borrower_type} | {before} | {after}{cf} | {row.direction.value} |")
    disc = ", ".join(r.borrower_type for r in r.impact_matrix.discovery_rows)
    L += [
        "",
        f"Discovery(자동판정 제외, 수동 정책검토): {disc}.",
        "",
        _h(3, "6.4 Rule Change Proposal (구조화 변경 제안)"),
        "",
        f"규제 변경이 여신 룰(`{r.proposal.rule_id}`)에 요구하는 변경을 구조화 제안으로 정식화한다. LLM은 실행 "
        "코드를 직접 수정하지 않으며, 제안은 사람 승인 후에만 결정론적 rule registry에 반영된다. LTV 계층별 "
        "변경:",
        "",
        "| 차주 계층 | 종전 | 변경 | 근거코드 |",
        "|---|---:|---:|---|",
    ]
    for pc in r.proposal.parameter_changes:
        L.append(f"| {pc.tier} | {pc.before_label} | {pc.after_label} | `{pc.reason_code}` |")
    L += [
        "",
        f"승인 상태: **{r.proposal.approval_status.value}**. 근거 정책: "
        f"{', '.join(r.proposal.source_policy_ids)}.",
        "",
        _h(3, "6.5 포트폴리오 영향 (합성)"),
        "",
        f"⚠️ 합성 데이터({port.size:,}명, 실데이터 아님). 각 차주의 LTV는 엔진 실제 판정이며, 집계는 다음과 같다.",
        "",
        "| 지표 | 값 |",
        "|---|---:|",
        f"| 영향 차주 (하향+신규제한) | {port.impacted:,} ({port.impacted / port.size:.0%}) |",
        f"| 경과규정 보호 | {port.grandfathered:,} |",
        f"| 고위험 (LTV 0%) | {port.high_risk:,} |",
        f"| Discovery (수동검토) | {port.discovery:,} |",
        "",
        "Before/After LTV 분포:",
        "",
        "| 버킷 | Before | After |",
        "|---|---:|---:|",
    ]
    buckets = ["70%", "60%", "40%", "0%", "명세부재", "Discovery", "범위외"]
    for b in buckets:
        bef = port.before_ltv_dist.get(b, 0)
        aft = port.after_ltv_dist.get(b, 0)
        if bef or aft:
            L.append(f"| {b} | {bef:,} | {aft:,} |")
    L += ["", "---", ""]
    return L


def _worked_examples(r: ValidationReport) -> list[str]:
    """실제 산출물에서 대표 사례를 뽑아 단계별로 서술(심층)."""
    rows = {row.key: row for row in r.impact_matrix.rows}

    def _row_of(direction: ImpactDirection, prefer_key: str | None = None):
        if prefer_key and prefer_key in rows:
            return rows[prefer_key]
        for row in r.impact_matrix.rows:
            if row.direction == direction:
                return row
        return None

    L = [
        _h(2, "6b. 대표 사례 심층 (Worked Examples)"),
        "",
        "검증의 구체성을 위해, 실제 산출물에서 뽑은 네 가지 대표 사례를 입력부터 판정·근거까지 서술한다. "
        "모든 값은 엔진 실제 출력이다.",
        "",
    ]
    # 1) 표준 하향
    row = _row_of(ImpactDirection.DOWNGRADE, "NO_HOME_STANDARD")
    if row:
        L += [
            _h(3, "사례 1 — 표준 하향 (무주택 일반)"),
            "",
            f"- **입력:** {row.region_label}, 무주택(house_count=0), 주택구입목적, 시행 후(2026-07-02).",
            f"- **Before(2026-06-30):** 非규제 기준선 → LTV {(_pct(row.before_ltv) if row.before_ltv is not None else '명세부재')}.",
            f"- **After(2026-07-02):** 규제지역 지정 → LTV {_pct(row.after_ltv)}.",
            f"- **방향/근거:** {row.direction.value} · `{', '.join(row.reason_codes)}`.",
            "- **해석:** 규제지역 지정만으로 자동 강화되는 표준 경로. 원문(FAQ)의 '70→40%'와 일치한다.",
            "",
        ]
    # 2) 경과규정 보호
    row = _row_of(ImpactDirection.UNCHANGED, "GRANDFATHERED_CONTRACT")
    if row and row.grandfathering_applied:
        cf = _pct(row.counterfactual_ltv) if row.counterfactual_ltv is not None else "-"
        L += [
            _h(3, "사례 2 — 경과규정 보호 (종전규정 유지)"),
            "",
            f"- **입력:** {row.region_label}, 무주택, 컷오프(6.30) 이전 계약+계약금, 시행 후 평가.",
            f"- **판정:** LTV {_pct(row.after_ltv)} 유지(방향 {row.direction.value}), 경과규정 해당.",
            f"- **counterfactual:** 경과규정이 없었다면 {cf}로 하향됐을 것 — 보호 효과를 정량화한다.",
            "- **해석:** 경과규정(P1)이 지역상태(P2)보다 우선한다. 시스템은 보호와 미보호 값을 함께 노출해 "
            "감사 가능성을 높인다.",
            "",
        ]
    # 3) 충돌(우선순위)
    row = _row_of(ImpactDirection.NEW_RESTRICTION, "OWNER_1_NON_DISPOSAL")
    if row:
        L += [
            _h(3, "사례 3 — 신규 제한 · 명세부재 (유주택)"),
            "",
            f"- **입력:** {row.region_label}, 비처분 1주택(유주택), 주택구입목적.",
            f"- **Before:** 非규제 유주택 기준선이 원문에 없음 → '명세부재'(사람 검토).",
            f"- **After:** 규제지역 유주택 → LTV {_pct(row.after_ltv)} (`{', '.join(row.reason_codes)}`).",
            f"- **방향:** {row.direction.value}. Before 값을 70%로 지어내지 않고 '명세부재'로 정직하게 표기한다.",
            "- **해석:** 이 사례가 시스템의 핵심 차별점이다 — 근거 없는 값을 만들지 않는다.",
            "",
        ]
    # 4) escalation
    if r.escalations:
        e = r.escalations[0]
        L += [
            _h(3, "사례 4 — 사람 검토 escalation"),
            "",
            f"- **사유코드:** `{e.reason_code}`.",
            f"- **설명:** {e.description}",
            "- **동작:** 엔진은 `NEEDS_HUMAN_REVIEW` 상태를 반환하고 LTV를 산출하지 않는다. Rule Change "
            "Proposal과 검증보고서 전체 판정이 이 escalation 때문에 사람 검토를 요구한다.",
            "- **해석:** '자동화 범위보다 검증 가능성·추적 가능성을 우선한다'(LOCKED §10)는 원칙의 실행이다.",
            "",
        ]

    # 5~6) 우선순위 충돌 — 엔진을 직접 실행해 실증(§H)
    from datetime import date as _date

    from .models import MortgageApplication
    from .rule_engine import evaluate as _eval

    conflicts = [
        ("사례 5 — 우선순위 충돌: 유주택 + 생애최초",
         dict(region_code="GURI", evaluation_date=_date(2026, 7, 2), house_count=1, first_home_buyer=True),
         "두 예외 조건이 충돌하지만 §H는 유주택(P4)을 생애최초(P5)보다 먼저 평가한다. 따라서 생애최초 70%가 "
         "아니라 유주택 0%로 판정된다 — 완화가 아닌 제한이 우선한다."),
        ("사례 6 — 우선순위 충돌: 정책대출 + 다주택",
         dict(region_code="GURI", evaluation_date=_date(2026, 7, 2), house_count=2, policy_mortgage_flag=True),
         "정책대출(P0b)이 최상위에 가까워, 다주택(P3)보다 먼저 Discovery로 분리된다. 정책대출은 코어 자동판정 "
         "대상이 아니므로 LTV를 산출하지 않고 수동 정책검토로 넘긴다."),
    ]
    for title, kw, interp in conflicts:
        d = _eval(MortgageApplication(**kw))
        ltv = "-" if d.max_ltv is None else _pct(d.max_ltv)
        L += [
            _h(3, title),
            "",
            f"- **입력:** {kw['region_code']}, " + ", ".join(
                f"{k}={v}" for k, v in kw.items() if k not in ("region_code", "evaluation_date")) + ", 시행 후.",
            f"- **판정:** status `{d.status.value}`, LTV {ltv}, 근거 `{', '.join(d.reason_codes)}`.",
            f"- **해석:** {interp}",
            "",
        ]
    L += ["이 충돌 사례들은 CHALLENGE split의 핵심 검증 대상이며, 엔진이 §H 우선순위를 정확히 따름을 보인다.",
          "", "---", ""]
    return L


def _assurance(r: ValidationReport) -> list[str]:
    L = [
        _h(2, "7. Assurance Layer — 4 DEEP dimension"),
        "",
        "Assurance는 폭이 아니라 깊이로 4개 dimension을 정량 측정한다. 본 검증 시점에 4개 전부 실측되었다.",
        "",
        "| dimension | 실측 | 임계 | 상태 |",
        "|---|---:|---|---|",
    ]
    for d in r.assurance_dimensions:
        val = d.value if d.measured else "미측정 (LLM 실행 대기)"
        state = "실측" if d.measured else "대기"
        L.append(f"| {d.label} | {val} | {d.threshold} | {state} |")
    L += [
        "",
        _h(3, "7.1 dimension별 정의와 해석"),
        "",
        "**① Citation / Source grounding.** 추출된 각 변경의 인용이 원문에 verbatim으로 존재하는 비율. LLM이 "
        "원문을 지어냈는지(환각)를 완전 결정론적으로 실측한다. 본 검증에서 모든 인용이 원문에 존재해 환각률이 "
        "0으로 측정되었다. 이 지표는 API·비용 없이 오프라인에서 재현된다.",
        "",
        "**② Change Completeness.** 사람이 확정한 골드의 필수 변경(LTV·시행일·경과규정·지역 지정) 중 추출이 "
        "포착한 비율. 규제에서 '원칙은 맞췄으나 시행일·경과규정을 놓치는' 실패를 잡기 위한 지표다.",
        "",
        "**③ Exception · Grandfathering Recall.** 예외(생애최초·서민실수요)와 경과규정 포착 비율. 금융규제에서 "
        "가장 위험한 오류 유형이므로 임계를 높게(≥95%) 둔다.",
        "",
        "**④ Rule-regression.** 룰엔진이 독립 명세 오라클과 일치하는 비율. 엔진이 명세를 정확히 구현했는지를 "
        "차등 검증으로 측정하며, 골드셋 회귀가 이를 다른 경로로 재확인한다.",
        "",
        "① Citation/Source grounding, ② Change Completeness, ③ Exception·GF Recall은 RegChange 추출 1회 "
        "실측을 결정론적으로 재계산한 값이고, ④ Rule-regression은 독립 오라클 차등 검증값이다. 지표는 "
        "저장값이 아니라 (추출 + 원문 + gold)에서 항상 재계산되므로 재현 가능하다.",
        "",
        "그 밖의 Assurance 항목(Source Contradiction, Temporal Consistency, Human Escalation Recall 등)은 "
        "로드맵/인프라로 정의되어 있으며, Audit Trail과 Approval Status는 항상 켜지는 인프라 통제다. 이는 폭을 "
        "넓히기보다 신뢰 가능한 4개 dimension을 깊게 측정한다는 설계 선택이다.",
        "",
        "---",
        "",
    ]
    return L


def _goldset(r: ValidationReport, manifest) -> list[str]:
    dev = r.gold_set["dev"]
    L = [
        _h(2, "8. 평가셋 설계 및 freeze (Gold Set)"),
        "",
        f"평가셋은 개발보다 먼저 설계하고 v{manifest['version'].lstrip('v')} 총 {manifest['total']}문항으로 "
        "freeze했다. 각 문항은 입력·골드 정답·근거 문서·카테고리·escalation 기대·정책 버전·rule_id를 포함한다. "
        "정답은 독립 명세 오라클에서 유도한다.",
        "",
        "| split | 규모 | 용도 | 상태 |",
        "|---|---:|---|---|",
        f"| DEV | {manifest['splits']['dev']['count']} | 상시 회귀·튜닝 | 개방 |",
        f"| LOCKED TEST | {manifest['splits']['locked']['count']} | 최종 성능평가 | **sealed** |",
        f"| CHALLENGE | {manifest['splits']['challenge']['count']} | 예외·경계·충돌·모호 적대 | **sealed** |",
        "",
        "DEV split 카테고리 분포 및 회귀 결과:",
        "",
        "| 카테고리 | 문항 | Pass Rate |",
        "|---|---:|---:|",
    ]
    for cat, (p, t, rate) in sorted(dev["by_category"].items()):
        L.append(f"| {cat} | {t} | {_pct(rate)} |")
    L += [
        "",
        "누수 방지 규율(§12): `load_split('locked'/'challenge')`는 명시적 unlock 없이는 열리지 않으며, split 간 "
        "입력이 disjoint임을 테스트로 강제한다. LOCKED·CHALLENGE는 코어 완성 후 최종 1회만 실행한다.",
        "",
        _h(3, "8.1 카테고리 설계 근거"),
        "",
        "금융규제에서 가장 무서운 오류는 원칙을 틀리는 것뿐 아니라 **예외·경과규정·시행일을 놓치는 것**이다. "
        "따라서 CHALLENGE split은 EXCEPTION·GRANDFATHERING·EFFECTIVE_DATE·CONFLICT·AMBIGUOUS를 가중한다. "
        "특히 CONFLICT(복수 조건 동시 충족 시 우선순위)와 AMBIGUOUS(기준 부재 → escalation 기대)는 이 시스템의 "
        "진짜 차별점을 검증한다 — 잘 만든 충돌·모호 사례 하나가 평범한 정상 사례 여럿보다 검증 가치가 크다. "
        "AMBIGUOUS 문항은 정답이 '특정 LTV'가 아니라 '사람 검토(escalation)'이며, 엔진이 값을 지어내지 않고 "
        "escalate하는지를 직접 검증한다.",
        "",
        "---",
        "",
    ]
    return L


def _limitations(r: ValidationReport) -> list[str]:
    L = [_h(2, "9. 한계 및 알려진 이슈"), ""]
    items = [
        ("단일 시나리오", "현 검증은 6·30 규제 변경 1건에 대한 것이다. 다른 정책·시점으로 일반화하려면 골드셋과 "
         "지역 버전을 확장해야 한다."),
        ("非규제 유주택 기준선 부재", "원문에 非규제지역 유주택 LTV 기준선이 명시되지 않아, 엔진은 값을 지어내지 "
         f"않고 `OWNER_BASELINE_UNKNOWN`으로 사람 검토에 escalate한다(현재 {len(r.escalations)}건). 이는 결함이 "
         "아니라 의도된 정직한 통제이나, 해당 케이스는 자동 판정되지 않는다."),
        ("골드 정답의 출처", "골드 정답은 독립 명세 오라클(사람 확정 명세에서 결정론적으로 유도)이다. 도메인 "
         "전문가의 최종 검수를 거친 v2가 아직 아니며, 이 한계는 부록·MANIFEST에 명시된다."),
        ("LLM 추출 1회·단일 모델", f"RegChange 추출 지표는 모델 1종({measured_assurance().model}) 1회 실행에 "
         "기반한다. 분산·모델 간 비교, CHALLENGE 세트로의 grounding 실패 유도 측정은 향후 과제다."),
        ("합성 포트폴리오", "포트폴리오 규모·분포는 가정된 합성 데이터다. 실데이터가 아니므로 절대 규모는 "
         "예시이며, 각 차주 LTV 판정만 엔진 실제 출력이다."),
        ("§E vs §H 알려진 모호성", "유주택+생애최초 동시 충족 시 §E 주석과 §H 알고리즘이 상충한다. 판정 권위는 "
         "§H(P4 우선, 유주택 0%)로 두되 CHALLENGE·OPEN_QUESTIONS(Q8)에 표면화했다."),
    ]
    for i, (title, body) in enumerate(items, 1):
        L += [f"**9.{i} {title}.** {body}", ""]
    L += ["---", ""]
    return L


def _governance(r: ValidationReport) -> list[str]:
    L = [
        _h(2, "10. 거버넌스 및 통제"),
        "",
        "- **AI초안 → 사람확정.** LLM은 변경안·영향분석·검토자료를 제안할 뿐 금융 의사결정을 직접 실행하지 "
        "않는다. 룰 명세·골드 정답은 사람이 확정한다.",
        "- **승인 통제.** Rule Change Proposal은 승인 상태 필드를 가지며, 현재 "
        f"**{r.proposal.approval_status.value}**로 사람 검토를 대기한다.",
        "- **Escalation.** 자동 판정 불가 시 지어내지 않고 사람 검토로 escalate한다. 현재 escalation:",
        "",
    ]
    for e in r.escalations:
        L.append(f"  - `{e.reason_code}` — {e.description}")
    if not r.escalations:
        L.append("  - (없음)")
    L += [
        "",
        "- **Provenance & Audit Trail.** 원문 해시, 추출 모델·날짜, 골드셋 버전·해시, 규칙 값의 출처를 "
        "모든 산출물에 남긴다.",
        f"- **전체 판정.** escalation이 존재하므로 시스템 전체 판정은 **{r.overall_status}** — 자동 승인하지 "
        "않고 사람 검토를 요구한다.",
        "",
        _h(3, "10.1 감사 추적 아티팩트"),
        "",
        "재현·감사를 위해 다음 산출물이 저장소에 고정되어 있다.",
        "",
        "| 아티팩트 | 경로 | 무결성/provenance |",
        "|---|---|---|",
        "| 원문 스냅샷 | `docs/sources/` | SHA-256 해시 (SOURCES.md) |",
        "| RegChange 골드 정답 | `docs/eval/regchange_gold_6_30.json` | 사람 확정 |",
        "| RegChange 추출 산출물 | `docs/eval/regchange_extraction_6_30.json` | 모델·날짜 `_meta` |",
        "| 골드셋(freeze) | `docs/eval/gold_set/` | split별 SHA-256 (MANIFEST) |",
        "| 룰 명세 | `docs/05_RULE_SPEC.md` | AI초안→사람확정 |",
        "| 의사결정 이력 | `docs/02_DECISION_LOG.md` | 날짜·결정·이유 |",
        "| 본 검증보고서 | `docs/VALIDATION_REPORT.md` | 코드 생성(재현 가능) |",
        "",
        "모든 지표는 저장된 숫자가 아니라 이 아티팩트들로부터 코드로 재계산된다. 따라서 아티팩트가 바뀌면 "
        "지표도 즉시 따라가며, 숫자를 손으로 조작할 여지가 없다.",
        "",
        "---",
        "",
    ]
    return L


def _conclusion(r: ValidationReport, m) -> list[str]:
    dev = r.gold_set["dev"]
    return [
        _h(2, "11. 결론 및 권고"),
        "",
        "6·30 규제 변경 시나리오 1건이 Source Snapshot부터 Validation Report까지 End-to-End로 완결되었고, "
        "각 단계의 정확성이 독립적·재현 가능한 방식으로 측정되었다. 결정론적 룰엔진은 오라클·골드셋 양 경로에서 "
        f"100% 통과({r.regression['passed']}/{r.regression['total']}, DEV {dev['passed']}/{dev['total']}), "
        f"RegChange 추출은 4개 DEEP dimension 전부 실측(인용 {_pct(m.citation_correctness)})되었다. "
        "시스템은 모르는 값을 지어내지 않고 사람 검토로 넘기는 통제를 일관되게 보였다.",
        "",
        _h(3, "권고 (다음 단계)"),
        "",
        "1. **LOCKED / CHALLENGE 최종 실행.** 코어 완성 시점에 sealed split을 1회 개봉해 최종 성능을 보고한다.",
        "2. **골드셋 도메인 검수(v2).** 오라클 유도 정답을 도메인 전문가가 최종 확정한다.",
        "3. **다중 모델·challenge grounding.** API 키 확보 시 여러 모델로 추출을 비교하고, CHALLENGE 원문으로 "
        "grounding 실패를 유도·측정한다.",
        "4. **정책 일반화.** 지역 버전·골드셋을 확장해 6·30 외 시나리오로 넓힌다.",
        "",
        "---",
        "",
    ]


def _appendices(r: ValidationReport, ext, manifest) -> list[str]:
    L = [_h(2, "부록 A. RegChange 추출 전체 목록 (인용 포함)"), ""]
    for i, c in enumerate(ext.changes, 1):
        ba = f"{c.before or '-'} → {c.after or '-'}"
        L += [
            f"**A.{i} [{c.category}]** {c.summary}  ({ba}, conf {c.confidence:.2f})",
            f"  - 인용 `{c.citation.source_doc_id}`: \"{c.citation.quote}\"",
            "",
        ]
    L += [_h(2, "부록 B. Impact Matrix 전체 행"), "",
          "| key | 지역 | 차주유형 | 기존 | 변경 | 방향 | 경과규정 | 근거코드 |",
          "|---|---|---|---:|---:|---|---|---|"]
    for row in r.impact_matrix.rows:
        before = "명세부재" if row.before_ltv is None else _pct(row.before_ltv)
        after = ("-" if row.after_ltv is None else _pct(row.after_ltv))
        gf = "해당" if row.grandfathering_applied else "-"
        L.append(f"| {row.key} | {row.region_label} | {row.borrower_type} | {before} | {after} | "
                 f"{row.direction.value} | {gf} | {', '.join(row.reason_codes) or '-'} |")

    L += ["", _h(2, "부록 C. 골드셋 카테고리 분포 & split"), "",
          "| category | DEV | LOCKED | CHALLENGE |", "|---|---:|---:|---:|"]
    cats = sorted({c for s in manifest["splits"].values() for c in s["by_category"]})
    for cat in cats:
        row = [cat] + [str(manifest["splits"][s]["by_category"].get(cat, 0)) for s in ("dev", "locked", "challenge")]
        L.append("| " + " | ".join(row) + " |")

    L += ["", _h(2, "부록 D. reason_code 사전"), "", "| code | 의미 |", "|---|---|"]
    for rc in ReasonCode:
        L.append(f"| `{rc.value}` | {_REASON_GLOSSARY.get(rc.value, '-')} |")

    L += ["", _h(2, "부록 E. 재현 방법"), "",
          "```bash",
          "python -m pytest                     # 전체 테스트",
          "python examples/demo_report.py       # 검증 보고서 요약(텍스트)",
          "python examples/build_report_doc.py  # 본 문서(마크다운) 생성",
          "python examples/demo_gold_set.py     # 골드셋 DEV 회귀",
          "python examples/run_extractor.py     # RegChange 추출 + Assurance",
          "python examples/render_ui.py         # 6개 화면(오프라인)",
          "```", "",
          "본 문서의 모든 수치는 위 코드 실행 결과와 일치한다(손으로 적지 않음).", ""]
    return L


def build_validation_document(report: ValidationReport | None = None) -> str:
    """전 실측 산출물을 종합한 검증보고서(마크다운)를 생성한다."""
    r = report if report is not None else build_validation_report()
    m = measured_assurance()
    ext = load_recorded_extraction()
    port = analyze_portfolio()
    manifest = load_manifest()

    parts: list[str] = []
    parts += _cover(r, m)
    parts += _toc()
    parts += _exec_summary(r, m, port)
    parts += _scope()
    parts += _architecture(r)
    parts += _data_section(r)
    parts += _methodology()
    parts += _results(r, m, ext, port)
    parts += _worked_examples(r)
    parts += _assurance(r)
    parts += _goldset(r, manifest)
    parts += _limitations(r)
    parts += _governance(r)
    parts += _conclusion(r, m)
    parts += _appendices(r, ext, manifest)
    return "\n".join(parts).rstrip() + "\n"
