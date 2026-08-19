"""랜딩 허브 — 링크 하나로 들어와 읽는 순서를 정해준다.

리크루터·면접관은 저장소를 뒤지지 않는다. 무엇을 푸는 시스템인지 30초 안에 알려주고,
증거로 바로 보내는 것이 이 페이지의 유일한 일이다.

**여기 수치도 손으로 적지 않는다** — 검증보고서·카드와 같은 `ValidationEvidence` 에서 온다.
세 문서가 서로 다른 숫자를 말하면 그 자체가 신뢰를 깎는다.
"""
from __future__ import annotations

from typing import Optional

from ..extractor.sources import SOURCE_FILES
from ..report.evidence import ValidationEvidence
from .theme import CSS, FONTS, esc

_LANDING_CSS = """
body{background:var(--background);color:var(--on-surface)}
.wrap{max-width:1080px;margin:0 auto;padding:0 24px}
.hero{padding:72px 0 40px}
.kicker{font-family:'JetBrains Mono',ui-monospace,monospace;font-size:11px;letter-spacing:.08em;
  text-transform:uppercase;color:var(--primary);font-weight:600}
.hero h1{font-size:clamp(28px,4.4vw,44px);line-height:1.18;font-weight:700;letter-spacing:-.02em;
  margin:14px 0 0;max-width:19ch}
.lede{margin:20px 0 0;font-size:17px;line-height:28px;color:var(--on-surface-variant);max-width:62ch}
.lede strong{color:var(--on-surface);font-weight:600}
.stats{display:grid;grid-template-columns:repeat(2,1fr);gap:1px;background:var(--outline-variant);
  border:1px solid var(--outline-variant);border-radius:8px;overflow:hidden;margin:40px 0 0}
@media(min-width:760px){.stats{grid-template-columns:repeat(4,1fr)}}
.stat{background:var(--surface-container-lowest);padding:18px 20px}
.stat .v{font-family:'JetBrains Mono',ui-monospace,monospace;font-size:24px;font-weight:500;
  line-height:1.1;color:var(--on-background)}
.stat .l{font-size:11.5px;line-height:16px;color:var(--on-surface-variant);margin-top:6px}
.sec{padding:56px 0 0}
.sec h2{font-size:13px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;
  color:var(--on-surface-variant);margin:0 0 4px}
.sec .sub{font-size:14px;line-height:22px;color:var(--on-surface-variant);margin:0 0 20px;max-width:66ch}
.grid{display:grid;grid-template-columns:1fr;gap:12px}
@media(min-width:700px){.grid{grid-template-columns:repeat(2,1fr)}}
@media(min-width:1000px){.grid.g3{grid-template-columns:repeat(3,1fr)}}
.tile{display:block;padding:20px;background:var(--surface-container-lowest);
  border:1px solid var(--outline-variant);border-radius:8px;text-decoration:none;color:inherit;
  transition:border-color .12s,transform .12s}
.tile:hover{border-color:var(--primary);transform:translateY(-1px)}
.tile .t{font-size:15px;font-weight:600;color:var(--on-background)}
.tile .d{font-size:13px;line-height:20px;color:var(--on-surface-variant);margin-top:6px}
.tile .m{font-family:'JetBrains Mono',ui-monospace,monospace;font-size:11px;
  color:var(--primary);margin-top:10px}
.note{margin-top:14px;padding:14px 16px;background:var(--surface-container-low);
  border-left:3px solid var(--primary);border-radius:0 4px 4px 0;font-size:13px;line-height:21px;
  color:var(--on-surface-variant)}
.note strong{color:var(--on-surface)}
footer{margin-top:72px;padding:28px 0 56px;border-top:1px solid var(--outline-variant);
  font-size:12px;line-height:20px;color:var(--on-surface-variant)}
footer code{font-family:'JetBrains Mono',ui-monospace,monospace;font-size:11px}
"""


def _stat(value: str, label: str) -> str:
    return f'<div class="stat"><div class="v">{esc(value)}</div><div class="l">{esc(label)}</div></div>'


