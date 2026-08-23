"""현업용 상품설명서 렌더러 — `ValidationEvidence` 만 읽어 Markdown 을 조립한다.

같은 엔진의 **고객 면**(내 한도 시그널)은 `docs/business/SERVICE_DESCRIPTION_TOMORROW.md`
가 설명한다. 이 문서는 **현업 면**만 다룬다 — 규제 공문이 뜬 날 심사·리스크·컴플라이언스·
전산이 실제로 해야 하는 일과, 이 시스템이 그중 무엇을 산출물로 내고 무엇을 사람에게
넘기는지.

**이 파일에는 도메인 수치 리터럴이 없다.** 모든 숫자는 evidence 에서 온다
(`tests/test_ops_description.py` 가 강제한다). 검증보고서와 같은 원칙이고, 같은 이유다 —
제출 문서의 수치가 실제와 갈라지는 것이 이 저장소에서 가장 자주 일어난 사고였다.
"""
from __future__ import annotations

from collections import Counter

from ..governance.risk import RISKS as _RISKS
from ..grandfathering import CUTOFF
from ..regions import REG_EFFECTIVE
from ..report.evidence import ValidationEvidence

PUBLIC_SITE = "https://ahra-june.github.io/RegImpact_AI/"


def _pct(x: float, digits: int = 0) -> str:
    return f"{x:.{digits}%}"


def _eok(n: int, digits: int = 0) -> str:
    """원 → 억원. 감소는 음수로 들어오므로 부호를 손으로 붙이지 않는다."""
    return f"{n / 1_0000_0000:,.{digits}f}억원".replace("-", "−")


def _yn(b: bool) -> str:
    return "✅" if b else "❌"


def render(ev: ValidationEvidence) -> str:
    parts = [
        _header(ev), _one_line(ev), _scope(ev), _dday(ev),
        _outputs(ev), _matrix(ev), _portfolio(ev), _rulechange(ev),
        _trust(ev), _not_automated(ev), _adoption(ev),
        _status(ev), _same_engine(ev), _verify(ev), _team(),
    ]
    return "\n\n".join(p.strip() for p in parts) + "\n"


# --------------------------------------------------------------------- 머리말
def _header(ev: ValidationEvidence) -> str:
    p = ev.this_policy
    return f"""# RegImpact AI — 현업용 상품설명서

**규제 대응 워크벤치** — 공문이 뜬 날, 여신 현업이 해야 할 일을 근거와 함께 산출물로 낸다.

| 항목 | 내용 |
|---|---|
| 대상 사용자 | 여신심사 · 리스크 · 컴플라이언스 · 여신 룰 운영(전산) · 모델검증 |
| 대상 업무 | 규제 공문 해석 → 룰 개정 → 테스트 → 포트폴리오 영향 산정 → 대내외 보고 |
| 실행 시나리오 | {p.policy_id} — {p.title} (시행 {p.effective_from}) |
| 생성 시각 | {ev.generated_at or "(미기입)"} |
| 생성 방법 | `python examples/build_ops_description.py` — 파이프라인 실행 결과에서 자동 조립 |
| LLM provider | `{ev.provider}` (재생 원본 `{ev.run_path}`) |
| 감사로그 head | `{ev.audit.head_hash}` |

> 이 문서의 **모든 수치는 파이프라인을 실제로 실행해 얻은 값**이다. 손으로 적은 숫자는 없다.
> 시스템이 바뀌면 이 문서도 바뀐다 — 재현 방법은 마지막 절."""


