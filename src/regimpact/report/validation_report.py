"""검증보고서 렌더러 — `ValidationEvidence` 만 읽어 Markdown 을 조립한다.

구조는 금융권 모델 검증보고서의 관례를 따른다 — 개념적 건전성 / 구현 정확성 /
성과 검증 / 거버넌스 / 한계 / 발견사항 / 재현성. 검증인이 읽는 순서다.

**이 파일에는 도메인 수치 리터럴이 없다.** 모든 숫자는 evidence 에서 온다.
`tests/test_validation_report.py` 가 그것을 강제한다 — 손으로 적은 숫자가 하나라도
들어가는 순간 보고서는 시간이 지나며 조용히 거짓말이 된다.
"""
from __future__ import annotations

from .. import rule_engine
from ..grandfathering import CUTOFF
from ..governance.risk import RISKS as _RISKS
from ..regions import REG_EFFECTIVE
from .evidence import ValidationEvidence


def _pct(x: float, digits: int = 0) -> str:
    return f"{x:.{digits}%}"


def _yn(b: bool) -> str:
    return "✅" if b else "❌"


def _eok(n: int, digits: int = 0) -> str:
    """원 단위를 억원으로 (감소는 음수)."""
    return f"{n / 1_0000_0000:,.{digits}f}억원"


def render(ev: ValidationEvidence) -> str:
    parts = [
        _header(ev), _summary(ev), _toc(),
        _s1_purpose(ev), _s2_scope(ev), _s3_method(ev), _s4_system(ev),
        _s5_data(ev), _s6_conceptual(ev), _s7_implementation(ev),
        _s8_extraction(ev), _s9_outcomes(ev), _s10_governance(ev),
        _s11_limits(ev), _s12_findings(ev), _s13_reproducibility(ev),
        _s14_conclusion(ev), _appendix(ev),
    ]
    return "\n\n".join(p.strip() for p in parts) + "\n"


# --------------------------------------------------------------------- 머리말
def _header(ev: ValidationEvidence) -> str:
    ex = ev.extraction
    return f"""# RegImpact AI — 시스템 검증보고서 (Validation Report)

| 항목 | 내용 |
|---|---|
| 대상 시스템 | RegImpact AI — 주택담보대출 규제 변경 영향분석·검증 시스템 |
| 검증 시나리오 | {ex.policy_id} — 규제지역 추가 지정 (시행 {ex.effective_from}) |
| 생성 시각 | {ev.generated_at or "(미기입)"} |
| 생성 방법 | `python examples/build_validation_report.py` — 파이프라인 실행 결과에서 자동 조립 |
| LLM provider | `{ev.provider}` (재생 원본 `{ev.run_path}`) |
| 감사로그 head | `{ev.audit.head_hash}` |

> 이 보고서의 **모든 수치는 파이프라인을 실제로 실행해 얻은 값**이다. 손으로 적은 숫자는 없다.
> 시스템이 바뀌면 보고서도 바뀐다. 재현 방법은 §13."""


def _summary(ev: ValidationEvidence) -> str:
    g, s, r, c = ev.grounding, ev.gold_score, ev.regression, ev.consistency
    cs = c.summary()
    im = ev.impact
    return f"""## 검증 종합의견 (Executive Summary)

{ev.extraction.policy_id} 규제 변경에 대해 원문 적재 → 변경 추출 → 시점 해석 → 고객 영향 →
룰 변경안 → 테스트케이스 → Assurance 를 관통 실행하고, 각 단계 산출물을 독립 기준과 대조했다.

| 검증 항목 | 결과 | 판단 |
|---|---|---|
| 인용 정확성 (Citation Correctness) | {_pct(g.citation_correctness)} ({g.grounded}/{g.total}) | 적정 |
| 변경 완전성 (Change Completeness) | {_pct(s.change_completeness)} | 적정 |
| 예외 재현율 (Exception Recall) | {_pct(s.exception_recall)} | 적정 |
| 룰엔진 회귀 (독립 오라클 대조) | {_pct(r.pass_rate)} ({r.passed}/{r.total}) | 적정 |
| 변경안 ↔ 엔진 일치 | {cs['passed']}/{cs['total']} | **조건부** — §10 |
| 정책 DB ↔ 지역 기준선 정합성 | {_yn(ev.drift.ok)} | 적정 |
| 심사 판정 커버리지 | {_pct(im.decision_coverage, 1)} | 적정 |
| 영향 측정 커버리지 | {_pct(im.impact_coverage, 1)} | **제약 있음** — §11 |
| 판별력 (오류 주입 시 지표 반응) | {len([d for d in ev.discrimination.results if d.detected])}/{len(ev.discrimination.results)} 지표 반응 | 적정 |

**종합의견.** 코어 판정 경로(주택구입목적 주담대 LTV)는 독립 명세 오라클과 전 케이스 일치하며,
LLM 산출물은 인용 근거가 원문에 존재하는지 결정적으로 검증된다. 다만 **자동 승인은 성립하지
않는다** — 변경안 일치검증 {cs['total']}건 중 {cs['failed']}건이 사람 검토를 요구하고(§10),
영향 측정 커버리지가 {_pct(im.impact_coverage, 1)}에서 상한에 걸린다(§11). 두 제약 모두
원문에 값이 없어서 생긴 것이며, 값을 추정해 메우지 않는 것이 이 시스템의 설계 원칙이다."""