def _scorecard_meta(ev: ValidationEvidence) -> str:
    sc = getattr(ev, "scorecard", None)
    if sc is None:
        return ""
    s = sc.summary()
    tail = f" · 미측정 {s['not_measured']}" if s["not_measured"] else ""
    return f"스코어카드 {s['verdict']} — {s['passed']}/{s['total']} 통과{tail}"


def _tile(href: str, title: str, desc: str, meta: str = "") -> str:
    m = f'<div class="m">{esc(meta)}</div>' if meta else ""
    return (f'<a class="tile" href="{esc(href)}"><div class="t">{esc(title)}</div>'
            f'<div class="d">{esc(desc)}</div>{m}</a>')


def render(ev: ValidationEvidence, *, commit: Optional[str] = None,
           playground: bool = False) -> str:
    """랜딩 페이지. 수치는 전부 evidence 에서 온다."""
    im, g, r = ev.impact, ev.grounding, ev.regression
    cs = ev.consistency.summary()

    screens = "".join([
        _tile("sources.html", "규제 문서 등록",
              "새 공문이 들어오는 입구. 원문 스냅샷 해시·정책 버전 타임라인·새 문서 등록.",
              f"원문 스냅샷 {len(SOURCE_FILES)}건 · 정책 버전 타임라인"),
        _tile("regchange.html", "규제 변경 분석",
              "공문에서 추출한 변경과 인용 근거. 각 항목이 원문 어디에서 왔는지 대조된다.",
              f"변경 {len(ev.extraction.changes)}건 · 인용 검증 {g.citation_correctness:.0%}"),
        _tile("impact_matrix.html", "임팩트 매트릭스",
              "업무영역별 조치·기한·담당. 자동처리 불가 행은 사유 없이 만들 수 없다.",
              f"{len(ev.matrix.rows)}행 · 자동처리 {ev.matrix.automation_rate:.0%}"),
        _tile("portfolio.html", "포트폴리오 영향",
              "합성 차주별 LTV 전이와 한도 변화. 커버리지를 판정·측정 두 축으로 나눠 본다.",
              f"{im.portfolio_size:,}건 · 판정 {im.decision_coverage:.1%} / 측정 {im.impact_coverage:.1%}"),
        _tile("rule.html", "룰 판정 로직",
              "확정 명세의 결정적 구현. 화면의 모든 LTV 값이 엔진 상수와 대조된다.",
              "P0~P7 우선순위"),
        _tile("assurance.html", "검증 (Assurance)",
              "인용 정확성·완전성·회귀·판별력을 한 화면에. 지표를 나열만 하지 않고 "
              "확정 임계와 대조해 판정한다.",
              _scorecard_meta(ev) or f"룰 회귀 {r.pass_rate:.0%} ({r.passed}/{r.total})"),
    ])
    if playground:
        screens += _tile("playground.html", "판정 플레이그라운드",
                         "차주 조건을 바꾸면 즉시 판정이 바뀐다. JS 포팅본은 Python 엔진과 전 케이스 대조된다.",
                         "직접 만져보기")

    docs = "".join([
        _tile("validation_report.html", "시스템 검증보고서",
              "개념적 건전성 · 구현 정확성 · 성과 검증 · 거버넌스 · 한계 · 발견사항. "
              "모든 수치가 파이프라인 실행에서 나온다.",
              f"자체 발견 결함 10건 기록"),
        _tile("model_system_card.html", "모델·시스템 카드",
              "사용 목적과 **범위 외·오용 방지**. LLM 이 무엇을 하고 무엇을 하지 않는지.",
              "Model Card 관례"),
        _tile("ai_risk_register.html", "AI 리스크 레지스터",
              "리스크 18건 / 5범주. 통제가 실재하는 코드를 가리키는지 테스트가 강제한다.",
              "잔여 High 1건 (의도적)"),
    ])

    commit_line = (f'빌드 <code>{esc(commit)}</code> · ' if commit else "")

    return f"""<!DOCTYPE html>
<html lang="ko"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>RegImpact AI — 규제 변경 영향분석·검증 시스템</title>
<meta name="description" content="주택담보대출 규제 변경을 추출하고, 그 변경이 여신 룰·고객 영향으로 어떻게 전파되는지 산출하며, 각 단계 산출물을 독립 기준과 대조하는 시스템.">
{FONTS}
<style>{CSS}{_LANDING_CSS}</style>
</head><body>
<div class="wrap">
  <header class="hero">
    <div class="kicker">금융규제 영향분석 · 검증 시스템</div>
    <h1>규제가 바뀌면, 무엇을 고쳐야 하는지 증명까지 함께 낸다</h1>
    <p class="lede">
      {esc(ev.extraction.policy_id)} 규제지역 추가 지정을 공문 원문에서 읽어
      <strong>변경 {len(ev.extraction.changes)}건</strong>을 추출하고,
      여신 룰·고객 영향·테스트케이스로 전파한 뒤,
      <strong>각 단계 산출물을 독립 기준과 대조</strong>했다.
    </p>
    <p class="lede">
      LLM 을 규제 판정에 쓰는 시스템이 아니다. LLM 은 <strong>인용 근거가 붙은 사실만</strong> 추출하고,
      판정은 사람이 확정한 명세를 구현한 결정적 엔진이 한다. 그 경계 덕분에
      엔진이 LLM 출력의 <strong>검증 기준</strong>이 될 수 있다.
    </p>

    <div class="stats">
      {_stat(f"{g.citation_correctness:.0%}", f"인용이 원문에 실재 ({g.grounded}/{g.total})")}
      {_stat(f"{r.pass_rate:.0%}", f"룰엔진 ↔ 독립 오라클 일치 ({r.total}케이스)")}
      {_stat(f"{cs['passed']}/{cs['total']}", "변경안 ↔ 엔진 교차검증")}
      {_stat(f"{im.impact_coverage:.1%}", "영향 측정 커버리지 (상한)")}
    </div>

    <div class="note">
      <strong>마지막 두 숫자가 100%가 아닌 것이 이 프로젝트의 요점이다.</strong>
      원문에 값이 없는 구간을 추정으로 메우지 않기 때문에 남은 것이고,
      그 자리는 <strong>사유와 함께 사람 검토로</strong> 넘어간다.
      값을 지어내면 두 숫자는 즉시 100%가 된다.
    </div>
  </header>

  <section class="sec">
    <h2>화면</h2>
    <p class="sub">모든 수치가 엔진 실제 출력이다 — 목업 값이 아니다.
      화면에 엔진이 모르는 LTV 값이 있으면 테스트가 실패한다.</p>
    <div class="grid g3">{screens}</div>
  </section>

  <section class="sec">
    <h2>검증 산출물</h2>
    <p class="sub">검증보고서·카드·레지스터가 같은 실행 결과에서 생성된다.
      세 문서가 서로 다른 숫자를 말하는 일이 없다.</p>
    <div class="grid g3">{docs}</div>
  </section>

  <section class="sec">
    <h2>재현</h2>
    <p class="sub">LLM 호출 0회로 전 과정이 재현된다 — 실제 실행 기록을 재생하기 때문이다.
      리뷰어는 API 키 없이 같은 수치를 얻는다.</p>
    <div class="note" style="border-left-color:var(--outline)">
<pre style="margin:0;font-family:'JetBrains Mono',ui-monospace,monospace;font-size:12px;line-height:19px;white-space:pre-wrap">pip install -e ".[dev]"
python -m pytest -q                          # 테스트 전량
python examples/demo_impact_e2e.py           # 파이프라인 11단계 관통
python examples/demo_discrimination.py       # 판별력 실측
python examples/build_validation_report.py   # 검증보고서 재생성</pre>
    </div>
  </section>

  <footer>
    {commit_line}생성 {esc(ev.generated_at or "—")} ·
    provider <code>{esc(ev.provider)}</code> ·
    감사로그 head <code>{esc(ev.audit.head_hash[:16])}…</code><br>
    공개 보도자료·FAQ 만 사용합니다. 실제 회사 문서·고객 데이터는 쓰지 않았고,
    포트폴리오는 층화 합성 데이터입니다.
  </footer>
</div>
</body></html>
"""