def _one_line(ev: ValidationEvidence) -> str:
    ex = ev.extraction
    im = ev.impact
    mx = ev.matrix
    return f"""## 1. 한 줄로

> **규제 공문 한 건을 넣으면, 그날 현업이 답해야 하는 네 가지 질문에 —
> 무엇이 바뀌었나 · 어느 룰을 어떻게 고치나 · 우리 보유분은 얼마나 움직이나 ·
> 무엇을 사람이 결정해야 하나 — 근거 인용이 붙은 산출물로 답한다.**

이번 실행({ex.policy_id})에서 실제로 나온 것은 이렇다.

| 질문 | 이번 실행의 답 |
|---|---|
| 무엇이 바뀌었나 | 공문에서 변경 **{len(ex.changes)}건** 추출 · 인용이 원문에 실재 **{_pct(ev.grounding.citation_correctness)}** ({ev.grounding.grounded}/{ev.grounding.total}) |
| 누가 무엇을 하나 | 업무영역별 조치 **{len(mx.rows)}행** · 자동처리 **{_pct(mx.automation_rate)}** · 시행 전 필수 **{len(mx.d_minus_required)}건** |
| 우리 보유분은 | 신청건 **{im.portfolio_size:,}건** 재평가 → 한도 감소 **{len(im.reduced)}건**({_pct(im.affected_rate, 1)}) · 총 **{_eok(im.total_limit_reduction)}** |
| 무엇이 사람 몫인가 | 사람 검토 **{im.human_review_count}건** · 사유 없이 넘기지 않는다 (각 건에 코드가 붙는다) |

마지막 줄이 이 제품의 성격이다. **"전부 자동으로 처리했습니다"라고 말하지 않는다** —
원문에 값이 없는 자리를 추정으로 메우면 여신 현업에서 그것은 편의가 아니라 사고다."""


def _scope(ev: ValidationEvidence) -> str:
    return """## 2. 이 문서의 범위 — 같은 엔진의 현업 면

이 시스템은 하나의 검증된 엔진 위에 두 개의 면을 갖는다.

| 면 | 쓰는 사람 | 산출물 | 설명 문서 |
|---|---|---|---|
| **고객 면** | 앱을 여는 차주 | 개인화 한도 판정·경과규정·근거 인용 | `SERVICE_DESCRIPTION_TOMORROW.md` (내 한도 시그널) |
| **현업 면** ← 이 문서 | 심사·리스크·컴플라이언스·전산 | 변경 추출 · 임팩트 매트릭스 · 룰 변경안 · 포트폴리오 영향 · 검증 문서 | 이 문서 |

두 면이 **같은 판정 엔진**을 쓴다. 그래서 규제 발표일에 고객 화면이 말하는 답과 창구·심사가
보는 근거가 갈라지지 않는다 — 이것은 운영 편의가 아니라 민원·분쟁 대응의 전제다."""


def _dday(ev: ValidationEvidence) -> str:
    mx = ev.matrix
    owners = Counter(r.owner.value for r in mx.rows)
    phases = Counter(r.phase.value for r in mx.rows)
    owner_line = " · ".join(f"{k} {v}행" for k, v in owners.most_common())
    phase_line = " · ".join(f"{k} {v}행" for k, v in phases.most_common())
    return f"""## 3. 규제 발표일 — 현업의 하루

공문은 대개 **장 마감 뒤에 뜨고, 시행은 다음 날**이다. 이번 시나리오도 그렇다
(발표 {ev.this_policy.published_at} · 시행 {ev.this_policy.effective_from} · 종전 규정 기준일 {CUTOFF}).

**지금(As-Is).** 담당자가 공문을 읽고 해석 회의를 열고, 룰 개정안을 만들고, 전산에 요건을
넘기고, 테스트케이스를 짜고, 보유 신청건 영향을 쿼리로 뽑고, 그 결과를 다시 보고서로 옮긴다.
같은 사실이 회의록·메일·엑셀·전산요건서에 **네 번 옮겨 적히고**, 옮길 때마다 근거가 떨어져
나간다. 시행 전날 밤에 가장 흔히 나오는 질문이 "이 숫자 어디서 나왔죠"인 이유다.

**이 시스템(To-Be).** 공문을 넣고 한 번 실행하면 아래 산출물이 **같은 실행에서** 나온다.
각 항목에 원문 인용이 붙어 있고, 실행 자체가 해시 체인 감사로그
(`{ev.audit.head_hash[:16]}…`, {len(ev.audit.events)}단계)로 남는다.

- 조치 배분: {owner_line}
- 시점 배분: {phase_line}

숫자를 옮겨 적는 단계가 없다. **보고서가 실행의 부산물**이다."""