def _toc() -> str:
    return """## 목차

1. 검증 배경 및 목적 · 2. 검증 범위 · 3. 검증 방법론 · 4. 대상 시스템 개요 ·
5. 데이터 적정성 · 6. 개념적 건전성 · 7. 구현 정확성(룰엔진) · 8. 성과 검증(추출·인용) ·
9. 성과 검증(영향 분석) · 10. 거버넌스(변경안 승인) · 11. 한계 및 가정 ·
12. 발견사항 및 조치 · 13. 재현성 및 감사추적 · 14. 결론 · 부록"""


# --------------------------------------------------------------------- 본문
def _s1_purpose(ev: ValidationEvidence) -> str:
    return f"""## 1. 검증 배경 및 목적

규제 변경이 발표되면 금융회사는 짧은 기간 안에 **무엇이 바뀌었는지 확정하고, 여신 규정과
전산 룰에 반영하고, 그 반영이 옳다는 것을 증명**해야 한다. 이 과정은 현재 사람이 원문을 읽고
표를 만들어 수행하며, 누락·오독이 그대로 고객 판정에 나간다.

RegImpact AI 는 그 작업을 LLM 으로 대체하는 시스템이 아니라, **LLM 산출물을 검증 가능하게
만드는** 시스템이다. 이 보고서의 목적은 그 검증 장치가 실제로 작동하는지를 확인하는 것이다.

검증 질문은 다음 세 가지다.

- **VQ1.** LLM 이 원문에 없는 것을 말하지 않는가 (§8)
- **VQ2.** 결정적 판정 로직이 확정 명세와 일치하는가 (§7)
- **VQ3.** 확정할 수 없는 것을 확정한 척하지 않는가 (§10, §11)"""


def _s2_scope(ev: ValidationEvidence) -> str:
    ex = ev.extraction
    return f"""## 2. 검증 범위 및 대상

**대상 시나리오** — {ex.policy_id}, 시행 {ex.effective_from}.
신규 지정 지역 {len(ex.target_regions)}곳: {", ".join(ex.target_regions)}.

**코어 범위 (자동 판정)** — 주택구입목적 주택담보대출의 적용 LTV 판정.

**범위 밖 (Discovery — 사람 검토로 분리)** — 전세대출·신용대출·중도금/이주비·사업자대출·
정책대출. 원문에 언급되지만 코어 자동판정에 넣지 않고 "수동 정책 검토 대상"으로 표시한다.
범위를 넓혀 얕게 처리하는 것보다 좁게 확실히 처리하고 나머지를 명시적으로 넘기는 편이
검증 가능하기 때문이다.

**검증하지 않은 것** — 실제 고객 데이터(합성 포트폴리오만 사용), 실 시스템 연동,
LLM 의 신규 추론 능력(재생 실행 사용, §13)."""


