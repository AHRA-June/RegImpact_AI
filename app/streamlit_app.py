"""RegImpact AI — 온라인 검증 콘솔 (Streamlit).

웹 샌드박스(web/sandbox.html)가 룰엔진을 JS로 옮긴 것이라면, 이 앱은 **저장소의 Python 엔진을
그대로** 돌린다. 포팅본이 아니므로 드리프트가 원천적으로 없고, LLM(Extractor)까지 온라인에서
실행할 수 있다.

로컬 실행:
    pip install -r requirements.txt
    streamlit run app/streamlit_app.py

배포: docs/ui/DEPLOY.md 참고 (Streamlit Community Cloud).
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date
from pathlib import Path

import streamlit as st

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from regimpact.models import (  # noqa: E402
    EvaluationStatus,
    LoanPurpose,
    MortgageApplication,
)
from regimpact.regions import (  # noqa: E402
    REGISTRY, SIDO_ORDER, get_region, regulated_codes, resolve_region_status,
)
from regimpact.rule_engine import evaluate  # noqa: E402
from regimpact.tc_generator import Category, generate_all, run_regression  # noqa: E402

st.set_page_config(page_title="RegImpact AI — 검증 콘솔", page_icon="⚖️", layout="wide")

# --- 지역 선택지: 레지스트리(전국 241곳)를 시도 순서대로 ---
_SIDO_RANK = {sido: i for i, sido in enumerate(SIDO_ORDER)}
REGION_CODES = sorted(REGISTRY, key=lambda c: (_SIDO_RANK.get(REGISTRY[c].sido, 99),
                                               REGISTRY[c].name))


def region_label(code: str, as_of: date) -> str:
    """선택지 라벨. 규제 여부는 평가일에 따라 달라지므로 평가일을 받아 표시한다."""
    r = REGISTRY[code]
    status, rtype = resolve_region_status(code, as_of)
    tag = {"SPECULATIVE_OVERHEATED": "투기과열", "ADJUSTMENT": "조정대상"}.get(
        rtype.value, "비규제" if status.value == "NON_REGULATED" else status.value)
    return f"{r.sido} {r.name} · {tag}"
REASON_KO = {
    "LTV_REGULATED_40": "규제지역 표준 40%",
    "EXCEPTION_FIRST_HOME": "생애최초 예외 70%",
    "EXCEPTION_REAL_DEMAND": "서민·실수요 예외 60%",
    "LTV_OWNER_0": "유주택(비처분) 0%",
    "LTV_MULTI_HOME_0": "다주택 0%",
    "LTV_BASELINE_70": "非규제 기준선 70%",
    "LTV_NONREG_OWNER_60": "非규제(수도권 外) 유주택 60%",
    "GRANDFATHERED_ACCEPTED_OR_CONTRACT": "경과규정 — 접수 또는 계약+계약금",
    "GRANDFATHERED_LAND_PERMIT": "경과규정 — 토지거래허가 신청",
    "OWNER_BASELINE_UNKNOWN": "유주택 기준값 명세 부재 → 사람 검토",
    "OUT_OF_SCOPE_PRODUCT": "주택구입목적 아님",
    "UNKNOWN_REGION": "레지스트리 미등록 지역 → 사람 검토",
    "DISCOVERY_POLICY_LOAN": "정책대출 → 수동 검토",
}
STATUS_KO = {
    "DECIDED": "판정 확정",
    "NEEDS_HUMAN_REVIEW": "사람 검토 필요",
    "DISCOVERY": "Discovery (수동)",
    "OUT_OF_SCOPE": "코어 범위 밖",
}

# 우선순위 사다리 (05_RULE_SPEC §H). 표시 전용 라벨.
STEPS = [
    ("P0", "스코프 — 주택구입목적인가"),
    ("P0b", "정책대출 → Discovery"),
    ("P1", "경과규정 G1 / G2 / G3 → 종전규정 시점으로 재판정"),
    ("P2", "지역 규제상태 해석 (미등록 코드 검사)"),
    ("P3", "다주택 — 규제지역 또는 수도권이면 0%"),
    ("P4", "유주택 (비처분 1주택)"),
    ("P4b", "非규제 무주택 기준선 70%"),
    ("P5", "생애최초"),
    ("P6", "서민·실수요자"),
    ("P7", "규제지역 무주택 일반 40%"),
]


def halting_step(decision, house_count: int = 0) -> str:
    """판정이 어느 우선순위 단계에서 short-circuit 됐는지를 **엔진 출력에서 역으로 읽는다**.

    주의: 규칙을 다시 구현하는 것이 아니라 출력(reason_code·rule_id·status)을 단계 라벨로
    매핑할 뿐이다. 엔진이 유일한 판정 주체라는 원칙을 깨지 않기 위함.
    """
    codes = set(decision.reason_codes)
    if "OUT_OF_SCOPE_PRODUCT" in codes:
        return "P0"
    if "UNKNOWN_REGION" in codes:
        return "P2"
    if "OWNER_BASELINE_UNKNOWN" in codes:
        return "P4"
    if "DISCOVERY_POLICY_LOAN" in codes:
        return "P0b"
    return {
        "MULTI_0": "P3",
        "REG_OWNER_0": "P4",
        "NONREG_OWNER_60": "P3" if house_count >= 2 else "P4",
        "NONREG_STD_70": "P4b",
        "REG_FIRSTHOME": "P5",
        "REG_REALDEMAND": "P6",
        "REG_STD": "P7",
    }.get(decision.applicable_rule_id, "P2")


def build_app(f) -> MortgageApplication:
    return MortgageApplication(
        region_code=f["region"],
        evaluation_date=f["evaldate"],
        house_count=f["house_count"],
        disposal_condition_flag=f["disposal"],
        first_home_buyer=f["firsthome"],
        real_demand_flag=f["realdemand"],
        policy_mortgage_flag=f["policy"],
        loan_purpose=LoanPurpose.HOME_PURCHASE if f["purpose"] == "주택구입" else LoanPurpose.OTHER,
        application_accepted_at=f["accepted"],
        contract_signed_at=f["contract"],
        downpayment_paid_at=f["downpay"],
        land_permit_target=f["landtarget"],
        land_permit_applied_at=f["landdate"],
    )


def opt_date(label: str, key: str, default_on: bool = False):
    """nullable 날짜 입력 — 체크를 꺼두면 None(이벤트 없음)."""
    c1, c2 = st.columns([1, 2])
    on = c1.checkbox("해당", key=key + "_on", value=default_on)
    d = c2.date_input(label, key=key, value=date(2026, 6, 30), disabled=not on,
                      label_visibility="collapsed")
    st.caption(label)
    return d if on else None


# ============================== 판정 탭 ==============================
def tab_verdict() -> None:
    left, right = st.columns([2, 3], gap="large")

    with left:
        st.subheader("신청 조건")
        evaldate = st.date_input("평가일 (지역 규제상태 해석 기준)", value=date(2026, 7, 2))
        region = st.selectbox(
            f"지역 — 전국 {len(REGION_CODES)}곳 (규제 {len(regulated_codes(evaldate))}곳)",
            REGION_CODES,
            index=REGION_CODES.index("GYEONGGI_GURI"),
            format_func=lambda c: region_label(c, evaldate),
            help="국토부 보도자료 참고2 「투기과열지구 및 조정대상지역 현황」 표 기준. "
                 "규제지역은 열거주의 — 지정된 곳만 규제지역이다.",
        )
        _r = get_region(region)
        _first_reg = next((v for v in _r.versions if v.status.value == "REGULATED"), None)
        st.caption(
            f"`{region}` · {'수도권' if _r.capital_area else '비수도권'} · "
            + (f"{_first_reg.effective_from} 지정" if _first_reg else "지정된 바 없음")
        )
        purpose = st.radio("대출 목적", ["주택구입", "그 외"], horizontal=True)
        house_count = st.select_slider("보유 주택 수", options=[0, 1, 2, 3], value=0)
        disposal = st.checkbox("처분조건부 1주택 (P4)", disabled=house_count < 1)
        firsthome = st.checkbox("생애최초 구입 (P5)")
        realdemand = st.checkbox("서민·실수요자 (P6)")
        policy = st.checkbox("정책대출 — 보금자리론 등 (P0b)")

        st.divider()
        st.markdown("**경과규정 이벤트** · §F 컷오프 `2026-06-30`")
        accepted = opt_date("G1 전산 접수 완료일", "accepted")
        contract = opt_date("G2 계약 체결일", "contract")
        downpay = opt_date("G2 계약금 납부일", "downpay")
        landtarget = st.checkbox("토지거래허가 대상 물건 (G3)")
        landdate = opt_date("G3 허가 신청 접수일", "landdate")

        st.divider()
        price = st.number_input("주택 가격 (억원) — 참고값, 코어 판정 아님",
                                min_value=1.0, max_value=50.0, value=9.0, step=0.5)

    app = build_app(dict(
        region=region, evaldate=evaldate, house_count=house_count, disposal=disposal,
        firsthome=firsthome, realdemand=realdemand, policy=policy, purpose=purpose,
        accepted=accepted, contract=contract, downpay=downpay,
        landtarget=landtarget, landdate=landdate,
    ))
    decision = evaluate(app)

    with right:
        st.subheader("판정")
        m1, m2, m3 = st.columns(3)
        ltv_txt = "—" if decision.max_ltv is None else f"{decision.max_ltv:.0%}"
        m1.metric("적용 LTV", ltv_txt)
        m2.metric("판정 상태", STATUS_KO[decision.status.value])
        m3.metric("규칙 ID", decision.applicable_rule_id or "—")

        if decision.status is EvaluationStatus.DECIDED:
            if decision.max_ltv == 0:
                st.error(f"주택가격 {price}억 기준 대출 가능액 **0원** — 규제지역 유주택·다주택은 "
                         "주택구입목적 대출이 금지된다.")
            else:
                st.success(f"주택가격 {price}억 기준 최대 대출 가능액 "
                           f"**{price * decision.max_ltv:,.2f}억** "
                           "(LTV만 적용한 참고값 — DTI·차주별 한도 미반영)")
        elif decision.status is EvaluationStatus.NEEDS_HUMAN_REVIEW:
            extra = ("수도권 비규제 유주택은 원문이 '非규제(수도권 外) 유주택 60%'만 명시해 근거가 없다. "
                     if "OWNER_BASELINE_UNKNOWN" in decision.reason_codes else "")
            st.warning("자동 판정을 **거부**했다. " + extra
                       + "확정 명세에 해당 기준값이 없으므로 숫자를 지어내지 않고 사람에게 넘긴다.")
        elif decision.status is EvaluationStatus.DISCOVERY:
            st.info("정책대출은 코어 자동판정에서 **분리**되어 있다(Discovery). 다른 조건은 평가하지 않는다.")
        else:
            st.info("주택구입목적이 아니면 이 엔진의 코어 판정 대상이 아니다.")

        st.markdown("**판정 근거 (reason_codes)**")
        for c in decision.reason_codes:
            st.markdown(f"- `{c}` — {REASON_KO.get(c, '')}")

        status, reg_type = resolve_region_status(region, evaldate)
        st.caption(
            f"지역상태 `{status.value}` / 지정유형 `{reg_type.value}` · "
            + ("경과규정 적용 — 종전규정(2026-06-30 시점)으로 재판정 · "
               if decision.grandfathering_applied else "경과규정 미적용 · ")
            + f"출처 {', '.join(decision.source_policy_ids) or '—'}"
        )

        # 시행 전 대비 (Impact Matrix 1행의 원형)
        before = evaluate(build_app(dict(
            region=region, evaldate=date(2026, 6, 15), house_count=house_count,
            disposal=disposal, firsthome=firsthome, realdemand=realdemand, policy=policy,
            purpose=purpose, accepted=accepted, contract=contract, downpay=downpay,
            landtarget=landtarget, landdate=landdate,
        )))
        b_txt = "—" if before.max_ltv is None else f"{before.max_ltv:.0%}"
        delta = None
        if before.max_ltv is not None and decision.max_ltv is not None:
            delta = f"{(decision.max_ltv - before.max_ltv) * 100:+.0f}%p"
        st.divider()
        st.markdown("**동일 조건 · 평가일만 시행 전(2026-06-15)로 되돌린 경우**")
        d1, d2 = st.columns(2)
        d1.metric("시행 전", b_txt)
        d2.metric("현재 평가일", ltv_txt, delta=delta, delta_color="inverse")

        st.divider()
        st.markdown("**우선순위 트레이스** — 어디서 short-circuit 됐는가")
        halt = halting_step(decision, house_count)
        reached = True
        for sid, label in STEPS:
            if not reached:
                st.markdown(f"<span style='opacity:.4'>◦ `{sid}` ~~{label}~~ · 미도달</span>",
                            unsafe_allow_html=True)
            elif sid == halt:
                st.markdown(f"**▸ `{sid}` {label} — 여기서 판정**")
                reached = False
            else:
                st.markdown(f"<span style='opacity:.65'>✓ `{sid}` {label}</span>",
                            unsafe_allow_html=True)


# ============================== 회귀 탭 ==============================
def tab_regression() -> None:
    report = run_regression()
    by_cat = report.pass_rate_by_category()

    st.subheader("Rule-Regression — 엔진 ⟷ 독립 명세 오라클")
    st.caption("엔진 출력을 기대값으로 쓰지 않는다. 명세(§H)에서 독립 유도한 오라클(challenger)과 "
               "대조해 회귀가 tautology가 되지 않게 한 차등 검증이다.")

    cols = st.columns(4)
    cols[0].metric("Rule-regression Pass Rate", f"{report.pass_rate:.0%}",
                   f"{report.passed}/{report.total}")
    for i, cat in enumerate(("BOUNDARY", "CONFLICT", "GRANDFATHERING")):
        p, n, rate = by_cat.get(cat, (0, 0, 1.0))
        cols[i + 1].metric(f"{cat} Pass Rate", f"{rate:.0%}", f"{p}/{n}")

    st.divider()
    rows = []
    for r in report.results:
        rows.append({
            "케이스": r.case.case_id,
            "분류": r.case.category.value,
            "설명": r.case.description,
            "기대(오라클)": "—" if r.case.expected.max_ltv is None
                            else f"{r.case.expected.max_ltv:.0%}",
            "실제(엔진)": "—" if r.actual.max_ltv is None else f"{r.actual.max_ltv:.0%}",
            "상태": r.actual.status.value,
            "결과": "✓ 통과" if r.passed else "✕ 불일치",
            "미결": "⚑" if r.case.spec_note else "",
        })
    cats = ["전체"] + [c.value for c in Category]
    pick = st.radio("분류 필터", cats, horizontal=True)
    view = rows if pick == "전체" else [x for x in rows if x["분류"] == pick]
    st.dataframe(view, width="stretch", hide_index=True)

    notes = [r for r in report.results if r.case.spec_note]
    if notes:
        st.markdown("**⚑ 명세 미결 항목이 걸린 케이스**")
        for r in notes:
            with st.expander(f"{r.case.case_id} — {r.case.description}"):
                st.write(r.case.spec_note)

    if report.failures:
        st.error(f"불일치 {len(report.failures)}건")
        for r in report.failures:
            with st.expander(f"✕ {r.case.case_id} [{r.case.category.value}]"):
                for m in r.mismatches:
                    st.code(m)


# ============================== Extractor 탭 ==============================
def tab_extractor() -> None:
    st.subheader("RegChange Extractor — 공문 → 구조화 추출 + Citation Assurance")
    st.caption("LLM이 공문에서 Before/After 변경을 뽑고, 그 인용문이 원문에 verbatim으로 "
               "존재하는지 deterministic하게 대조한다(환각 실측). 골드 정답지와의 완전성·재현율도 함께 산출.")

    def _secret(name: str) -> str:
        """secrets.toml이 아예 없는 환경에서도 죽지 않게 감싼다."""
        try:
            return st.secrets.get(name, "")
        except Exception:
            return ""

    key = os.environ.get("ANTHROPIC_API_KEY") or _secret("ANTHROPIC_API_KEY")
    if key:
        os.environ["ANTHROPIC_API_KEY"] = key
    else:
        st.warning("`ANTHROPIC_API_KEY`가 없다. Streamlit Cloud 앱 설정의 Secrets에 넣으면 "
                   "이 탭에서 실제 추출을 돌릴 수 있다. (없어도 나머지 탭은 전부 동작)")
        return

    from regimpact.extractor import (  # 지연 import — 키 없을 때 SDK 불필요
        check_citation_grounding, extract_regchange, load_sources, score_against_gold,
    )
    from regimpact.extractor import anthropic_completion

    sources = load_sources()
    st.write(f"원문 {len(sources)}건 로드: `{'`, `'.join(sources)}`")
    model = st.selectbox("모델", ["claude-opus-5", "claude-sonnet-5"], index=0)

    if not st.button("추출 실행 (실제 LLM 호출 — 비용 발생)", type="primary"):
        return

    with st.spinner("공문에서 규제 변경을 추출하는 중…"):
        extraction = extract_regchange(sources, complete=anthropic_completion(model=model))
    gold = json.loads((REPO / "docs" / "eval" / "regchange_gold_6_30.json").read_text(encoding="utf-8"))
    grounding = check_citation_grounding(extraction, sources)
    scored = score_against_gold(extraction, gold)

    c = st.columns(4)
    c[0].metric("Citation Correctness", f"{grounding.citation_correctness:.0%}",
                f"{grounding.grounded}/{grounding.total}")
    c[1].metric("Unsupported Claim Rate", f"{grounding.unsupported_claim_rate:.0%}",
                delta_color="inverse")
    c[2].metric("Change Completeness", f"{scored.change_completeness:.0%}")
    c[3].metric("Exception Recall", f"{scored.exception_recall:.0%}")

    st.caption(f"시행일 정확 `{scored.effective_date_correct}` · 대상지역 정확 `{scored.regions_correct}`")
    if scored.missed_changes:
        st.warning("놓친 변경: " + ", ".join(scored.missed_changes))
    if scored.missed_exceptions:
        st.warning("놓친 예외: " + ", ".join(scored.missed_exceptions))
    if grounding.ungrounded:
        st.error("원문에서 인용문을 찾지 못한 항목 (환각 의심)")
        for item in grounding.ungrounded:
            st.code(f"{item.category} — {item.summary}\n  인용: {item.citation.quote}")

    st.divider()
    st.markdown("**추출 결과 전문**")
    st.json({
        "policy_id": extraction.policy_id,
        "effective_from": extraction.effective_from,
        "target_regions": extraction.target_regions,
        "changes": [
            {"category": c_.category, "summary": c_.summary, "before": c_.before,
             "after": c_.after, "confidence": c_.confidence,
             "citation": {"source_doc_id": c_.citation.source_doc_id, "quote": c_.citation.quote}}
            for c_ in extraction.changes
        ],
    })


# ============================== main ==============================
st.title("⚖️ RegImpact AI — 검증 콘솔")
st.caption("2026-06-30 주택시장 안정대책 · 주택구입목적 주담대 LTV. "
           "규칙 값·우선순위는 사람이 확정한 명세(`docs/05_RULE_SPEC.md` v1)에서 오며 LLM이 생성하지 않는다. "
           "이 엔진은 LLM 출력을 채점하는 기준점(ground truth)이다.")

t1, t2, t3 = st.tabs(["LTV 판정", f"회귀 콘솔 ({len(generate_all())})", "Extractor (LLM)"])
with t1:
    tab_verdict()
with t2:
    tab_regression()
with t3:
    tab_extractor()

st.divider()
st.caption(
    f"지역 — 전국 {len(REGISTRY)}곳의 규제상태·지정일은 국토부 보도자료 참고2 「투기과열지구 및 "
    "조정대상지역 현황」 표에서 왔다. 서울 25개 자치구는 6·30과 무관하게 이미 전부 규제지역이며"
    "(강남4구 '16.11.3 조정 → '17.8.3 투기과열), 6·30이 더한 곳은 화성동탄·용인기흥·구리 3곳이다. "
    "레지스트리에 없는 코드는 非규제로 넘겨짚지 않고 사람 검토로 넘어간다. "
    "2026-08-18 확정 — ①비규제 유주택 60%(MOLIT 참고1). 원문이 '수도권 外'를 명시하므로 수도권 비규제 "
    "유주택은 근거 부재로 사람 검토에 남는다. ②다주택 판정이 지역 분기보다 앞(FSC p2: 수도권 內 규제 무관 0%) — "
    "인천 다주택은 비규제여도 0%, 울산·제주 다주택은 유주택 기준 60%. ③경과규정의 종전규정은 70% 고정이 아니라 "
    "컷오프 시점 규정으로 재판정 — 이미 규제지역이던 강남은 경과규정이 붙어도 40%. "
    "한계 — 코어 판정은 LTV뿐이다. `CFL-04`(유주택+생애최초)는 §E와 §H가 상충하는 미결 항목으로 "
    "현재는 §H를 권위 기준으로 채택했다(Q8)."
)