def _outputs(ev: ValidationEvidence) -> str:
    ex, g, mx, im, r = ev.extraction, ev.grounding, ev.matrix, ev.impact, ev.regression
    cs = ev.consistency.summary()
    return f"""## 4. 산출물 — 한 번 실행에서 나오는 것

| # | 산출물 | 현업에서 쓰는 자리 | 이번 실행 실측 | 화면 |
|---|---|---|---|---|
| 1 | 규제 문서 등록 | 원문 스냅샷·해시·정책 버전 타임라인 | 정책 버전 {len(ev.policy_timeline)}건 · 지역 기준선 {ev.baseline_region_count}곳 · 정합성 {_yn(ev.drift.ok)} | `sources.html` |
| 2 | 규제 변경 추출 + 인용 검증 | 해석 회의 자료 · 변경 요약 | 변경 {len(ex.changes)}건 · 인용 실재 {_pct(g.citation_correctness)} · 무근거 주장률 {_pct(g.unsupported_claim_rate)} | `regchange.html` |
| 3 | 임팩트 매트릭스 | 업무영역별 조치·기한·담당 배분 | {len(mx.rows)}행 · 자동처리 {_pct(mx.automation_rate)} · 시행 전 필수 {len(mx.d_minus_required)}건 | `impact_matrix.html` |
| 4 | 룰 변경안 + 회귀 테스트 | 전산 요건 · 심사 룰 개정 | 엔진 교차검증 {cs['passed']}/{cs['total']} · 회귀 {r.passed}/{r.total} ({_pct(r.pass_rate)}) | `rule.html` |
| 5 | 포트폴리오 영향 분석 | 리스크 보고 · 대외 보고 집계 | {im.portfolio_size:,}건 재평가 · 감소 {len(im.reduced)}건 · {_eok(im.total_limit_reduction)} | `portfolio.html` |
| 6 | 검증·거버넌스 문서 | 모델검증 · 감독 대응 · 내부 증빙 | 리스크 {len(_RISKS)}건/{len({x.category for x in _RISKS})}범주 · 스코어카드 통과 {ev.scorecard.summary()['passed']}/{ev.scorecard.summary()['total']} (미측정 {ev.scorecard.summary()['not_measured']}) | `validation_report.html` 외 2종 |

여섯 개가 **서로 다른 실행에서 나온 것이 아니다.** 같은 evidence 객체를 읽으므로 문서끼리
숫자가 어긋날 수 없고, 어긋나면 배포 전에 테스트가 먼저 실패한다.

### 4-1. 규제 문서 등록 — 근거의 출발점

원문(보도자료·FAQ)을 파일 그대로 보관하고 **sha256 해시**를 기록한다. 이후 모든 인용은 이
스냅샷과 글자 단위로 대조되므로, "그 문장 원문에 있었나요"라는 질문에 회의 없이 답한다.
정책 버전 DB에는 이번 대책만이 아니라 **과거 규제지역 지정 이력({len(ev.policy_timeline)}건)** 이
들어 있어, "직전까지 유효했던 규정과 무엇이 다른가"를 시점으로 되짚을 수 있다
(직전 정책: `{ev.previous.policy_id}` — {ev.previous.title}).

### 4-2. 규제 변경 추출 + 인용 검증 — LLM 이 하는 유일한 일

LLM 은 공문에서 **변경 사실만** 뽑는다. 항목마다 원문 인용이 강제되고, 그 인용이 원문에
실제로 존재하는지 기계가 대조한다. 이번 실행에서 {ev.extraction.policy_id} 문서
{len(ev.sources)}건에서 변경 {len(ex.changes)}건을 뽑았고, 카테고리 분포는 다음과 같다.

{_category_table(ex)}

**LLM 은 규칙 값을 만들지 않는다.** 값은 사람이 확정한 명세에서 오고, LLM 산출물은 그 명세의
구현(엔진)과 대조되는 쪽이다.

나머지 산출물(3~6번)은 5·6·7·8절에서 하나씩 본다."""