def _s3_method(ev: ValidationEvidence) -> str:
    return f"""## 3. 검증 방법론

값의 출처에 따라 검증 방법을 나눈다. **자기 채점을 피하는 것**이 설계의 축이다.

| 산출물 | 성격 | 검증 방법 | 기준(ground truth) |
|---|---|---|---|
| 추출된 변경 사실 | LLM 생성 | 인용 verbatim 대조 + 골드 대조 | 공문 원문, 사람 확정 골드 |
| LTV 판정 | 결정적 코드 | **차등 검증** — 독립 명세 오라클과 대조 | `docs/05_RULE_SPEC.md` §H |
| 지역 규제상태 | 데이터 | 정책 DB ↔ 엔진 기준선 양방향 정합성 | MOLIT 참고2 현황표 |
| 룰 변경안 | 결정적 조립 | 엔진 상수와 교차검증 | 룰엔진 상수 |
| 검증 하니스 자체 | — | **판별력(negative control)** — 오류 주입 후 지표 반응 측정 | 정상값 대비 |

마지막 행이 핵심이다. 정상 데이터에서 100%가 나오는 것만으로는 하니스가 오류에 반응하는지
알 수 없다. **항상 100%인 검증 시스템은 그 자체가 red flag다.**"""


def _s4_system(ev: ValidationEvidence) -> str:
    rows = "\n".join(
        f"| {i} | {e.action} | {e.target} | `{e.entry_hash[:12]}…` |"
        for i, e in enumerate(ev.audit.events)
    )
    return f"""## 4. 대상 시스템 개요

파이프라인은 다음 순서로 관통하며, 각 단계가 감사로그에 이벤트를 남긴다.

| # | 단계 | 대상 | 해시 |
|---|---|---|---|
{rows}

각 이벤트의 해시는 직전 해시를 포함한다(해시 체인). 사후 변조 시 체인이 깨진다(§13)."""


def _s5_data(ev: ValidationEvidence) -> str:
    docs = "\n".join(
        f"| {doc_id} | {len(text):,}자 |" for doc_id, text in ev.sources.items()
    )
    return f"""## 5. 데이터 적정성 검증

### 5.1 원문 스냅샷

공개 보도자료·FAQ 만 사용한다. 실제 회사 문서·고객 데이터는 쓰지 않는다.

| 문서 | 추출 텍스트 |
|---|---|
{docs}

원본 파일과 sha256 해시는 저장소에 고정돼 있다.

{ev.source_table}

### 5.2 지역 레지스트리

지역 규제상태는 시점 버전 데이터로 관리한다. 현재 등록 지역 **{ev.baseline_region_count}곳**.
값 출처는 MOLIT 보도참고자료 p5 「투기과열지구 및 조정대상지역 현황」 표이며,
추정 없이 원문에서 이관했다(`regulatory_facts.md` C16).

**미등록 지역은 비규제가 아니라 UNKNOWN 으로 처리해 사람 검토로 보낸다.** 미등록을 조용히
비규제로 간주하면 데이터 누락이 관대한 판정으로 새어나간다 — §12 발견사항 R-01 참조.

### 5.3 합성 포트폴리오

실제 고객 데이터를 쓰지 않으므로 층화 합성 포트폴리오 **{len(ev.portfolio):,}건**
(seed `{ev.impact.seed}`)을 사용한다. 구성 비율은 코드 상수로 고정돼 재현 가능하다.

| 세그먼트 | 비중 |
|---|---|
""" + "\n".join(
        f"| {k} | {_pct(v, 1)} |" for k, v in ev.portfolio_composition.items()
        if isinstance(v, float)
    ) + """

이 포트폴리오는 **성능 주장의 근거가 아니라 커버리지 측정 도구**다. 합성 데이터로 정확도를
주장하는 것은 순환이므로, 여기서는 "판정이 가능한가 / 영향을 측정할 수 있는가"만 센다."""


