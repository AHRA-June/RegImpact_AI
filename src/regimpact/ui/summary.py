"""검증 요약 — 검증보고서(600여 줄)를 한두 화면으로 압축한 페이지.

2026-08-19 사용자 리뷰: "지금의 검증보고서는 너무 길어서 뭐라는 건지 이해하기 힘들다.
목적·목표·뭘 했는지·결과(점수, 영향도)·뭐가 작동하고 뭐가 부족한지를 짧게."

원칙은 본문 보고서와 같다 — **모든 수치는 evidence 에서 온다.** 이 파일에는 라벨과
문장 구조만 있고 숫자 리터럴은 없다. 점수는 나열이 아니라 확정 임계와의 대조로 보여주고,
부족한 것(단일 정책·커버리지 상한·골드셋 한계)을 점수와 같은 비중으로 싣는다 —
좋은 것만 요약하면 요약이 곧 과장이 된다.
"""
from __future__ import annotations

from ..report.evidence import ValidationEvidence
from .pages import _SEGMENT_TONE, _won
from ..impact.customer import Segment
from .theme import bar, card, chip, esc, explainer, glance, page, page_title, stat, table

# 스코어카드 지표명(영문 고정 id) → 화면 라벨. 값이 아니라 표기만 여기서 정한다.
_METRIC_KO = {
    "Citation Correctness": "인용 정확성",
    "Unsupported Claim Rate": "근거 없는 주장",
    "Change Completeness": "변경 완전성",
    "Exception Recall": "예외 재현율",
    "Effective-date Accuracy": "시행일 정확성",
    "Region Accuracy": "지역 정확성",
    "Policy Baseline Consistency": "정책 DB ↔ 엔진 정합",
    "Policy-version Consistency": "시점·정책 버전 일관성",
    "Rule-regression Pass Rate": "룰 회귀 통과율",
    "Boundary-case Pass Rate": "경계 케이스 통과율",
    "Conflict-case Pass Rate": "충돌 케이스 통과율",
    "JS Port Agreement": "JS 포팅 일치율",
}

_DIM_KO = {
    "① Hallucination · Grounding": "① 환각 방지 · 인용 검증",
    "② RegChange 추출 완전성": "② 규제 변경 추출 완전성",
    "③ 시점·정책 버전 일관성": "③ 시점·정책 버전 일관성",
    "④ Rule · Test 회귀": "④ 룰 · 테스트 회귀",
}

_VERDICT = {
    "PASS": ("통과", "good"),
    "FAIL": ("미달", "bad"),
    "NOT_MEASURED": ("미측정", "warn"),
}


def _fmt(v, direction) -> str:
    if v is None:
        return "—"
    return f"{v:.0%}"


def _score_rows(sc) -> list[list[str]]:
    rows = []
    last_dim = None
    for m in sc.all_metrics:
        t = m.threshold
        dim = t.dimension.value
        if dim != last_dim:
            rows.append([
                f'<div class="font-mono-label text-mono-label uppercase '
                f'text-on-surface-variant">{esc(_DIM_KO.get(dim, dim))}</div>', "", "", ""])
            last_dim = dim
        label, tone = _VERDICT[m.verdict.name if hasattr(m.verdict, "name") else str(m.verdict)]
        thr = "미확정" if t.threshold is None else f"{t.direction.value} {t.threshold:.0%}"
        rows.append([
            esc(_METRIC_KO.get(t.metric, t.metric))
            + (' <span class="text-error">★</span>' if t.high_risk else ""),
            chip(_fmt(m.value, t.direction), mono=True,
                 tone="good" if label == "통과" else "neutral"),
            f'<span class="text-body-sm text-on-surface-variant">{esc(thr)}</span>',
            chip(label, tone=tone),
        ])
    return rows