def _category_table(ex) -> str:
    cats = Counter(c.category for c in ex.changes)
    head = "| 카테고리 | 건수 | 현업에서 무엇이 되나 |\n|---|---|---|"
    meaning = {
        "REGION": "규제지역 기준선 갱신 — 어느 지역 신청건이 대상인지",
        "LTV": "심사 룰의 비율 개정 — 룰 변경안의 본체",
        "EXCEPTION": "예외 판정 분기 (생애최초·서민실수요·정책모기지 등)",
        "EFFECTIVE_DATE": "시행일·기준일 — 전산 반영 시점과 소급 여부",
        "GRANDFATHERING": "경과규정 — 이미 접수·계약된 건의 처리 기준",
        "SCOPE_LIMIT": "적용범위 제한 (한도·만기·전입의무 등) — 별도 룰로 분리",
    }
    rows = "\n".join(
        f"| {k} | {v}건 | {meaning.get(k, '—')} |" for k, v in cats.most_common()
    )
    return head + "\n" + rows


def _matrix(ev: ValidationEvidence) -> str:
    mx = ev.matrix
    dm = "\n".join(
        f"| {r.area} | {r.deliverable} | {r.owner.value} | {_yn(r.automatable)} |"
        for r in mx.d_minus_required
    )
    reasons = Counter(
        (r.human_review_reason or "").split("—")[0].split(".")[0].strip()
        for r in mx.human_review_rows
    )
    reason_rows = "\n".join(f"| {k} | {v}행 |" for k, v in reasons.most_common())
    return f"""## 5. 업무영역별 조치 — 임팩트 매트릭스

"규제가 바뀌었으니 알아서 챙기세요"는 조치가 아니다. 매트릭스는 **업무영역 ×
무엇을 해야 하는가 × 언제까지 × 누가 × 근거**를 행으로 낸다. 이번 실행은
{len(mx.rows)}행(코어 {len(mx.core_rows)}행 · Discovery {len(mx.discovery_rows)}행)이고,
업무영역은 {len({r.area for r in mx.rows})}개다.

### 5-1. 시행 전에 반드시 끝나야 하는 것 ({len(mx.d_minus_required)}건)

| 업무영역 | 산출물 | 담당 | 자동생성 |
|---|---|---|---|
{dm}

### 5-2. 자동처리 불가 {len(mx.human_review_rows)}행 — **사유 없이 만들 수 없다**

자동처리율은 {_pct(mx.automation_rate)}다. 나머지는 "미구현"이 아니라 **사람이 결정해야 하는 자리**이고,
매트릭스는 사유가 비어 있는 행을 만들 수 없게 되어 있다(생성 단계에서 막힌다).

| 사람 검토 사유 (요약) | 행 수 |
|---|---|
{reason_rows}

이 표가 현업 관점에서 이 제품의 핵심이다. **넘기는 일과 넘기지 않는 일의 경계가 문서로
고정되어 있고**, 그 경계가 매 실행마다 같은 규칙으로 다시 그려진다."""