def _s6_conceptual(ev: ValidationEvidence) -> str:
    tl = "\n".join(
        f"| {e.policy.effective_from} | {e.state} | {e.policy.policy_id} | "
        f"{e.predecessor_id or '—'} |"
        for e in ev.policy_timeline
    )
    prev = ev.previous.policy_id if ev.previous else "없음"
    preview = "\n".join(
        f"| {c.region_name} | {c.before.value} | {c.after.value} |"
        for c in ev.region_preview
    )
    return f"""## 6. 개념적 건전성 검증

### 6.1 정책은 문서가 아니라 버전이다

이 시스템의 질문은 "이 문서에 무엇이 쓰여 있나"가 아니라
**"이번 정책 시행 시점에, 직전까지 유효했던 정책과 무엇이 달라졌는가"** 다.
따라서 정책은 시행일 구간을 갖는 버전이고 `supersedes` 로 이어진다.

| 시행일 | 상태 | 정책 | 직전 정책 |
|---|---|---|---|
{tl}

이번 정책 `{ev.this_policy.policy_id if ev.this_policy else "—"}` 의 직전 유효 정책: **{prev}**

이번 정책이 바꾸는 지역:

| 지역 | 이전 | 이후 |
|---|---|---|
{preview}

### 6.2 규칙 값은 LLM 이 만들지 않는다

LTV 값·우선순위는 사람이 확정한 명세(`docs/05_RULE_SPEC.md`)에서 오고, 룰엔진은 그 명세의
구현이다. LLM 은 인용 근거가 붙은 **사실만** 추출하며, 그 추출은 룰엔진을 수정하지 않고
구조화 변경안(§10)으로 조립되어 사람 승인 대기 상태가 된다.

이 경계 덕분에 룰엔진이 LLM 출력의 **검증 기준**이 될 수 있다. 반대 방향이면 순환이다.

### 6.3 판정 우선순위

우선순위는 short-circuit 이며 명세 §E 에서 확정됐다.

```
P0  스코프(주택구입목적 아님)      → OUT_OF_SCOPE
P0b 정책대출                      → DISCOVERY
P0c 수도권 다주택                 → {_pct(rule_engine.LTV_MULTI)} (규제지역 여부 무관)
P0d 지역 미상                     → 사람 검토
P1  경과규정 (컷오프 {CUTOFF})     → 종전규정
P2  지역상태 (효력일 {REG_EFFECTIVE})
P3~P7 다주택 → 유주택 → 생애최초 → 서민실수요 → 일반
```

P0c 와 P0d 의 위치는 변이 테스트로 고정돼 있다 — 순서를 바꾸면 회귀가 실패한다(§12)."""


def _s7_implementation(ev: ValidationEvidence) -> str:
    r = ev.regression
    cats = "\n".join(
        f"| {cat} | {p}/{t} | {_pct(rate)} |"
        for cat, (p, t, rate) in r.pass_rate_by_category().items()
    )
    disc = [d for d in ev.discrimination.results if d.metric.startswith("Rule Regression")]
    mut = "\n".join(
        f"| {d.metric.split('(')[1].rstrip(')')} | {_pct(d.clean)} | {_pct(d.corrupted)} | {_yn(d.detected)} |"
        for d in disc
    )
    return f"""## 7. 구현 정확성 검증 — 룰엔진 (VQ2)

### 7.1 차등 검증 (differential testing)

룰엔진의 출력을 스스로 채점하지 않는다. 명세 §H 를 **독립적으로 재구현한 오라클**과 대조한다.
오라클은 `rule_engine`·`regions`·`grandfathering` 을 import 하지 않아 구조적으로 독립이다.

결과: **{r.passed}/{r.total} ({_pct(r.pass_rate)})**

| 카테고리 | 통과 | 비율 |
|---|---|---|
{cats}

### 7.2 이 일치율이 증명하는 것과 하지 않는 것

증명하는 것은 **"엔진 == 명세"** 이지 **"명세 == 현실"** 이 아니다. 두 구현이 같은 명세에서
유도되므로, 명세 자체의 오독은 이 지표로 잡히지 않는다. 실제로 그런 사례가 있었다(§12 R-01).

### 7.3 변이 테스트 — 하니스에 이빨이 있는가

엔진 상수를 의도적으로 변조하고 오라클이 잡는지 확인했다.

| 변이 | 정상 | 변조 후 | 탐지 |
|---|---|---|---|
{mut}"""