def render(ev: ValidationEvidence, *, qa_confirmed: int = 0, qa_total: int = 0) -> str:
    sc = ev.scorecard
    s = sc.summary()
    g, r, im, ext = ev.grounding, ev.regression, ev.impact, ev.extraction
    total = len(im.impacts)
    unmeasured = [m.threshold.metric for m in sc.all_metrics if m.value is None]

    verdict_label = {"PASS": "통과", "FAIL": "미달"}.get(s["verdict"], s["verdict"])

    top = glance(
        f"종합 판정 {verdict_label} — 확정 임계 대조 {s['passed']}/{s['total']} 통과, "
        f"미측정 {s['not_measured']}, 고위험 미달 {s['high_risk_failed']}건. "
        f"수치는 전부 파이프라인 실행에서 왔다.",
        [chip(f"임계 통과 {s['passed']}/{s['total']}",
              tone="good" if s["verdict"] == "PASS" else "bad"),
         chip(f"미측정 {s['not_measured']} (정직하게 표기)", tone="warn"),
         chip(f"인용 원문 확인 {g.citation_correctness:.0%}", tone="good"),
         chip(f"룰 회귀 {r.pass_rate:.0%} ({r.total}케이스)", tone="good")],
    )

    purpose = card(
        "목적 · 목표 · 방법",
        '<ul class="flex flex-col gap-2" style="line-height:24px">'
        "<li><b>목적</b> — 규제 공문이 나오면 <b>무엇이 바뀌고, 여신 룰과 고객에게 어떤 "
        "영향인지</b>를 근거(원문 인용)와 함께 산출한다.</li>"
        "<li><b>목표</b> — 예외·시행일·경과규정 누락 <b>0건</b>(고위험 지표 임계 100%). "
        "원문에 없는 값은 지어내지 않고 사유와 함께 사람에게 올린다.</li>"
        "<li><b>방법</b> — LLM은 <b>인용이 붙은 사실 추출만</b> 하고, 판정은 사람이 확정한 "
        "명세를 구현한 결정적 룰엔진이 한다. 단계마다 산출물을 <b>독립 기준</b>(원문 대조·"
        "사람 확정 골드·독립 오라클)과 대조한다.</li></ul>",
        note="전문은 검증보고서(§1~§13) — 이 페이지는 그 1페이지 요약이다",
    )

    n_docs = len(ev.sources)
    flow_steps = [
        f"공문 {n_docs}건 스냅샷(해시)",
        f"변경 {len(ext.changes)}건 추출 + 인용 {g.grounded}/{g.total} 원문 대조",
        f"룰 변경 {len([d for d in ev.rule_diff if d['before'] != d['after']])}건 도출",
        f"고객 {total:,}건 영향 계산",
        f"독립 검증 {s['total']}지표 대조",
    ]
    flow = (
        '<div class="flex flex-wrap items-center gap-2">'
        + '<span class="text-on-surface-variant">→</span>'.join(
            chip(t, tone="primary") for t in flow_steps)
        + "</div>"
    )
    did = card("무엇을 했나 — 파이프라인 한 줄", flow,
               note=f"전 과정이 LLM 재호출 없이 재현된다 (provider {ev.provider})")

    scores = card(
        "결과 ① 검증 점수 — 확정 임계와의 대조",
        table(["지표 (★=고위험)", "실측", "임계", "판정"], _score_rows(sc),
              align_center=(1, 2, 3)),
        note="점수 나열이 아니라 임계 대조다 — 미측정은 통과로 치지 않는다",
    )

    seg_bars = "".join(
        bar(seg.value, im.segment_counts[seg.value], total, tone=_SEGMENT_TONE[seg])
        for seg in Segment if im.segment_counts[seg.value]
    )
    impact_expl = (
        '<div class="text-body-md" style="max-width:72ch;line-height:25px">'
        f"규제지역 지정으로 합성 고객 {total:,}건 중 <b>{len(im.reduced):,}건"
        f"({im.affected_rate:.1%})의 대출 한도가 줄어든다</b> — 총 "
        f"<b>{_won(abs(im.total_limit_reduction))} 감소</b>, "
        f"건당 평균 {_won(abs(im.avg_limit_reduction))}. "
        f"경과규정(시행 전 계약·접수)이 {im.grandfathered_count:,}건을 보호한다. "
        f"심사 판정은 {im.decision_coverage:.1%}까지 자동으로 가능하지만, 영향 측정은 "
        f"{im.impact_coverage:.1%}에서 멈춘다 — <b>원문에 없는 기준값을 추정하지 않기 "
        "때문</b>이며, 그 구간은 사유와 함께 사람 검토로 넘어간다.</div>"
    )
    impact_card = card(
        "결과 ② 고객 영향도",
        '<div class="grid grid-cols-4 gap-4 mb-4">'
        + stat("한도 감소", f"{len(im.reduced):,}건", tone="bad",
               sub=f"전체 {total:,}건의 {im.affected_rate:.1%}")
        + stat("총 감소액", _won(abs(im.total_limit_reduction)), tone="bad",
               sub=f"건당 평균 {_won(abs(im.avg_limit_reduction))}")
        + stat("경과규정 보호", f"{im.grandfathered_count:,}건", tone="good",
               sub="종전규정 유지")
        + stat("자동 커버리지", f"{im.decision_coverage:.1%}",
               sub=f"영향 측정은 {im.impact_coverage:.1%}")
        + "</div>"
        + f'<div class="flex flex-col gap-3 mb-4">{seg_bars}</div>'
        + impact_expl,
        note="합성 포트폴리오 계산 결과다 — 시장 추정치가 아니다 (실 고객데이터 미사용)",
    )

    works = [
        f"인용 → 원문 대조: {g.grounded}/{g.total} 전건이 원문에 그대로 존재",
        f"룰엔진 ↔ 독립 명세 오라클: {r.total}케이스 전건 일치 (경계·충돌 포함)",
        "경과규정 판정: 컷오프 당일·시행 전일 경계 케이스 통과",
        "정책 버전 DB ↔ 엔진 기준선: 양방향 정합 (한쪽만 고치면 검사가 잡는다)",
        "화면 JS 포팅본 ↔ Python 엔진: 전 케이스 대조 후에만 배포",
        "해시체인 감사로그: 산출 과정이 위·변조 탐지 가능한 기록으로 남는다",
    ]
    qa_line = (
        f"QA 골드 검수 진행 중 ({qa_confirmed}/{qa_total} 확정) — 확정 전까지 QA 지표는 상대 비교용"
        if qa_total else "QA 골드는 검수 진행 중 — 확정 전까지 QA 지표는 상대 비교용"
    )
    lacks = [
        f"{', '.join(_METRIC_KO.get(m, m) for m in unmeasured) or '일부 지표'}은 "
        "미측정으로 남겼다 — 미측정은 통과가 아니다 "
        "(시점·정책 버전 일관성은 시점 질의 골드 12문항이 🤖 초안이라 검수 후 측정 가동)",
        f"영향 측정 커버리지 {im.impact_coverage:.1%} 상한 — 원문에 없는 기준값(Q10)을 "
        "추정하지 않는 대가다. 지어내면 즉시 100%가 된다",
        "골드 정답지 작성자 = 개발자 — 독립 벤치마크가 아니다 (추출 골드는 사람 확정 완료, "
        + qa_line + ")",
        "봉인 평가셋(LOCKED/CHALLENGE) 미개봉 — 최종 성능은 아직 평가 전이다",
        "Policy-version Consistency 임계 미정(TBD) — 시점 질의 측정 가동 전 "
        "(나머지 임계값은 2026-08-19 사용자 확정)",
    ]
    two_col = (
        '<div class="grid grid-cols-2 gap-6">'
        '<div><div class="font-h3 text-h3 text-secondary mb-3">작동하는 것</div>'
        '<ul class="flex flex-col gap-2">'
        + "".join(f'<li class="flex gap-2"><span class="text-secondary">✓</span>'
                  f'<span style="line-height:22px">{esc(w)}</span></li>' for w in works)
        + "</ul></div>"
        '<div><div class="font-h3 text-h3 text-on-tertiary-fixed-variant mb-3">부족한 것 (정직하게)</div>'
        '<ul class="flex flex-col gap-2">'
        + "".join(f'<li class="flex gap-2"><span class="text-on-tertiary-fixed-variant">△</span>'
                  f'<span style="line-height:22px">{esc(x)}</span></li>' for x in lacks)
        + "</ul></div></div>"
    )
    honest = card("작동하는 것 / 부족한 것", two_col,
                  note="부족한 것은 숨긴 게 아니라 설계의 대가다 — 상세는 검증보고서 §11(한계)·§12(발견사항)")

    links = (
        '<div class="flex flex-wrap gap-3">'
        '<a class="flex items-center gap-2 px-4 py-2 rounded-lg bg-primary text-on-primary '
        'font-medium" href="validation_report.html">검증보고서 전문 보기</a>'
        '<a class="flex items-center gap-2 px-4 py-2 rounded-lg border border-outline-variant '
        'text-on-surface font-medium" href="assurance.html">지표 상세 (검증 화면)</a>'
        '<a class="flex items-center gap-2 px-4 py-2 rounded-lg border border-outline-variant '
        'text-on-surface font-medium" href="portfolio.html">영향도 상세 (포트폴리오 화면)</a>'
        "</div>"
    )

    body = (
        page_title("검증 요약",
                   "검증보고서 전체의 한 페이지 요약 — 목적·수행 내용·결과·한계.")
        + explainer(
            "긴 검증보고서를 한 페이지로 줄인 요약입니다 — 이 시스템이 뭘 하고, "
            "얼마나 잘하고, 뭐가 부족한지.",
            "본문 보고서와 같은 실제 실행 결과. 사람이 옮겨 적은 숫자가 없어서 "
            "요약과 본문의 수치가 어긋날 수 없습니다.",
            "위에서부터: 종합 판정 → 목적 → 한 일 → 점수 → 고객 영향 → 잘 되는 것/부족한 것. "
            "더 깊이 보려면 맨 아래 링크로 본문 보고서에 갑니다.",
        )
        + top + purpose + did + scores + impact_card + honest
        + card("더 보기", links)
    )
    return page(title="검증 요약", active="validation_summary.html",
                scenario="검증보고서 1페이지 요약", status=f"종합 판정 {verdict_label}",
                body=body)