def _portfolio(ev: ValidationEvidence) -> str:
    im = ev.impact
    seg = "\n".join(f"| {k} | {v:,}건 |" for k, v in
                    sorted(im.segment_counts.items(), key=lambda x: -x[1]))
    tr = "\n".join(f"| {k} | {v:,}건 |" for k, v in
                   sorted(im.ltv_transitions.items(), key=lambda x: -x[1]))
    w = im.worst_case
    return f"""## 6. 우리 보유분은 얼마나 움직이는가 — 포트폴리오 영향

보유 신청건을 **시행 전({im.before_date})과 후({im.after_date}) 두 시점으로 각각 다시 판정**해
차이를 집계한다. 한 시점만 계산하는 도구로는 이 표를 만들 수 없다.

| 지표 | 값 |
|---|---|
| 재평가 대상 | {im.portfolio_size:,}건 (층화 합성 데이터, seed `{im.seed}`) |
| 한도 감소 | {len(im.reduced):,}건 ({_pct(im.affected_rate, 1)}) |
| 총 한도 감소액 | {_eok(im.total_limit_reduction)} |
| 감소 건 평균 | {_eok(im.avg_limit_reduction, 1)} |
| 경과규정 보호 | {im.grandfathered_count:,}건 |
| 사람 검토 | {im.human_review_count:,}건 (판정 불가 {im.undecidable_count:,} · 변화량 미상 {im.impact_unknown_count:,}) |
| 커버리지 | 심사 판정 {_pct(im.decision_coverage, 1)} · 영향 측정 {_pct(im.impact_coverage, 1)} |

### 6-1. LTV 전이

| 전이 | 건수 |
|---|---|
{tr}

### 6-2. 세그먼트

| 세그먼트 | 건수 |
|---|---|
{seg}

가장 크게 움직인 건은 `{w.customer_id}`({w.region_code} · 주택가격 {_eok(w.property_price)}) —
LTV {_pct(w.before.max_ltv)} → {_pct(w.after.max_ltv)}, 적용 룰 `{w.before.applicable_rule_id}` →
`{w.after.applicable_rule_id}`.

> **합성 데이터임을 밝힌다.** 실제 고객 데이터는 쓰지 않았다. 실 데이터에 연결하면 같은
> 파이프라인이 같은 표를 실 수치로 낸다 — 필요한 것은 신청건의 지역·주택가격·주택수·
> 계약/접수일이며, 그 밖의 개인정보는 이 계산에 들어가지 않는다."""


def _rulechange(ev: ValidationEvidence) -> str:
    p, r = ev.proposal, ev.regression
    cs = ev.consistency.summary()
    fails = "\n".join(f"| {c.name} | {c.detail} |"
                      for c in ev.consistency.checks if not c.passed)
    cat = "\n".join(f"| {k} | {p_}/{n_} ({_pct(rate)}) |"
                    for k, (p_, n_, rate) in sorted(r.pass_rate_by_category().items()))
    unmapped = "\n".join(f"- {u}" for u in p.unmapped)
    return f"""## 7. 룰 변경안과 회귀 테스트 — 전산에 넘기는 것

추출된 변경을 **구조화된 룰 변경안(DRAFT)** 으로 조립하고, 그 변경안을 엔진과 교차검증한 뒤,
테스트케이스를 생성해 돌린다. 승인은 사람이 한다 — 이번 실행의 변경안 상태는
**`{p.status.value}`** 다.

| 항목 | 값 |
|---|---|
| 대상 룰 | `{p.rule_id}` ({p.change_type.value}) |
| 변경 전 → 후 | {p.before.region_status} LTV {_pct(p.before.max_ltv)} → {p.after.region_status} LTV {_pct(p.after.max_ltv)} |
| 예외 | {', '.join(p.exceptions)} |
| 경과규정 기준일 | {p.grandfathering.cutoff_date} (조건 {len(p.grandfathering.conditions)}종) |
| 근거 인용 | {len(p.sources)}건 (필드마다 원문 문서 id 와 문장) |
| 엔진 교차검증 | {cs['passed']}/{cs['total']} 통과 · {cs['failed']}건 사람 확인 |
| 회귀 테스트 | {r.passed}/{r.total} ({_pct(r.pass_rate)}) — 명세 독립 재구현 오라클과 대조 |

### 7-1. 사람 확인이 걸린 {cs['failed']}건

| 검증 항목 | 왜 사람인가 |
|---|---|
{fails}

### 7-2. 룰로 배치되지 않은 변경 {len(p.unmapped)}건

{unmapped}

LTV 로 분류됐지만 **비율이 아닌 것**(한도·만기·전입의무)이다. 자동으로 LTV 룰에 밀어 넣으면
숫자는 채워지지만 룰은 틀린다. 그래서 배치하지 않고 사람에게 넘긴다.

### 7-3. 회귀 테스트 카테고리별

| 카테고리 | 통과율 |
|---|---|
{cat}"""