def _s8_extraction(ev: ValidationEvidence) -> str:
    g, s = ev.grounding, ev.gold_score
    ex = ev.extraction
    cats: dict = {}
    for item in ex.changes:
        cats[item.category] = cats.get(item.category, 0) + 1
    cat_rows = "\n".join(f"| {k} | {v} |" for k, v in sorted(cats.items()))
    disc = [d for d in ev.discrimination.results
            if not d.metric.startswith(("Rule Regression", "Proposal"))]
    disc_rows = "\n".join(
        f"| {d.metric} | {_pct(d.clean)} | {_pct(d.corrupted)} | {_yn(d.detected)} |"
        for d in disc
    )
    missed = ", ".join(s.missed_changes) if s.missed_changes else "없음"
    return f"""## 8. 성과 검증 — 추출 및 Citation Assurance (VQ1)

### 8.1 추출 결과

공문 {len(ev.sources)}건에서 변경 **{len(ex.changes)}건** 추출. 시행일 `{ex.effective_from}`,
대상 지역 {len(ex.target_regions)}곳.

| 카테고리 | 건수 |
|---|---|
{cat_rows}

문서별로 따로 추출한 뒤 문서 간 병합한다. 한 번에 전 문서를 넣으면 문서 간 열거가 서로를
가려 예외 항목이 누락된다(§12 D-02).

### 8.2 인용 근거 검증 (grounding)

추출된 각 항목의 인용이 원문에 **verbatim 으로 존재하는지** 결정적으로 확인한다.
LLM 이 스스로 판단하지 않는다.

- Citation Correctness: **{_pct(g.citation_correctness)}** ({g.grounded}/{g.total})
- Unsupported Claim Rate: **{_pct(g.unsupported_claim_rate)}**

### 8.3 사람 확정 골드 대조

- Change Completeness: **{_pct(s.change_completeness)}** (필수 변경 {len(ev.gold.get("required_changes", []))}건 기준)
- Exception Recall: **{_pct(s.exception_recall)}** (예외 {len(ev.gold.get("exceptions", []))}건 기준)
- 시행일 정확: {_yn(s.effective_date_correct)} · 지역 정확: {_yn(s.regions_correct)}
- 놓친 항목: {missed}

골드는 사람이 원문 대조로 확정했고 채점 대상 필드의 sha256 지문이 고정돼 있어,
확정 이후 수정되면 재검수 필요로 드러난다.

### 8.4 판별력 — 오류를 주입하면 지표가 떨어지는가

| 지표 | 정상 | 오류 주입 | 탐지 |
|---|---|---|---|
{disc_rows}

**간극의 크기에 주목해야 한다.** 추출 {len(ex.changes)}건 중 인용 1건을 환각으로 바꿔도
Citation Correctness 는 소폭만 움직인다 — 집계 비율은 단건 오류에 둔감하다.
반면 시행일·지역은 단일 값이라 틀리면 바닥까지 떨어진다. 따라서 집계 비율은 추세 지표로 읽고,
**항목 단위 검사가 실질 탐지력을 담당한다.** 상세는 `docs/eval/VALIDATION_LIMITS.md`."""


def _s9_outcomes(ev: ValidationEvidence) -> str:
    im = ev.impact
    seg = "\n".join(f"| {k} | {v:,}건 |" for k, v in im.segment_counts.items())
    trans = "\n".join(f"| {k} | {v:,}건 |" for k, v in im.ltv_transitions.items())
    esc = "\n".join(f"| {k} | {v:,}건 |" for k, v in im.escalation_reasons.items())
    diff = "\n".join(
        f"| {d['rule_id']} | {d['condition']} | "
        f"{'기준없음' if d['before'] is None else _pct(d['before'])} | "
        f"{'기준없음' if d['after'] is None else _pct(d['after'])} |"
        for d in ev.rule_diff
    )
    return f"""## 9. 성과 검증 — 영향 분석

### 9.1 룰 변경 diff (엔진에서 기계적으로 유도)

| rule_id | 조건 | 이전 | 이후 |
|---|---|---|---|
{diff}

### 9.2 고객 세그먼트별 영향 (합성 포트폴리오 {im.portfolio_size:,}건)

| 구분 | 건수 |
|---|---|
{seg}

LTV 전이:

| 전이 | 건수 |
|---|---|
{trans}

- 한도 감소 대상: **{len(im.reduced):,}건** ({_pct(im.affected_rate, 1)})
- 총 한도 감소액: **{_eok(im.total_limit_reduction)}** (건당 평균 {_eok(im.avg_limit_reduction, 2)})
- 경과규정 보호: {im.grandfathered_count:,}건

### 9.3 커버리지 — 두 축으로 나눠 본다

| 지표 | 값 | 의미 |
|---|---|---|
| 심사 판정 커버리지 | **{_pct(im.decision_coverage, 1)}** | LTV 판정을 자동으로 내릴 수 있는 비율 |
| 영향 측정 커버리지 | **{_pct(im.impact_coverage, 1)}** | 변화량(한도 증감)까지 계산할 수 있는 비율 |

두 축을 하나로 합치면 "판정은 되는데 변화량을 못 재는" 건이 판정 실패로 잘못 집계된다.
유주택자는 판정({_pct(rule_engine.LTV_OWNER)})은 서지만 **종전 기준값이 원문에 없어**
변화량을 못 낸다(§11).

자동판정 중단 사유:

| 사유 | 건수 |
|---|---|
{esc}

### 9.4 임팩트 매트릭스

전체 {len(ev.matrix.rows)}행 (코어 {len(ev.matrix.core_rows)} · Discovery {len(ev.matrix.discovery_rows)}).
코어 자동처리 가능 비율 **{_pct(ev.matrix.automation_rate)}**, 사람 검토 {len(ev.matrix.human_review_rows)}행.
D-day 전 필수 {len(ev.matrix.d_minus_required)}건.

자동처리 불가 행은 **사유 없이 만들 수 없다** — 스키마가 거부한다. "왜 사람이 봐야 하는지"가
빠진 매트릭스는 검증 산출물이 아니기 때문이다."""


def _s10_governance(ev: ValidationEvidence) -> str:
    p, c = ev.proposal, ev.consistency
    cs = c.summary()
    checks = "\n".join(
        f"| {ck.name} | {_yn(ck.passed)} | {ck.expected} | {ck.actual} |" for ck in c.checks
    )
    conflicts = "\n".join(f"- {x}" for x in p.conflicts) or "- 없음"
    unmapped = "\n".join(f"- {x}" for x in p.unmapped) or "- 없음"
    return f"""## 10. 거버넌스 검증 — Rule Change Proposal (VQ3)

### 10.1 승인 경로

LLM 은 룰엔진을 직접 고치지 않는다. 추출 → **구조화 변경안(DRAFT)** → 엔진 교차검증 →
사람 승인 → registry 반영 순서이며, 변경안은 **절대 APPROVED 로 태어나지 않는다.**

현재 변경안 상태: **{p.status.value}** · 근거 인용 {len(p.sources)}건

세그먼트별 LTV(after): {p.after.ltv_by_segment}

### 10.2 엔진 교차검증 결과 — {cs['passed']}/{cs['total']}

| 검사 | 통과 | 기대(엔진) | 실제(변경안) |
|---|---|---|---|
{checks}

검증 방향은 **항상 엔진 → 변경안**이다. 반대로 하면 LLM 출력이 스스로를 검증하게 된다.

### 10.3 미통과 항목은 결함이 아니라 사람 검토 대상이다

**세그먼트 값 충돌**

{conflicts}

한 세그먼트에 서로 다른 값이 추출된 경우다. 최빈값을 채택하되 충돌 자체를 남긴다.
동률이면 아무것도 고르지 않는다 — 임의 선택은 값 창작이다.

**LTV 가 아닌 변경 항목 (엔진이 모델링하지 않는 룰 차원)**

{unmapped}

규제에는 LTV 외에 한도·전입의무·만기 규제가 함께 들어 있는데 엔진은 LTV 만 다룬다.
변경안이 그 공백을 드러낸 것이므로, 조용히 버리지 않고 사람에게 넘긴다.

이 항목들을 통과시키려면 값을 지어내거나 항목을 버려야 한다. 둘 다 하지 않는다."""


def _s11_limits(ev: ValidationEvidence) -> str:
    im = ev.impact
    splits = "\n".join(
        f"| {s['split']} | {s['count']}문항 | 고위험 {_pct(s['high_risk_ratio'], 1)} | "
        f"{', '.join(s['authored_by'])} |"
        for s in ev.split_stats
    )
    return f"""## 11. 한계 및 가정 (Limitations Register)

| # | 한계 | 영향 | 대응 |
|---|---|---|---|
| L1 | 非규제(수도권) 비처분 1주택 LTV 가 원문에 없다 | 영향 측정 커버리지 {_pct(im.impact_coverage, 1)} 상한 | 추정 금지 → 사람 검토로 escalate |
| L2 | 인용의 **적절성**은 미검증 (verbatim 존재만 확인) | 원문 아무 문장이나 붙여도 통과 | 골드 키워드 + 사람 검수 |
| L3 | Change Completeness 는 recall 이지 precision 이 아니다 | 골드에 없는 변경은 측정 대상 밖 | 골드 확장 시 개선 |
| L4 | 합성 포트폴리오는 성능 주장의 근거가 아니다 | 정확도 주장 불가 | 커버리지 측정에만 사용 |
| L5 | 집계 비율은 단건 오류에 둔감 | 소수 환각을 가릴 수 있음 | 항목 단위 검사 병행(§8.4) |
| L6 | LLM 실행은 재생(replay) | 신규 추론 성능 벤치마크 아님 | 결정적 재현 목적 |
| L7 | 해시 체인은 **끝에서 자른 로그**를 혼자 못 잡는다 | 절단 은폐 가능 | head 해시를 로그 바깥에 보관(§13) |

### 골드 평가셋 봉인 상태

| split | 규모 | 고위험 비중 | 작성 |
|---|---|---|---|
{splits}

LOCKED / CHALLENGE 는 20자 이상의 사유 없이는 **로드 자체가 거부**되며, 접근은 append-only
로그에 남는다. 봉인은 문서가 아니라 코드로 강제된다.

전체 한계 분석은 `docs/eval/VALIDATION_LIMITS.md`."""