def _trust(ev: ValidationEvidence) -> str:
    g, r, sc = ev.grounding, ev.regression, ev.scorecard
    s = sc.summary()
    disc = "\n".join(
        f"| {d.metric} | {_pct(d.clean)} | {_pct(d.corrupted)} | {_yn(d.detected)} |"
        for d in ev.discrimination.results
    )
    return f"""## 8. 왜 현업이 이 산출물을 믿을 수 있나

여신에서 잘못된 한도 안내는 오답이 아니라 **사고**다. 그래서 역할을 갈랐다.

| 층 | 누가 | 무엇을 보장하나 |
|---|---|---|
| 추출 | LLM | 인용이 붙은 사실만. 인용은 원문과 글자 단위 대조 — {_pct(g.citation_correctness)} ({g.grounded}/{g.total}) |
| 판정 | 결정적 룰엔진 | 사람이 확정한 명세의 구현. 같은 입력 → 항상 같은 결과 |
| 검증 | 독립 재구현 오라클 | 명세에서 따로 유도한 검증기와 전 케이스 대조 — {r.passed}/{r.total} ({_pct(r.pass_rate)}) |
| 기록 | 해시체인 감사로그 | 실행 {len(ev.audit.events)}단계 · 검증 {_yn(ev.audit.verify().ok)} · head `{ev.audit.head_hash[:16]}…` |
| 판정 | Assurance 스코어카드 | 지표 {s['total']}개를 확정 임계와 대조 — 통과 {s['passed']} · 미달 {s['failed']} · 미측정 {s['not_measured']} |

**미측정을 통과로 세지 않는다.** 모르는 것을 통과로 처리하는 것이 검증 체계가 무력해지는
가장 흔한 경로이고, 모델검증 부서가 가장 먼저 보는 자리이기도 하다. 이번 실행에서 미측정으로
남은 지표와 그 이유는 이렇다.

{_not_measured_table(ev)}

### 8-1. 지표가 실제로 오류에 반응하는가 (판별력)

"인용 정확성 {_pct(g.citation_correctness)}"는 그 지표가 **틀린 것을 틀렸다고 말할 수 있을 때만** 의미가 있다.
그래서 산출물에 오류를 일부러 주입하고 지표가 떨어지는지 측정한다.

| 지표 | 정상 | 오염 주입 후 | 탐지 |
|---|---|---|---|
{disc}

집계 비율은 단건 오류에 둔감하다는 것도 함께 드러난다 — 그래서 **항목 단위 검사**가
실질 탐지력을 담당한다. 이 한계는 검증보고서에 그대로 적혀 있다."""


_NOT_MEASURED_WHY = {
    "JS Port Agreement": "브라우저 포팅본 대조는 node 가 있어야 돈다 — 배포 빌드에서 측정되고, "
                         "한 건이라도 어긋나면 배포가 중단된다",
    "Policy-version Consistency": "시점 질의 골드가 아직 사람 검수 전이다 — 검수가 끝나면 "
                                  "코드 수정 없이 측정이 켜진다",
}


def _not_measured_table(ev: ValidationEvidence) -> str:
    rows = [
        f"| {m.threshold.metric} | {_NOT_MEASURED_WHY.get(m.threshold.metric, '—')} |"
        for d in ev.scorecard.dimensions for m in d.metrics
        if getattr(m.verdict, "name", "") == "NOT_MEASURED"
    ]
    if not rows:
        return "이번 실행에서는 미측정 지표가 없다."
    return "| 미측정 지표 | 왜 재지 못했나 |\n|---|---|\n" + "\n".join(rows)


def _not_automated(ev: ValidationEvidence) -> str:
    im = ev.impact
    esc = "\n".join(f"| `{k}` | {v:,}건 | {_ESCALATION.get(k, '—')} |"
                    for k, v in sorted(im.escalation_reasons.items(), key=lambda x: -x[1]))
    return f"""## 9. 자동화하지 않는 자리 — 이 제품이 파는 것의 절반

커버리지는 심사 판정 {_pct(im.decision_coverage, 1)} · 영향 측정 {_pct(im.impact_coverage, 1)} 에서 멈춘다.
값을 추정으로 메우면 두 숫자는 즉시 100%가 된다. 메우지 않는다.

사람에게 넘어간 {im.human_review_count:,}건은 **사유 코드와 함께** 넘어간다
(한 건에 사유가 여러 개 붙을 수 있어 아래 합계는 건수보다 크다).

| 사유 코드 | 건수 | 무엇을 결정해야 하나 |
|---|---|---|
{esc}

여신 현업에서 이 표가 갖는 뜻은 분명하다. 담당자는 {im.portfolio_size:,}건을 다시 보지 않고,
**결정이 필요한 자리만** 본다. 그리고 그 결정이 왜 필요한지가 코드로 남아 있어, 나중에
"이건 왜 사람이 봤죠"라는 질문에 로그로 답한다.

거버넌스 절차도 자동화 대상이 아니다 — 내규 개정은 위원회 승인 사항이고, 이 시스템은
**초안까지만** 만든다."""


_ESCALATION = {
    "OWNER_BASELINE_UNKNOWN": "원문에 해당 구간 기준값이 없다 — 도메인 확정 선행",
    "MULTI_HOME_BASELINE_UNKNOWN": "다주택 기준선이 이 공문 범위 밖 — 별도 규정 확인",
    "LTV_OWNER_0": "판정은 됐으나 변화량 산정에 종전 기준값이 필요",
    "GRANDFATHERED_ACCEPTED_OR_CONTRACT": "경과규정 대상 — 접수·계약 증빙 확인 필요",
    "GRANDFATHERED_LAND_PERMIT": "토지거래허가 관련 경과규정 — 개별 확인 필요",
}


def _adoption(ev: ValidationEvidence) -> str:
    return f"""## 10. 도입 — 무엇이 필요하고, 무엇이 필요 없나

**필요한 것**

| 구분 | 내용 |
|---|---|
| 입력 ① | 규제 공문 원문 (보도자료·FAQ 등 텍스트/PDF) |
| 입력 ② | 보유 신청건 — 지역·주택가격·주택수·계약일/접수일 (그 밖의 개인정보는 쓰지 않는다) |
| 확정 | 룰 값·예외 기준의 **도메인 확정** — 이것은 사람이 한다 |

**필요 없는 것**

- **판정용 LLM 호출.** LLM 은 추출 단계에서만 쓰인다. 판정·집계·검증은 결정적 코드다.
  이 문서의 전 수치도 실제 실행 기록 재생(provider `{ev.provider}`)으로 **LLM 호출 0회**에
  재현된다.
- **런타임 의존성.** 판정 엔진은 외부 라이브러리 없이 동작하고, 브라우저 포팅본이 원본과
  대조된 뒤에만 배포된다. 화면은 정적 파일이라 **서버 호출 없이** 뜬다.
- **고객 데이터 반출.** 고객 면(웹뷰)은 입력이 기기를 벗어나지 않고, 현업 면은 행내에서
  돈다."""


def _status(ev: ValidationEvidence) -> str:
    im = ev.impact
    return f"""## 11. 지금 되는 것 · PoC 기간에 할 것 · 한계

**이미 동작한다 (공개 데모에서 확인 가능)**

- 공문 등록·해시 스냅샷·정책 버전 타임라인, 직전 정책 대비 비교
- 변경 추출 + 인용 원문 대조, 카테고리 분류
- 임팩트 매트릭스 (담당·기한·근거·사람검토 사유)
- 룰 변경안 조립 + 엔진 교차검증 + 회귀 테스트 생성·실행
- 포트폴리오 {im.portfolio_size:,}건 두 시점 재평가와 집계
- 검증보고서 · 모델·시스템 카드 · AI 리스크 레지스터 자동 생성
- 해시체인 감사로그, Assurance 스코어카드, 판별력(오류 주입) 측정
- 규제 원문 검색(BM25) · 영향 지식그래프 · 판정 플레이그라운드

**PoC 기간 목표**

- 실 신청건 데이터 연결 (합성 포트폴리오 → 행내 데이터, 스키마 매핑)
- 공문 수집·추출 파이프라인 자동화 (지금은 실행을 사람이 건다)
- 룰 변경안 → 행내 룰 운영 시스템 포맷 연계
- 도메인 확정이 필요한 공백(아래 한계)을 현업과 함께 채우기

**한계 (그대로 밝힌다)**

- 포트폴리오 수치는 **층화 합성 데이터** 기반이다. 실 고객 데이터를 쓰지 않았다.
- 원문에 기준값이 없는 구간은 **추정하지 않는다** — 커버리지가
  {_pct(im.decision_coverage, 1)} / {_pct(im.impact_coverage, 1)} 에서 멈추는 이유다.
- 변경안은 **DRAFT** 다. 승인·내규 개정은 사람·위원회의 몫이다.
- 한도 산정은 스트레스 금리 가산 등 일부 항목이 미반영이며, 최종 한도는 심사로 확정된다."""