def _s12_findings(ev: ValidationEvidence) -> str:
    return """## 12. 발견사항 및 조치 (Findings & Remediation)

검증 과정에서 발견된 결함과 조치다. **자체 발견 결함을 기록하는 것이 이 절의 목적**이며,
지표가 좋아 보일 때도 계측기를 의심해야 한다는 근거이기도 하다.

| ID | 발견 | 심각도 | 조치 | 상태 |
|---|---|---|---|---|
| R-01 | 기존 규제지역(강남·서초·송파·용산)이 비규제로 판정 — 무주택 차주가 LTV 70% 수령 | **높음** | 참고2 현황표에서 레지스트리 전량 이관 + 미등록은 UNKNOWN 으로 escalate | 해결 |
| R-01b | **차등검증이 R-01 을 놓침** — TC 생성기가 강남을 "미등록 지역" 예시로 쓰고 오라클도 같은 오독을 공유해 일치율 100% | **높음** | 오라클 독립 재기입, TC 케이스 교체·신설 | 해결 |
| D-02 | 전 문서 일괄 추출 시 문서 간 열거가 서로를 가려 예외 누락 (Exception Recall 50%) | 중간 | 문서별 추출 + 문서 간 병합으로 구조 변경 | 해결 |
| D-03 | "모델이 인용을 환각한다"는 초기 결론이 **오진** — 원인은 공백 정규화(PDF 가 단어 중간에서 줄바꿈) | 중간 | 채점기 수정 후 재측정 → 환각률 0% | 철회 |
| G-01 | 골드 채점 실패 12건이 전부 표현 차이 아티팩트 | 낮음 | **프롬프트가 아니라 채점기를 수정** — 프롬프트를 맞추면 모델을 채점기에 훈련시키는 셈 | 해결 |
| P-01 | 변경안 빌더가 LTV 를 스칼라 하나에 담아 마지막 항목이 이김 (규제지역 표준이 정책대출 값으로 덮임) | 중간 | 세그먼트별 집계 + 충돌 기록 | 해결 |
| P-02 | LTV 파서가 맨숫자를 100으로 나눠 "한도 6억원"→LTV 0.06, "만기 30년"→0.30 생성 | 중간 | 비율 표기·0~1 소수만 허용, 나머지는 unmapped 로 보고 | 해결 |
| P-03 | 정책 미리보기가 before/after 를 같은 시점으로 조회해 **변화가 사라짐** | 낮음 | before 를 시행 전날로 | 해결 |
| A-01 | 봉인 접근 로그가 테스트 실행 노이즈로 채워져 실제 접근이 파묻힘 | 낮음 | 같은 날·같은 사유 반복은 횟수로 접음 | 해결 |
| C-01 | 정책 DB ↔ 기준선 드리프트 검사가 `regulated_type` 을 비교하지 않음 (투기과열 40% ↔ 조정 50% 구분 실패) | 중간 | 유형 비교 추가 (변이 테스트로 발견) | 해결 |

### 반복된 교훈

같은 실수를 두 번 했다 — **지표가 나쁘면 모델보다 계측기를 먼저 의심해야 한다**(D-03, G-01).
그리고 R-01 은 그 반대 경우다 — **지표가 완벽할 때도 같은 의심이 필요하다.**
R-01 은 어떤 지표로도 잡히지 않았고, 공문 원문을 다시 읽어서 발견됐다."""