def _same_engine(ev: ValidationEvidence) -> str:
    return """## 12. 고객 면과의 연결 — 같은 엔진이라는 것의 실무적 의미

규제 발표일에 가장 비싼 사고는 **창구와 앱이 다른 말을 하는 것**이다. 이 시스템은 고객
화면의 판정과 현업 산출물의 판정이 같은 엔진에서 나오고, 브라우저에서 도는 판정 포팅본은
원본 엔진과 전건 대조된 뒤에만 배포된다. 그래서

- 고객이 앱에서 본 "경과규정 대상입니다"와 심사가 보는 판정 근거가 **같은 룰 id** 를 가리키고,
- 콜센터로 온 문의를 그 자리에서 같은 화면으로 되짚을 수 있으며,
- 규제 해석이 바뀌면 **양쪽이 동시에** 바뀐다 (한쪽만 고쳐지는 상태가 구조적으로 안 생긴다).

한 번의 도입으로 고객 콘텐츠와 내부 업무도구가 함께 열린다는 뜻이기도 하다."""


def _verify(ev: ValidationEvidence) -> str:
    return f"""## 13. 직접 확인 · 재현

공개 사이트: {PUBLIC_SITE}

| 보실 것 | 페이지 |
|---|---|
| 규제 문서 등록 | `sources.html` |
| 규제 변경 분석 | `regchange.html` |
| 임팩트 매트릭스 | `impact_matrix.html` |
| 룰 변경안 | `rule.html` |
| 고객·포트폴리오 영향 | `portfolio.html` |
| 검증 (Assurance) | `assurance.html` |
| 검증보고서 · 모델카드 · 리스크 레지스터 | `validation_report.html` · `model_system_card.html` · `ai_risk_register.html` |
| 고객 면 (같은 엔진) | `signal.html` |

재현 — API 키 없이, LLM 호출 0회로 같은 수치가 나온다.

```bash
pip install -e ".[dev]"
python -m pytest -q                            # 테스트 전량
python examples/demo_impact_e2e.py             # 파이프라인 관통 실행
python examples/build_ops_description.py       # 이 문서 재생성
python tools/build_site.py                     # 사이트 전체 재빌드
```

이 문서가 주장하는 수치와 시스템이 어긋나면 **테스트가 먼저 실패한다.**
(생성 {ev.generated_at or "—"} · provider `{ev.provider}` · 감사로그 head `{ev.audit.head_hash[:16]}…`)"""


def _team() -> str:
    return """## 14. 만든 사람

금융권 개인여신 데이터분석 8년 7개월. 규제가 바뀌는 날 은행 안에서 해석 → Rule 변경 →
테스트 → 전산 반영을 직접 수행한 당사자다. LTV 차등 전략을 설계해 불량률 5.77% → 3.16%
로 개선한 실적이 있다.

이 문서의 산출물 목록이 곧 그 업무의 목록이다 — 없던 도구를 상상해서 만든 것이 아니라,
**하던 일을 산출물로 고정한 것**이다. 다만 이전 재직사의 데이터·문서는 이 프로젝트에 일절
사용하지 않았고, 근거는 전부 공개 보도자료·FAQ 다."""