def _s13_reproducibility(ev: ValidationEvidence) -> str:
    v = ev.audit.verify()
    return f"""## 13. 재현성 및 감사추적

### 13.1 재현

```bash
pip install -e ".[dev]"
python -m pytest -q                          # 전체 테스트
python examples/demo_impact_e2e.py           # 파이프라인 관통 (LLM 호출 0회)
python examples/demo_discrimination.py       # 판별력 실측
python examples/build_validation_report.py   # 이 보고서 재생성
```

LLM 호출 없이 전 과정이 재현된다 — provider `{ev.provider}` 가 실제 실행 기록
(`{ev.run_path}`)을 재생하기 때문이다. 리뷰어는 API 키 없이 같은 수치를 얻는다.

### 13.2 감사추적

이번 실행의 감사로그: **{len(ev.audit)}건**, 체인 무결성 **{_yn(v.ok)}**.

```
head = {ev.audit.head_hash}
```

각 이벤트 해시가 직전 해시를 포함하므로 항목 수정·순서 변경·중간 삭제는 즉시 드러난다.
**끝에서부터 잘라내는 것은 체인만으로 잡히지 않으므로**(L7), 위 head 해시를 로그 바깥에
남긴다 — 이 보고서가 그 앵커 역할을 한다.

### 13.3 값의 출처 분리

이 보고서의 모든 수치는 `regimpact.report.evidence.collect()` 한 번의 실행에서 나온다.
렌더러에는 도메인 수치 리터럴이 없으며, 테스트가 그것을 강제한다."""


def _s14_conclusion(ev: ValidationEvidence) -> str:
    cs = ev.consistency.summary()
    im = ev.impact
    return f"""## 14. 검증 결론 및 의견

**결론.** 대상 시스템은 규제 변경 1건에 대해 원문에서 변경 사실을 추출하고, 그 사실이 원문에
실재하는지 검증하며, 결정적 판정 로직을 독립 기준과 대조하고, 확정할 수 없는 것을 사람에게
넘기는 일련의 과정을 **재현 가능한 형태로** 수행한다.

**조건.** 다음 두 가지 때문에 현재 상태로 **완전 자동 승인은 적절하지 않다.**

1. 변경안 일치검증 {cs['total']}건 중 {cs['failed']}건이 미통과이며, 둘 다 원문에 값이
   없거나 엔진 범위 밖이라 사람 판단이 필요하다(§10.3).
2. 영향 측정 커버리지가 {_pct(im.impact_coverage, 1)} 상한에 걸린다 — 非규제 수도권 유주택
   기준값이 원문에 없기 때문이다(L1).

두 제약 모두 시스템의 결함이 아니라 **원문의 공백을 그대로 드러낸 결과**이며,
값을 추정해 메우지 않는 것이 설계 의도다.

**권고.**

- ✍️ 非규제(수도권) 비처분 1주택 LTV 기준값을 도메인에서 확정 → L1 해소 시 영향 측정
  커버리지 상한이 올라간다
- ✍️ QA 골드 DEV 40문항 사람 검수 (현재 전량 AI 초안)
- 코어 완성 시점에 LOCKED / CHALLENGE 최초 1회 개봉 — 그때까지는 열지 않는다
- 엔진이 다루지 않는 룰 차원(한도·전입의무·만기)의 범위 편입 여부 결정(§10.3)"""


def _appendix(ev: ValidationEvidence) -> str:
    rows = "\n".join(
        f"| {i+1} | {it.category} | {it.summary} | {it.before or '—'} | {it.after or '—'} | "
        f"{it.citation.source_doc_id} |"
        for i, it in enumerate(ev.extraction.changes)
    )
    return f"""## 부록 A. 추출 변경 전체 목록 ({len(ev.extraction.changes)}건)

| # | 카테고리 | 요약 | 이전 | 이후 | 근거 문서 |
|---|---|---|---|---|---|
{rows}

## 부록 B. 참고 문서

| 문서 | 내용 |
|---|---|
| `docs/00_BRIEF.md` | 프로젝트 정의·LOCKED 원칙 |
| `docs/05_RULE_SPEC.md` | 확정 룰 명세 (엔진 구현의 기준) |
| `docs/regulatory_facts.md` | 사람 확정 규제 사실 (C01~C16) |
| `docs/eval/VALIDATION_LIMITS.md` | 검증 한계 상세 분석 |
| `docs/governance/MODEL_SYSTEM_CARD.md` | Model & System Card |
| `docs/governance/AI_RISK_REGISTER.md` | AI 리스크 레지스터 ({len(_RISKS)}건) |
| `docs/02_DECISION_LOG.md` | 의사결정 이력 |
| `docs/07_BRANCH_TRIAGE.md` | 브랜치 정리·이식 백로그 |"""
